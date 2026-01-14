import os
import tempfile
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, Optional
from contextlib import asynccontextmanager

import modal
import torch
import torchaudio
import librosa
import soundfile as sf
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

# -----------------------------------------------------------------------------
# Modal Configuration
# -----------------------------------------------------------------------------

image = (
    modal.Image.debian_slim()
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(
        "fastapi==0.109.0",
        "uvicorn[standard]==0.27.0",
        "python-multipart==0.0.6",
        "librosa==0.10.1",
        "soundfile==0.12.1",
        "numpy==1.24.3",
        "torch==2.1.0",
        "torchaudio==2.1.0",
        # "demucs==4.0.0", # Uncomment when ready for real model
    )
)

app = modal.App("boss-effector-gpu")

# -----------------------------------------------------------------------------
# Application State & Constants
# -----------------------------------------------------------------------------

# Global state for models
ml_models: Dict[str, Any] = {"demucs": None, "effector": None}

# GPU Setup
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Temporary Directory (Use /tmp for container compatibility)
TEMP_DIR = Path(tempfile.gettempdir()) / "boss_effector"

# -----------------------------------------------------------------------------
# Model Loading & Utilities
# -----------------------------------------------------------------------------


def load_demucs_model():
    """Demucs 모델 로드 (음원 분리용)"""
    try:
        # from demucs.pretrained import get_model
        # model = get_model('htdemucs')
        # model.to(DEVICE)
        # return model
        print(f"🚀 Using device: {DEVICE}")
        return None  # 현재는 시뮬레이션
    except Exception as e:
        print(f"⚠️  Demucs 모델 로드 실패: {e}")
        return None


def load_effector_model():
    """이펙터 예측 모델 로드"""
    try:
        # model = torch.load('models/effector_classifier.pth')
        # model.to(DEVICE)
        # model.eval()
        # return model
        return None  # 현재는 시뮬레이션
    except Exception as e:
        print(f"⚠️  이펙터 모델 로드 실패: {e}")
        return None


def remove_file(path: str):
    """파일 삭제 유틸리티 (백그라운드 작업용)"""
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except Exception as e:
        print(f"⚠️ 파일 삭제 실패 ({path}): {e}")


async def separate_guitar_with_demucs(audio_path: str, output_path: str) -> None:
    """Demucs를 사용하여 기타 트랙 분리"""
    model = ml_models.get("demucs")

    if model is not None:
        # 실제 Demucs 사용 코드
        # from demucs.apply import apply_model
        # waveform, sr = torchaudio.load(audio_path)
        # sources = apply_model(model, waveform.to(DEVICE))
        # guitar = sources[0, 2]  # 기타 채널
        # torchaudio.save(output_path, guitar.cpu(), sr)
        pass

    # 시뮬레이션: 원본을 그대로 저장 및 간단한 처리
    y, sr = librosa.load(audio_path, sr=22050)
    guitar_enhanced = y * 0.8  # 임시 처리
    sf.write(output_path, guitar_enhanced, sr)


async def predict_effector_with_model(
    sample_path: str, extracted_path: str
) -> Dict[str, Any]:
    """딥러닝 모델로 이펙터 예측"""
    model = ml_models.get("effector")

    if model is not None:
        # 실제 모델 사용 코드
        pass

    # 시뮬레이션: 오디오 특성 분석
    y_sample, sr_sample = librosa.load(sample_path, sr=22050)
    y_extracted, sr_extracted = librosa.load(extracted_path, sr=22050)

    # 간단한 오디오 분석
    rms_sample = np.sqrt(np.mean(y_sample**2))
    rms_extracted = np.sqrt(np.mean(y_extracted**2))

    spectral_centroid_sample = np.mean(
        librosa.feature.spectral_centroid(y=y_sample, sr=sr_sample)
    )
    spectral_centroid_extracted = np.mean(
        librosa.feature.spectral_centroid(y=y_extracted, sr=sr_extracted)
    )

    # 시뮬레이션 결과
    effector_types = ["Overdrive", "Distortion", "Fuzz", "Chorus", "Delay", "Reverb"]
    effector_type = np.random.choice(effector_types)

    parameters = {
        "Gain": f"{np.random.uniform(5.0, 9.0):.1f}",
        "Tone": f"{np.random.uniform(4.0, 8.0):.1f}",
        "Level": f"{np.random.uniform(6.0, 9.0):.1f}",
        "Drive": np.random.choice(["Low", "Medium", "High"]),
        "EQ_Bass": f"{np.random.uniform(-3, 3):+.1f}dB",
        "EQ_Mid": f"{np.random.uniform(-3, 3):+.1f}dB",
        "EQ_Treble": f"{np.random.uniform(-3, 3):+.1f}dB",
    }

    return {
        "effector_type": effector_type,
        "parameters": parameters,
        "confidence": float(np.random.uniform(0.75, 0.95)),
        "analysis": {
            "sample_rms": float(rms_sample),
            "extracted_rms": float(rms_extracted),
            "spectral_centroid_diff": float(
                abs(spectral_centroid_sample - spectral_centroid_extracted)
            ),
        },
    }


