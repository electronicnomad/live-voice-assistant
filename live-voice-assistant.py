import os
import sys

# 강제로 로컬 사이트 패키지 경로를 추가합니다. (ModuleNotFoundError 해결용)
# Force-add the local site-packages path. (To resolve ModuleNotFoundError)
local_packages = os.path.expanduser("~/.local/lib/python3.11/site-packages")
if os.path.exists(local_packages) and local_packages not in sys.path:
    sys.path.insert(0, local_packages)

import asyncio
import re
import subprocess
import time
import pyaudio
import audioop
import logging
import threading
import queue
from google import genai
from google.genai import types
import datetime

# ==========================================
# 로깅 설정
# Logging configuration
# ==========================================
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("live-voice-assistant")
logging.getLogger('google_genai.types').setLevel(logging.ERROR)
logging.getLogger('google_genai').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.WARNING)

import shutil

def cleanup_old_logs(log_dir=LOG_DIR, max_days=7, min_free_mb=1024):
    """
    지정된 기간이 지났거나 파일 시스템 여유 공간이 부족할 때 이전 로그를 삭제합니다.
    Deletes old logs when they exceed the retention period or when free disk space is low.
    - max_days: 보관할 최대 일수 (기본 7일) / Maximum number of days to keep (default 7 days)
    - min_free_mb: 유지해야 할 최소 여유 공간 MB (기본 1024MB = 1GB) / Minimum free space MB to maintain (default 1024MB = 1GB)
    """
    try:
        now = time.time()
        log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.log') or f.endswith('.txt')]
        # 오래된 파일부터 정렬 (오름차순)
        # Sort from the oldest file first (ascending order)
        log_files.sort(key=os.path.getmtime)

        for log_file in log_files:
            # 1. 기간 기반 삭제
            # 1. Deletion based on retention period
            file_age_days = (now - os.path.getmtime(log_file)) / (24 * 3600)
            if file_age_days > max_days:
                os.remove(log_file)
                log.info(f"[Cleanup] 오래된 로그 삭제됨 ({file_age_days:.1f}일 경과): {os.path.basename(log_file)}")
                continue

            # 2. 용량 기반 삭제 (남은 공간 확인)
            # 2. Deletion based on capacity (check remaining space)
            free_space_mb = shutil.disk_usage(log_dir).free / (1024 * 1024)
            if free_space_mb < min_free_mb:
                os.remove(log_file)
                log.info(f"[Cleanup] 용량 확보를 위해 로그 삭제됨 (여유 {free_space_mb:.1f}MB): {os.path.basename(log_file)}")
                
    except Exception as e:
        log.error(f"[Cleanup] 로그 정리 중 오류 발생: {e}")

# 프로그램 시작 시 1회 실행하여 찌꺼기 청소
# Run once at program startup to clean up leftover files
cleanup_old_logs()

