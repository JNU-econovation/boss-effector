from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import torch
import torchaudio
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path
import tempfile
import os
from typing import Dict, Any

app = FastAPI(title="Boss Effector GPU Server")

# GPU 설정
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🚀 Using device: {DEVICE}")

# 임시 파일 저장
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)


def load_demucs_model():
    """
    Demucs 모델 로드 (음원 분리용)
    실제 구현시 사용
    """
    try:
        # from demucs.pretrained import get_model
        # model = get_model('htdemucs')
        # model.to(DEVICE)
        # return model
        return None  # 현재는 시뮬레이션
    except Exception as e:
        print(f"⚠️  Demucs 모델 로드 실패: {e}")
        return None


def load_effector_model():
    """
    이펙터 예측 모델 로드
    실제 구현시 커스텀 모델 사용
    """
    try:
        # model = torch.load('models/effector_classifier.pth')
        # model.to(DEVICE)
        # model.eval()
        # return model
        return None  # 현재는 시뮬레이션
    except Exception as e:
        print(f"⚠️  이펙터 모델 로드 실패: {e}")
        return None


# 모델 로드
DEMUCS_MODEL = load_demucs_model()
EFFECTOR_MODEL = load_effector_model()


async def separate_guitar_with_demucs(audio_path: str, output_path: str) -> None:
    """
    Demucs를 사용하여 기타 트랙 분리
    """
    if DEMUCS_MODEL is not None:
        # 실제 Demucs 사용 코드
        # from demucs.apply import apply_model
        # waveform, sr = torchaudio.load(audio_path)
        # sources = apply_model(DEMUCS_MODEL, waveform.to(DEVICE))
        # guitar = sources[0, 2]  # 기타 채널
        # torchaudio.save(output_path, guitar.cpu(), sr)
        pass
    
    # 시뮬레이션: 원본을 그대로 저장
    y, sr = librosa.load(audio_path, sr=22050)
    
    # 실제로는 AI 모델이 기타만 추출
    # 여기서는 약간의 필터링으로 시뮬레이션
    guitar_enhanced = y * 0.8  # 임시 처리
    
    sf.write(output_path, guitar_enhanced, sr)


async def predict_effector_with_model(sample_path: str, extracted_path: str) -> Dict[str, Any]:
    """
    딥러닝 모델로 이펙터 예측
    """
    if EFFECTOR_MODEL is not None:
        # 실제 모델 사용 코드
        # sample, sr1 = torchaudio.load(sample_path)
        # extracted, sr2 = torchaudio.load(extracted_path)
        # 
        # # 특성 추출
        # features = extract_audio_features(sample, extracted)
        # features_tensor = torch.tensor(features).to(DEVICE)
        # 
        # # 모델 추론
        # with torch.no_grad():
        #     output = EFFECTOR_MODEL(features_tensor)
        #     effector_type = decode_effector_type(output)
        #     parameters = decode_parameters(output)
        # 
        # return {
        #     "effector_type": effector_type,
        #     "parameters": parameters,
        #     "confidence": float(output.max())
        # }
        pass
    
    # 시뮬레이션: 오디오 특성 분석
    y_sample, sr_sample = librosa.load(sample_path, sr=22050)
    y_extracted, sr_extracted = librosa.load(extracted_path, sr=22050)
    
    # 간단한 오디오 분석
    rms_sample = np.sqrt(np.mean(y_sample**2))
    rms_extracted = np.sqrt(np.mean(y_extracted**2))
    
    # 스펙트럼 분석
    spectral_centroid_sample = np.mean(librosa.feature.spectral_centroid(y=y_sample, sr=sr_sample))
    spectral_centroid_extracted = np.mean(librosa.feature.spectral_centroid(y=y_extracted, sr=sr_extracted))
    
    # 시뮬레이션 결과 (실제로는 모델 출력)
    effector_types = ["Overdrive", "Distortion", "Fuzz", "Chorus", "Delay", "Reverb"]
    effector_type = np.random.choice(effector_types)
    
    parameters = {
        "Gain": f"{np.random.uniform(5.0, 9.0):.1f}",
        "Tone": f"{np.random.uniform(4.0, 8.0):.1f}",
        "Level": f"{np.random.uniform(6.0, 9.0):.1f}",
        "Drive": np.random.choice(["Low", "Medium", "High"]),
        "EQ_Bass": f"{np.random.uniform(-3, 3):+.1f}dB",
        "EQ_Mid": f"{np.random.uniform(-3, 3):+.1f}dB",
        "EQ_Treble": f"{np.random.uniform(-3, 3):+.1f}dB"
    }
    
    return {
        "effector_type": effector_type,
        "parameters": parameters,
        "confidence": float(np.random.uniform(0.75, 0.95)),
        "analysis": {
            "sample_rms": float(rms_sample),
            "extracted_rms": float(rms_extracted),
            "spectral_centroid_diff": float(abs(spectral_centroid_sample - spectral_centroid_extracted))
        }
    }


@app.get("/")
async def root():
    """GPU 서버 상태"""
    return {
        "service": "Boss Effector GPU Server",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "models_loaded": {
            "demucs": DEMUCS_MODEL is not None,
            "effector": EFFECTOR_MODEL is not None
        }
    }


@app.get("/health")
async def health_check():
    """헬스체크"""
    return {
        "status": "healthy",
        "device": DEVICE,
        "gpu_available": torch.cuda.is_available()
    }


@app.post("/extract-guitar")
async def extract_guitar(audio: UploadFile = File(...)):
    """
    원곡에서 기타 소리 추출
    GPU를 사용하여 소스 분리
    """
    input_path = None
    output_path = None
    
    try:
        # 임시 파일로 저장
        input_path = TEMP_DIR / f"input_{audio.filename}"
        output_path = TEMP_DIR / f"guitar_{audio.filename}"
        
        with open(input_path, "wb") as f:
            f.write(await audio.read())
        
        # GPU로 기타 추출
        await separate_guitar_with_demucs(str(input_path), str(output_path))
        
        # 추출된 기타 파일 반환
        return FileResponse(
            output_path,
            media_type="audio/wav",
            filename=f"guitar_{audio.filename}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기타 추출 실패: {str(e)}")
    
    finally:
        # 입력 파일 정리 (출력은 전송 후 정리)
        if input_path and input_path.exists():
            try:
                input_path.unlink()
            except:
                pass


@app.post("/predict-effector")
async def predict_effector(
    guitar_sample: UploadFile = File(...),
    extracted_guitar: UploadFile = File(...)
):
    """
    이펙터 종류와 파라미터 예측
    GPU를 사용하여 딥러닝 모델 추론
    """
    sample_path = None
    extracted_path = None
    
    try:
        # 임시 파일로 저장
        sample_path = TEMP_DIR / f"sample_{guitar_sample.filename}"
        extracted_path = TEMP_DIR / f"extracted_{extracted_guitar.filename}"
        
        with open(sample_path, "wb") as f:
            f.write(await guitar_sample.read())
        
        with open(extracted_path, "wb") as f:
            f.write(await extracted_guitar.read())
        
        # GPU로 이펙터 예측
        result = await predict_effector_with_model(str(sample_path), str(extracted_path))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이펙터 예측 실패: {str(e)}")
    
    finally:
        # 임시 파일 정리
        for path in [sample_path, extracted_path]:
            if path and path.exists():
                try:
                    path.unlink()
                except:
                    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)