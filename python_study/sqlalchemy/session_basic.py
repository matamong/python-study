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
from random import seed
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
select() 구문을 사용해서 Select object를 생성한 다음,
Session.execute() 및 Session.scalars()같은 메서드를 사용해서 Result를 반환하기 위해 쿼링을 한다.
ScalarResult와 같은 Result객체로 반환된다.

쿼링 가이드느 여기로 -> https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html
SQLAlchemy가 2.X로 업데이트되면서, Query API는 더 이상 사용되지 않는다. (레거시 플젝을 위해 지원은 한다.)
SQLAlchemy Core가 select()하기 위해 사용하는 Session.execute()방법을 사용한다.
이 방법은 Query처럼 한 번에 모든 것을 실행하지않고 단계를 거친다.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

with Session(engine) as session:
    # 'User' object들을 위한 쿼리
    stmt = select(User).filter_by(name="ed") 
    
    # User object들의 list
    user_obj = session.scalars(stmt).all() 

    # 각각의 column들을 위한 쿼리
    stmt = select(User.name, User.fullname)

    # Row object들의 list
    rows = session.execute(stmt).all()


## SELECT를 써보자
"""
select() 함수를 사용해야 SELECT 구문이 생성되고 Select object를 반환한다.
리턴할 entity나 SQL 표현식(eg. column)은 위치에 따라 함수에 전달된다.
Select.Where()메서드같은 추가적인 메서드를 사용하면 완전한 문장을 만들 수 있다.
"""
stmt = select(User).where(User.name == "spongebob")

result = session.execute(stmt)

for user_obj in result.scalars():
    print(f"{user_obj.name} {user_obj.fullname}")
"""
이렇게 완성된 Select Object(stmt)가 주어지면,
ORM 내에서 결과 행을 얻기 위해 객체는 Session.execute()에 전달되며, 그런 다음 Result 객체가 반환된다.
SQL은 다음과 같다.

SELECT user_account.id, user_account.name, user_account.fullname
FROM user_account
WHERE user_account.name = ?
[...] ('spongebob',)
"""



## Selecting ORM Entities and Attributes
"""
! 잠깐 !
ORM에서 ENTITY(엔티티)는 테이블의 데이터. 엔티티 클래스는 테이블과 일대일로 매핑되는 클래스인 것을 알고 가자.
"""

"""
select() 함수는 ORM과 관련된 객체들을 다루는데 사용되며, 
ORM-주석이 달린 엔터티를 포함하는 경우 Session 객체를 통해 실행하는 것이 일반적이다. (ORM-Mapping된 객체의 인스턴스를 얻을 수 있기 때문이다)
Connection객체를 직접 사용할 때는 result row들은 column레벨의 데이터만 가지고 있을 것이다.(매핑된 객체가 아니기 때문에)
"""


"""
아래는 User entity에서 select()를 수행하여 
User가 매핑된 테이블에서 select를 수행하는 Select를 생성한다.
"""
result = session.execute(select(User).order_by(User.id))

"""
ORM 엔티티들에 대해 select를 하면, 각각의 컬럼들의 series가 아니라,
result로써 entity 자체가 리턴된다. (single element row임)
즉, 결과로 반환되는 것은 각 행의 개별 열이 아니라, 행당 하나의 요소로서 엔터티 자체가 반환되는 것이다.

아래를 보면 Result 객체는 row당 하나의 element를 가지고 있는 Row 객체를 반환하며, 이 element는 User객체를 포함한다.

>>> result.all()
[(User(id=1, name='spongebob', fullname='Spongebob Squarepants'),),
 (User(id=2, name='sandy', fullname='Sandy Cheeks'),),
 (User(id=3, name='patrick', fullname='Patrick Star'),),
 (User(id=4, name='squidward', fullname='Squidward Tentacles'),),
 (User(id=5, name='ehkrabs', fullname='Eugene H. Krabs'),)]


 Result (Result 객체)
├─ Row 1 (첫 번째 행)
│   └─ User(id=1, name='spongebob', fullname='Spongebob Squarepants') (User 객체)
├─ Row 2 (두 번째 행)
│   └─ User(id=2, name='sandy', fullname='Sandy Cheeks') (User 객체)
├─ Row 3 (세 번째 행)
│   └─ User(id=3, name='patrick', fullname='Patrick Star') (User 객체)
├─ Row 4 (네 번째 행)
│   └─ User(id=4, name='squidward', fullname='Squidward Tentacles') (User 객체)
└─ Row 5 (다섯 번째 행)
    └─ User(id=5, name='ehkrabs', fullname='Eugene H. Krabs') (User 객체)

"""


"""
하지만 ORM Entity를 포함하는 row 목록을 select할 때는 Row 오브젝트로 계속 생성하는 대신,
ORM Entity를 다이렉트로 받는 것이 일반적이다.
그럴려면 Session.execute() 메서드 대신 Session.scalars() 메서드를 사용한다. 
이렇게 하면 ORM Enttiy를 다이렉트로 받는 ScalarResult 객체가 반환된다.
"""
session.scalars(select(User).order_by(User.id)).all()
"""
이렇게 하면 아래와 같이 다이렉트로 받을 수 있다. (SQL문은 동일)

[User(id=1, name='spongebob', fullname='Spongebob Squarepants'),
 User(id=2, name='sandy', fullname='Sandy Cheeks'),
 User(id=3, name='patrick', fullname='Patrick Star'),
 User(id=4, name='squidward', fullname='Squidward Tentacles'),
 User(id=5, name='ehkrabs', fullname='Eugene H. Krabs')]


Session.scalars()는 엄청 다른 건 없고 그냥
Session.execut()를 호출해서 Result를 얻고 Result.scalars()를 호출하는 것과 똑같다.
"""



### 