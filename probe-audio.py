import pyaudio

def probe_devices():
    p = pyaudio.PyAudio()
    print(f"Number of devices: {p.get_device_count()}")
    
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        print(f"Device {i}: {dev['name']}")
        print(f"  Input Channels: {dev['maxInputChannels']}")
        print(f"  Output Channels: {dev['maxOutputChannels']}")
        print(f"  Default Sample Rate: {dev['defaultSampleRate']}")
        
        rates = [8000, 16000, 22050, 44100, 48000]
        supported_input = []
        supported_output = []
        
        for rate in rates:
            # Check input
            # 입력 지원 여부 확인
            if dev['maxInputChannels'] > 0:
                try:
                    if p.is_format_supported(rate, input_device=i, input_channels=1, input_format=pyaudio.paInt16):
                        supported_input.append(rate)
                except Exception:
                    pass
            # Check output
            # 출력 지원 여부 확인
            if dev['maxOutputChannels'] > 0:
                try:
                    if p.is_format_supported(rate, output_device=i, output_channels=1, output_format=pyaudio.paInt16):
                        supported_output.append(rate)
                except Exception:
                    pass
        
        if supported_input:
            print(f"  Supported Input Rates (1 ch, int16): {supported_input}")
        if supported_output:
            print(f"  Supported Output Rates (1 ch, int16): {supported_output}")
    
    p.terminate()

if __name__ == "__main__":
    probe_devices()
