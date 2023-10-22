"""
FastAPI application이 시작되고 request를 받기 전에 실행되는 코드를 작성할 수 있다. (오직 한 번)
FastAPI application이 shutdown될 때 실행되는 코드를 작성할 수 있다. (오직 한 번)

이로써, application lifespan을 커버할 수 있는 로직을 작성할 수 있음
모든 app이 사용해야하는 공통 resource, clean up해야하는 것들 등에 쓰일 수 있음.
ex) DB connection pool, 공유해야하는 머신러닝 모델 로딩해놓기 등등 
"""

"""
로딩하는데에 시간이 꽤 걸리는 머신러닝 모델이 있다고 생각해보자.
최상위 모듈에서 로드를 한다고 해도 간단한 테스트를 위해 실행하는 경우에도 로딩이 되어야 하기 때문에 시간이 오래 걸린다.
그러므로 app이 request를 받기 바로 직전(코드가 로드되는 시점이 아니다!)에 로딩을 해보자.
"""


"""
lifespan 파라미터와 context manager를 이용해서 로딩을 해보자.
"""

from contextlib import contextmanager
from fastapi import FastAPI

def fake_answer_to_everythin_ml_model(x: float):
    return x * 42

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model (when start up)
    ml_models["answer_to_everythin"] = fake_answer_to_everythin_ml_model
    yield
    # Clean up the ML model and release the resources (when shut down)
    ml_models.clear()


app = FastAPI(lifespan=lifespan)

@app.get("/predict")
async def predict(x: float):
    result = ml_models["answer_to_everythin"](x)
    return {"result": result}


"""
lifespan 파라미터는 FastAPI -> Router로 전달되어 그 곳에서 체크된다. 최초로 request를 받기 전에 실행되는 듯
"""