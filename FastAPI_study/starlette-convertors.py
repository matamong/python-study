import math
import typing
import uuid


T = typing.TypeVar("T")

class Convertor(typing.Generic[T]):
    """
    ClassVar: 클래스 변수를 정의할 때 사용하는 타입 힌트
    Python은 static이 없지만 이와 "유사한 기능"을 ClassVar로 구현할 수 있다.
    유사한 기능이란, 
    변수를 Class 수준에서 공유하고
    클래스 인스턴스가 아니라 클래스 이름으로 접근할 수 있는 것이다.

    ex:
        class A:
            x: ClassVar[int] = 1
            y: int = 2

        A.x
        >>> 1
        A.y
        >>> 2
        a = A()
        a.x
        >>> 1
        a.y
        >>> 2
        a.x = 3
        a.x
        >>> 3
        A.x
        >>> 1
    """
    regex: typing.ClassVar[str] = ""

    def convert(self, value: str) -> T:
        raise NotImplementedError()
    
    def to_string(self, value: T) -> str:
        raise NotImplementedError()
    

class StringConvertor(Convertor):
    regex = "[^/]+" # 이 정규식은 /를 제외한 모든 문자열을 의미한다.

    def convert(self, value: str) -> str:
        return value
    
    def to_string(self, value: str) -> str:
        value = str(value)
        assert "/" not in value, "path 구분자가 포함되어 있으면 안됨"
        assert value, "빈 문자열은 안됨"
        return value



class PathConvertor(Convertor):
    regex = ".*" # 이 정규식은 모든 문자열을 의미한다.

    def convert(self, value: str) -> str:
        return str(value)
    
    def to_string(self, value: str) -> str:
        return str(value)
    

class IntegerConvertor(Convertor):
    regex = "[0-9]+" # 이 정규식은 0~9까지의 숫자를 의미한다."

    def convert(self, value: str) -> int:
        return int(value)
    
    def to_string(self, value: int) -> str:
        value = int(value)
        assert value >= 0, "음수는 지원하지 않음"
        return str(value)
    

class FloatConvertor(Convertor):
    # 이 정규식은 0~9까지의 숫자 뒤에 소수점이 올 수도 있고, 올 수도 없다는 의미이다.  ex: 1, 1.1, 1.11, 1.111, ...
    regex = r"[0-9]+(\.[0-9]+)?" 

    def convert(self, value: str) -> float:
        return float(value)
    
    def to_string(self, value: float) -> str:
        value = float(value)
        assert value >= 0, "음수는 지원하지 않음"
        assert not math.isnan(value), "NaN은 지원하지 않음"
        assert not math.isinf(value), "inf는 지원하지 않음"
        return ("%0.20f" % value).rstrip("0").rstrip(".") # 소수점 이하 20자리까지 표현하고, 0과 .을 제거한다.
    


class UUIDConvertor(Convertor):
    
    # 이 정규식은 UUID를 의미한다. ex: 123e4567-e89b-12d3-a456-426614174000
    regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"

    def convert(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)
    
    def to_string(self, value: uuid.UUID) -> str:
        return str(value)
    


CONVERTER_TYPES = {
    "str": StringConvertor(),
    "path": PathConvertor(),
    "int": IntegerConvertor(),
    "float": FloatConvertor(),
    "uuid": UUIDConvertor(),
}


def register_url_convertor(key: str, convertor: Convertor) -> None:
    """
    사용자 정의 Convertor를 등록한다.
    """
    CONVERTER_TYPES[key] = convertor