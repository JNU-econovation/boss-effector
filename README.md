# 🎸 Boss Effector - AI Guitar Effect Analyzer

**AI를 활용하여 음악에서 기타 소리를 추출하고, 사용된 이펙터와 파라미터를 예측하는 웹 애플리케이션입니다.**

이 프로젝트는 **FastAPI** 기반의 메인 서버와 **Modal** 기반의 Serverless GPU 서버로 구성되어 있습니다.

## 🏗️ 아키텍처

```mermaid
graph TD
    Client[Frontend (Web)] -->|HTTP| MainAPI[Main API Server (Local/Cloud)]
    MainAPI -->|HTTPS| Modal[Modal GPU Server (Serverless)]
    
    subgraph "Local / Main Server"
        MainAPI
    end
    
    subgraph "Modal Cloud"
        Modal --> Demucs[Source Separation Model]
        Modal --> EffectorModel[Effect Prediction Model]
    end
```

- **Frontend**: HTML/CSS/Vanilla JS (User Interface)
- **Main API**: FastAPI (Orchestrator, File Validation, Stream Response)
- **GPU Server**: Modal (Serverless GPU, AI Models Execution)

## 📁 프로젝트 구조

```
boss-effector/
├── main.py                     # 메인 FastAPI 서버 (Local Orchestrator)
├── requirements.txt            # 메인 서버 의존성
├── .env                        # 환경 변수 (GPU 서버 URL 등)
├── frontend/                   # 웹 프론트엔드
│   ├── index.html
│   ├── script.js
│   └── style.css
│
├── gpu-server/                 # GPU 처리 서버 (Modal)
│   ├── app.py                  # Modal 앱 정의 및 FastAPI
│   └── requirements-gpu.txt    # (참고용) GPU 서버 의존성
│
├── uploads/                    # 임시 업로드 폴더 (자동 생성)
└── README.md
```

## 🚀 시작하기 (Getting Started)

### 1. 환경 설정

먼저 프로젝트를 클론하고 의존성을 설치합니다.

```bash
# 레포지토리 클론
git clone https://github.com/your-username/boss-effector.git
cd boss-effector

# Python 가상환경 생성 및 활성화 (권장)
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 메인 서버 의존성 설치
pip install -r requirements.txt
```

### 2. GPU 서버 배포 (Modal)

이 프로젝트는 무거운 AI 모델 처리를 위해 [Modal](https://modal.com/)을 사용합니다.

1.  **Modal 설치 및 로그인**:
    ```bash
    pip install modal
    modal setup
    ```

2.  **GPU 서버 실행 (Dev Mode)**:
    개발 중에는 코드가 변경되면 자동으로 재배포되는 `serve` 명령어를 사용하세요.
    ```bash
    modal serve gpu-server/app.py
    ```
    *터미널에 출력되는 URL(예: `https://your-username--boss-effector-gpu-fastapi-app.modal.run`)을 복사하세요.*

3.  **GPU 서버 배포 (Production)**:
    ```bash
    modal deploy gpu-server/app.py
    ```

### 3. 메인 서버 설정 및 실행

1.  **.env 파일 생성**:
    프로젝트 루트에 `.env` 파일을 생성하고, 위에서 복사한 Modal URL을 입력합니다.

    ```env
    # .env
    GPU_SERVER_URL=https://your-username--boss-effector-gpu-fastapi-app.modal.run
    ```

2.  **메인 서버 실행**:
    ```bash
    uvicorn main:app --reload --port 8000
    ```
    서버가 `http://localhost:8000`에서 실행됩니다.

### 4. 프론트엔드 실행

별도의 빌드 과정 없이 정적 파일 서버로 실행하거나, `index.html`을 브라우저에서 직접 열어도 됩니다.

```bash
# Python 내장 서버 사용 (추천)
python -m http.server 3000 --directory frontend
```
브라우저에서 `http://localhost:3000`으로 접속하세요.

---

## 🛠️ 개발 가이드

### 로컬 GPU 서버 실행 (옵션)
Modal을 사용하지 않고 로컬 GPU(CUDA)를 사용하여 테스트하려면 다음과 같이 실행합니다.

```bash
# GPU 서버 의존성 설치
pip install -r gpu-server/requirements-gpu.txt

# 로컬에서 GPU 서버 실행 (포트 8001)
cd gpu-server
uvicorn app:web_app --reload --port 8001
```
이 경우 `.env` 파일의 `GPU_SERVER_URL`을 `http://localhost:8001`로 변경해야 합니다.

## 🔌 API 문서

### Main API (Port 8000)
- `GET /`: 서비스 상태 및 설정 정보 확인
- `GET /health`: GPU 서버와의 연결 상태 확인
- `POST /analyze`: (Stream) 오디오 파일을 업로드하고 분석 결과 스트림 수신

### GPU Server API (Modal / Port 8001)
- `POST /extract-guitar`: 원곡에서 기타 트랙 분리 (Demucs)
- `POST /predict-effector`: 기타 샘플과 추출된 트랙을 비교하여 이펙터 예측

## 🔒 보안 및 주의사항
- **.env**: API URL 등 민감한 정보가 포함될 수 있으므로 Git에 커밋하지 마세요.
- **비용**: Modal은 GPU 사용 시간에 따라 과금되므로, 사용하지 않을 때는 `modal serve`를 종료하거나 앱을 중지하세요.

## 📝 라이선스
MIT License