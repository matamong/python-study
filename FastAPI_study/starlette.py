"""
Starlette의 routing에 대한 공부.
https://www.starlette.io/routing/
"""

### 참고 모듈
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
###



import functools
from tkinter import SE
import trace
import typing
from urllib import response
from xml.etree.ElementInclude import include
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
        요약: ASGI 요청과 현재 Route의 경로를 일치시키고, 일치한 경우에 대한 정보를 반환
        
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
import contextlib
import traceback

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
    """
    URL 경로와 뷰 함수(핸들러)를 연결하는 역할.
    각 `Route`객체는 특정 URL 경로와 연결된 뷰 함수를 가지고 있다.
    요청이 해당 경로로 들어오면 연결된 뷰 함수를 호출한다.
    """
    def __init__(
        self,
        path: str,
        endpoint: typing.Callable, # 단일 request를 받고 response를 내보내는 동기나 비동기함수 HTTPEndpint. 혹은 ASGI interface를 구현한 클래스 (Starlette의 HTTPEndpoint같은거)
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
    """
    path와 해당 경로에 연결된 app 또는 route 설정,
    middleware 적용
    """

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

    
    @property # 읽기 전용 속성을 만들 때 사용한다. 함수를 속성처럼 사용할 수 있다. 이 말인 즉슨, 함수를 호출할 때 ()를 붙이지 않아도 된다는 뜻이다.
    def routes(self) -> typing.List[BaseRoute]:
        return getattr(self._base_app, "routes", [])
    

    def matches(self, scope: Scope) -> typing.Tuple[Match, Scope]:
        if scope["type"] in ("http", "websocket"):
            path = scope["path"]
            match = self.path_regex.match(path)
            if match:
                
                """
                path를 정규식과 비교하여 일치하는 경우,
                정규식 패턴에 의해 일치된 그룹들을 딕셔너리로 가져오는 부분
                self.path_regex 패턴에 정의된 경로에 다음과 같은 그룹들이 있다고 가정하자.
                    {user:str}
                    {post_id:int}
                    {category:str}
                
                주어진 path 문자열이 '/matamong/123/backend' 라면, matched_params는 다음과 같다.
                    "user": "john" (str 그룹)
                    "post_id": "123" (int 그룹)
                    "category": "tech" (str 그룹)
                
                """
                matched_params = match.groupdict()


                for key, value in matched_params.items():
                    matched_params[key] = self.param_convertors[key].converter(value)  # 경로의 각 매개변수를 해당하는 변환기를 사용하여 변환
                remaining_path = "/" + matched_params.pop("path") # 남은 경로를 가져오고, "path" 매개변수는 따로 처리 eg. /api/users/{path:path}
                matched_path = path[: -len(remaining_path)] # 일치하는 경로를 추출
                path_parmas = dict(scope.get("path_parmas", {}))
                path_parmas.update(matched_params) # 경로 매개변수를 업데이트
                root_path = scope.get("root_path", "")

                # 새로운 스코프를 생성하여 경로 매개변수 및 경로 정보를 전달
                child_scope = {
                    "path_params": path_parmas,
                    "app_root_path": scope.get("app_root_path", root_path),
                    "root_path": root_path + matched_path,
                    "path": remaining_path,
                    "endpoint": self.app,
                }
                return Match.FULL, child_scope
            return Match.NONE, {}
 
 # 이하 다 비슷해서 생략


"""
PEP에서는 TypeVar를 사용할 때 _T, _U, _V 등의 이름을 사용하라고 권장한다.
만약 인자가 있는 경우에는 그냥 사용해도 된다.

eg.
  _T = TypeVar("_T")
  _P = ParamSpec("_P")
  AddableType = TypeVar("AddableType", int, float, str)
  AnyFunction = TypeVar("AnyFunction", bound=Callable)
"""
_T = typing.TypeVar("_T")


class _AsyncLiftContextManager(typing.AsyncContextManager[_T]):
    """
    비동기 컨텍스트 매니저를 동기 컨텍스트 매니저로 변환하는 wrapper 클래스
    동기와 비동기 컨텍스트 매니저의 호환성을 위해서 사용.
    """
    def __init__(self, cm: typing.ContextManager[_T]):
        self._cm = cm
    
    async def __aenter__(self) -> _T:
        return self._cm.__enter__()

    async def __aexit__(
        self,
        exc_type: typing.Optional[typing.Type[BaseException]],
        exc_value: typing.Optional[BaseException],
        traceback: typing.Optional[types.TracebackType],
    ) -> typing.Optional[bool]:
        return self._cm.__exit__(exc_type, exc_value, traceback)



################################
# 이 밑으로는 Router에 대한 공부
################################
import warnings

from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.types import Lifespan
from starlette.datastructures import URL

# wrapper 공부하기
def _wrap_gen_lifspan_context(
    lifespan_context: typing.Collable[[typing.Any], typing.Generator]
) -> typing.Collable[[typing.Any], typing.AsyncContextManager]:
    """
    함수를 래핑하고, 일반적인 제너레이터 컨텍스트 매니저를 비동기 컨텍스트 매니저로 변환하는 데 사용.
    일반적인 동기 코드와 비동기 코드 간의 호환성을 유지하면서 컨텍스트 매니저를 적용하는 것이 목적이다.
    
    `lifespan_context`는 일반적인 제너레이터 컨텍스트 매니저를 반환하는 함수이다. 
    이 함수를 비동기 컨텍스트 매니저로 변환하여 반환한다.

    """

    cmgr = contextlib.contextmanager(lifespan_context) # 제너레이터 컨텍스트 매니저를 생성한다.

    @functools.wraps(cmgr) # 원래 함수를 래핑하는 데 사용된다. 원래 함수의 정보를 유지한다.
    def wrapper(app: typing.Any) -> _AsyncLiftContextManager:
        return _AsyncLiftContextManager(cmgr(app))
    
    return wrapper


class _DefaultLifespan:
    """
    Router 클래스가 사용하는 기본 라이프스팬(Lifespan) 클래스이다.
    애플리케이션의 시작 및 종료 시점에 특정 동작을 수행할 수 있도록 한다.
    """
    def __init__(self, router: "Router"):
        self._router = router
    
    async def __aenter__(self) -> None:
        # aplication의 시작 시점에 필요한 동작 eg. app 초기화, DB 연결
        await self._router.startup()
    
    async def __aexit__(self, *exc_info: object) -> None: # *exc_info는 가변인자를 의미한다. 즉, 여러 개의 인자를 받을 수 있다는 뜻이다.
        # aplication의 종료 시점에 필요한 동작
        await self._router.shutdown()

    def __call__(self: _T, app: object) -> _T:
        # 호출될 때
        return self


class Router:
    """
    Route들을 모아서 관리하는 클래스
    """
    def __init__(
        self,
        routes: typing.Optional[typing.Sequence[BaseRoute]] = None,
        redirect_slashes: boot =True,
        default: typing.Optional[ASGIApp] = None,
        on_startup: typing.Optional[typing.Sequence[typing.Callable]] = None,
        on_shutdown: typing.Optional[typing.Sequence[typing.Callable]] = None,
        
        # Router 클래스가 어떤 타입의 최상위 애플리케이션을 다룰지를 정적으로 알 수 없기 때문에 typing.Any로 제네릭을 설정
        # FastAPI, Flask, Django, RESTful API 등등...
        lifespan: typing.Optional[Lifespan[typing.Any]] = None,
    ) -> None:
        self.routes = [] if routes is None else list(routes)
        self.redirect_slashes = redirect_slashes
        self.default = self.not_found if default is None else default
        self.on_startup = [] if on_startup is None else list(on_startup)    # 시작 될 때 실행해야 할 작업들
        self.on_shutdown = [] if on_shutdown is None else list(on_shutdown) # 종료될 때 실행해야 할 작업들

        if on_startup or on_shutdown:
            warnings.warn(
                "on_startup이랑 on_shutdown은 deprecated됐다잉. lifespand를 써랏"
                "https://www.starlette.io/lifespan/."
                "오 이렇게 끊어서 사용해도 되네 굿",
                DeprecationWarning
            )
        
        if lifespan is None:
            self.lifespan_context: Lifespan = _DefaultLifespan(self)
        
        elif inspect.inspect.isasyncgenfunction(lifespan):
            warnings.warn(
                "async generator 함수는 deprecated되었다잉. @contextlib.asynccontextmanger 함수를 써랏",
                DeprecationWarning,
            )
            self.lifespan_context = contextlib.asynccontextmanager(
                lifespan, # type: ignore[arg-type] <-- type error 무시하는 주석
            )
        elif inspect.isgeneratorfunction(lifespan):
            warnings.warn(
                "generator 함수는 deprecated되었다잉. @contextlib.contextmanger 함수를 써랏",
                DeprecationWarning,
            )
            self.lifespan_context = _wrap_gen_lifspan_context(
                lifespan, # type: ignore[arg-type]
            )
        else:
            self.lifespan_context = lifespan

    async def not_found(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            websocket_close = WebSocketClose()
            await websocket_close(scope, receive, send)
            return
        
        # Starlette 애플리케이션 내에서는 예외 처리를 사용하여 응답을 처리하고, 
        # 일반 ASGI 앱에서는 예외를 발생시키지 않고 응답을 반환한다.
        # 일반 ASGI 앱은 Starlette와 같은 예외 처리 방식을 가지고 있지 않을 수 있으니껜.
        if "app" in scope:
            raise HTTPException(status_code=404)
        else:
            response = PlainTextResponse("Not Found", status_code=404)
        await response(scope, receive, send)
    

    async def url_path_for(self, __name: str, **path_params) -> URLPath:
        for route in self.routes:
            try:
                return route.url_path_for(__name, **path_params)
            except NoMatchFound:
                pass 
        raise NoMatchFound(__name, path_params) # 모든 route에서 일치하는 경로를 찾지 못한 경우, NoMatchFound 예외를 발생시킨다.
    

    async def startup(self) -> None:
        """
        `.on_startup` 이벤트 핸들러들을 구동한다. 비동기라면 비동기로, 동기라면 동기로.
        """
        for handler in self.on_startup:
            if is_async_callable(handler):
                await(handler)
            else:
                handler()
    
    async def lifespan(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
         ASGI lifespan message를 처리하여 애플리케이션의 시작과 종료 시점에 필요한 작업을 관리한다.
        (ASGI lifespan message는 우리가 app의 startup과 shutdown 이벤트들을 관리할 수 있게해주는 메시지 프로콜임.)
        """
        started = False
        app: typing.Any = scope.get("app")
        await receive() # ASGI 메시지 수신
        try:
            async with self.lifespan_context(app) as maybe_state:
                if maybe_state is not None:
                    if "state" not in scope:
                        raise RuntimeError(
                            '서버는 lifespan scope에서 "state"를 지원하지 않습니다잉'
                        )
                    scope["state"].update(maybe_state)  # 애플리케이션의 상태 정보를 scope에 업데이트
                await send({"type": "lifespan.startup.complete"})
                started = True
                await receive()
        except BaseException:
            exc_text = traceback.format_exc()
            if started:
                await send({"type": "lifespan.startup.failed", "message": exc_text})
            else:
                await send({"type": "lifespan.startup.failed", "message": exc_text})
            raise
        else:
            await send({"type": "lifespan.shutdown.complete"})
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Router 클래스의 메인 entry point.
        """
        assert scope["type"] in ("http", "websocket", "lifespan")

        if "router" not in scope:
            scope["router"] = self
        
        if scope["type"] == "lifespan":
            await self.lifespan(scope, receive, send)
            return
        
        partial = None

        for route in self.routes:
            # 받은 scope에서 route들이 매치되는지 찾고 있으면 넘겨준다
            match, child_scope = route.mathces(scope)
            if match == Match.FULL:
                scope.update(child_scope)
                await route.handle(scope, receive, send)
                return
            elif match == Match.PARTIAL and partial is None:
                partial = route
                partial_scope = child_scope

        if partial is not None:
            # partial 매치들을 다룬다. endpoint가 request를 처리할 수 있지만, 선호되는 option은 아닐 때 사용된다.
            # 405 Method Not Allowed를 다룰 때 사용된다고한다.
            scope.update(partial_scope)
            await partial.handle(scope, receive, send)
            return
        
        # 슬래시가 없는 경우에 슬래시가 있는 URL로 리디렉션
        if scope["type"] == "http" and self.redirect_slashes and scope["path"] != "/":
            redirect_scope = dict(scope)
            if scope["path"].endswith("/"):
                redirect_scope["path"] = scope["path"].rstrip("/")
            else:
                redirect_scope["path"] = scope["path"] + "/"
        
            for route in self.routes:
                mathc, child_scope = route.matches(redirect_scope)
                if match != Match.NONE:
                    redirect_url = URL(scope=redirect_scope)
                    response = RedirectResponse(url=str(redirect_url))
                    await response(scope, receive, send)
                    return
        
        await self.default(scope, receive, send)

        def __eq__(self, other: typing.Any) -> bool:
            return isinstance(other, Router) and self.routes == other.routes
        
        def mount(
            self, path: str, app: ASGIApp, name: typing.Optional[str] = None
        ) -> None: # pragma: no cover <-- 테스트에서 제외
            """
            """
            route = Mount(path, app=app, name=name)
            self.routes.append(route)

        def host(
            self, host: str, app: ASGIApp, name: typing.Optional[str] = None
        ) -> None: ...

        def add_route(
            self, 
            path: str,
            endpoint:typing.Callable,
            methods: typing.Optional[typing.List[str]] = None,
            name: typing.Optional[str] = None,
            include_in_schema: bool = True,
        ) -> None: # pragma: noconver
            route = Route(
                path,
                endpoint=endpoint,
                methods=methods,
                name=name,
                include_in_schema=include_in_schema,
            )
            self.routes.appned(route)
        
        ...

            
            
