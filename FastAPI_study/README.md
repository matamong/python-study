# 패키지의 `__init__.py`에 모듈 모아놓는 이유
### 모듈 엑세스가 편해진다
- 패키지만 불러와도 `__init__.py`에 있는 모듈들 불러올 수 있음

```python
# mypackage의 __init__.py에 mymodule import한 경우
import mypackage
result = mypackage.mymodule.my_function()
```

### 가시성 향상
- 모아놓은 모듈을 보고 뭐 사용하는지 확인 가능

<br>

