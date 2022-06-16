# Middleware
- https://docs.djangoproject.com/en/4.0/topics/http/middleware/
- https://docs.djangoproject.com/en/4.0/ref/middleware/

<br>

- Django의 `request`, `response` 프로세스를 중간에서 가로채는 프레임워크의 훅이다. 가볍고 로우레벨의 플러그시스템이라고 보면 된다.
- 각각의 미들웨어 컴포넌트는 각각의 역할이 있다.
- setting에 등록된 순서가 중요하다. 세션관련 미들웨어는 반드시 세션을 먼저 거쳐야하는 것처럼.
  - 각각의 미들웨어는 request를 다음 레이어에 전달하기 위해서 `get_response`를 호출한다. 
  - request가 들어올 때는 위에서부터 아래로
  - response가 나갈 때는 아래에서부터 위로
- 미들웨어가 없어도 된다! 그래도 CommonMiddleware정도는 하라고한다.
## Custom Middleware
### def call
- 미들웨어 팩토리는 `get_response`로 호출할 수 있고 middleware를 리턴한다.
    - 팩토리 메소드 패턴으로 ㅇㅇ
```python
def simple_middleware(get_response):
    # 최초 한 번 설정
    
    def middleware(request):
        # view에 들어가기 전(혹은 다음 미들웨어) 각각의 request에 대하여 동작할 코드를 여기에
        
        response = get_response(request)
        
        # view가 호출되고나서 각각의 request/response에 대하여 동작할 코드를 여기
        
        return response
    
    return middleware

```
### Class call
- 조금 더 디테일하게 만질 수 있음
- MiddlewareMixin을 상속받으면 예전버전이랑 스무스하게 연결할 수 있음
```python
class SimpleMiddleware:
    #서버 돌 때 최초 초기화 한 번
    def __init__(self, get_response):
        self.get_response = get_response
    
    # request 올 때마다 계에에ㅔㅇ속
    # 웬만하면 쓸 일 없음 장고가 process_request(), process_response() 를 바로 호출해버리기 땜시롱
    def __call__(self, request):
        # view에 들어가기 전(혹은 다음 미들웨어) 각각의 request에 대하여 동작할 코드를 여기에
        
        response = self.get_response(request)

        # view가 호출되고나서 각각의 request/response에 대하여 동작할 코드를 여기
        
        return response
```

### Other Middleware Hooks
클래스를 기반으로한 미들웨어에 쓸만한 다른 훅 메소드들이 있음
- `process_view()`
  - 장고가 View를 호출하기 바로 직전에 호출된다.
- `process_exception()`
  - View가 예외를 던지면 장고가 호출함 
- `process_template_response()`
  - View 실행이 끝나면 바로 호출됨.
  - 템플릿 가지고 있으믄 렌더해주는듯? 더 알아봐야함 