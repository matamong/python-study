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
