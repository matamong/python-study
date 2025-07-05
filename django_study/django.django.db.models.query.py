"""
- filter() 한 줄이 add_q()로 넘어가면서 WhereNode가 어떻게 구성되는지,
- annotate()로 들어간 Count가 어떻게 SELECT COUNT(...)로 변하는지 등등.
"""

"""
< 간단 Filter 작동 방식 >

Book.objects.filter(published=True)
       │
       ▼
Book 클래스에 정의된 Manager (보통 `objects`)
       │
       ▼
Manager.get_queryset() → QuerySet(Book)
       │
       ▼
QuerySet.filter()
       │
       ▼
Query.add_q()
       │
       ▼
Query.where ← WhereNode ← 조건들
       │
       ▼
Query.get_compiler().as_sql()
       │
       ▼
SQL 실행: SELECT * FROM book WHERE published = true;

"""
"""
< Filter & Annotate & Value >

Book.objects.filter(published=True).annotate(num_authors=Count("authors")).values("title", "num_authors")

1. QuerySet 시작 (Book.objects)
        │
2. filter(published=True)
        │
        ▼
QuerySet._filter_or_exclude()
        │
        ▼
Query.add_q(Q(published=True))
→ WHERE published = true

3. annotate(num_authors=Count("authors"))
        │
        ▼
QuerySet._annotate()
        │
        ▼
Query.add_annotation(Count("authors"), alias="num_authors")
→ SELECT ..., COUNT(authors.id) AS num_authors
→ GROUP BY 필요한 필드 자동 결정됨

4. values("title", "num_authors")
        │
        ▼
Query.set_values(["title", "num_authors"])
→ SELECT title, COUNT(authors.id) AS num_authors
→ 결과는 dict로 반환됨

"""

from typing import Type
from django.db.models import sql
from django.db.models.utils import (
    AltersData 
)
from regex import D

