from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
from pathlib import Path
import librosa
import soundfile as sf
import numpy as np
from typing import Dict, Any
import tempfile
import httpx
import aiofiles

app = FastAPI(title="Boss Effector API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 환경 변수 설정
GPU_SERVER_URL = os.getenv("GPU_SERVER_URL", "http://localhost:8001")
MAX_GUITAR_SAMPLE_DURATION = 8
MIN_SONG_DURATION = 30
ALLOWED_AUDIO_FORMATS = {'.wav', '.mp3', '.m4a', '.mp4'}

# 임시 파일 저장
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def extract_guitar_from_song(song_path: str, output_path: str) -> None:
    """
    GPU 서버를 통해 원곡에서 기타 소리 추출
    """
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # GPU 서버로 파일 전송
            async with aiofiles.open(song_path, 'rb') as f:
                file_content = await f.read()
            
            files = {'audio': (Path(song_path).name, file_content, 'audio/mpeg')}
            
            # GPU 서버 API 호출
            response = await client.post(
                f"{GPU_SERVER_URL}/extract-guitar",
                files=files
            )
            
            if response.status_code != 200:
                raise Exception(f"GPU 서버 오류: {response.text}")
            
            # 추출된 기타 저장
            async with aiofiles.open(output_path, 'wb') as f:
                await f.write(response.content)
                
    except httpx.TimeoutException:
        raise Exception("GPU 서버 타임아웃: 파일이 너무 크거나 서버가 응답하지 않습니다.")
    except Exception as e:
        raise Exception(f"기타 추출 실패: {str(e)}")


async def predict_effector_params(guitar_sample_path: str, extracted_guitar_path: str) -> Dict[str, Any]:
    """
    GPU 서버를 통해 이펙터와 파라미터 예측
    """
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # 두 파일을 GPU 서버로 전송
            async with aiofiles.open(guitar_sample_path, 'rb') as f1, \
                       aiofiles.open(extracted_guitar_path, 'rb') as f2:
                sample_content = await f1.read()
                extracted_content = await f2.read()
            
            files = {
                'guitar_sample': (Path(guitar_sample_path).name, sample_content, 'audio/mpeg'),
                'extracted_guitar': (Path(extracted_guitar_path).name, extracted_content, 'audio/mpeg')
            }
            
            # GPU 서버 API 호출
            response = await client.post(
                f"{GPU_SERVER_URL}/predict-effector",
                files=files
            )
            
            if response.status_code != 200:
                raise Exception(f"GPU 서버 오류: {response.text}")
            
            return response.json()
                
    except httpx.TimeoutException:
        raise Exception("GPU 서버 타임아웃: 모델 추론 시간이 초과되었습니다.")
    except Exception as e:
        raise Exception(f"이펙터 예측 실패: {str(e)}")


async def validate_local_file(path: Path, filename: str, min_duration: float = 0) -> tuple:
    """
    로컬에 저장된 오디오 파일 유효성 검증
    returns: (is_valid, duration, error_message)
    """
    file_ext = Path(filename).suffix.lower()
    
    if file_ext not in ALLOWED_AUDIO_FORMATS:
        return False, 0, f"지원하지 않는 파일 형식입니다. {ALLOWED_AUDIO_FORMATS} 만 가능합니다."
    
    try:
        # librosa는 동기 함수이므로 스레드 풀에서 실행하는 것이 좋지만, 여기서는 간단히 처리
        # 대용량 파일의 경우 비동기 래퍼가 필요할 수 있음
        y, sr = librosa.load(str(path), sr=None, duration=None)
        duration = len(y) / sr
        
        if duration < min_duration:
            return False, duration, f"오디오 길이가 너무 짧습니다. 최소 {min_duration}초가 필요합니다. (현재: {duration:.1f}초)"
            
        return True, duration, None
        
    except Exception as e:
        return False, 0, f"오디오 파일을 읽을 수 없습니다: {str(e)}"


async def process_analysis_stream(guitar_sample_path: Path, song_path: Path, guitar_sample_name: str, song_name: str):
    """
    분석 프로세스를 스트리밍으로 진행 상황 전송
    """
    extracted_guitar_path = None
    
    try:
        # 1단계: 파일 검증 (10%)
        yield f"data: {json.dumps({'status': 'progress', 'progress': 10, 'message': '파일 검증 중...'})}\n\n"
        await asyncio.sleep(0.5)
        
        is_valid, duration, error = await validate_local_file(guitar_sample_path, guitar_sample_name, min_duration=MAX_GUITAR_SAMPLE_DURATION)
        if not is_valid:
            yield f"data: {json.dumps({'status': 'error', 'message': f'기타 샘플: {error}'})}\n\n"
            return
        
        is_valid, duration, error = await validate_local_file(song_path, song_name, min_duration=MIN_SONG_DURATION)
        if not is_valid:
            yield f"data: {json.dumps({'status': 'error', 'message': f'원곡: {error}'})}\n\n"
            return
        
        # 2단계: 파일 저장 확인 (20%) - 이미 저장됨
        yield f"data: {json.dumps({'status': 'progress', 'progress': 20, 'message': '파일 분석 준비 완료...'})}\n\n"
        
        extracted_guitar_path = UPLOAD_DIR / f"extracted_guitar_{song_name}"
        
        # 3단계: GPU 서버로 기타 추출 (30% ~ 60%)
        yield f"data: {json.dumps({'status': 'progress', 'progress': 30, 'message': '🎸 GPU 서버에 연결 중...'})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'status': 'progress', 'progress': 40, 'message': '🎸 원곡에서 기타 소리를 추출하고 있습니다... (AI 처리 중)'})}\n\n"
        
        await extract_guitar_from_song(str(song_path), str(extracted_guitar_path))
        
        yield f"data: {json.dumps({'status': 'progress', 'progress': 60, 'message': '✓ 기타 소리 추출 완료!'})}\n\n"
        await asyncio.sleep(0.5)
        
        # 4단계: GPU 서버로 이펙터 예측 (60% ~ 90%)
        yield f"data: {json.dumps({'status': 'progress', 'progress': 70, 'message': '🔍 GPU 서버에서 이펙터를 분석하고 있습니다...'})}\n\n"
        await asyncio.sleep(0.5)
        
        yield f"data: {json.dumps({'status': 'progress', 'progress': 80, 'message': '⚙️ AI 모델이 파라미터를 추정하고 있습니다...'})}\n\n"
        
        result = await predict_effector_params(str(guitar_sample_path), str(extracted_guitar_path))
        
        yield f"data: {json.dumps({'status': 'progress', 'progress': 90, 'message': '✓ 파라미터 추정 완료!'})}\n\n"
        await asyncio.sleep(0.5)
        
        # 5단계: 완료 (100%)
        yield f"data: {json.dumps({'status': 'progress', 'progress': 100, 'message': '🎉 모든 분석이 완료되었습니다!'})}\n\n"
        yield f"data: {json.dumps({'status': 'completed', 'result': result})}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    finally:
        # 임시 파일 정리
        for path in [guitar_sample_path, song_path, extracted_guitar_path]:
            if path and path.exists():
                try:
                    path.unlink()
                except:
                    pass


# 이건 이렇게 하드코딩 된 게 맞는건가?
@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "Boss Effector API",
        "version": "1.0.0",
        "status": "running",
        "gpu_server": GPU_SERVER_URL,
        "endpoints": {
            "analyze": f"{app.url_path_for('analyze_guitar_effect')} (POST)",
            "health": f"{app.url_path_for('health_check')} (GET)"
        }
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    gpu_status = "disconnected"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{GPU_SERVER_URL}/health")
            if response.status_code == 200:
                gpu_status = "connected"
    except:
        pass
    
    return {
        "status": "healthy",
        "gpu_server": gpu_status
    }


@app.post("/analyze")
async def analyze_guitar_effect(
    guitar_sample: UploadFile = File(..., description="기타 샘플 사운드 파일"),
    original_song: UploadFile = File(..., description="원곡 파일")
):
    """
    기타 이펙터 분석 API
    GPU 서버를 통해 처리됨
    """
    # 파일을 미리 저장 (StreamingResponse 내부에서 UploadFile을 읽으면 closed file 에러 발생 가능)
    guitar_sample_path = UPLOAD_DIR / f"guitar_sample_{guitar_sample.filename}"
    song_path = UPLOAD_DIR / f"song_{original_song.filename}"
    
    try:
        async with aiofiles.open(guitar_sample_path, "wb") as f:
            await f.write(await guitar_sample.read())
        
        async with aiofiles.open(song_path, "wb") as f:
            await f.write(await original_song.read())
            
        return StreamingResponse(
            process_analysis_stream(guitar_sample_path, song_path, guitar_sample.filename, original_song.filename),
            media_type="text/event-stream"
        )
    except Exception as e:
        # 저장 중 에러 발생 시 파일 정리
        if guitar_sample_path.exists():
            guitar_sample_path.unlink()
        if song_path.exists():
            song_path.unlink()
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)