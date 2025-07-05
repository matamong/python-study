# 장고 ORM 작동 방식

```text
[Model 클래스] 
   ↓
[QuerySet API 호출 (filter, annotate, values...)]
   ↓
[Query 객체 생성 및 트랜스포머들 동작 (Query.add_q, Query.where 등)]
   ↓
[SQLCompiler → as_sql()]
   ↓
[DB 커넥터로 raw SQL 실행]
   ↓
[결과를 Python 객체로 역직렬화하여 리턴]
```

## 실제 예시로
```python
class Author(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    rating = models.FloatField()
```

```python
Book.objects.filter(author__name="Tolstoy").annotate(avg_rating=Avg("rating")).values("title", "avg_rating")
```

### 1단계: 모델 → 매니저 → QuerySet
- Book.objects: `objects`는 `Book` 클래스에 붙은 **매니저 객체 (Manager)**
- Manager는 `.get_queryset()`을 호출해서 `QuerySet` 인스턴스를 리턴
```python
# django.db.models.manager.Manager
# get_queryset 코드
def get_queryset(self):
    return QuerySet(self.model, using=self._db)
```
- 즉, Book.objects → QuerySet(model=Book) 객체 생성됨.

### 2단계: QuerySet 메서드 체이닝 (복제 → 수정 구조)

Django의 `QuerySet` 메서드 (`filter()`, `annotate()`, `values()` 등)는 **기존 인스턴스를 직접 수정하지 않고**,  
**복제본(QuerySet)을 만들어 변경사항을 적용한 뒤 리턴**하는 구조로 작동한다.

---

#### 왜 복제해서 수정하는가?

- **불변성 유지**: 원본 QuerySet은 안전하게 재사용 가능
- **체이닝 지원**: `.filter().annotate().values()`처럼 연속 호출 가능
- **메모리 효율**: DB 접근 전까지는 Query 구조만 복사됨 (얕은 복사 수준)
- **디버깅 편리**: 중간 단계 QuerySet을 따로 저장해서 테스트 가능

---

#### 예를 들면,

```python
qs1 = Book.objects.all()
qs2 = qs1.filter(author__name="Tolstoy")
```
- `qs1`은 전체 Book 목록
- `qs2`는 author__name="Tolstoy" 조건이 붙은 새로운 QuerySet
- `qs1`은 절대 변하지 않음

```python
qs1 = Book.objects.all()
qs2 = qs1.filter(title__icontains="War")
qs3 = qs2.annotate(avg_rating=Avg("rating"))

print(qs1.query)
print(qs2.query)
print(qs3.query)
```
이렇게 하면 3개가 각각 다르게 구성된 `Query` 객체를 가짐
(각각 `where`, `annotations`, `select` 구성이 다름)

---
내부는 이렇게 되어있다.
```python
# django.db.models.query.QuerySet

def filter(self, *args, **kwargs):
    return self._filter_or_exclude(False, args, kwargs)

def _filter_or_exclude(self, negate, args, kwargs):
    clone = self._clone()  # ← 복제본 생성
    clone._filter_or_exclude_inplace(negate, args, kwargs)  # ← 필터 조건 추가
    return clone
```

### 3단계: `Query` 객체 구성
- `QuerySet.query` 에 있는 객체가 핵심 `Query` 객체임. 
  - `.django.db.models.sql.query.Query` 에 있음
- 이 객체에 다음 필드들이 하나하나 쌓임
  - `.where` : 
  - `.annotations`
  - `.select`
  - `.join_map`, `.alias_map` 
- 즉, Query 조립 단계

객체만 구성하고 SQL은 안날림

### 4단계: 평가하는 시점
```python
for b in Book.objects.filter(...): ...
list(Book.objects.values(...))
```
이런 시점에 lazy evaluation해서 SQL 생성함.

### 5단계: SQLComplier.as_sql() -> 문자열 생성
- `django.db.models.sql.compiler.SQLCompiler`
```python
sql, params = queryset.query.get_compiler(using).as_sql()
```
- `.as_sql()`:
  - SELECT 
  - JOIN
  - WHERE
  - GROUP BY, HAVING
  - 최종적으로 (sql, params) 튜플 리턴