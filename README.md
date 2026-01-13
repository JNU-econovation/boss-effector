# 🎸 Boss Effector - AI Guitar Effect Analyzer

AI를 활용하여 음악에서 기타 소리를 추출하고 사용된 이펙터와 파라미터를 예측하는 웹 애플리케이션입니다.

## 🏗️ 아키텍처

```
┌─────────────┐
│  Frontend   │  (Vanilla JS + HTML/CSS)
│ index.html  │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│  Main API   │  (FastAPI - CPU)
│  main.py    │  포트: 8000
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│ GPU Server  │  (FastAPI - GPU, Docker)
│   app.py    │  포트: 8001
└─────────────┘
   - 소스 분리 (Demucs)
   - 이펙터 예측 (Custom Model)
```

## 📁 프로젝트 구조

```
boss-effector/
├── main.py                     # 메인 FastAPI 서버 (CPU)
├── requirements.txt            # 메인 서버 의존성
├── frontend/
│   └── index.html             # 웹 UI
│
├── gpu-server/                # GPU 처리 서버 (Docker 필수)
│   ├── app.py                 # GPU FastAPI 서버
│   ├── Dockerfile             # Docker 이미지 설정
│   ├── requirements-gpu.txt   # GPU 서버 의존성
│   └── models/                # AI 모델 파일들 (추후 추가)
│
├── uploads/                   # 임시 파일 (자동 생성)
└── README.md
```

## 🚀 로컬에서 실행하기

### 1. 메인 API 서버 실행 (CPU)

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (Reload 모드)
uvicorn main:app --reload
```

메인 서버: `http://localhost:8000` <br>
스웨거 서버: `http://localhost:8000/docs`

### 2. GPU 서버 실행 (로컬 테스트용)

```bash
# 의존성 설치
pip install -r requirements-gpu.txt

# 서버 실행 (8001 포트 지정)
uvicorn app:app --app-dir gpu-server --reload --port 8001
```

GPU 서버: `http://localhost:8001`<br>
스웨거 서버: `http://localhost:8001/docs`

### 3. 프론트엔드 실행

```bash
# 정적 파일 서버 실행
python -m http.server 3000 -d frontend
```

프론트엔드: `http://localhost:3000/frontend/index.html`

## 🐳 Docker로 GPU 서버 실행

### 빌드

```bash
cd gpu-server
docker build -t boss-effector-gpu .
```

### 실행 (GPU 사용)

```bash
docker run --gpus all -p 8001:8001 boss-effector-gpu
```

### 실행 (CPU만 - 테스트용)

```bash
docker run -p 8001:8001 boss-effector-gpu
```
## 📖 사용 방법

1. **기타 샘플 업로드**: 추출하고 싶은 기타 사운드 (최소 8초)
2. **원곡 업로드**: 기타가 포함된 전체 곡 (최소 30초)
3. **분석 시작**: 버튼 클릭
4. **진행 상황 확인**:
   - 파일 검증
   - 파일 저장
   - GPU 서버에서 기타 추출 (소스 분리)
   - GPU 서버에서 이펙터 예측 (딥러닝)
5. **결과 확인**: 이펙터 타입 및 파라미터

## 🔌 API 문서

### 메인 API (포트 8000)

#### `GET /`
서비스 정보 및 GPU 서버 연결 상태

#### `GET /health`
헬스체크 (메인 + GPU 서버 상태)

#### `POST /analyze`
기타 이펙터 분석
- **Parameters**: 
  - `guitar_sample`: 기타 샘플 파일
  - `original_song`: 원곡 파일
- **Response**: Server-Sent Events 스트림

### GPU API (포트 8001)

#### `GET /`
GPU 서버 정보 (디바이스, 모델 로드 상태)

#### `GET /health`
GPU 서버 헬스체크

#### `POST /extract-guitar`
소스 분리로 기타 추출
- **Parameters**: `audio` (원곡 파일)
- **Response**: 추출된 기타 오디오 파일

#### `POST /predict-effector`
이펙터 예측
- **Parameters**: 
  - `guitar_sample`: 기타 샘플
  - `extracted_guitar`: 추출된 기타
- **Response**: 이펙터 타입 및 파라미터 JSON

## ⚙️ 환경 변수

### 메인 서버 (main.py)
```bash
GPU_SERVER_URL=http://localhost:8001  # GPU 서버 주소
```

### Docker Compose
```yaml
version: '3.8'
services:
  main-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GPU_SERVER_URL=http://gpu-server:8001
  
  gpu-server:
    build: ./gpu-server
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## 🔒 보안 고려사항

1. **파일 크기 제한**: FastAPI 기본값 사용
2. **파일 타입 검증**: 허용된 확장자만 처리
3. **임시 파일 자동 정리**: 처리 후 삭제
4. **CORS**: 프로덕션에서는 특정 도메인으로 제한
5. **API 인증**: 프로덕션 배포 시 추가 필요

## 🧪 테스트

### cURL로 GPU 서버 테스트

```bash
# 기타 추출 테스트
curl -X POST http://localhost:8001/extract-guitar \
  -F "audio=@song.mp3" \
  --output guitar.wav

# 이펙터 예측 테스트
curl -X POST http://localhost:8001/predict-effector \
  -F "guitar_sample=@sample.mp3" \
  -F "extracted_guitar=@guitar.wav"
```

### Python으로 메인 API 테스트

```python
import requests

files = {
    'guitar_sample': open('sample.mp3', 'rb'),
    'original_song': open('song.mp3', 'rb')
}

response = requests.post(
    'http://localhost:8000/analyze', 
    files=files, 
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

## 📝 라이선스

MIT License