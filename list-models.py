from google import genai
key = open('.env').read()
for line in key.splitlines():
    if 'GEMINI_API_KEY' in line:
        api_key = line.split('=',1)[1].strip().strip("'").strip('"')
for ver in ['v1alpha', 'v1beta']:
    print(f'\n=== {ver} ===')
    try:
        c = genai.Client(api_key=api_key, http_options={'api_version': ver})
        for m in c.models.list():
            if 'live' in m.name.lower():
                print(m.name)
    except Exception as e:
        print(f'Error: {e}')