# ==========================================
# [1] 설정 (Config & .env Loader)
# [1] Configuration (Config & .env Loader)
# ==========================================
def load_env(file_path=".env"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip().strip("'").strip('"')

load_env()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Live API 모델
# Live API model
MODEL_ID = "gemini-3.1-flash-live-preview"

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

if not GEMINI_API_KEY:
    print("[Error] GEMINI_API_KEY가 .env 파일에 없습니다.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# 오디오 기본 설정 (Gemini Live API 권장)
# Default audio settings (recommended by Gemini Live API)
FORMAT = pyaudio.paInt16
CHANNELS = 1
GEMINI_INPUT_RATE = 16000   # 마이크 → Gemini / Microphone → Gemini
GEMINI_OUTPUT_RATE = 24000  # Gemini → 스피커 / Gemini → Speaker
GEMINI_RATE = GEMINI_INPUT_RATE  # 하위 호환용 / For backward compatibility

# ==========================================
# [2] 하드웨어 탐색 및 PyAudio 인덱스/샘플 레이트 매핑
# [2] Hardware discovery and PyAudio index/sample-rate mapping
# ==========================================
def get_pyaudio_config():
    p = pyaudio.PyAudio()
    mic_index = None
    speaker_index = None
    mic_rate = GEMINI_RATE
    speaker_rate = GEMINI_RATE
    
    print("\n[System] 오디오 장치 탐색 중...")
    
    # 공통 샘플 레이트 테스트 후보
    # Common sample-rate test candidates
    test_rates = [16000, 44100, 48000, 22050, 8000]

    # 1. USB 마이크 찾기 및 지원 레이트 확인
    # 1. Find USB microphone and check supported rates
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        name = dev.get('name', '')
        if "USB" in name and dev.get('maxInputChannels', 0) > 0:
            mic_index = i
            print(f"   -> 마이크 발견: [{i}] {name}")
            # 지원하는 샘플 레이트 찾기
            # Find a supported sample rate
            for rate in test_rates:
                try:
                    if p.is_format_supported(rate, input_device=i, input_channels=CHANNELS, input_format=FORMAT):
                        mic_rate = rate
                        break
                except: continue
            print(f"      - 마이크 지원 샘플 레이트 선택: {mic_rate} Hz")
            break
            
    # 2. USB 또는 기본 스피커 찾기 및 지원 레이트 확인
    # 2. Find USB or default speaker and check supported rates
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        name = dev.get('name', '')
        if "USB" in name and dev.get('maxOutputChannels', 0) > 0 and i != mic_index:
            speaker_index = i
            print(f"   -> 외부 스피커 발견: [{i}] {name}")
            # 지원하는 샘플 레이트 찾기
            # Find a supported sample rate
            for rate in test_rates:
                try:
                    if p.is_format_supported(rate, output_device=i, output_channels=CHANNELS, output_format=FORMAT):
                        speaker_rate = rate
                        break
                except: continue
            print(f"      - 스피커 지원 샘플 레이트 선택: {speaker_rate} Hz")
            break
            
    if mic_index is None: 
        mic_info = p.get_default_input_device_info()
        mic_index = mic_info['index']
        mic_rate = int(mic_info['defaultSampleRate'])
        
    if speaker_index is None: 
        speaker_info = p.get_default_output_device_info()
        speaker_index = speaker_info['index']
        speaker_rate = int(speaker_info['defaultSampleRate'])
    
    p.terminate()
    return mic_index, speaker_index, mic_rate, speaker_rate

MIC_INDEX, SPEAKER_INDEX, MIC_RATE, SPEAKER_RATE = get_pyaudio_config()

# Live API Best Practice: 40ms 청크 계산
# Live API Best Practice: calculate 40ms chunk
CHUNK = int(MIC_RATE * 0.04)

# ==========================================
# [3] 메인 루프
# [3] Main loop
# ==========================================
async def run_forever():
    """Gemini 세션 진입 및 유지 루프 / Loop to enter and maintain the Gemini session"""

    print("\n[System] 마이크 입력을 시작합니다. 바로 대화하실 수 있습니다.")
    log.info("Gemini Live 대화 모드 시작")

    p = pyaudio.PyAudio()
    
    # 마이크는 상시 켜둡니다.
    # Keep the microphone always on.
    try:
        mic_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=MIC_RATE,
            input=True,
            input_device_index=MIC_INDEX,
            frames_per_buffer=CHUNK
        )
    except Exception as e:
        log.error(f"마이크를 열 수 없습니다: {e}")
        p.terminate()
        return

    # 스피커 설정
    # Speaker configuration
    try:
        speaker_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SPEAKER_RATE,
            output=True,
            output_device_index=SPEAKER_INDEX,
            frames_per_buffer=CHUNK
        )
    except Exception as e:
        log.error(f"스피커를 열 수 없습니다: {e}")
        mic_stream.stop_stream()
        mic_stream.close()
        p.terminate()
        return

    # 전역 상태 공유를 위한 변수들
    # Variables for sharing global state
    send_queue = asyncio.Queue(maxsize=10)
    speaker_queue = queue.Queue(maxsize=10)
    
    app_state = {
        "running": True,         # 전체 프로그램 실행 상태 / Overall program running state
        "is_playing": False,     # 스피커 출력 상태 / Speaker output state
    }

    def speaker_worker():
        """스피커 재생 및 리샘플링 전담 스레드 / Dedicated thread for speaker playback and resampling"""
        out_state = None
        while app_state["running"]:
            try:
                audio_data = speaker_queue.get(timeout=0.1)
                if audio_data:
                    app_state["is_playing"] = True
                    if SPEAKER_RATE != GEMINI_OUTPUT_RATE:
                        audio_data, out_state = audioop.ratecv(audio_data, 2, CHANNELS, GEMINI_OUTPUT_RATE, SPEAKER_RATE, out_state)

                    try:
                        speaker_stream.write(audio_data, exception_on_underflow=False)
                    except:
                        pass

                    if speaker_queue.empty():
                        time.sleep(0.05)
                        if speaker_queue.empty():
                            app_state["is_playing"] = False
                            out_state = None
            except queue.Empty:
                app_state["is_playing"] = False
            except Exception as e:
                log.error(f"Speaker Thread Error: {e}")

    def mic_worker(loop):
        """마이크 캡처 및 리샘플링 전담 스레드 / Dedicated thread for microphone capture and resampling"""
        in_state = None
        last_log_time = 0

        while app_state["running"]:
            try:
                data = mic_stream.read(CHUNK, exception_on_overflow=False)

                # 에코 캔슬링: 스피커 재생 중일 땐 마이크 캡처 무시
                # Echo cancellation: ignore mic capture while the speaker is playing
                if app_state["is_playing"]:
                    data = b'\x00' * len(data)

                # 리샘플링 (Mic Rate -> Gemini Rate 16000Hz)
                # Resampling (Mic Rate -> Gemini Rate 16000Hz)
                if MIC_RATE != GEMINI_RATE:
                    resampled_data, in_state = audioop.ratecv(data, 2, CHANNELS, MIC_RATE, GEMINI_RATE, in_state)
                else:
                    resampled_data = data

                # Gemini 대화 모드: 서버 전송 큐에 데이터 넣기
                # Gemini conversation mode: put data into the server send queue
                rms = audioop.rms(resampled_data, 2)
                if rms > 1500: # 대화 감지 임계값 / Speech detection threshold
                    curr = time.time()
                    if curr - last_log_time > 1.0:
                        log.debug(f"[MIC] 사용자 음성 감지 (RMS: {rms})")
                        last_log_time = curr

                try:
                    loop.call_soon_threadsafe(
                        lambda d: send_queue.put_nowait(d) if not send_queue.full() else None,
                        resampled_data
                    )
                except:
                    pass

            except Exception as e:
                log.error(f"Mic Thread Error: {e}")
                break

    # 스레드 시작
    # Start the threads
    loop = asyncio.get_event_loop()
    speaker_thread = threading.Thread(target=speaker_worker, daemon=True)
    speaker_thread.start()
    mic_thread = threading.Thread(target=mic_worker, args=(loop,), daemon=True)
    mic_thread.start()

    config = {
        "system_instruction": {"parts": [{"text": "You are a helpful AI assistant. Respond directly and concisely. Always respond in the same language the user speaks. Default to English if the language is unclear."}]},
        "response_modalities": ["AUDIO"],
        "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Despina"}}},
        "context_window_compression": {
            "trigger_tokens": 800000,
            "sliding_window": {"target_tokens": 10000}
        }
    }

    try:
        while app_state["running"]:
            log.info("Connecting to Gemini Live API...")
            try:
                async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
                    log.info("Connected. Session started.")

                    # 큐에 남은 예전 데이터 정리
                    # Clear out stale data remaining in the queue
                    while not send_queue.empty():
                        try: send_queue.get_nowait()
                        except: break

                    async def send_task():
                        while app_state["running"]:
                            try:
                                # timeout을 주어 루프가 막히지 않게 함
                                # Use a timeout so the loop doesn't get blocked
                                data = await asyncio.wait_for(send_queue.get(), timeout=0.1)

                                await session.send_realtime_input(
                                    audio=types.Blob(data=data, mime_type=f"audio/pcm;rate={GEMINI_RATE}")
                                )

                            except asyncio.TimeoutError:
                                continue
                            except Exception as e:
                                log.warning(f"Send task err: {e}")
                                break

                    async def receive_task():
                        audio_chunk_count = 0
                        while app_state["running"]:
                            try:
                                async for message in session.receive():
                                    if not app_state["running"]: break

                                    if message.go_away is not None:
                                        # GoAway 수신 시 일정 시간 뒤 연결 종료 예고
                                        # GoAway received: connection will close after the given time
                                        log.warning(f"[RECV] GoAway 수신: {message.go_away.time_left}초 후 연결 종료")

                                    server_content = message.server_content
                                    if server_content is not None:
                                        if server_content.interrupted:
                                            log.info("[RECV] Interrupted: 봇 응답 중단")
                                            while not speaker_queue.empty():
                                                try: speaker_queue.get_nowait()
                                                except: break

                                        if server_content.turn_complete:
                                            audio_chunk_count = 0

                                        model_turn = server_content.model_turn
                                        if model_turn is not None:
                                            for part in model_turn.parts:
                                                if part.inline_data and part.inline_data.data:
                                                    audio_chunk_count += 1
                                                    speaker_queue.put(part.inline_data.data)
                                                elif part.text:
                                                    log.info(f"Bot: {part.text}")
                                                    print(f"Bot: {part.text}")
                            except asyncio.CancelledError:
                                break
                            except Exception as e:
                                log.warning(f"[RECV] receive 에러: {e}")
                                break
                            await asyncio.sleep(0.1)

                    send_t = asyncio.create_task(send_task())
                    recv_t = asyncio.create_task(receive_task())

                    done, pending = await asyncio.wait(
                        [send_t, recv_t],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()

            except Exception as e:
                log.error(f"Streaming Session Error: {e}")

            # 세션이 끊기면 잠시 후 재연결
            # If the session drops, reconnect after a short delay
            if app_state["running"]:
                await asyncio.sleep(1.0)

    except KeyboardInterrupt:
        raise
    finally:
        log.info("프로그램 종료, 리소스 정리 중...")
        app_state["running"] = False
        speaker_thread.join(timeout=1.0)
        mic_thread.join(timeout=1.0)
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()
        p.terminate()
        log.info("정리 완료.")

if __name__ == "__main__":
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        log.info("사용자가 종료했습니다 (Ctrl+C)")
        print("\n[System] 프로그램을 종료합니다.")

