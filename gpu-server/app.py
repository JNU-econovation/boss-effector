import os
import shutil
import subprocess
import tempfile
import torch
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

import modal
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

# -----------------------------------------------------------------------------
# 1. Image Definition & Dependencies
# -----------------------------------------------------------------------------

MODEL_URL = "https://zenodo.org/records/13694558/files/ev-pre-aug.ckpt?download=1"

# 이미지 정의
image = (
    modal.Image.debian_slim()
    .apt_install("git", "wget", "ffmpeg", "libsndfile1", "aria2")
    .pip_install(
        # Web Server
        "fastapi==0.109.0",
        "uvicorn[standard]==0.27.0",
        "python-multipart==0.0.6",
        # Audio & ML (Core)
        "librosa==0.10.1",
        "soundfile==0.12.1",
        "numpy==1.24.3",
        "torch==2.1.0",
        "torchaudio==2.1.0",
        "pandas==2.1.1",
        "scipy==1.11.3",
        "scikit-learn==1.3.1",
        # Query-Bandit & Model Dependencies
        "pytorch_lightning==2.1.0",
        "hydra-core==1.3.2",
        "omegaconf==2.3.0",
        "jsonargparse[signatures]>=4.27.7",
        "torch-audiomentations==0.11.1",
        "einops==0.7.0",
        "wandb==0.16.0",
        "hear21passt",
        "fire==0.5.0",
    )
    # Repository Setup
    .run_commands(
        "git clone https://github.com/kwatcharasupat/query-bandit /app/query-bandit"
    )
    # Weights Setup (Repository 루트에 바로 다운로드)
    .run_commands(
        f"aria2c -x 16 -s 16 -k 1M -o ev-pre-aug.ckpt -d /app/query-bandit '{MODEL_URL}'",
    )
)

app = modal.App("boss-effector-gpu")

# -----------------------------------------------------------------------------
# Application Constants
# -----------------------------------------------------------------------------

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# -----------------------------------------------------------------------------
# 2. Model Logic (Class-based for Statefulness)
# -----------------------------------------------------------------------------


@app.cls(image=image, gpu="A10G", timeout=600, scaledown_window=60)
class AudioInference:
    """
    기타 추출 및 이펙터 예측을 담당하는 추론 클래스입니다.
    클래스로 구조화하여 향후 모델 로드 상태를 유지할 수 있습니다.
    """

    def __enter__(self):
        # 컨테이너 시작 시 실행 (모델 로드 등)
        # 현재 Query-Bandit은 CLI 기반이라 별도 로드가 없지만,
        # 나중에 Effector 예측 모델을 여기서 self.model = load_model() 형태로 로드하면 매우 빠릅니다.
        self.tmp_base = Path(tempfile.gettempdir()) / "boss_effector"
        self.tmp_base.mkdir(parents=True, exist_ok=True)
        print("✅ AudioInference initialized.")

    @modal.method()
    def run_query_bandit(
        self, input_bytes: bytes, query_bytes: bytes, filename_prefix: str
    ) -> str:
        """Query-Bandit CLI 실행"""

        # 작업별 격리된 디렉토리 생성
        job_id = os.urandom(4).hex()
        job_dir = self.tmp_base / f"job_{job_id}"
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            input_path = job_dir / f"input_{filename_prefix}"
            query_path = job_dir / f"query_{filename_prefix}"
            output_dir = job_dir / "output"
            output_dir.mkdir(exist_ok=True)

            # 출력 파일 경로 명시 (디렉토리 + 파일명)
            output_file_path = output_dir / "extracted.wav"

            # 바이트 데이터 저장
            with open(input_path, "wb") as f:
                f.write(input_bytes)
            with open(query_path, "wb") as f:
                f.write(query_bytes)

            # CLI 실행 (ckpt_path를 레포지토리 루트로 변경)
            cmd = [
                "python",
                "train.py",
                "inference_byoq",
                "--ckpt_path",
                "ev-pre-aug.ckpt",  # train.py와 같은 위치에 있으므로 파일명만 써도 무방
                "--input_path",
                str(input_path),
                "--query_path",
                str(query_path),
                "--output_path",
                str(output_file_path),
                "--batch_size",
                "12",
                "--use_cuda",
                "true",
            ]

            print(f"🚀 Executing Query-Bandit for {filename_prefix}...")

            # subprocess 실행 (cwd는 레포지토리 루트)
            env = os.environ.copy()
            env["CONFIG_ROOT"] = "./config"

            result = subprocess.run(
                cmd, cwd="/app/query-bandit", env=env, capture_output=True, text=True
            )

            if result.returncode != 0:
                print(f"❌ Error: {result.stderr}")
                raise Exception(f"Model Inference Failed: {result.stderr}")

            # 결과 파일 확인
            if not output_file_path.exists():
                files = list(output_dir.glob("*.wav"))
                if files:
                    return str(files[0])
                raise Exception(f"Output file not found at {output_file_path}")

            return str(output_file_path)

        except Exception as e:
            # 에러 발생 시 정리하고 재발생
            shutil.rmtree(job_dir)
            raise e

    @modal.method()
    def predict_effector(
        self, sample_bytes: bytes, extracted_bytes: bytes
    ) -> Dict[str, Any]:
        """
        [확장 포인트] 이펙터 파라미터 예측
        향후 실제 PyTorch/TensorFlow 모델을 self.model로 로드하여 여기서 inference 수행
        """
        import numpy as np

        # (시뮬레이션 로직 - 실제 구현 시 교체)
        effector_types = [
            "Overdrive",
            "Distortion",
            "Fuzz",
            "Chorus",
            "Delay",
            "Reverb",
        ]

        return {
            "effector_type": str(np.random.choice(effector_types)),
            "parameters": {
                "Gain": f"{np.random.uniform(1, 10):.1f}",
                "Tone": f"{np.random.uniform(1, 10):.1f}",
                "Level": f"{np.random.uniform(1, 10):.1f}",
            },
            "confidence": 0.95,
        }


