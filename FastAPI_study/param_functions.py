"""
FastAPI의 parameter function은
Path, Query, Header, Cookie, Body, Form, File, Depends 등등
다양한 유형의 HTTP request 데이터를 처리하는 함수이다.


Depends, Query, Body에서는 간편하게 Annotated를 사용하여 parameter function을 정의할 수 있다.
이 방식은 IDE와 type-checker가 type을 인지하게하면서 dependency와 type annotation을 동시에 사용할 수 있게 해준다.
(Annotated는 python 3.9에서 추가된 기능이다.)
"""

from typing import Annotated, Any, Callable, Optional, TypeAlias, Union
from enum import Enum
from xml.etree.ElementInclude import include
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



"""
Query class는 쿼리 파라미터를 처리하기 위한 클래스
"""
from fastapi._compat import Undefined

_Unset: Any = Undefined

def Query(  # noqa: N802
    default: Any = Undefined,
    *,
    default_factory: Union[Callable[[], Any], None] = _Unset,
    alias: Optional[str] = None,
    alias_priority: Union[int, None] = _Unset,
    # TODO: update when deprecating Pydantic v1, import these types
    # validation_alias: str | AliasPath | AliasChoices | None
    validation_alias: Union[str, None] = None,
    serialization_alias: Union[str, None] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    regex: Annotated[
        Optional[str],
        deprecated(
            "Deprecated in FastAPI 0.100.0 and Pydantic v2, use `pattern` instead."
        ),
    ] = None,
    discriminator: Union[str, None] = None,
    strict: Union[bool, None] = _Unset,
    multiple_of: Union[float, None] = _Unset,
    allow_inf_nan: Union[bool, None] = _Unset,
    max_digits: Union[int, None] = _Unset,
    decimal_places: Union[int, None] = _Unset,
    examples: Optional[List[Any]] = None,
    example: Annotated[
        Optional[Any],
        deprecated(
            "Deprecated in OpenAPI 3.1.0 that now uses JSON Schema 2020-12, "
            "although still supported. Use examples instead."
        ),
    ] = _Unset,
    openapi_examples: Optional[Dict[str, Example]] = None,
    deprecated: Optional[bool] = None,
    include_in_schema: bool = True,
    json_schema_extra: Union[Dict[str, Any], None] = None,
    **extra: Any,
) -> Any:
    return params.Query(
        default=default,
        default_factory=default_factory,
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        regex=regex,
        discriminator=discriminator,
        strict=strict,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        example=example,
        examples=examples,
        openapi_examples=openapi_examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        json_schema_extra=json_schema_extra,
        **extra,
    )


"""
params 모듈의 Query 클래스로 반환하는 것을 볼 수 있다.
Query도 결국 Param을 상속받은 클래스이다.
Param 클래스는 pydantic의 FieldInfo를 상속받은 클래스이다.
FieldInfo는 직접 사용할 수 없다.
"""
from pydantic.fields import FieldInfo

class Param(FieldInfo):
    ...

class Query(Param):
    ...


"""
parama_functions.py의 첫 PR이 흥미로웠다.
parms.py가 있는데 왜 이걸 쓰는거지 했는데 바로 이유가 나왔기 때문이다.


원래는 params모듈의 (...)를 사용하고 있었는데,
mypy에서 (...)를 사용하면 type 체크에 문제가 있었다.
mypy의 잘못이 아니라, mypy는 잘 작동하고 있는데 FastAPI에서 typing 시스템을 
최대한으로 사용하고 있었기 때문에 발생한 문제였다. 
(path 작업 함수들은 FastAPI에 의해서만 사용되기 때문에 mypy가 이를 이해하지 못했다.)

관련 PR:
    https://github.com/tiangolo/fastapi/pull/226


근본적인 클래스 자체의 type 선언을 어떻게 할 수는 없으나, 함수 리턴 type의 선언은 재정의 할 수 있었다.
그리하여 모든 path param 클래스를 함수로 변환해버린 것이다.
이렇게 하면, 함수가 호출될 때 실제로 코드가 실행되며 FastAPI는 애플리케이션이 실행되는 동안 이를 검사할 수 있다.



"""