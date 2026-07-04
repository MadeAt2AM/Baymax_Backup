import urllib.request
import urllib.parse
import json
from pathlib import Path

content = Path("/root/.hermes/.env").read_text()
token = None
for line in content.split("\n"):
    if line.startswith("TELEGRAM_BOT_TOKEN=*** and not line.startswith("#"):
        token = line.split("=", 1)[1]
        break

url = f"https://api.telegram.org/bot{token}/sendMessage"
data = urllib.parse.urlencode({
    "chat_id": "-1003825565541",
    "text": "👋 Hi Chris! Telegram is back up and running. All fixed!"
}).encode()
with urllib.request.urlopen(url, data=data, timeout=10) as r:
    result = json.loads(r.read())
    print("Sent:", result["ok"], "msg_id:", result["result"]["message_id"])
