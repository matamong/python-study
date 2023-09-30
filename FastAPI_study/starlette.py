import functools
from tkinter import SE
import typing
from urllib import response
from fastapi import HTTPException, WebSocket
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

from starlette.types import ASGIApp
from starlette._utils import is_async_callable
from starlette.requests import Request


def NoMatchFound(Exception):
    """
    `.url_for(name, **path_params)`, `url_path_for(name, **path_params)`에 의해서 일어나며,
    맞는 route가 없을 때 발생한다.

    대체로 Exception의 경우 모듈 맨 위에 있어야하는거 잊지말기ㅣㅣ 여기선 공부용이니껜 여기 둠!
    """

    def __init__(self, name: str, path_params: typing.Dict[str, typing.Any]) -> None:
        params = ",".join(list(path_params.keys()))
        super().__init__(f'No route exists for name "{name}" and params "{params}".')


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


def replace_params(
        path: str,
        param_convertors: typing.Dict[str, Convertor],
        path_params: typing.Dict[str, str],
) -> typing.Tuple[str, dict]:
    """
    경로에 있는 파라미터 플레이스홀더를 실제 값으로 대체하고 대체된 경로와 업데이트된 파라미터 딕셔너리를 반환.

    params:
        path: 경로 문자열
        param_convertors: 파라미터의 이름과 파라미터 변환기를 매핑한 딕셔너리
        path_params: 경로 파라미터를 담고 있는 딕셔너리
    
    return:
        Tuple[str, dict]: 대체된 경로와 업데이트된 파라미터 딕셔너리
    """
    for key, value in list(path.parmas.items()):
        if "{" + key + "}" in path:
            convertor = param_convertors[key]
            value = convertor.to_string(value)
            path = path.replace("{" + key + "}", value)
            path_params.pop(key)
    return path, path_params


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

def websocket_session(func: typing.Callable) -> ASGIApp:
    """
    `func(session)` 코루틴을 받아서 ASGI 애플리케이션을 반환한다.
    """
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI 애플리케이션 함수.
        
        Args:
            scope (Scope): ASGI 요청 스코프.
            receive (Receive): 메시지 수신을 위한 함수.
            send (Send): 메시지 전송을 위한 함수.
        """
        session = WebSocket(scope, receive=receive, send=send)
        await func(session)
    return app


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
            self.methods = None
        else:
            self.methods = {method.upper() for method in methods}
            if "GET" in self.methods:
                self.methods.add("HEAD")

        self.path_regex, self.path_format, self.param_convertors = compile_path(path)
    

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        if scope["type"] == "http":
            match = self.path_regex.match(scope["path"])
            if match:
                matched_params = match.groupdict()
                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].convertor(value) 
                path_params = dict(scope.get("path_params", {})) # dictionary의 원하는 데이터를 안전하게 불러올 수 있음 오 굿굿
                path_params.update(matched_params)
                child_scope = {"endpoint": self.endpoint, "path_params": path_params}
                if self.methods and scope["method"] not in self.methods:
                    return Match.PARTIAL, child_scope
                else:
                    return Match.FULL, child_scope
        return Match.NONE, {}


    def url_path_for(self, __name: str, **path_params: typing.Any) -> URLPath:
        """
        라우트의 URL 경로를 생성한다.
        """
        seen_params = set(path_params.keys())
        expected_params = set(self.param_convertors.keys())

        if __name != self.name or seen_params != expected_params:
            raise NoMatchFound(__name, path_params)

        path, remaining_params = replace_params(
            self.path_format, self.param_convertors, path_params
        )
        assert not remaining_params
        return URLPath(path=path, protocol="http")
    

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI 요청을 처리한다. 그래서 코루틴이다.
        """
        if self.methods and scope["method"] not in self.methods:
            headers = {"Allow": ", ".join(self.methods)}
            if "app" in scope:
                raise HTTPException(status_code=405, headers=headers)
            else:
                response = PlainTextResponse(
                    "Method Not Allowed", status_code=405, headers=headers
                )
            await response(scope, receive, send)
        else:
            await self.app(scope, receive, send)
    

    def __eq__(self, other: typing.Any) -> bool:
        return(
            isinstance(other, Route)
            and self.path == other.path
            and self.endpoint == other.endpoint
            and self.methods == other.methods
        )


    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        methods = sorted(self.methods or [])
        path, name = self.path, self.name
        return f"{class_name}(path={path!r}, name={name!r}, methods={methods!r})" 
    


class WebSocketRoute(BaseRoute):
    """
    비슷해서 패스
    """
    pass


class Mount(BaseRoute):
    def __init__(
        self,
        path: str,
        app: typing.Optional[ASGIApp] = None,
        routes: typing.Optional[typing.Sequence[BaseRoute]] = None,
        name: typing.Optional[str] = None,
        *,
        middleware: typing.Optional[typing.Sequence[Middleware]] = None,
    ) -> None:
        assert path == "" or path.startswith("/"), "Routed paths must always start with '/'"
        assert(
            app is not None or routes is not None
        ), "Either an 'app' or 'routes' must be provided."
        self.path = path.rstrip("/")
        if app is not None:
            self._base_app: ASGIApp = app
        else:
            self._base_app = Router(routes=routes)
        self.app = self._base_app
        if middleware is not None:
            for cls, options in reversed(middleware):
                """
                미들웨어는 순서가 중요하다.
                그러므로 여기서 미들웨어를 역순으로 stack에 쌓는다.
                그래서 맨 마지막에 쌓인 미들웨어가 가장 먼저 실행된다.
                """
                self.app = cls(self.app, **options)
        self.name = name
        self.path_regex, self.path_format, self.param_convertors = compile_path(
            self.path + "/{path:path}"
        )