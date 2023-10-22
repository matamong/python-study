"""
https://github.com/tiangolo/fastapi/commits/master/fastapi/concurrency.py
"""


from contextlib import asynccontextmanager
import types
from typing import AsyncGenerator, ContextManager, TypeVar
from anyio import CapacityLimiter
import anyio
from fastapi import concurrency # 참고


_T = TypeVar("_T")

@asynccontextmanager
async def contextmanager_in_threadpool(
    cm: ContextManager[_T],
) -> AsyncGenerator[_T, None]:
    """
    contextmanager의 __exit__ 메서드 용량 제한을 없애는 이유:
        만약 컨텍스트 매니저가 내부 리소스 풀(예: 데이터베이스 연결 풀)을 가지고 있다면, 
        제한을 없애지 않으면 경쟁 조건과 데드락이 발생할 수 있기 때문이다. 
        따라서 __exit__ 메서드를 용량 제한(스레드 수에 대한 제한) 없이 실행하여 이러한 문제를 피하고
        컨텍스트 매니저의 안전한 동작을 보장한다.
        각 호출마다 새로운 limiter를 만들기 때문에 0이 아닌 임의의 제한자가 작동한다.(1은 임의로 선택한 값이다.)


    참고:

        Issue
        https://github.com/tiangolo/fastapi/issues/3205

        PR
        https://github.com/tiangolo/fastapi/pull/5122
    
        Commit
        https://github.com/tiangolo/fastapi/commit/f8460a8b54fd4975ca64c7fbe8d516740781f0df


    일어났던 이슈:
        동기적인 DB에 연결할 때, 의존성 주입을 사용하면 요청이 많을 때 데드락이 나는 이슈가 있었다.
        이슈에서는 동기적 DB에서 의존성 주입 대신에 엔드포인트 내에서 context manager 방식으로 세션을 처리하면 데드락이 안 났다고 한다.

    이슈 디버깅 결론:
        Dependency들과 path작업들은 함수(def함수만 해당)로 정의되어 anyio 스레드풀에서 실행된다.
        `db.execute`는 블로킹 call(특정 작업이 완료될 때까지 제어를 반환하지 않고 대기하는 call)이며, 이로 인해 풀 내의 worker들이 path 작업 함수 내에서 블록되었다.
        이는 dependency 생성자가 `finally` 블록을 호출하지 못하게 했고 결과적으로 SQLAlchemy의 연결이 해체되지 못하도록 했던 것이다.
        즉, db.execute와 같은 블로킹 호출이 path 작업 함수 내에서 실행될 때, 경로 작업 함수가 실행 중에 모든 스레드가 블록되어 버려, 
        의존성 생성자의 finally 블록이 호출되지 않아 SQLAlchemy 연결이 해제되지 못하게 되지 못 한 것이다.

        
    해결 방법:
        일단 local capacity limiter를 둬서 용량 제한을 없앤듯.
    """
    exit_limiter = CapacityLimiter(1)   # 최대 1개의 스레드만 실행
    try:
        yield await concurrency.run_in_threadpool(cm.__enter__) # 컨텍스트 매니저의 __enter__ 실행
    except Exception as e:
        ok = bool(
            await anyio.to_thread.run_sync(
                cm.__exit__, type(e), e, None, limiter=exit_limiter
            )
        )
        if not ok:
            raise 
    else:
        # 예외가 발생하지 않은 경우에도 __exit__ 메서드를 호출하여 정리
        await anyio.to_thread.run_sync(
            cm.__exit__, None, None, None, limiter=exit_limiter
        )



"""
CpacacityLimiter
"""
from anyio import get_asynclib

class CapacityLimiter:
    """
    __new__ :
        객체 생성 및 반환.
        불변(immutable) 객체를 생성하거나, 객체 생성 시 특별한 로직을 적용해야 할 때 사용
    
    __init__:
        객체 초기화

    example:
        class MyClass:
            def __new__(cls):
                # 객체 생성 및 반환
                instance = super(MyClass, cls).__new__(cls)
                instance.value = 10
                return instance

            def __init__(self):
                # 객체 초기화
                self.value = 20
    """
    def __new__(cls, total_tokens: float) -> CapacityLimiter:
        return get_asynclib().CapacityLimiter(total_tokens)
    
    async def __aenter__(self) -> None:
        raise NotImplementedError
    
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool | None:
        raise NotImplementedError
