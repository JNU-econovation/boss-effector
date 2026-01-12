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

## 🚀 로컬 개발 시작하기

### 1. 메인 API 서버 실행 (CPU)

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
```

메인 서버: `http://localhost:8000`

### 2. GPU 서버 실행 (로컬 테스트용)

```bash
cd gpu-server

# 의존성 설치
pip install -r requirements-gpu.txt

# 서버 실행
python app.py
```

GPU 서버: `http://localhost:8001`

### 3. 프론트엔드 실행

```bash
# Python 간이 서버
python -m http.server 3000

# 또는 그냥 브라우저에서 frontend/index.html 열기
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

## ☁️ 클라우드 배포

### Google Cloud Run에 GPU 서버 배포

```bash
# 1. Google Cloud 프로젝트 설정
gcloud config set project YOUR_PROJECT_ID

# 2. Container Registry에 이미지 푸시
cd gpu-server
docker build -t gcr.io/YOUR_PROJECT_ID/boss-effector-gpu .
docker push gcr.io/YOUR_PROJECT_ID/boss-effector-gpu

# 3. Cloud Run 배포 (GPU 사용)
gcloud run deploy boss-effector-gpu \
  --image gcr.io/YOUR_PROJECT_ID/boss-effector-gpu \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 600

# 배포된 URL을 환경 변수로 설정
export GPU_SERVER_URL=https://boss-effector-gpu-xxxxx.run.app
```

### 메인 서버 배포 (선택사항)

```bash
# Cloud Run, AWS Lambda, Vercel 등 자유롭게 선택
# 환경 변수로 GPU_SERVER_URL 설정 필요
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

## 🧠 AI 모델 통합

### 현재 상태
- 시뮬레이션 코드로 동작
- 실제 모델 없이도 테스트 가능

### 실제 모델 통합하기

#### 1. 소스 분리 모델 (Demucs)

```python
# gpu-server/app.py에서
from demucs.pretrained import get_model
from demucs.apply import apply_model

def load_demucs_model():
    model = get_model('htdemucs')
    model.to(DEVICE)
    return model

async def separate_guitar_with_demucs(audio_path, output_path):
    waveform, sr = torchaudio.load(audio_path)
    sources = apply_model(DEMUCS_MODEL, waveform.to(DEVICE))
    guitar = sources[0, 2]  # 기타 채널
    torchaudio.save(output_path, guitar.cpu(), sr)
```

#### 2. 커스텀 이펙터 예측 모델

```python
# 모델 학습 후
torch.save(model.state_dict(), 'models/effector_classifier.pth')

# gpu-server/app.py에서
def load_effector_model():
    model = YourEffectorModel()
    model.load_state_dict(torch.load('models/effector_classifier.pth'))
    model.to(DEVICE)
    model.eval()
    return model
```

## ⚙️ 환경 변수

### 메인 서버 (main.py)
```bash
GPU_SERVER_URL=http://localhost:8001  # GPU 서버 주소
```

### Docker Compose (선택)
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

## 💰 예상 클라우드 비용

### Google Cloud Run (GPU)
- **요금**: 사용한 만큼만 과금
- **예상**: 요청당 $0.01 ~ $0.05
- **무료 티어**: 월 200만 요청까지 무료 (CPU만)

### 비용 절감 팁
1. GPU는 추론 시에만 사용
2. 모델을 경량화 (Quantization, Pruning)
3. 배치 처리로 효율성 증가
4. 캐싱 활용

## 🔮 향후 개선 사항

- [ ] 실제 Demucs 모델 통합
- [ ] 커스텀 이펙터 분류 모델 학습
- [ ] 모델 최적화 (TensorRT, ONNX)
- [ ] 배치 처리 지원
- [ ] 웹소켓으로 실시간 진행률
- [ ] 결과 캐싱
- [ ] 사용자 인증
- [ ] 파일 업로드 제한 강화
- [ ] 결과 시각화 (파형, 스펙트로그램)

## 📝 라이선스

MIT License

## 🤝 기여

프로젝트에 기여를 환영합니다!

## 📧 문의

이슈를 통해 문의해주세요.