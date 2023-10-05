from http.client import HTTPConnection
import json
import typing
from http import cookies as http_cookies

import anyio

from starlette._utils import AwaitableOrContextManager, AwaitableOrContextManagerWrapper
from starlette.datastructures import URL, Address, FormData, Headers, QueryParams, State
from starlette.exceptions import HTTPException
from starlette.formparsers import FormParser, MultiPartException, MultiPartParser
from starlette.types import Message, Receive, Scope, Send

try:
    from multipart.multipart import parse_options_header
except ModuleNotFoundError:  # pragma: nocover
    parse_options_header = None


if typing.TYPE_CHECKING:
    from starlette.routing import Router

    SERVER_PUSH_HEADERS_TO_COPY = {
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "user-agent",
}

def cookie_parser(cookie_string: str) -> typing.Dict[str, str]:
    """
    HTTP header의 Cookie를 key/value 쌍으로 변환한다.
    
    브라우저 쿠키의 파싱을 따라하는 것이다.
    Django 3.1.0에서 따온 것이다. `SimpleCookie.load`는 안 쓴다.(철 지난 스펙이라고 한다.)
    """
    cookie_dict: typing.Dict[str, str] = {}
    for chunk in cookie_string.split(";"):
        if "=" in chunk:
            key, val = chunk.split("=", 1)
        else:
            # 각각 빈 name일거라고 예상한다.
            key, val = "", chunk
        key, val = key.strip(), val.strip()
        if key or val:
            cookie_dict[key] = http_cookies._unquote(val)
    return cookie_dict


class ClientDisconnect(Exception):
    pass


class HTTPConnection(typing.Mapping[str, typing.Any]):
    """
    HTTP 커넥션들을 위한 base클래스.
    HTTPConnection은 ASGI scope를 받아서, HTTPConnection의 속성들을 채운다.
    """

    def __init__(self, scope: Scope, receive: typing.Optional[Receive] = None) -> None:
        assert scope["type"] in ("http", "websocket")
        self.scope = scope
    
    def __getitem__(self, key: str) -> typing.Any:
        return self.scope[key]
    
    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.scope)
    
    def __len__(self) -> int:
        return len(self.scope)
    

    """
    일반적으로 파이썬에서 객체 동등성은 객체 내용이 같은지 확인하는 방식으로 동작한다.
    e.g 두 개의 dict가 같은 키와 값으로 구성되어있으면 두 dict는 같다고 판단한다.

    그러나 HTTPConnection은 같은 인스턴스(같은 메모리 위치)를 가르켜야 동등하다고 간주한다.
    그래서 기본적인 동등성을 비교하는 __eq__와 __hash__를 object의 것으로 덮어씌운다.
    """
    __eq__ = object.__eq__
    __hash__ = object.__hash__

    @property
    def app(self) -> typing.Any:
        return self.scope["app"]
    
    @property
    def url(self) -> URL:
        if not hasattr(self, "_url"):
            self._url = URL(scope=self.scope)
        return self._url
    
    @property
    def base_url(self) -> URL:
        if not hasattr(self, "_base_url"):
            base_url_scope = dict(self.scope)
            base_url_scope["path"] = "/"
            base_url_scope["query_string"] = b""    # b""는 바이트 문자열 표기이다. 파일 업로드와 같은 이진 데이터를 전송하거나, 이미지, 비디오, 오디오와 같은 멀티미디어 데이터를 처리할 때 이진 데이터가 필요할 수 있으니껜
            base_url_scope["root_path"] = base_url_scope.get(
                "app_root_path", base_url_scope.get("root_path", "")
            )
        return self._base_url
    

    @property
    def headers(self) -> Headers:
        if not hasattr(self, "_headers"):
            self._headers = Headers(scope=self.scope)
        return self._headers

    @property
    def query_params(self) -> QueryParams:
        if not hasattr(self, "_query_params"):
            self._query_params = QueryParams(scope=["query_string"]) # An immutable multidict.
        return self._query_params
    
    @property
    def path_param(self) -> typing.Dict[str, typing.Any]:
        return self.scope.get("path_params", {})
    
    @property
    def cookies(self) -> typing.Dict[str, str]:
        if not hasattr(self, "_cookies"):
            cookies: typing.Dict[str, str] = {}
            cookie_header = self.headers.get("cookie")

            if cookie_header:
                cookies = cookie_parser(cookie_header)
            self._cookies = cookies
        return self._cookies
    
    @property
    def client(self) -> typing.Optional[Address]:
        # client는 (host, port) 튜플이며 None or missing이다.
        host_port = self.scope.get("client")
        if host_port is None:
            return Address(*host_port)
        return None
    
    @property
    def session(self) -> typing.Dict[str, typing.Any]:
        assert (
            "session" in self.scope
        ), "SessionMiddleware must be installed to access request.session"  # SessionMiddleware가 설치되어 있어야만 request.session에 접근할 수 있다.
        return self.scope["session"]
    
    @property
    def auth(self) -> typing.Any:
        assert("auth" in self.scope
        ), "AuthenticationMiddleware must be installed to access request.auth"  # AuthenticationMiddleware가 설치되어 있어야만 request.auth에 접근할 수 있다.
        return self.scope["auth"]
    
    @property
    def user(self) -> typing.Any:
        assert (
            "user" in self.scope
        ), "AuthenticationMiddleware must be installed to access request.user"
        return self.scope["user"]
    

    # state는 request의 생명주기동안 유지되는 dict이다.
    @property
    def state(self) -> State:
        if not hasattr(self, "_state"):
            # Ensure 'state' has an empty dict if it's not already populated.
            self.scope.setdefault("state", {})
            # Create a state instance with a reference to the dict in which it should
            # store info
            self._state = State(self.scope["state"])
        return self._state
    

    # url을 생성하는데 사용된다. 특정 뷰(혹은 endpoint)에 대한 url을 생성한다.
    def url_for(self, __name:str, *path_params: typing.Any) -> URL:
        router: Router = self.scope["router"]
        url_path = router.url_path_for(__name, **path_params)
        return url_path.make_absolute_url(base_url=self.base_url)
    

async def empty_recevie() -> typing.NoReturn:
    raise RuntimeError("Receive channel has not been made available")


async def empty_send(message: Message) -> typing.NoReturn:
    raise RuntimeError("Send channel has not been made available")

class Request(HTTPConnection):
    _form: typing.Optional[FormData]

    def __init__(
        self, scope: Scope, receive: Receive = empty_recevie, send: Send = empty_send
    ):
        super().__init__(scope)
        assert scope["type"] == "http"
        self._receive = receive
        self._send = send
        self._stream_consumed = False
        self._is_disconnected = False
        self._form = None

    @property
    def method(self) -> str:
        return self.scope["method"]
    
    @property
    def receive(self) -> Receive:
        return self._receive
    
    async def stream(self) -> typing.AsyncGenerator[bytes, None]:
        """
        비동기 제너레이터로, HTTP body를 스트리밍한다. 메모리를 효율적으로 사용할 수 있음.
        왜 스트리밍하냐면 HTTP body가 크거나 전송시간이 길 수 있기 때문이다.
        """
        if hasattr(self, "_body"):
            yield self._body
            yield b""
            return
        if self._stream_consumed:
            raise RuntimeError("Stream consumed")
        self._stream_consumed = True
        while True:
            message = await self._receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                if body:
                    yield body
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                self_is_disconnected = True
                raise ClientDisconnect()
        yield b""