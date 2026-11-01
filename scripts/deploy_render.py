"""Create only the named free MVP service; credentials never leave environment/API transport."""

import argparse
import json
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--key-file", required=True)
parser.add_argument("--groq-key-file", required=True)
parser.add_argument("--owner", required=True)
parser.add_argument("--frontend-origin", required=True)
args = parser.parse_args()
headers = {"Authorization": "Bearer " + Path(args.key_file).read_text().strip()}
with httpx.Client(base_url="https://api.render.com/v1", headers=headers, timeout=60) as client:
    listed = client.get("/services", params={"limit": 100})
    listed.raise_for_status()
    existing = [
        entry["service"]
        for entry in listed.json()
        if entry["service"]["name"] == "ai-learning-assistant-api"
        and entry["service"]["ownerId"] == args.owner
    ]
    if existing:
        service = existing[0]
    else:
        payload = {
            "type": "web_service",
            "name": "ai-learning-assistant-api",
            "ownerId": args.owner,
            "repo": "https://github.com/Astavicious/ai-learning-assistant",
            "branch": "main",
            "autoDeployTrigger": "off",
            "serviceDetails": {
                "runtime": "docker",
                "plan": "free",
                "region": "frankfurt",
                "numInstances": 1,
                "healthCheckPath": "/api/health",
            },
            "envVars": [
                {"key": "GROQ_API_KEY", "value": Path(args.groq_key_file).read_text().strip()},
                {"key": "ALLOWED_ORIGINS", "value": args.frontend_origin},
                {"key": "GENERATION_MODEL", "value": "openai/gpt-oss-20b"},
                {"key": "GLOBAL_DAILY_TOKENS", "value": "60000"},
            ],
        }
        response = client.post("/services", json=payload)
        if not response.is_success:
            print(
                "Create failed",
                response.status_code,
                response.json().get("message", "See Render dashboard for details"),
            )
            raise SystemExit(1)
        body = response.json()
        service = body.get("service", body)
    details = {
        "id": service["id"],
        "url": service["serviceDetails"].get("url"),
        "plan": service["serviceDetails"].get("plan"),
        "dashboard": service.get("dashboardUrl"),
    }
    assert details["plan"] == "free"
    print(json.dumps(details))
    Path(".deployment").mkdir(exist_ok=True)
    Path(".deployment/render.json").write_text(json.dumps(details, indent=2))
