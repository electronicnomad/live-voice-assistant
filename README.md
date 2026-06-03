# Live Voice Assistant (Live Streaming)

**live-voice-assistant** is an intelligent real-time voice assistant project for the Raspberry Pi.
By applying the latest **Gemini Multimodal Live API**, it supports **seamless and natural full-duplex real-time conversation**, just like talking to a person.

---

## Key Features

* **Instant Conversation Mode:** Starts receiving microphone input and begins real-time conversation the moment it launches.
* **True Real-Time Streaming (Websocket):** Splits the microphone audio into small chunks and sends them to the server immediately, while the AI's responses are played through the speaker in real time.
* **Human-Like Conversation Flow (Interruption Support):** If the user starts speaking while the AI is talking, it **immediately stops speaking and listens to the user's new input**.
* **Pure Multimodal Audio:** It understands the audio data itself and replies directly with audio, without any text conversion (STT/TTS), so intonation and emotional expression are far richer and more natural.
* **Session Stability & Optimization:** Optimized queue management and automatic reconnection logic support long, uninterrupted, comfortable conversations.
* **Detailed Logging System:** The AI's response text and the microphone input status (RMS) are automatically saved to the `logs/` directory, making it easy to preserve conversation records and diagnose issues.

---

## Requirements & Installation

### 1. Install System Packages

Linux system packages such as PyAudio are required for audio streaming.

```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev
```

### 2. Install Python Libraries

After activating the virtual environment (`venv`), install the required libraries.

```bash
# With the virtual environment activated
pip install -r requirements.txt
# (or install directly: pip install google-genai pyaudio)
```

### 3. Configure the API Key (Important)

Create a `.env` file in the project root directory and enter a Gemini API key that supports the Live API.

```text
GEMINI_API_KEY=your_actual_api_key_here
```

---

## How to Run

Run the main script inside the virtual environment.

```bash
python live-voice-assistant.py
```

* Once you see the message `마이크 입력을 시작합니다. 바로 대화하실 수 있습니다.`, just speak into the microphone right away.
* To fully exit the program, press `Ctrl + C`.

---

## Changing the Voice

You can change the voice the assistant uses when it replies. In the `live-voice-assistant.py` file, change the `voice_name` value inside `config` to the name of the voice you want. (Default: `Despina`)

```python
"speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Despina"}}},
```

You can **preview each voice** and pick the one you like. The official documentation page below has an audio playback button for each voice, so you can check the actual tone and feel before choosing.

* Preview & voice list: <https://docs.cloud.google.com/text-to-speech/docs/gemini-tts>

Available voice names (28 total):

* **Female:** Achernar, Aoede, Autonoe, Callirrhoe, Despina, Erinome, Gacrux, Kore, Laomedeia, Leda, Pulcherrima, Sulafat, Vindemiatrix, Zephyr
* **Male:** Achird, Algenib, Algieba, Alnilam, Charon, Enceladus, Fenrir, Iapetus, Orus, Puck, Rasalgethi, Sadachbia, Sadaltager, Schedar, Umbriel, Zubenelgenubi

---

## Registering as a Linux System Service (Systemd)

Follow these steps to make it start automatically when the Raspberry Pi boots.

### 1. Create the Service File

```bash
sudo nano /etc/systemd/system/live-voice-assistant.service
```

### 2. Enter the Contents (account and paths need editing)

In the content below, edit the `User`, `WorkingDirectory`, and `ExecStart` paths to match your actual environment before pasting. (Example for when the default username is `ubuntu`.)

```ini
[Unit]
Description=live-voice-assistant (Gemini Live) Service
After=network.target sound.target

[Service]
# When the Raspberry Pi default username is 'ubuntu'
User=ubuntu
WorkingDirectory=/home/data/services/live-voice-assistant

# Recommended approach using a virtual environment (venv):
ExecStart=/home/data/services/live-voice-assistant/venv/bin/python /home/data/services/live-voice-assistant/live-voice-assistant.py
# If installed via system packages without a venv, use the system python3:
# ExecStart=/usr/bin/python3 /home/data/services/live-voice-assistant/live-voice-assistant.py

# Environment variables may be needed for audio device recognition (assuming the ubuntu account UID is 1000)
Environment="XDG_RUNTIME_DIR=/run/user/1000"

Restart=always
RestartSec=10
StandardOutput=inherit
StandardError=inherit

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start the Service

```bash
# Reload the service configuration
sudo systemctl daemon-reload

