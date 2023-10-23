"""
FastAPI의 parameter function은
Path, Query, Header, Cookie, Body, Form, File, Depends 등등
다양한 유형의 HTTP request 데이터를 처리하는 함수이다.


Depends, Query, Body에서는 간편하게 Annotated를 사용하여 parameter function을 정의할 수 있다.
이 방식은 IDE와 type-checker가 type을 인지하게하면서 dependency와 type annotation을 동시에 사용할 수 있게 해준다.
(Annotated는 python 3.9에서 추가된 기능이다.)
"""

from typing import Annotated, Any, Callable, Optional, TypeAlias

from fastapi import Depends

# 기존 방식
async def handler(dep: MyClass = Depends(my_dependency)):
    ...

# Annotated 방식
async def handler(dep: Annotated[MyClass, Depends(my_dependency)]):
    ...

# 이런 방식으로도 사용할 수 있다.
MyDependecy: TypeAlias = Annotated[MyClass, Depends(my_dependency)]
async def handler(dep: MyDependecy):
    ...

"""
아래는 그와 관련된 issue, pr과 PEP-593 Annotated에 대한 설명이다.

issue:
    Support PEP 593 Annotated for specifying dependencies and parameters
    https://github.com/tiangolo/fastapi/issues/3323

pr:
    Add support for PEP-593 Annotated for specifying dependencies and parameters
    https://github.com/tiangolo/fastapi/pull/4871

    Fix parameterless Depends() with generics
    https://github.com/tiangolo/fastapi/pull/9479 (bug fix)

pep:
    https://peps.python.org/pep-0593/


위의 issue와 pr등을 정리해보자.

python의 typing.Annotated를 사용하면 기존 type에 metadata를 추가하고
이 metadata를 정적타입체크와 런타임에서 활용할 수 있게해준다.

"""

from fastapi import params

def Depends(
    dependency: Optional[Callable[..., Any]] = None, *, use_cache: bool = True
) -> Any:
    return params.Depends(dependency, use_cache=use_cache)



"""
fastapi.params

Depends 클래스는 파라미터로 함수 or 클래스를 받아서 그것을 의존성으로 제공하는 역할을 한다.
의존성 캐싱도 관리한다!
기본적으로 캐싱은 True로 설정되어있다.
캐싱을 사용하면 같은 의존성이 여러 번 실행되지 않고 한 번 계산된 결과가 재사용된다.
"""
class Depends:
    def __init__(
        self, dependency: Optional[Callable[..., Any]] = None, *, use_cache: bool = True
    ):
        self.dependency = dependency
        self.use_cache = use_cache
    
    def __repr__(self) -> str:
        attr = getattr(self.dependency, "__name__", type(self.dependency).__name__)
        cache = "" if self.use_cache else ", use_cache=False"
        return f"{self.__class__.__name__}({attr}{cache})"
