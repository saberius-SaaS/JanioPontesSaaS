import subprocess, json

result = subprocess.run(
    ['gcloud', 'logging', 'read',
     'resource.type=cloud_run_revision AND resource.labels.service_name=jp-saas-app AND timestamp>="2026-05-29T17:58:00Z"',
     '--limit=30', '--format=json'],
    capture_output=True, text=True, shell=True
)

if result.returncode != 0:
    print("STDERR:", result.stderr)
else:
    logs = json.loads(result.stdout)
    for l in logs:
        text = l.get('textPayload', '') or ''
        jmsg = ''
        jp = l.get('jsonPayload', {})
        if isinstance(jp, dict):
            jmsg = jp.get('message', '')
        msg = text or jmsg
        if msg:
            ts = l.get('timestamp', '')[:19]
            print(f"[{ts}] {msg[:300]}")
