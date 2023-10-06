# 패키지의 `__init__.py`에 모듈 모아놓는 이유
### 모듈 엑세스가 편해진다
- 패키지만 불러와도 `__init__.py`에 있는 모듈들 불러올 수 있음

```python
# mypackage의 __init__.py에 mymodule import한 경우
import mypackage
result = mypackage.mymodule.my_function()
```

### 가시성 향상
- 모아놓은 모듈을 보고 뭐 사용하는지 확인 가능

<br><br>



# Why generator for DB Dependency? (🚧 WIP)

DB 의존성 주입에서, 보통 DB session 연결과 닫을 때는 시작과 끝을 깔끔하게 처리해주는 `Context Manager`로 처리해야한다고 생각했는데, <br>`Generator`를 이용해서 그 처리를 해주더라. <br>
바로 아래와 같이 말이다.
```python
def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> models.User:
    ...
    user = crud.user.get(db, id=token_data.sub)
    ...
    return user

```


<br>


비동기 요청에서 `Dependency`를 `context manager`로 사용하면 매 요청마다 새로운 `context`를 생성해야해서 리소스를 많이 잡아먹기 때문에, <br>
`generator`를 이용해서 동적으로 값을 생성하고 처리하는 듯 하다. <br>
하지만, DB 세션 연결과 같이 무조건 끝을 닫아줘야하는 처리에 관해서는 context manager같이 동작하는 것이 필요함에 따라 논의가 이루어졌고, <br> 그렇게 `context manager` 와 비슷한 형식의 generator dependency가 생긴 듯.


<br>

2019년에 FastAPI의 이슈 [Contextmanager as dependency · Issue #49 · tiangolo/fastapi](https://github.com/tiangolo/fastapi/issues/49) 에서 논의가 되었고 [Dependencies with yield (used as context managers)
#595](https://github.com/tiangolo/fastapi/pull/595)에서 context manager과 비슷한 형식의 dependency가 적용 된 듯. <br>
내부적으로는 아래와 같이 context manager decorator를 이용해서 generator를 conetx manager like하게 만드는 듯

```python
async def solve_generator(
    *, call: Callable, stack: AsyncExitStack, sub_values: Dict[str, Any]
) -> Any:
    if inspect.isgeneratorfunction(call):
        cm = contextmanager_in_threadpool(contextmanager(call)(**sub_values))
    elif inspect.isasyncgenfunction(call):
        cm = asynccontextmanager(call)(**sub_values)
    return await stack.enter_async_context(cm)

```

<br>

FastAPI의 문서에서도 FastAPI의 context manager와 비슷한 형식의 Dependency는 
- [@contextlib.contextmanager](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager)
- [@contextlib.asynccontextmanager](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager)

이 두 context manager를 Dependency 내부에서 사용을 한다고 한다. (https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/#__tabbed_1_1) <br>



<br><br>

---

TODO <br>
https://medium.com/@sumeetsarkar/trinity-of-context-managers-generators-decorators-4809a991c76b <br>
이거 참고해서 정리하기~~