# -----------------------------------------------------------------------------
# 3. FastAPI Server
# -----------------------------------------------------------------------------

web_app = FastAPI(title="Boss Effector GPU Server")

# Modal Class 인스턴스 (컨테이너 내에서 재사용됨)
inference_service = AudioInference()


# 파일/디렉토리 삭제 (상위 디렉토리인 job_dir 삭제)
def cleanup_file(path: str):
    try:
        p = Path(path)
        # job_xxx 폴더를 찾아서 삭제
        if "job_" in p.parent.name:
            shutil.rmtree(p.parent)
        elif p.exists():
            p.unlink()
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")


# GPU 서버 상태
@web_app.get("/")
async def root():
    # 모델 가중치 파일 확인 (Repository 루트)
    weights_path = Path("/app/query-bandit/ev-pre-aug.ckpt")
    weights_loaded = weights_path.exists() and weights_path.stat().st_size > 0

    return {
        "service": "Boss Effector GPU Server",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "N/A",
        "status": {
            "model_weights_loaded": weights_loaded,
            "query_bandit_ready": weights_loaded,  # CLI 기반이므로 가중치만 있으면 준비 완료
        },
    }


@web_app.post("/extract-guitar")
async def extract_guitar_endpoint(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),  # 원곡
    query: UploadFile = File(...),  # 기타 샘플 (Query)
):
    try:
        # 1. 데이터 읽기
        audio_bytes = await audio.read()
        query_bytes = await query.read()

        # 2. Modal Class 메서드 호출 (로컬 컨테이너 내 직접 호출)
        # output_path는 컨테이너 내부의 임시 경로임
        output_path = inference_service.run_query_bandit.local(
            audio_bytes, query_bytes, audio.filename
        )

        # 3. 결과 반환 및 정리 예약
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=f"extracted_{audio.filename}.wav",
            background=background_tasks.add_task(cleanup_file, output_path),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@web_app.post("/predict-effector")
async def predict_effector_endpoint(
    guitar_sample: UploadFile = File(...), extracted_guitar: UploadFile = File(...)
):
    try:
        sample_bytes = await guitar_sample.read()
        extracted_bytes = await extracted_guitar.read()

        result = inference_service.predict_effector.local(sample_bytes, extracted_bytes)
        return JSONResponse(content=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# 4. Entrypoint
# -----------------------------------------------------------------------------


@app.function(image=image, gpu="A10G", timeout=600)
@modal.asgi_app()
def fastapi_app():
    return web_app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(web_app, host="0.0.0.0", port=8001)
