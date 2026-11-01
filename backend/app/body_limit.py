from fastapi import HTTPException
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        upload = scope["path"] == "/api/documents"
        maximum = 11 * 1024 * 1024 if upload else 65536
        message = (
            "Each PDF must be 10 MB or smaller."
            if upload
            else "The request is too large. Shorten your question or conversation history."
        )
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = maximum + 1
        if declared > maximum:
            return await JSONResponse({"detail": message}, status_code=413)(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            event = await receive()
            received += len(event.get("body", b""))
            if received > maximum:
                raise HTTPException(413, message)
            return event

        return await self.app(scope, limited_receive, send)
