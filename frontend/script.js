const API_URL = 'http://localhost:8000';
        
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

analyzeBtn.addEventListener('click', async () => {
    errorMessage.classList.remove('active');
    resultsContainer.classList.remove('active');
    progressContainer.classList.add('active');
    analyzeBtn.disabled = true;

    const formData = new FormData();
    formData.append('guitar_sample', guitarFile);
    formData.append('original_song', songFile);

    try {
        updateProgress(10, '파일 업로드 중...');

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

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.status === 'progress') {
                        updateProgress(data.progress, data.message);
                    } else if (data.status === 'completed') {
                        updateProgress(100, '분석 완료!');
                        displayResults(data.result);
                    } else if (data.status === 'error') {
                        throw new Error(data.message);
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
    
    if (result.effector_type) {
        html += `
            <div class="result-item">
                <div class="result-label">이펙터 타입</div>
                <div class="result-value">${result.effector_type}</div>
            </div>
        `;
    }

    if (result.parameters) {
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