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

<br>

# 왜 Generic을 사용하는가


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
- `lst`가 list임을 명시해줌으로써 런타임 오류를 방지할 수 있다.
- 제네릭 타입 자체는 어떤 데이터 특정한 데이터타입을 나타내지 않는다.
- 함수 호출 시 전달되는 인자에 따라 동적으로 결정

<br><br>

- 한정도 가능
```python
from typing import TypeVar

AnyStr = TypeVar('AnyStr', str, bytes)

def concat(x: AnyStr, y: AnyStr) -> AnyStr:
    return x + y
```