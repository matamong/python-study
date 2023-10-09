# https://docs.sqlalchemy.org/en/20/orm/session_basics.html

# Session Basic
## What does the Session do?
"""

- DB와의 모든 상호작용을 설립한다.
- lifespane동안에 로드했던가 연관되어있는 모든 객체들에 대해서 "holding zone"으로서의 역할
- ORM 매핑객체를 반환하고 수정하는 SELECT 및 기타 쿼리가 수행되는 인터페이스를 제공한다.
- ORM 객체 자체는 Identity map이라는 구조 안에서 Session 내부에서 유지된다.
    - Identity map이란, 각 obj의 고유한 복사본을 유지하는 데이터 구조이다. 

Session은 대게 statlesss한 형태로 시작한다.
쿼리가 실행되거나 객체가 지속되면 session과 연결된 engine에서 연결 리소스를 요청한 다음,
해당 connection에 대한 transaction을 설립한다.
이 transaction은 session이 commit() 또는 rollback()을 호출할 때까지 유지된다.


Session에서 유지 관리하는 ORM객체는 Python에서 속성이나 컬렉션이 수정될 때마다 변경 사항을 추적한다.
DB가 쿼리되려고 할 때마다 혹은 트랜잭션이 커밋되려고 할 때마다 session은 먼저 메모리에 저장된(보류중인, pendding) 변경 사항을 DB에 flush한다.
이를 unit of work라고 한다.

Session을 사용할 때, session이 보유한 transaction에 db row에 대해서 proxy ojbect로 관리되는 **ORM mapped 객체**를 사용하는 것이 유용하다.
실제 DB와 매칭되는 오브젝트 state를 유지하기위해서 다양한 이벤트들이 존재한다.
session에서 obj를 분리(detach)하는 것은 가능하지만 계속 사용하려면 session에 다시 연결해야한다.
"""


# Basic of Using a Session
## Opening and Closing a Session
"""
session은 session자체로 혹은 sessionmaker를 사용해서 생성할 수 있다.
대부분 연결을 위해서 하나의 Engine을 전달한다.

아래에서 보듯이 session은 with문을 사용해서 생성할 수 있다.
with문을 벗어나면 session은 자동으로 close된다.

Session.commit()을 호출할지는 선택이며
session으로 수행한 작업에 DB에 유지될 새 데이터가 포함된 경우에만 필요하다.
SELECT만 호출하고 변경 사항을 쓸 필요가 없다면 commit()을 호출할 필요가 없다.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("postgresql+psycopg2://scott:tiger@localhost/")

with Session(engine) as session:
    session.add(some_object)
    session.add(some_other_object)
    session.commit()


## Commiitng
"""
Session.commit()은 COMMIT을 하기 전에 Session.flush()를 실행한다.
이 때, 변경이 없으면 아무것도 하지 않음으로써 DB에 불필요한 COMMIT을 방지한다.
"""


## Framing out a begin / commit / rollback block
"""
`framing`으로 만약 모든 동작이 성공했다면 commit()을 호출하고, 실패했다면 rollback()을 호출한다.
Python에서는 다음과 같이 try/except/finally문을 사용해서 구현할 수 있다.
"""
with Session(engine) as session:
    session.begin()
    try:
        session.add(some_object)
        session.add(some_other_project)
    except:
        session.rollback()
        raise
    else:
        session.commit()



"""
위 예제처럼 긴 형식의 작업 시퀀스는 Session.begin()메서드에서 return된 SessionTransaction 객체를 사용해서 더 간단하게 구현할 수 있다.
Session.begine()은 context manager 인터페이스를 제공한다.

안 쪽 context는 exception이 없으면 session.commit()을 호출하고,
바깥쪽 context는 session.close()를 호출한다.
"""
with Session(engine) as session:
    with session.begin():
        session.add(some_object)
        session.add(some_other_object)



"""
두 context를 합치면 더 간결하게 만들 수 있다.
"""
with Session(engine) as session, session.begin():
    session.add(some_object)
    session.add(some_other_object)



## Using a sessionmaker
"""
sessionmaker의 목적은 정해진 configuration에 대한 session을 팩토리형식으로 제공하는 것이다.
application이 모듈 수준의 Engine을 가지고있다면, sessionmaker는 그 Engine에 맞게 session을 생성한다.
"""
Session = sessionmaker(engine)

with Session() as session:
    session.add(some_object)
    session.add(some_other_object)
    session.commit()




"""
sessionmker는 engine과 유사하기 때문에 Engine.begin()과 유사한 자체 sessionmaker.begin()을 가지고 있다.
commit도 되고 close도 한다.
"""
Session = sessionmaker(engine)

with Session.begin() as session:
    session.add(some_object)
    session.add(some_other_object)



# Querying
"""

"""