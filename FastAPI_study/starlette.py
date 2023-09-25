import typing

AppType = typing.TypeVar("AppType", bound="Starlette")

class Starlette:
    def __init__(
        self: "AppType"
    ) -> None:
        pass

###
# Type을 Starlette으로 정한 AppType 제네릭을 사용하면 Starlette 클래스의 서브클래스만 허용된다.
# 이는 Starlette 클래스의 서브클래스만 AppType으로 사용할 수 있다는 뜻이다.
# 쉽게 말하면, Starlette 클래스의 서브클래스만 인자로 받을 수 있다는 뜻이다.
###