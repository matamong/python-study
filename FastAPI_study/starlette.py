import functools
from tkinter import SE
import typing
from fastapi import WebSocket
from fastapi.concurrency import run_in_threadpool

from fastapi.responses import PlainTextResponse 

###
# Type을 Starlette으로 정한 AppType 제네릭을 사용하면 Starlette 클래스의 서브클래스만 허용된다.
# 이는 Starlette 클래스의 서브클래스만 AppType으로 사용할 수 있다는 뜻이다.
# 쉽게 말하면, Starlette 클래스의 서브클래스만 인자로 받을 수 있다는 뜻이다.
###
AppType = typing.TypeVar("AppType", bound="Starlette")

class Starlette:
    """
    어플리케이션 인스턴스를 생성한다.
    """
    def __init__(
        self: "AppType",
        debug: bool = False,

        # typing.Sequence는 list, tuple, range 등의 시퀀스 타입을 의미한다. Set은 포함되지 않는다.
        routes: typing.Optional[typing.Sequence[BaseRoute]] = None
    ) -> None:
        pass


####################
# 이 밑으로 BaseRoute에 대한 공부
####################
from enum import Enum
from starlette.datastructures import URLPath
from starlette.websockets import WebSocketClose

# MutalbleMapping은 dict와 같은 변경가능한(Mutable) 매핑 타입의 특성을 정의한다.
Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]

# typing.Callable은 함수의 타입을 정의한다.
# 예를 들어, typing.Callable[[int, int], int]는 int형 인자 2개를 받아서 int형을 반환하는 함수의 타입을 의미한다.
# typing.Awaitable은 awaitable 객체의 타입을 정의한다.
# 예를 들어, typing.Awaitable[int]는 int형 awaitable 객체의 타입을 의미한다.
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]

