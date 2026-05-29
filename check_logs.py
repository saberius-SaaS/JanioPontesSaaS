import subprocess, json, os

# Find gcloud path
gcloud_path = os.popen("where gcloud").read().strip().split("\n")[0]
print(f"gcloud path: {gcloud_path}")

result = subprocess.run(
    [gcloud_path, 'logging', 'read',
     'resource.type=cloud_run_revision AND resource.labels.service_name=jp-saas-app AND timestamp>="2026-05-29T17:40:00Z"',
     '--limit=50', '--format=json'],
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
            print(f"[{ts}] {msg[:200]}")
