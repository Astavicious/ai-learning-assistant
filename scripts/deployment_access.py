"""Read-only access check. Credentials are read from private files and never printed."""

import argparse
import json
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--render-key-file")
parser.add_argument("--vercel-key-file")
args = parser.parse_args()
if args.render_key_file:
    key = Path(args.render_key_file).read_text().strip()
    with httpx.Client(
        base_url="https://api.render.com/v1", headers={"Authorization": "Bearer " + key}, timeout=30
    ) as client:
        for endpoint in ("owners?limit=20", "services?limit=100"):
            response = client.get("/" + endpoint)
            print("render", endpoint.split("?")[0], response.status_code)
            if response.is_success:
                entries = response.json()
                print(
                    json.dumps(
                        [
                            {
                                k: v
                                for k, v in (entry.get("owner") or entry.get("service") or entry).items()
                                if k in ("id", "name", "type", "serviceDetails")
                            }
                            for entry in entries
                        ]
                    )
                )
if args.vercel_key_file:
    key = Path(args.vercel_key_file).read_text().strip()
    with httpx.Client(
        base_url="https://api.vercel.com", headers={"Authorization": "Bearer " + key}, timeout=30
    ) as client:
        response = client.get("/v2/teams")
        print("vercel teams", response.status_code)
        teams = response.json().get("teams", []) if response.is_success else []
        print(json.dumps([{k: t.get(k) for k in ("id", "name", "slug")} for t in teams]))
        for team_id in [None] + [t["id"] for t in teams]:
            response = client.get(
                "/v9/projects", params={"limit": 100, **({"teamId": team_id} if team_id else {})}
            )
            print("vercel projects", team_id, response.status_code)
            if response.is_success:
                print(
                    json.dumps(
                        [
                            {
                                k: p.get(k)
                                for k in ("id", "name", "accountId", "framework", "rootDirectory", "link")
                            }
                            for p in response.json().get("projects", [])
                        ]
                    )
                )