"""
AlterData 클래스 : 
    - 상속받은 서브클래스가 어떤 메서드를 오버라이드할 때, 기존 메서드의 alters_data 속성을 자동으로 복사
    - `__init_subclass__` 라는 함수만 있는데, 이 메서드는 "DB에 영향을 준다"는 표시인 alters_data = True를 자동으로 유지
    - AltersData를 받은 클래스를 상속한 클래는 자동으로 update함수같의 DB에 영향을 주는 함수에 대해서 alters_data = True로 유지해줌
    - alters_data는 내부적으로 아래를 위해 사용됨.
        - QuerySet 캐시 무효화 여부
            - 지연 평가(lazy evaluation)를 할 때, SQL을 실제로 날린 다음에 DB에서 받아온 결과를 _result_cache에 저장함.
            - 이후 반복 평가할 때는 _result_cache에서 꺼내옴
            - 근데 만약에 어떤 메서드가 DB를 바꾸는데 캐시를 그대로 사용하면 안됨!
        - 데이터 변경 쿼리인지 판단
            - ORM 내부의 일부 로직은 "읽기 전용 쿼리" 와 "쓰기 쿼리" 를 구분해서 처리해야 함.
            - 읽기 쿼리:  캐시, 복제 DB, select_related 허용 가능
            - 쓰기 쿼리: atomic 트랜잭션 보장, write DB 강제 라우팅, 캐시 무효화, select_related 금지 필요
        - ORM 트래킹 시스템과 연동
            - pre/post signal의 자동 제어 여부 등.
    - QuerySet.update, QuerySet.create, QuerySet.delete 같은 것들이 alters_data는=True임.

"""
class QuerySet(AltersData):
    """Represent a lazy database lookup for a set of objects."""
    
    def __init__(self, model=None, query=None, using=None, hints=None):
        self.model = model
        self._db = using
        self._hints = hints or {}
        self._query = query or sql.Query(self.model)
        self._result_cache = None
        self._sticky_filter = False
        self._for_write = False
        self._prefetch_related_lookups = ()
        self._prefetch_done = False
        self._known_related_objects = {}  # {rel_field: {pk: rel_obj}}
        # self._iterable_class = ModelIterable TODO
        self._fields = None
        self._defer_next_filter = False
        self._deferred_filter = None


    def as_manager(cls): # cls: 현재 QuerySet 클래스 (ex: BookQuerySet)
        # 내가 만든 커스텀 QuerySet 클래스를 .objects 같은 Manager처럼 쓸 수 있게 만들어줌
        from django.db.models.manager import Manager

        manager = Manager.from_queryset(cls)() # 해당 QuerySet을 기반으로 하는 Manager 클래스를 동적으로 생성 /  `from_qureyset`은 QuerySet의 메서드들을 자동으로 연결해서 새로운 Manager 클래스를 만들어주
        manager._build_with_as_maanger = True
        return manager

    as_manager.queryset_only = True # 이건 QuerySet 기반임"이라고 표시
    as_manager = classmethod(as_manager) # 인스턴스가 아니라 클래스 단위에서 호출 가능하게

    ########################
    # PYTHON MAGIC METHODS # 들
    ########################
    # __iter__, __bool__ 뭐 이런거


    """
    iterator 구현해서,
    보통 for book in Book.objects.all(): 하면,
    → 내부적으로는 QuerySet의 __iter__() → _fetch_all() → 결과를 한꺼번에 메모리에올리는데 너무 많으면 Out of Memory 걸릴 수 있음.
    그래서 .iterator() 로 쪼개서 가져오깅

    Book.objects.all().iterator(chunk_size=1000) 이렇게.
    
    근데 .prefetch_related() 는 어떻게?? 
    - .prefetch_related()는 내부적으로 N+1 방지를 위해 related object들을 미리 가져와야 함
    - 이건 메모리 위에 결과를 "다 리스트로 올려놓고" 후처리하는 구조임
    - iterator랑 대치됨. 
    - 그래서 prefetch_related()와 함께 쓸 땐 chunk_size를 명시해야 안전하게 작동
    - 이 때, "쿼리는 한 번만 날리고", 메모리에서 chunk 단위로 결과를 끊어서 prefetch만 나눠서 처리

    """
    def _iterator(self, use_chunked_fetch, chunk_size):
        iterable = self._iterable_class(
            self,
            chunked_fetch=use_chunked_fetch,
            chunk_size=chunk_size or 2000,
        )
        if not self._prefetch_related_lookups or chunk_size is None:
            yield from iterable
            return
        
    def iterator(self, chunk_size=None):
        """
        An iterator over the results from applying this QuerySet to the
        database. chunk_size must be provided for QuerySets that prefetch
        related objects. Otherwise, a default chunk_size of 2000 is supplied.
        """
        if chunk_size is None:
            if self._prefetch_related_lookups:
                raise ValueError("님 프리페치 사용하고 있으니까 chunk_size 명시하세여!!")
        elif chunk_size <= 0:
            raise ValueError("chunk_size는 양수여요!!")
        use_chunked_fetch = not connections[self.db].settings_dict.get( # DB 커서를 서버 사이드 방식으로 사용할 수 있는지?
            "DISABLE_SERVER_SIDE_CURSORS"
        )
        """
        서버 사이드 커서(Server-side cursor)란?
            - 클라이언트 커서 (default)
                - SQL 실행 후 결과 전체를 한 번에 가져옴
                - `cursor.fetchall()`
                - 큰 데이터 처리 시 메모리 낭비 많음
                - 일반적으로 빠름
            - 서버 사이드 커서
                - DB 서버가 커서 열고 결과를 일부만 넘김
                - `cursor.fetchmany(chunk_size)`
                - 메모리 효율 좋음
                - 약간 느릴 수 있지만 안전
        
        - Django는 PostgreSQL, Oracle, 일부 DB에서 iterator() + chunk_size 패턴을 쓸 때 → 서버 사이드 커서를 자동으로 활성화함.
        - 왜 해야 함?
            - 일부 DB나 설정에서는 서버 사이드 커서를 지원하지 않거나, 비활성화할 수 있음.
            - 그럴 땐 iterator()가 chunked fetch를 못 쓰게 막아야 함
        - 주의:
            - 서버사이드에 계속 커서가 있는,.... 즉 DB를 계속 물고있기 때문에 결과를 오래 들고 있지 말고, 바로 처리하고 넘기는 일에 써야함.
            - stream 느낌으로다가..!
    
        """
        return self._iterator(use_chunked_fetch, chunk_size)
    
    @staticmethod
    def _validate_values_are_expressions(values, method_name):
        """
        Avg("rating"), Sum("pages") 같은 Expression 객체가 맞는지 확인

        Expression은 내부적으로 resolve_expression() 메서드를 구현해야 함
        (F(), Value(), Avg(), Subquery() 등 모두 이 메서드를 가지고 있음)


        Book.objects.aggregate(avg_rating=Avg("rating")) <- 이렇게 Avg("rating") 객체를 써야하는데
        Book.objects.aggregate(avg_rating="rating") <- 이렇게 str 쓰는거 거르겠다는 것.

        """
        invalid_args = sorted(
            str(arg) for arg in values if not hasattr(arg, "resolve_expression")
        )
        if invalid_args:
            raise TypeError("Expression 객체 쓰세욧!!")
    
    def aggregate(self, *args, **kwargs):
        """
        Retrun a dictionary containing the calculations (aggregation) over the current queryset.

        If args is present the expression is passed as a kwrg using the Aggregate object's default alias.
        """
        self._validate_values_are_expressions(
            (*args, *kwargs.values()), method_name="aggregate"
        )
        for arg in args:
            kwargs[arg.default_alias] = arg
        
        """
         현재 QuerySet의 쿼리 객체를 복사(chain) 하고, 
         집계 함수들(Avg, Sum, 등)을 SQL로 바꾼 뒤 DB에 실행하고 결과 딕셔너리를 리턴
         (원본 Query는 건드리지 않고, 복제본에서 집계용 설정만 추가해서 .get_aggregation() 실행)
         (.annotate(), .values()와 충돌 안 나게 별도의 쿼리 사용)
        """
        return self.query.chain().get_aggregation(self.db, kwargs)
    
    """
    clone() Vs chain()
    
    - .chain()은 clone()처럼 복제는 하지만, aggregate나 count처럼 "리턴 형태가 아예 다른 경우"를 처리하는 데 특화된 복사

    예를 들면,
    aggregate(), count(), exists() 들은 
    결과 구조 자체가 "리스트 of 모델 인스턴스"가 아니라 "딕셔너리 하나"로 바뀜
    왜?
    - 결과가 무조건 1줄이고
    - 모델 인스턴스도 필요 없고
    - 그 값이 바로 필요한 상황
    이면 dict로 돌려줌.

    그런데 filter 이런거는 쿼리셋 리스트임. 그래서 이걸 섞어쓰면 꼬임. 
    그래서 chain()으로 안전하게 새 Query 복사본을 만들고, 집계에 꼭 필요한 정보만 설정해서 SQL 충돌 없이 집계 쿼리를 날릴 수 있게 함.

    """