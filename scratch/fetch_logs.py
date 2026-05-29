import subprocess
import json

cmd = [
    "gcloud", "logging", "read",
    'resource.type="cloud_run_revision" AND resource.labels.service_name="jp-saas-app"',
    "--limit=50",
    "--format=json"
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.stdout:
    logs = json.loads(result.stdout)
    for log in logs:
        text = log.get("textPayload", log.get("jsonPayload", {}).get("message", ""))
        print(log.get("timestamp"), text)
else:
    print(result.stderr)