class Match(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2

class BaseRoute:
    """
    Starlette의 BaseRoute
    Starlette.routing에 정의되어 있다. 
    """

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        """
        라우트가 scope와 일치하는지 확인한다.
        Scope는 웹 프레임워크에서 사용되는 용어로,
        request, response과 관련된 정보를 포함하는 dicrioanry이다.
        여기서 Scope는 ASGI의 scope이다.
        Scope는 어플리케이션의 상태 및 환경정보를 포함되어 있으며,
        Routing과 Middleware 처리에 사용된다.

        params:
            scope: ASGI 요청의 Scope 객체
                    Scope 객체는 일반적으로 다음과 같은 정보를 포함한다:
                        type: 현재 요청의 유형을 나타내는 문자열 (예: "http.request").
                        http_version: HTTP 버전 (예: "1.1").
                        method: HTTP 메서드 (예: "GET", "POST" 등).
                        path: 요청된 URL 경로 (예: "/api/users").
                        headers: HTTP 헤더 정보를 담고 있는 딕셔너리.
                        query_string: URL 쿼리 문자열.
                        scheme: HTTP 또는 HTTPS와 같은 프로토콜 스킴.
        
        return:
            Tuple[Match, Scope]
                Match: 라우트가 scope와 일치하는지 여부를 나타내는 Match 객체
                Scope: 일치하는 경우, 일치하는 부분을 제외한 나머지 Scope 객체
        
        """
        raise NotImplementedError() # 이 메서드가 꼭 구현되어야 한다는 뜻이다.
    
    def url_path_for(self, name: str, **path_params: typing.Any) -> URLPath:
        """
        라우트의 URL 경로를 생성한다.
        가변적인 path_params를 받아서 URLPath를 반환한다.

        params:
            name: 라우트의 이름
            path_params: 가변적인 path 파라미터
        
        return:
            URLPath: 라우트의 URL 경로를 나타내는 URLPath 객체
        """
        raise NotImplementedError()

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI 요청을 처리한다.
        
        params:
            Scope: ASGI 요청의 Scope 객체
            Receive: ASGI 요청의 receive 콜백
            Send: ASGI 요청의 send 콜백
        """
        raise NotImplementedError()
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        이 메서드는 호출 가능한 클래스로서, Router에 의해 호출된다.
        Route는 거의 Router에 의해 호출되지만,
        그래도 간단한 앱에서는 route를 독립적으로 사용될 수도 있다. (인위적이긴 하지만)
        scope이 update되고, handle 메서드가 호출된다.

        params:
            Scope: ASGI 요청의 Scope 객체
            Receive: ASGI 요청의 receive 콜백
            Send: ASGI 요청의 send 콜백
        
        """
        match, child_scope = self.matches(scope)
        if match == Match.NONE:
            if scope["type"] == "http":
                response = PlainTextResponse("Not Found", status_code=404)
                await response(scope, receive, send)
            elif scope["type"] == "websocket":
                websocket_close = WebSocketClose
                await send({"type": "websocket.close", "code": 404})
            return
        
        scope.update(child_scope)
        await self.handle(scope, receive, send)


####################
# 이 밑으로 BaseRoute를 상속받는 Route에 대한 공부
####################

# inspect module은 함수, 클래스, 메서드 등의 속성 및 구조를 동적으로 검사하고 분석한다.
# 동적이란 말은 실행 중에 검사할 수 있다는 뜻이다.
import inspect
import re

from starlette.types import ASGIApp
from starlette._utils import is_async_callable
from starlette.requests import Request
from starlette.convertors import Convertor, CONVERTOR_TYPES # URL 경로 변환기

def get_name(endpoint: typing.Callable) -> str:
    """
    endpoint가 클래스인지 함수인지에 따라 이름을 반환한다.

    params:
        endpoint: 라우트의 endpoint로 사용되는 함수 또는 클래스 (Callable 타입)
    
    return:
        str: endpoint의 이름
    """
    if inspect.isfunction(endpoint) or inspect.isclass(endpoint):
        return endpoint.__name__
    return endpoint.__class__.__name__


def request_response(func: typing.Callable) -> ASGIApp:
    """
    함수나 코루틴을 받아서 ASGI 애플리케이션을 반환한다.
    """
    is_coroutine = is_async_callable(func)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        """
        Closure 함수로서, ASGI 애플리케이션을 반환한다.
        Closure, 함수 내부에 정의된 함수를 의미한다.
        함수 외부에서 직접 호출할 수 없고, 함수 내부에서만 호출할 수 있다.
        호출할 때는, 외부 함수의 반환값을 변수에 할당하고, 그 변수를 함수처럼 호출한다.
        예를 들어,
            def outer_func():
                def inner_func():
                    print("Hello, world!")
                return inner_func

            outer_func()()
            >>> Hello, world!

        이러한 Closure함수를 이용하는 주된 이유는, 함수 내부의 함수를 외부에서 접근할 수 없게 하기 위해서이다.
        콜백이나 데이터 은닉 등등에 이용된다.
        """
        request = Request(scope, receive=receive, send=send)
        if is_coroutine:
            # func가 코루틴인 경우 직접 호출
            response = await func(request)
        else:
            # func가 동기 함수인 경우 스레드 풀에서 실행
            """
            동기 함수를 스레드 풀에서 실행하는 이유는,
            동기 함수가 블로킹되면 ASGI 애플리케이션의 이벤트 루프가 블로킹될 수 있는데,
            이 때 스레드 풀을 사용하여 별도의 스레드에서 처리할 수 있게 할 수 있기 때문이다.
            """
            response = await run_in_threadpool(func, request)
        
        # 요청을 처리한 결과를 ASGI 애플리케이션으로 응답 전송
        await response(scope, receive, send)
    
    return app


# `{}`로 둘러쌓인 문자열을 찾음 `:`로 옵션도 찾음 eg. '{param}', '{parmam:int}'
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


def compile_path(
        path: str,
) -> typing.Tuple[typing.Pattern, str, typing.Dict[str, Convertor]]:
    """
    주어진 경로 str에서 변수와 그에 대한 정보를 추출하고, 정규식 패턴과 함께 반환한다.
    "/{username:str}" "{subdomain}.mydomain.org" 같은 str을 받아서
    (regex, format, {param_name:convertor}) 의 Tuple로 반환한다.
    
    **regex부분이라 심오하게 공부하진 않았고 Convertor를 어떻게 사용했는지만 참고**

    params:
        path: 경로 str
    return:
        Tuple[typing.Pattern, str, typing.Dict[str, Convertor]]
            typing.Pattern: 경로에 대한 정규식 패턴 (ex: "/(?P<username>[^/]+)")
            str: 경로에 대한 포맷 문자열 (ex: "/{username}")
            typing.Dict[str, Convertor]: 경로에 대한 파라미터 변환기 ({"username": StringConvertor()})

            Convertor 공부는 커밋 ee37dc 참고
    """
    is_host = not path.startswith("/")

    path_regex = "^"
    path_format = ""
    duplicated_params = set()

    idx = 0
    param_convertors = {}
    for match in PARAM_REGEX.finditer(path):
        param_name, convertor_type = match.groups("str") # 
        convertor_type = convertor_type.lstrip(":") # convertor_type의 맨 앞에 있는 ':'를 제거한다. (ex: ":str" -> "str")
        assert(
            convertor_type in CONVERTOR_TYPES
        ), f"Unknown path converter '{convertor_type}'"
        convertor = CONVERTOR_TYPES[convertor_type]

        path_regex += re.escape(path[idx:match.start()])
        path_regex += f"(?P<{param_name}>{convertor.regex})"

        path_format += path[idx:match.start()]
        path_format +=  "{%s}" % param_name

        if param_name in param_convertors:
            duplicated_params.add(param_name)
        
        param_convertors[param_name] = convertor

        idx = match.end()

        if duplicated_params:
            names = ", ".join(sorted(duplicated_params))
            ending = "s" if len(duplicated_params) > 1 else ""
            raise ValueError(f"Duplicate parameter name{s}: {names}")
        
        if is_host:
            path_regex += re.escape(path[idx:])
            path_format += path[idx:]
        else:
            path_regex += re.escape(path[idx:]) + "$"
        
        path_format += path[idx:]

        return re.compile(path_regex), path_format, param_convertors



class Route(BaseRoute):
    def __init__(
        self,
        path: str,
        endpoint: typing.Callable,
        *,
        methods: typing.Sequence[str] = None,
        name: typing.Optional[str] = None,
        include_in_schema: bool = True,
    ) -> None:
        
        # python에서 assert는 False일 경우 AssertionError를 발생시킨다.
        # [assert 조건, 에러메시지] 형식으로 사용한다. 유용한듯
        assert path.startswith("/"), "Routed paths must always start with '/'"

        self.path = path
        self.endpoint = endpoint
        self.name = get_name(endpoint) if name is None else name
        self.include_in_schema = include_in_schema # 스키마에 포함할지 여부


        endpoint_handler = endpoint

        """
        만약, endpoint_handler가 function.partial로 감싸진 함수라면, 
        while을 사용해서 일반 함수가 될 때까지 partial 함수를 깐다.

        functools.partial은 함수를 부분적으로 실행시키는 함수이다.
        함수의 일부인자를 고정시키고, 나머지 인자를 호출시에 넣어서 실행시킬 수 있다.
        예를 들면, 
            def add(a, b):
                return a + b
            
            add_1 = functools.partial(add, 1)
            add_1(2)
            >>> 3
        """
        while isinstance(endpoint_handler, functools.partial):
            endpoint_handler = endpoint_handler.func


        """
        endpoint_handler는 비동기 함수 또는 메서드라면,
        ASGI 애플리케이션을 생성하고 self.app에 할당한다.
        아니라면 endpoint 그대로 self.app에 할당한다.
        """
        if inspect.isfunction(endpoint_handler) or inspect.ismethod(endpoint_handler):
            self.app = request_response(endpoint)
            if methods is None:
                methods = ["GET"]
        else:
            # Endpoint가 클래스일 때. ASGI로 다룬다.
            self.app = endpoint
        
        if methods is None:
            self.mothods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                # GET 메서드가 있으면 HEAD 메서드도 추가한다. 
                # 왜냐하면, GET을 사용할 때 HEAD도 같이 사용을 하기로 약속되어 있기 때문이다.
                # 왜 약속을 했냐면, GET과 HEAD를 동시에 써야 효율성, 네트워크 이득, 캐싱등에 좋기 때문이다.
                # 예를 들면, 웹 브라우저가 각 이미지를 표시하기 전에 이미지해상도, 크기등을 알아야하는데
                # HEAD 메서드를 사용하지 않으면 GET으로 다운로드를 받은 다음에야 정보를 알아낼 수 있기 때문에
                # 효율적이지않다. GET으로 다운로드를 하기 전에 HEAD로 각 이미지의 메타데이터를 먼저 요청하면
                # 필요한 이미지만 다운로드하므로 로딩 시간이 단축된다.
                # 또는 HEAD로 브라우저, 서버의 캐싱된 웹 리소스가 최신인지 확인할 수 있기 때문에 효율적인 캐싱이 가능하다.
                self.methods.add("HEAD")
        
        self.path_regex, self.path_format, self.param_convertors = compile_path(path) # 컴파일된 경로 정규식, 포맷, 파라미터 변환기를 할당한다.


        def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
            if scope["type"] == "http":
                match = self.path_regex.match(scope["path"]) # path_regex와 path가 일치하는지 확인한다.
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convert(value)
