import json
from operator import methodcaller
import re
import typing
from urllib import response
import webbrowser

from starlette import status
from starlette._utils import is_async_callable
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import Message, Receive, Scope, Send
from starlette.websockets import WebSocket


"""
Starlette의 HTTPEndpoint의 dispatch는 좀 다르다.
클래스인스턴스를 생성하지않고 클래스자체를 디스패치해서 요청을 처리한다잉.
요런 식으로.

class Homepage(HTTPEndpoint):
    async def get(self, request):
        return PlainTextResponse(f"Hello, world!")


class User(HTTPEndpoint):
    async def get(self, request):
        username = request.path_params['username']
        return PlainTextResponse(f"Hello, {username}")

routes = [
    Route("/", Homepage),
    Route("/{username}", User)
]

app = Starlette(routes=routes)


그리고 HTTP endpoint는 알맞는 handler와 연결시킬 요청 메서드가 없으면 405 Method Not Allowed를 반환한다.
"""
class HTTPEndpoint:
    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == "http"
        self.scope = scope
        self.receive = receive
        self.send = send
        self._allowed_methods = [
            method
            for method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
            if getattr(self, method.lower(), None) is not None
        ]
    
    def __await__(self) -> typing.Generator:
        return self.dispatch().__await__()
    
    async def dispatch(self) -> None:
        request = Request(self.scope, receive=self.receive)

        """
        HTTP규정상
        "HEAD" 메서드에 대한 처리를 따로 구현하지 않은 경우, 
        클라이언트가 "HEAD" 메서드로 요청을 보내더라도 서버는 기본적으로 GET 메서드와 동일한 처리를 수행.
        HEAD인데 지금 head처리가 없으면 get으로 처리한다는 뜻.
        """
        handler_name = (
            "get"
            if request.method == "HEAD" and not hasattr(self, "head")
            else request.method.lower()
        )

        handler: typing.Callable[[Request], typing.Any] = getattr(
            self, handler_name, self.method_not_allowed
        )
        is_aync = is_async_callable(handler)
        if is_aync:
            response = await handler(request)
        else:
            response = await run_in_threadpool(handler, request)
        await response(self.scope, self.receive, self.send)

    
    async def method_not_allowed(self, request: Request) -> Response:
        headers = {"Allow": ", ".join(self._allowed_methods)}
        if "app" in self.scope:
            raise HTTPException(status_code=405, headers=headers)
        return PlainTextResponse("Method Not Allowed", status_code=405, headers=headers)
    

class WebSocketEndpoint:
    """
    다음에 WebSocket공부할때
    """
    pass


