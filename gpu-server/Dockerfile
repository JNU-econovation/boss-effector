# NVIDIA CUDA 베이스 이미지 (GPU 사용)
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Python 설치
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# Python 패키지 설치
COPY requirements-gpu.txt .
RUN pip3 install --no-cache-dir -r requirements-gpu.txt

# 애플리케이션 코드 복사
COPY app.py .

# 모델 디렉토리 생성 (실제 모델 파일들을 여기에 넣음)
RUN mkdir -p models temp

# 모델 파일 복사 (있다면)
# COPY models/ models/

# 포트 노출
EXPOSE 8001

# 환경 변수
ENV PYTHONUNBUFFERED=1

# 서버 실행
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]