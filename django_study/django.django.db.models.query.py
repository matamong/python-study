"""
- filter() 한 줄이 add_q()로 넘어가면서 WhereNode가 어떻게 구성되는지,
- annotate()로 들어간 Count가 어떻게 SELECT COUNT(...)로 변하는지 등등.
"""

"""
< 간단 Filter 작동 방식 >

Book.objects.filter(published=True)
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

from django.db.models import sql
from django.db.models.utils import (
    AltersData 
)

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
