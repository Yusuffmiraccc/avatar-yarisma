"""Streaming request-body limit for document uploads (before multipart parsing)."""

import re
from uuid import uuid4

from starlette.responses import JSONResponse


class UploadBodyLimitMiddleware:
    def __init__(self, app, *, path: str, max_body_bytes: int):
        self.app = app
        self.path = path
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") != "POST" or scope.get("path") != self.path:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length is not None:
            try:
                if int(length) > self.max_body_bytes:
                    await self._reject(scope, receive, send, headers)
                    return
            except ValueError:
                pass

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _BodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLarge:
            await self._reject(scope, receive, send, headers)

    async def _reject(self, scope, receive, send, headers):
        supplied = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = supplied if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied) else str(uuid4())
        response = JSONResponse(
            status_code=413,
            content={"error": {"code": "PAYLOAD_TOO_LARGE", "message": "İstek gövdesi izin verilen boyutu aşıyor."},
                     "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )
        await response(scope, receive, send)


class _BodyTooLarge(Exception):
    pass
