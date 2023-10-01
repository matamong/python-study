# Python Study :rage2:
파이썬을 씹고 뜯고 맛보고 즐기자 <br>
힘들 땐 고양이 영상을 보자. :cat2: :cat2: :cat2:
## 목차
- **:arrow_right: [Middleware](https://github.com/matamong/django-study/tree/main/django_study/middleware_study)**


<br><br>

# 왜 Generic을 사용하는가
https://docs.python.org/3/library/typing.html#typing.TypeVar <br>
https://stackoverflow.com/questions/57551899/what-the-code-t-typevar-t-means-in-a-pyi-file <br>



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
Key = TypeVar('Key')
Value = TypeVar('Value')

#`key`의 type은 `key_to_lookup`과 type이 맞아야한다.
# 이렇게 사용하기 위해 TypeVar로 type을 맞추는 것이다.
def lookup(input_dict: Dict[Key, Value], key_to_lookup: Key) -> Value:
    return input_dict[key_to_loopup]
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

_T = TypeVar("_T")

def func(a: _T, b: _T) -> _T:
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