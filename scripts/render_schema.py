"""Inspect the current official Render create-service request schema."""

import json

import httpx

spec = httpx.get("https://api-docs.render.com/openapi/render-public-api-1.json", timeout=30).json()
operation = spec["paths"]["/services"]["post"]
schema = operation["requestBody"]["content"]["application/json"]["schema"]
print(json.dumps(schema, indent=2))
for name in (
    "serviceDetails",
    "webServiceDetails",
    "servicePOST",
    "webServiceDetailsPOST",
    "serviceCreate",
    "service",
):
    if name in spec.get("components", {}).get("schemas", {}):
        print(name, json.dumps(spec["components"]["schemas"][name], indent=2))
