# Python Study :rage2:
파이썬을 씹고 뜯고 맛보고 즐기자 <br>
힘들 땐 고양이 영상을 보자. :cat2: :cat2: :cat2:
## 목차
- **:arrow_right: [Middleware](https://github.com/matamong/django-study/tree/main/django_study/middleware_study)**

<br><br>

# UV
## install
### macOS/Linux
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```
### Windows(PowerShell)
```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

```
## 사용법
### 가상환경 생성
```
uv venv 
```
### 파이썬 설정
- 파이썬도 자체적으로 관리 가능.
```
uv python install 3.10

uv python list

# Python 3.10으로 가상 환경 생성
uv venv --python 3.10

# 혹은 Python 3.12로 가상 환경 생성 (다른 디렉토리에서 또는 기존 .venv 삭제 후)
# 기존 .venv를 삭제하고 새로 만들 경우:
# rm -rf .venv
# uv venv --python 3.12
```
```
source .venv/bin/activate # uv 써도 이렇게 활성화해야하는 듯
```
- `.python-version` 만들어서 지정할 수 도 있음. (uv가 pyenv처럼 인식함)
```
echo "3.11" > .python-version
```
- 가상 환경을 명시적으로 활성화할 필요 없이 uv run을 사용하면 uv가 현재 프로젝트의 설정(즉, .venv와 연결된 Python 버전)에 맞춰 스크립트를 실행
```
uv run python matamong.py
```
### 패키지관리
## `pyproject.toml`로 관리
- 루트 디렉토리에 `pyproject.toml` 생성
```
# pyproject.toml
[project]
name = "your-project-name" # 프로젝트 이름을 적절히 변경
version = "0.1.0"
description = "A short description of your project"

[build-system]
requires = ["setuptools>=61.0"] # 또는 ["hatchling"] 등 사용하는 빌드 백엔드
build-backend = "setuptools.build_meta" # 또는 "hatchling.build_meta" 등

[tool.uv]
# uv 관련 설정을 여기에 추가할 수 있습니다. (현재는 비워둬도 됨)
```
- `uv add` 로 인스톨
```
uv add llama-index-core
```
- 이 방식은 uv가 프로젝트 내 여러 독립적인 디렉토리를 하나의 패키지로 강제로 묶으려 하기 때문에 디렉토리가 많으면 복잡해짐. 그래서 본 프로젝트는 아래 `requirements.txt`방식을 사용
## `requirements.txt`로 관리
- 기존 `.venv` 방식 사용하면서 아래처럼 관리
```
uv pip install -r requirements.txt
uv pip uninstall llama-index-core
```
```
uv pip install llama-index-core
```
```
uv pip freeze > requirements.txt
```

<br><br>

# 왜 Generic을 사용하는가
https://docs.python.org/3/library/typing.html#typing.TypeVar <br>
https://stackoverflow.com/questions/57551899/what-the-code-t-typevar-t-means-in-a-pyi-file <br>

**Generic은 나중에 정해질 타입을 미리 임의로 정해놓는 것.**

<br><br>

```python
def add_and_return_sum(lst, a, b):
    lst.append(a)
    lst.append(b)
    result = 0
    for item in lst:
        result += item
    return result

my_list = [1, 2, 3]
total_sum = add_and_return_sum(my_list, 4, 5)
print(total_sum)
```

- `lst` 에 어떤 데이터타입이라도 올 수 있다. 이것은 런타임 오류를 발생시킬 것이다.

<br><br>

```python
from typing import List, TypeVar

T = TypeVar('T')

def add_and_return_sum(lst: List[T], a: T, b: T) -> T:
    lst.append(a)
    lst.append(b)
    result = 0
    for item in lst:
        result += item
    return result

my_list = [1, 2, 3]
total_sum = add_and_return_sum(my_list, 4, 5)
print(total_sum)
```
- `typing.TypeVar`는 다양한 type을 정의한 것이다. 만약 type을 정의하지않았다면, 모든 type이 유효하다.
- `lst`가 list임을 명시해줌으로써 런타임 오류를 방지할 수 있다.
- 제네릭 타입 자체는 어떤 데이터 특정한 데이터타입을 나타내지 않는다.
- 함수 호출 시 전달되는 인자에 따라 동적으로 결정
- 같은 type을 이용할 수 있게 하고싶을 때 type을 맞출 수 있다.
- 즉, 이 예시에서는 lst, a, b가 모두 같은 타입이어야 한다고 TypeVar를 이용해서 명시한 것이다. 



<br><br>


```python
from typing import TypeVar

AnyStr = TypeVar('AnyStr', str, bytes)

def concat(x: AnyStr, y: AnyStr) -> AnyStr:
    return x + y
```
- 한정도 가능

<br><br>

### 추가예시


```python
from typing import TypeVar

T = TypeVar('T')            # <-- 'T'는 어느 type이든지 될 수 있음
A = TypeVar('A', str, int)  # <-- 'A'는 str이거나 int여야함
```

<br>

```python
from typing import TypeVar, Dict
K = TypeVar('Key')
V = TypeVar('Value')

#`key`의 type은 `key_to_lookup`과 type이 맞아야한다.
# 이렇게 사용하기 위해 TypeVar로 type을 맞추는 것이다.
def lookup(input_dict: Dict[K, V], key_to_lookup: K) -> Value:
    return input_dict[key_to_loopup]

# 즉,딕셔너리에서 값을 찾는데, key의 타입이 Dict의 키 타입과 같아야 한다는 보장인 것
```

<br>

```python
B = TypeVar('B', float, int)

def add_x_and_y(x: B, y: B) -> B:
    return x + y

```

<br><br>

### python3.12 새로운 문법
python3.12에서는 TypeVar에 대해서 새로운 문법이 생긴듯.

```python

# 이 코드는
from typing import TypeVar

T = TypeVar("T")

def func(a: T, b: T) -> T:
    ...

# 3.12에서 다음과 같다.
def func[T](a: T, b: T) -> T:
    ...
```

<br><br><br>


# ContextManager
 리소스 관리와 관련된 작업을 보다 쉽게 처리하기 위한 프로토콜(Protocol) <br>
주로 `with` 문과 함께 사용되며, 리소스의 생성과 소멸을 효과적으로 관리. <br>
- `__enter__`와 `__exit__` 메서드를 구현하여 컨텍스트 관리자를 생성
- 주로 파일 열기 및 닫기, DB 연결 및 해제 등의 작업에 씀

## eg
```python
class FileManager:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_value, traceback):
        if self.file:
            self.file.close()

