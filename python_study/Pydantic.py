"""
Pydantic이 뭔데?
unstructure 데이터 검증 및 파싱 작업을 간단하게 만들어주는데 사용됨.
데이터 모델을 정의하고 유효성을 확인하고 파싱함. 오류 처리도 도와준다.
Pydnatic 문서에 가보면 parsing과 transformation 라이브러리지 validation 라이브러리가 아니라고 못 박아놓는다.
input이 아니라 output을 위한 라이브러리라고 한다. 오 input validation으로 쓴 것 같은데 활용을 잘못한듯.

doc:
    https://docs.pydantic.dev/2.4/concepts/models/

"""


"""
BaseModel은 Python 데이터 모델을 정의하기 위한 기본 클래스이다.
"""

__all__ = 'BaseModel', 'create_model'

import typing
from typing import Any, ClassVar

from pydantic import ConfigDict
from pydantic.fields import FieldInfo


class BaseModel(metaaclass=model_construction.ModelMetaclass):
    if typing.TYPE_CHECKING:

        # 클래스 속성
        model_config: ClassVar[ConfigDict]
        """"
        모델 설정.
        Config는 TypeDict를 상속받음.

        TypeDict는 다음과 같이 dict의 키와 값 형식을 지정할 수 있다.
        
        e.g:
            from typing import TypedDict

            class Person(TypedDict):
                name: str
                age: int
                email: str
        
        ConfigDict는 Pydantic 모델의 설정을 구성하기 위한 특별한 딕셔너리 형식이다.
        `allow_mutation`, `validate_assigment`, `orm_mode`, `json_encoders` 등 옵션을 설정할 수 있다.
        
        다음과 같이 쓰인다.

        e.g:
            class MyModel(BaseModel):
                name: str

                class Config:
                    allow_mutation = True
                    json_encoders = {
                        decimal.Decimal: str
                    }
        """

        model_field: ClassVar[dict[str, FieldInfo]]
        """
        필드에 대한 정보를 담고 있는 딕셔너리. 사용자가 접근할 필요는 없고 Pydantic이 알아서 해주는 영역이다.
        아래는 model_field 속성들 설명으로 chatgpt 돌려버림

        annotation: 필드의 타입 어노테이션(annotation)입니다. 필드의 데이터 유형을 나타냅니다.
        default: 필드의 기본값입니다. 필드에 값이 제공되지 않을 때 사용됩니다.
        default_factory: 필드의 기본값을 생성하는 팩토리 함수다. default와 함께 사용될 수 있습니다.
        alias: 필드의 별칭(alias) 이름다. 필드를 다른 이름으로 직렬화 및 역직렬화할 때 사용됩니다.
        alias_priority: 필드 별칭의 우선순위를 나타내는 숫자입니다.
        validation_alias: 필드의 유효성 검사 별칭(alias) 이름입니다.
        serialization_alias: 필드의 직렬화(alias) 별칭 이름입니다.
        title: 필드의 제목(타이틀)입니다.
        description: 필드에 대한 설명입니다.
        examples: 필드의 예시 값 목록입니다.
        exclude: 필드를 모델 직렬화에서 제외할지 여부를 나타내는 부울 값입니다.
        discriminator: 태그 유니온(tagged union)에서 필드의 이름을 식별하는 데 사용됩니다.
        json_schema_extra: JSON 스키마에 추가적인 속성을 포함하는 딕셔너리입니다.
        frozen: 필드가 변경 불가능한(frozen)지 여부를 나타내는 부울 값입니다.
        validate_default: 필드의 기본값을 유효성 검사할지 여부를 나타내는 부울 값입니다.
        repr: 필드를 모델 표현(representation)에 포함할지 여부를 나타내는 부울 값입니다.
        init_var: 필드를 데이터클래스(dataclass)의 생성자에 포함할지 여부를 나타내는 부울 값입니다.
        kw_only: 필드가 데이터클래스의 생성자에서 키워드 전용 인자(keyword-only argument)로 사용될지 여부를 나타내는 부울 값입니다.
        metadata: 메타데이터 제약 사항의 목록입니다.

        """

        __class_vars__: ClassVar[set[str]]
        __private_attributes__: ClassVar[dict[str, ModelPrivateAttr]]
        __signature__: ClassVar[Signature]

        __pydantic_complete__: ClassVar[bool]
        __pydantic_core_schema__: ClassVar[CoreSchema]
        __pydantic_custom_init__: ClassVar[bool]
        __pydantic_decorators__: ClassVar[_decorators.DecoratorInfos]
        __pydantic_generic_metadata__: ClassVar[_generics.PydanticGenericMetadata]
        __pydantic_parent_namespace__: ClassVar[dict[str, Any] | None]
        __pydantic_post_init__: ClassVar[None | Literal['model_post_init']]
        __pydantic_root_model__: ClassVar[bool]
        __pydantic_serializer__: ClassVar[SchemaSerializer]
        __pydantic_validator__: ClassVar[SchemaValidator]

        __pydantic_extra__: dict[str, Any] | None = _Field(init=False)  # type: ignore
        __pydantic_fields_set__: set[str] = _Field(init=False)  # type: ignore
        __pydantic_private__: dict[str, Any] | None = _Field(init=False)  # type: ignore

    else:
        # `model_fields` and `__pydantic_decorators__` must be set for
        # pydantic._internal._generate_schema.GenerateSchema.model_schema to work for a plain BaseModel annotation
        model_fields = {}
        __pydantic_decorators__ = _decorators.DecoratorInfos()
        # Prevent `BaseModel` from being instantiated directly:
        __pydantic_validator__ = _mock_val_ser.MockValSer(
            'Pydantic models should inherit from BaseModel, BaseModel cannot be instantiated directly',
            val_or_ser='validator',
            code='base-model-instantiated',
        )
        __pydantic_serializer__ = _mock_val_ser.MockValSer(
            'Pydantic models should inherit from BaseModel, BaseModel cannot be instantiated directly',
            val_or_ser='serializer',
            code='base-model-instantiated',
        )


    """
    __slots__을 사용하면 클래스의 인스턴스에 저장할 수 있는 속성(인스턴스 변수)을 미리 정의할 수 있다.
    파이썬 클래스의 인스턴스는 __dict__ 속성을 가지고 있어서 인스턴스 변수를 동적으로 추가할 수 있다. 
    기본적으로 dict는 키와 값 쌍을 저장하는 데 필요한 추가 메모리를 사용한다. 또 문자열을 저장하는 등등
    이는 메모리 사용량을 늘리는 요인 중 하나다.
    때문에 __slots__를 이용해서 인스턴스 변수를 미리 정의해서 그 만큼만 사용하겠다고 박아놓음으로써 메모리 사용량을 줄일 수 있다.
    """
    __slots__ = '__dict__', '__pydantic_fields_set__', '__pydantic_extra__', '__pydantic_private__'

    model_config = ConfigDict()
    __pydantic_complete__ = False
    __pydantic_root_model__ = False


    def __init__(__pydantic_self__, **data: Any) -> None:
        ...
