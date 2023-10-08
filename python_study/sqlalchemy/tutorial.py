from sqlalchemy import create_engine, text

# About this tutorial...
"""
https://docs.sqlalchemy.org/en/20/tutorial/index.html#unified-tutorial

SQLAlchemy의 Core와 ORM을 사용하는 방법을 설명한다.
Core: 
    SQL 추상화 계층을 제공하고 Python을 사용하여 
    SQL 데이터베이스로 직접 작업할 수 있는 low-level수준의 SQL 툴킷이다. 
    유연하고 빠르며 다양한 데이터베이스와 호환되도록 설계되었다.

ORM: 
    데이터베이스 작업을 위한 ORM(Object Relational Mapper)을 제공하는 SQLAlchemy Core 위에 구축된 상위 수준 API이다.
    ORM을 사용하면 Python 클래스를 데이터베이스 테이블에 매핑하고 해당 클래스의 인스턴스를 사용하여 해당 테이블의 데이터와 상호 작용한다.
    쉽게 사용할 수 있지만 Core만큼 유연하고 성능이 좋진 않다.


sqlalchemy는 Core와 ORM을 이해하면
sqlalchemy를 더 깊게 이해할 수 있다고 하여 이 튜토리얼을 따라해보기로 했다.
"""




# Engine
"""
https://docs.sqlalchemy.org/en/20/tutorial/engine.html

Lazy initailizing:
    create_engine을 했을 때, Engine은 실제로 DB와 연결되지 않는다.
    연결은 Engine이 처음으로 실행될 때(필요할 때) 발생한다.
    이것은 소프트웨어 디자인 패턴 중 하나인 lazy initializing이라고 한다. 
    이렇게 함으로써 캐싱역할을 하는 것이 있으면 그것을 연결해주고 
    아니면 새로운 인스턴스를 생성하는 등 유연하게 처리할 수 있다.
    (https://docs.sqlalchemy.org/en/20/glossary.html#term-lazy-initialization )
    (https://en.wikipedia.org/wiki/Lazy_initialization)

    
"""
engine = create_engine('sqlite+pysqlite:///:memory:', echo=True)




# Working with Transactions and the DBAPI
"""
https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html

DBAPI는 DB와 연결된 커넥션을 통해 트랜잭션을 관리한다.
connection객체의 사용범위를 특정 context로 제한하기위해 context manager(with)을 사용한다.
이렇게 하면 connection이 더이상 사용되지 않을 때 자동으로 반환된다.
아래와 같이 작성하면, with문이 끝나면서 연결 범위가 해제되면서 ROLLBACK이 발생하며 트랜잭션이 종료된다.
트랜잭션은 자동으로 커밋되지 않는다.

(참고: 아래의 result는 Result객체이다.)
"""
with engine.connect() as conn:
    result = conn.execute(text("select 'hello world'"))
    print(result.all())


## commit as you go
"""
그래서 데이터를 커밋하려면 일반적으로 Connection.commit()을 호출해야 한다.
특별한 경우에는 `autocommit`모드를 사용할 수 있긴 하다.
즉, DBAPI connection는 non-autocommitting이 기본이다.

아래의 예제는 commit을 적용한 방식으로,
commit as you go라고도 한다. 이 말은 데이터를 추가할 때마다 커밋한다는 뜻이다.
"""
with engine.connect() as conn:
    conn.execute(text("CREATE TABLE some_table (x int, y int)"))
    conn.execute(
        text("INSERT INTO some_table (x, y) VALUES (:x, :y)"),
        [{"x": 1, "y": 1}, {"x": 2, "y": 4}],
    )
    conn.commit



## begin once
"""
또 다른 방법은, 트랜잭션을 명시적으로 시작하고 커밋하는 것이다.
engine.begin()메서드는 Connection의 scope와 enclose을 관리한다.

아래의 예제는 begin once라고도 한다. 이 말은 트랜잭션을 한번만 시작한다는 뜻이다.

아래 코드를 실행하면 implicit transaction이 시작된다. 
implicit라고 하는 이유는 SQLAlchemy는 DB에 실질적으로 command를 보내지 않았기 때문이다.
그저 DBAPI의 implicit transaction을 시작했을 뿐이다.
"""
with engine.begin() as conn:
    conn.execute(
        text("INSERT INTO some_table (x, y) VALUES (:x, :y)"),
        [{"x": 1, "y": 1}, {"x": 2, "y": 4}],
    )



# Basics of Statement Execution
"""
https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html#basics-of-statement-execution

SQL문이 작동하는 구성 요소와 메커니즘을 더 자세히 살펴보자.
(이 섹션의 내용 대부분은 최신 ORM에서 Session.execute() 메서드를 사용할 때 와 동일하다.)
"""


## Fetching Rows
"""
아래와 같이 text SELECT 문을 이용해서 나온 Result를 자세히 살펴보자.
"""
with engine.connect() as conn:
    result = conn.execute(text("SELECT x, y FROM some_table"))
    for row in result:
        print(f"x: {row.x}  y: {row.y}")


"""
Result는 Row 객체들을 반환한다.
Result는 가져온 Row를 변환하는 많은 메서드를 가지고있다.
또한 Python iterator 인터페이스를 구현하고 있어서, Row 객체 컬렉션을 직접 반복할 수 있다.
"""

### Row
"""
Row 객체 자체는 Python의 namedtuple처럼 작동하도록 되어있다.
따라서 다음과 같이 활용할 수 있다.
"""

#### Tuple Assignment
"""
가장 Python의 관용적인 스타일은 tuple assignment를 사용하는 것이다.
row를 받을 때, 각각의 변수에 row의 값을 할당한다.
"""
for x, y in result:
    ...


#### Integer Index
"""
Tuples는 Python의 시퀀스로, 공간을 인덱싱할 수 있다.
"""
for row in result:
    x = row[0]


#### Attribute Name
"""
Python의 namedtuple처럼, Row는 attribute를 가진다.
이름은 일반적으로 SQL문이 각 행의 열에 할당하는 이름이다.
"""
for row in result:
    y = row.y

    print(f"Row: {row.x} {y}")


#### Mapping Access
"""
Python의 maapping오브젝트로 받으려면 Result.mapping()메서드를 사용한해서 MappingResult로 만들어야한다.
(python의 maaping오브젝트는 key, value 쌍으로 이루어진 오브젝트이다. dict가 대표적인 예이다.)
"""
for dict_row in result.mappings():
    x = dict_row["x"]
    y = dict_row["y"]


## Sending Parameters
"""
https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html#sending-parameters

다음처럼 bounding형식으로 파라미터를 전달할 수 있다.
"""
with engine.connect() as conn:
    conn.execute(
         text("INSERT INTO some_table (x, y) VALUES (:x, :y)"),
         [{"x": 11, "y": 12}, {"x": 13, "y": 14}],
        )
    conn.commit()



# Later...
"""
Lazy load, Lazy loads, lazy loaded, lazy loaidng:
    ORM에서 `lazy load`라 함은, 객체를 처음 로드할 때 연관된 객체를 로드하지 않고,
    객체가 실제로 사용될 때 연관된 객체를 로드하는 것을 말한다.
    이런 패턴을 사용하면 관련 테이블의 속성을 즉시 처리할 필요가 없으므로 객체 가져오기에 소요되는
    복잡성과 시간이 줄어든다.
"""