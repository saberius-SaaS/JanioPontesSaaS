import base64

with open('gas/Portal.html', 'r', encoding='utf-8') as f:
    line = f.readlines()[187].strip()

b64_str = line.split('base64,')[1].split('"')[0]

with open('app/static/logo.jpg', 'wb') as f:
    f.write(base64.b64decode(b64_str))

print("Logo saved successfully.")
