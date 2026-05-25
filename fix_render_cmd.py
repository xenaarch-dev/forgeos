"""Fix Render service start command to include $PORT."""
import sys
sys.path.insert(0, '/home/padmaja/forge/forgeos')

from tools.http import http_request
from config import TOOLS
import json

key = TOOLS.render_api_key

start_cmd = "uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"
build_cmd = "pip install -r requirements.txt"

payload = {
    "serviceDetails": {
        "envSpecificDetails": {
            "buildCommand": build_cmd,
            "startCommand": start_cmd,
        }
    }
}

resp = http_request(
    "https://api.render.com/v1/services/srv-d89l4tmgvqtc73c3v8p0",
    method="PATCH",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    json_body=payload,
)

if resp:
    sd = resp.get("serviceDetails", {})
    env = sd.get("envSpecificDetails", {})
    print("buildCommand:", env.get("buildCommand"))
    print("startCommand:", env.get("startCommand"))
else:
    print("Response:", resp)