# Register for automatic startup at boot
sudo systemctl enable live-voice-assistant.service

# Start the service immediately
sudo systemctl start live-voice-assistant.service
```

### 4. Check Logs (real-time subtitles available)

```bash
journalctl -u live-voice-assistant.service -f
```

---

## Project Structure

* `live-voice-assistant.py`: The main streaming script with the Gemini Live API applied.
* `.env`: File that stores settings requiring security, such as the API key.
* `logs/`: Directory where the system's session log files are stored, including AI response text and microphone status.
* `requirements.txt`: List of Python dependencies.
* `check-vol.py`: Utility to check the system microphone input status.
* `list-models.py`: Utility to query the list of available Gemini models.
* `probe-audio.py`: Utility to probe audio input/output devices.
* `venv/`: Isolated space for Python packages.

---
---

# Live Voice Assistant (Live Streaming)

**live-voice-assistant**는 라즈베리 파이를 위한 지능형 실시간 음성 비서 프로젝트입니다.  
가장 최신의 **Gemini Multimodal Live API**를 적용하여, 사람과 대화하듯 **끊김 없고 자연스러운 양방향(Full-Duplex) 실시간 대화**를 지원합니다.

---

## 혁신적인 주요 기능

* **즉시 대화 모드:** 실행과 동시에 마이크 입력을 받아 바로 실시간 대화를 시작합니다.
* **진정한 실시간 스트리밍 (Websocket):** 마이크 소리를 작은 조각(Chunk) 단위로 쪼개어 서버로 즉시 전송하고, 인공지능의 답변도 실시간으로 스피커로 출력합니다.
* **사람 같은 대화 흐름 (Interruption 지원):** 인공지능이 말하고 있는 도중에도 사용자가 말을 시작하면, **즉시 말하기를 멈추고 사용자의 새로운 말을 경청**합니다.
* **순수 멀티모달 오디오:** 텍스트 변환(STT/TTS) 과정 없이 오디오 데이터 그 자체를 이해하고 오디오로 직접 답변하므로, 억양과 감정 표현이 훨씬 풍부하고 자연스럽습니다.
* **세션 안정성 및 최적화:** 최적화된 큐(Queue) 관리와 자동 재연결 로직을 통해 장시간 끊김 없는 쾌적한 대화를 지원합니다.
* **상세 로깅 시스템:** 인공지능의 답변 텍스트와 마이크 입력 상태(RMS)를 `logs/` 디렉토리에 자동 저장하여 대화 기록 보존 및 문제 확인이 용이합니다.

---

## 필수 준비물 및 설치

### 1. 시스템 패키지 설치

PyAudio 등 오디오 스트리밍을 위한 리눅스 시스템 패키지가 필요합니다.

```bash
sudo apt update
sudo apt install python3-pyaudio portaudio19-dev
```

### 2. Python 라이브러리 설치

가상환경(`venv`)을 활성화한 후, 필수 라이브러리를 설치합니다.

```bash
# 가상환경 활성화 상태에서
pip install -r requirements.txt
# (또는 직접 설치: pip install google-genai pyaudio)
```

### 3. API 키 설정 (중요)

프로젝트 루트 디렉토리에 `.env` 파일을 만들고, Live API를 지원하는 Gemini API 키를 입력합니다.

```text
GEMINI_API_KEY=your_actual_api_key_here
```

---

## 실행 방법

가상환경에서 메인 스크립트를 실행합니다.

```bash
python live-voice-assistant.py
```

* 실행 후 `마이크 입력을 시작합니다. 바로 대화하실 수 있습니다.` 메시지가 보이면 바로 마이크에 대고 말하면 됩니다.
* 프로그램을 완전히 종료하려면 `Ctrl + C`를 누르세요.

---

## 음성(목소리) 변경

비서가 대답할 때 사용하는 목소리는 변경할 수 있습니다. `live-voice-assistant.py` 파일의 `config` 안 `voice_name` 값을 원하는 음성 이름으로 바꾸면 됩니다. (기본값: `Despina`)

```python
"speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Despina"}}},
```

각 목소리를 직접 **미리 들어본 뒤** 마음에 드는 음성을 고를 수 있습니다. 아래 공식 문서 페이지에 음성별 오디오 재생 버튼이 있어 실제 톤과 분위기를 확인한 후 선택할 수 있습니다.

* 미리 듣기 및 음성 목록: <https://docs.cloud.google.com/text-to-speech/docs/gemini-tts>

선택 가능한 음성 이름 (총 28종):

* **여성:** Achernar, Aoede, Autonoe, Callirrhoe, Despina, Erinome, Gacrux, Kore, Laomedeia, Leda, Pulcherrima, Sulafat, Vindemiatrix, Zephyr
* **남성:** Achird, Algenib, Algieba, Alnilam, Charon, Enceladus, Fenrir, Iapetus, Orus, Puck, Rasalgethi, Sadachbia, Sadaltager, Schedar, Umbriel, Zubenelgenubi

---

## Linux 시스템 서비스(Systemd) 등록 방법

라즈베리 파이가 부팅될 때 자동으로 실행되도록 설정하려면 다음 단계를 따르세요.

### 1. 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/live-voice-assistant.service
```

