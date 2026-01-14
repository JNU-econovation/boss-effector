const API_URL = 'http://localhost:8000';

// DOM Elements
const guitarInput = document.getElementById('guitar-sample');
const songInput = document.getElementById('original-song');
const guitarInfo = document.getElementById('guitar-info');
const songInfo = document.getElementById('song-info');
const analyzeBtn = document.getElementById('analyze-btn');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const progressMessage = document.getElementById('progress-message');
const resultsContainer = document.getElementById('results-container');
const resultsContent = document.getElementById('results-content');
const errorMessage = document.getElementById('error-message');

let guitarFile = null;
let songFile = null;

// File Inputs
guitarInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        guitarFile = file;
        guitarInfo.textContent = `✓ ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        guitarInfo.classList.add('selected');
        checkFiles();
    }
});

songInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        songFile = file;
        songInfo.textContent = `✓ ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
        songInfo.classList.add('selected');
        checkFiles();
    }
});

function checkFiles() {
    if (guitarFile && songFile) {
        analyzeBtn.disabled = false;
    }
}

// Analyze Process
analyzeBtn.addEventListener('click', async () => {
    errorMessage.classList.remove('active');
    resultsContainer.classList.remove('active');
    progressContainer.classList.add('active');
    analyzeBtn.disabled = true;

    const formData = new FormData();
    formData.append('guitar_sample', guitarFile);
    formData.append('original_song', songFile);

    try {
        updateProgress(5, '파일 업로드 중...');

        const response = await fetch(`${API_URL}/analyze`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('분석 요청 실패');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.status === 'progress') {
                            updateProgress(data.progress, data.message);
                        } else if (data.status === 'completed') {
                            updateProgress(100, '분석 완료!');
                            displayResults(data.result);
                        } else if (data.status === 'error') {
                            throw new Error(data.message);
                        }
                    } catch (e) {
                        console.error('JSON Parse Error:', e);
                    }
                }
            }
        }
    } catch (error) {
        showError(error.message);
        progressContainer.classList.remove('active');
    } finally {
        analyzeBtn.disabled = false;
    }
});

function updateProgress(percent, message) {
    progressBar.style.width = `${percent}%`;
    progressBar.textContent = `${percent}%`;
    progressMessage.textContent = message;
}

function displayResults(result) {
    progressContainer.classList.remove('active');
    resultsContainer.classList.add('active');

    let html = '';
    
    // 오디오 재생기 추가 (URL 방식)
    if (result.audio_url) {
        // API_URL과 결합하여 전체 주소 생성
        const audioFullUrl = `${API_URL}${result.audio_url}`;
        
        html += `
            <div class="result-item" style="display: block; text-align: center; background: none;">
                <div class="result-label" style="margin-bottom: 10px;">🎸 추출된 기타 사운드</div>
                <audio controls style="width: 100%;">
                    <source src="${audioFullUrl}" type="audio/wav">
                    브라우저가 오디오 재생을 지원하지 않습니다.
                </audio>
                <div style="margin-top: 5px;">
                    <a href="${audioFullUrl}" download="extracted_guitar.wav" style="color: #aaa; text-decoration: none; font-size: 0.8em;">⬇️ 다운로드</a>
                </div>
            </div>
            <hr style="border: 0; border-top: 1px solid #555; margin: 15px 0;">
        `;
    }
    
    if (result.effector_type) {
        html += `
            <div class="result-item">
                <div class="result-label">이펙터 타입</div>
                <div class="result-value" style="color: var(--primary-color); font-size: 1.1em;">${result.effector_type}</div>
            </div>
        `;
    }

    if (result.parameters) {
        html += `<div style="margin-top: 15px; margin-bottom: 10px; font-size: 0.9em; color: #888;">추천 파라미터</div>`;
        for (const [key, value] of Object.entries(result.parameters)) {
            html += `
                <div class="result-item">
                    <div class="result-label">${key}</div>
                    <div class="result-value">${value}</div>
                </div>
            `;
        }
    }

    resultsContent.innerHTML = html;
}

function showError(message) {
    errorMessage.textContent = `❌ 오류: ${message}`;
    errorMessage.classList.add('active');
}