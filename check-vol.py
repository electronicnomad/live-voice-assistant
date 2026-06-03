import subprocess
import audioop
import sys

# 마이크 설정 (본인 환경에 맞게)
# Microphone configuration (adjust to your own environment)
MIC_HW_ID = "plughw:1,0"

print(f"=== 마이크 볼륨 측정기 ({MIC_HW_ID}) ===")
print("1. 가만히 있어보세요 (배경 소음 측정)")
print("2. 말을 해보세요 (목소리 크기 측정)")
print("--------------------------------------")

cmd = ["arecord", "-D", MIC_HW_ID, "-f", "S16_LE", "-r", "44100", "-c", "1", "-t", "raw", "-q"]
process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

try:
    while True:
        data = process.stdout.read(2048)
        if not data: break
        
        rms = audioop.rms(data, 2)
        
        # 게이지바 시각화
        # Gauge bar visualization
        bar = "|" * (rms // 200)
        print(f"Volume: {rms:5d} {bar}")

except KeyboardInterrupt:
    process.terminate()