# 사용 예시
with FileManager("example.txt", "w") as file:
    file.write("Hello, ContextManager!")

# 이러면 파일이 자동으로 닫힘

```


<br><br><br>

# AsyncContextManager

비동기 코드에서 사용되는 컨텍스트 매니저를 정의하기 위한 Python의 타입 <br>
주로 `async with`문과 함께 사용됨.
- `__aenter__(self)`와 `__aexit__(self, exc_type, exc_value, traceback)` 를 구현하여 생성

## eg
```python

from contextlib import AsyncContextManager

class AsyncFileReaderWriter(AsyncContextManager):
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
    
    async def __aenter__(self):
        self.file = await open(self.filename, self.mode)
        return self.file
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.file.close()

# 사용 예시
async with AsyncFileReaderWriter("example.txt", "w") as file:
    await file.write("Hello, Async World!") # async with 구문을 빠져나올 때 파일이 자동으로 닫힘
```

<br><br><br>

# Asyncio

## Coroutine
https://docs.python.org/3/glossary.html#term-coroutine <br>
https://peps.python.org/pep-0492/ <br>

- Python3.5에서 시작됐다.(2015년에 나왔다니 생각보다 최근이군)
- 코루틴은 subroutines의 일반화 버전이다. subroutines는 한 포인트로 들어가고 다른 포인트로 나가는 방식이다. coroutine은 다양한 포인트에서 들어가고 나가고 다시 시작 될 수 있다. `async def` 와 함께 구현된다.

Coroutine은 async/await 구문을 사용해서 사용하지만 단순히 이것만 쓴다고 되는 것은 아니다. <br>
coroutine을 돌리기위해서 `asyncio`가 다음의 매커니즘을 제공한다. <br>

1. 최상위 entry 포인트에서 `asyncio.run()`를 사용
    ```python
    >>> import asyncio

    >>> async def main():
    ...    print('hello')
    ...    await asyncio.sleep(1)
    ...    print('world')

    >>> asyncio.run(main())

    hello
    world
    ```
2. Coroutine Awating

등등...

<br>

## Await
`await` 는 내부적으로 두 가지 동작을 한다.
- `await` 에 딸려있는 코루틴 함수(Awaitable 객체)를 `Event Loop`에 실행해달라고 등록
- 실행권을 `Event Loop`에게 줌

이 동작을 하다가 `Event Loop`는 코루틴이 종료되거나 에러가 발생하면 실행권을 돌려준다. <br>
즉, 비동기 작업을 정의하고 await를 사용하여 다른 작업의 완료를 기다리는 동안 실행을 중단하거나 양보하는데 사용하는 것이다.

<br>

## Event Loop
https://docs.python.org/3/library/asyncio-eventloop.html <br>
https://thinhdanggroup.github.io/event-loop-python/#understanding-the-event-loop-in-python <br>
https://www.pythontutorial.net/python-concurrency/python-event-loop/ <br>

### 날 계속 찾지마~ 내가 나중에 알려줄게!
이벤트 루프는 싱글 스레드 안에서 다양한 작업들을 관리하기 위한 스케쥴링 매커니즘이다. <br>

### Work Flow

![](https://www.pythontutorial.net/wp-content/uploads/2022/07/python-event-loop.svg)

- 작업 등록(register)
  - 실행해야 할 작업이나 함수를 대기 중인 상태로 등록.
  - 이 작업은 coroutines이라고도 알려져있다. 
  - 이벤트 루프는 이벤트 큐라는 자료 구조를 가지고 이 작업들의 큐를 관리한다.
  - e.g.
    - 사용자의 클릭 이벤트, 네트워크 요청, 타이머 이벤트 등등...
- 이벤트 감지
  - 이벤트 루프는 계속해서 새로운 이벤트들을 체크한다.
- 작업 실행
  - 이벤트가 감지되면 이벤트 루프는 큐를 바라보고 작업을 실행한다.
  - 여기서 중요한 것은!이벤트 루프는 오직 한 번에 한 작업만 실행할 수 있다는 것이다.
  - 그러나, 작업은 일시정지되거나 재개되면서 비동기의 매직을 보여주는 것이다.
- 실행 콜백
  - 작업이 콜백함수와 연관되어있다면, 이벤트루프는 작업이 끝나고 콜백을 해준다.


<br><br><br>