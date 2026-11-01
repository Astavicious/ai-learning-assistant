"""Configure the existing linked MVP project and deploy its committed frontend."""

import argparse
import json
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--key-file", required=True)
parser.add_argument("--backend", required=True)
args = parser.parse_args()
with httpx.Client(
    base_url="https://api.vercel.com",
    headers={"Authorization": "Bearer " + Path(args.key_file).read_text().strip()},
    timeout=60,
) as client:
    project_response = client.get("/v9/projects/ai-learning-assistant")
    project_response.raise_for_status()
    project = project_response.json()
    project_id = project["id"]
    response = client.patch(
        "/v9/projects/" + project_id,
        json={
            "framework": "vite",
            "rootDirectory": "frontend",
            "buildCommand": "npm run build",
            "installCommand": "npm ci",
            "outputDirectory": "dist",
            "nodeVersion": "22.x",
        },
    )
    response.raise_for_status()
    response = client.post(
        f"/v10/projects/{project_id}/env",
        params={"upsert": "true"},
        json={
            "key": "VITE_API_URL",
            "value": args.backend,
            "type": "plain",
            "target": ["production", "preview", "development"],
        },
    )
    response.raise_for_status()
    domains = client.get(f"/v9/projects/{project_id}/domains")
    domains.raise_for_status()
    print("domains", json.dumps([d["name"] for d in domains.json()["domains"]]))
    link = project["link"]
    response = client.post(
        "/v13/deployments",
        json={
            "name": "ai-learning-assistant",
            "project": project_id,
            "target": "production",
            "gitSource": {"type": "github", "repoId": str(link["repoId"]), "ref": "main"},
        },
    )
    if not response.is_success:
        print(
            "Deployment failed",
            response.status_code,
            response.json().get("error", {}).get("message", "Unknown error"),
        )
        raise SystemExit(1)
    deployment = response.json()
    details = {k: deployment.get(k) for k in ("id", "url", "readyState", "alias")}
    print(json.dumps(details))
    Path(".deployment").mkdir(exist_ok=True)
    Path(".deployment/vercel.json").write_text(json.dumps(details, indent=2))