### 2. 내용 입력 (사용자 계정 및 경로 수정 필요)

아래 내용 중 `User`, `WorkingDirectory`, `ExecStart` 경로를 실제 환경에 맞게 수정하여 붙여넣습니다. (기본 사용자명이 `ubuntu`인 경우의 예시)

```ini
[Unit]
Description=live-voice-assistant (Gemini Live) Service
After=network.target sound.target

[Service]
# 라즈베리 파이 기본 사용자 이름이 'ubuntu'인 경우
User=ubuntu
WorkingDirectory=/home/data/services/live-voice-assistant

# 가상환경(venv)을 사용하는 권장 방식:
ExecStart=/home/data/services/live-voice-assistant/venv/bin/python /home/data/services/live-voice-assistant/live-voice-assistant.py
# 만약 가상환경 없이 시스템 패키지로 설치했다면 시스템 python3를 사용합니다:
# ExecStart=/usr/bin/python3 /home/data/services/live-voice-assistant/live-voice-assistant.py

# 오디오 장치 인식을 위해 환경변수 추가가 필요할 수 있습니다. (ubuntu 계정의 UID가 1000이라고 가정)
Environment="XDG_RUNTIME_DIR=/run/user/1000"

Restart=always
RestartSec=10
StandardOutput=inherit
StandardError=inherit

[Install]
WantedBy=multi-user.target
```

### 3. 서비스 활성화 및 실행

```bash
# 서비스 설정 불러오기
sudo systemctl daemon-reload

# 부팅 시 자동 실행 등록
sudo systemctl enable live-voice-assistant.service

# 서비스 즉시 시작
sudo systemctl start live-voice-assistant.service
```

### 4. 로그 확인 (실시간 자막 확인 가능)

```bash
journalctl -u live-voice-assistant.service -f
```

---

## 프로젝트 구조

* `live-voice-assistant.py`: Gemini Live API가 적용된 메인 스트리밍 스크립트.
* `.env`: API 키 등 보안이 필요한 설정을 보관하는 파일.
* `logs/`: 인공지능 답변 텍스트, 마이크 상태 등 시스템의 세션 로그 파일들이 저장되는 디렉토리.
* `requirements.txt`: 파이썬 의존성 목록.
* `check-vol.py`: 시스템 마이크 입력 상태를 확인하는 유틸리티.
* `list-models.py`: 사용 가능한 Gemini 모델 목록을 조회하는 유틸리티.
* `probe-audio.py`: 오디오 입출력 장치를 탐색하는 유틸리티.
* `venv/`: 파이썬 패키지 독립 공간.
