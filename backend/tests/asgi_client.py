from __future__ import annotations

import asyncio
import json as json_module
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Message, Scope


class ASGIResponse:
    def __init__(self, messages: list[Message]) -> None:
        start = next(message for message in messages if message["type"] == "http.response.start")
        self.status_code = start["status"]
        self.headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in start.get("headers", [])
        }
        self.content = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        self.text = self.content.decode("utf-8")

    def json(self) -> Any:
        return json_module.loads(self.text)


class TestClient:
    __test__ = False

    def __init__(self, app: ASGIApp, client: tuple[str, int] = ("127.0.0.1", 55000)) -> None:
        self.app = app
        self.client = client

    def __enter__(self) -> "TestClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, path: str, headers: Mapping[str, str] | None = None) -> ASGIResponse:
        return self.request("GET", path, headers=headers)

    def post(
        self,
        path: str,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> ASGIResponse:
        return self.request("POST", path, json=json, headers=headers)

    def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> ASGIResponse:
        parsed = urlsplit(url)
        request_headers = [(key.lower().encode("latin-1"), value.encode("latin-1")) for key, value in (headers or {}).items()]
        body = b""
        if json is not None:
            body = json_module.dumps(json).encode("utf-8")
            request_headers.append((b"content-type", b"application/json"))
        scope: Scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": parsed.scheme or "http",
            "path": parsed.path or "/",
            "raw_path": (parsed.path or "/").encode("ascii"),
            "query_string": parsed.query.encode("ascii"),
            "root_path": "",
            "headers": request_headers,
            "client": self.client,
            "server": ("testserver", 80),
            "state": {},
        }
        messages: list[Message] = []
        first_message = True

        async def receive() -> Message:
            nonlocal first_message
            if first_message:
                first_message = False
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: Message) -> None:
            messages.append(message)

        async def run_app() -> None:
            await self.app(scope, receive, send)

        asyncio.run(run_app())
        return ASGIResponse(messages)
