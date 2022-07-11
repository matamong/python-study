# https://docs.djangoproject.com/en/4.0/topics/db/managers/
# Manager클래스는 DB쿼리 작업이 장고 모델에게 제공되는 Interface이다.
# 장고의 모든 모델에게는 적어도 하나의 매니저가 존재한다.



# 1. Manager names
# 기본적으로 장고는 Manager를 objects라는 이름으로 모든 model 클래스에 넣어놓는다.
# 그럼에도 objects라는 필드이름을 쓰고싶거나,
# Manager에 있어 objects라는 이름 이외의 이름을 사용하고싶다면 각 모델별로 리네이밍하자.
# 해당 모델에 models.Manager()를 활용하장
from django.db import models

class Person(models.Model):
    # ...
    people = models.Manager()   # Person.objects 대신 Person.people.all()과 같이 사용할 수 있다.


# 2. Custom Managers
# 몇몇의 모델을 base Manager로 확장함으로써 커스텀 Manager를 사용할 수 있고 
# 모델에서 커스텀 Manager를 인스턴스화 할 수 있다.
# Managers를 커스터마이징할 이유는 두 가지가 있겠다.
# 하나는 Manager에 메소드들을 더 추가하기 위함이고
# 또 한가지 더는 Manager가 반환하는 초기 QuerySet을 변경하기 위함이다.


# 2-1. Adding extra manager methods
# manager 메소드를 추가하는 것은 모델에 테이블 수준의 기능을 추가하는 데 선호되는 방법이다.
# (테이블 수준이 아닌 행(row)수준의 기능(모델 객체의 단일 인스턴스에서 작동하는 기능)은 Model 메서드를 사용해야한다잉)

from django.db import models
from django.db.models.functions import Coalesce

class PollManager(models.Manager):
    def with_counts(self):
        return self.annotate(
            num_responses=Coalesce(models.Count("response"), 0)
        )

class OpinionPoll(models.Model):
    question = models.CharField(max_length=200)
    objects = PollManager()

class Response(models.Model):
    poll = models.ForeignKey(OpinionPoll, on_delete=models.CASCADE)


# 위 예제에서는 OpinionPoll.objects.with_counts()을 사용하여 
# num_responses 속성이 들어있는 OpinionPoll 객체의 QuerySet을 가져올 수 있다.

# custom Manager메서드는 QuerySet뿐만 아니라 원하는건 뭐든지 반환할 수 있다.
# Manager 메서드는 self.model을 통하여 자신이 소속한 모델 클래스에 접근할 수 있다.


# 2-2. Modifying a manager's initial QuerySet
# Manager의 기본 QuerySet은 시스템의 모든 객체들을 반환한다. 
# 예를 들면,

class Book(models.Model):
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=50)

# Book.objects.all()은 데이터베이스의 모든 book들을 반환할 것이다.
# 이러한 Manager의 기본 QuerySet은 Manager.get_queryset() 메서드를 오버라이딩해서 오버라이드할 수 있다.

# get_queryset()은 필요한 속성들과 함께 QuerySet을 반환할 것이다.
# 예를 들면, 다음과 같다.

class AuthorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role='A')

class EditorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role='E')

class Person(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(max_length=1, choices=[('A', _('Author')), ('E', _('Editor'))])
    people = models.Manager()
    author = AuthorManager()
    editor = EditorManager()