# -----------------------------------------------------------------------------
# FastAPI Setup
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Manager
    - 앱 시작 시: 모델 로드 및 임시 디렉토리 생성
    - 앱 종료 시: 정리
    """
    # Startup
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ml_models["demucs"] = load_demucs_model()
    ml_models["effector"] = load_effector_model()
    print("✅ Models loaded and initialized.")

    yield

    # Shutdown
    ml_models.clear()
    print("🛑 Shutting down and clearing models.")


web_app = FastAPI(title="Boss Effector GPU Server", lifespan=lifespan)


# GPU 서버 상태
@web_app.get("/")
async def root():
    return {
        "service": "Boss Effector GPU Server",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0)
        if torch.cuda.is_available()
        else "N/A",
        "models_loaded": {
            "demucs": ml_models["demucs"] is not None,
            "effector": ml_models["effector"] is not None,
        },
    }


# 헬스체크 엔드포인트
@web_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
    }


# 기타소리 추출 엔드포인트
@web_app.post("/extract-guitar")
async def extract_guitar(
    background_tasks: BackgroundTasks, audio: UploadFile = File(...)
):
    input_path = None
    output_path = None

    try:
        # 임시 파일로 저장
        input_path = TEMP_DIR / f"input_{audio.filename}"
        output_path = TEMP_DIR / f"guitar_{audio.filename}"

        content = await audio.read()
        with open(input_path, "wb") as f:
            f.write(content)

        # GPU로 기타 추출
        await separate_guitar_with_demucs(str(input_path), str(output_path))

        # 전송 후 파일 삭제 예약
        background_tasks.add_task(remove_file, str(output_path))

        # 추출된 기타 파일 반환
        return FileResponse(
            output_path, media_type="audio/wav", filename=f"guitar_{audio.filename}"
        )

    except Exception as e:
        if output_path and output_path.exists():
            output_path.unlink()
        raise HTTPException(status_code=500, detail=f"기타 추출 실패: {str(e)}")

    finally:
        if input_path and input_path.exists():
            try:
                input_path.unlink()
            except:
                pass


# 기타 이펙터 분석 엔드포인트
@web_app.post("/predict-effector")
async def predict_effector(
    guitar_sample: UploadFile = File(...), extracted_guitar: UploadFile = File(...)
):
    sample_path = None
    extracted_path = None

    try:
        sample_path = TEMP_DIR / f"sample_{guitar_sample.filename}"
        extracted_path = TEMP_DIR / f"extracted_{extracted_guitar.filename}"

        with open(sample_path, "wb") as f:
            f.write(await guitar_sample.read())

        with open(extracted_path, "wb") as f:
            f.write(await extracted_guitar.read())

        # GPU로 이펙터 예측
        result = await predict_effector_with_model(
            str(sample_path), str(extracted_path)
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이펙터 예측 실패: {str(e)}")

    finally:
        for path in [sample_path, extracted_path]:
            if path and path.exists():
                try:
                    path.unlink()
                except:
                    pass


# -----------------------------------------------------------------------------
# Modal Entrypoint
# -----------------------------------------------------------------------------


@app.function(image=image, gpu="T4", timeout=600)
@modal.asgi_app()
def fastapi_app():
    return web_app


if __name__ == "__main__":
    import uvicorn

    # 로컬 테스트용
    uvicorn.run(web_app, host="0.0.0.0", port=8001)
