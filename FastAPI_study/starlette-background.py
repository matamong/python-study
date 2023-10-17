from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.background import BackgroundTasks

async def signup(request):
    data = await request.json()
    username = data['username']
    email = data['email']
    tasks = BackgroundTasks()
    tasks.add_task(send_welcome_email, to_address=email)
    tasks.add_task(send_admin_notification, username=username)
    message = {'status': 'Signup successful'}
    return JSONResponse(message, background=tasks)


async def send_welcome_email(to_address):
    ...

async def send_admin_notification(username):
    ...


routes = [
    Route('/user/signup', endpoint=signup, methods=['POST'])
]

app = Starlette(routes=routes)


"""
Starlette BackgroundTask
"""

import sys
import typing

if sys.version_info >= (3, 10): # pragma: no cover
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from starlette._utils import is_async_callable
from starlette.concurrency import run_in_threadpool

"""
Parameter specification variable. static type checker를 위해 사용.
주로 Callable의 파라미터를 다른 Callable로 넘겨주고싶을 때 사용한다. 흠 더 공부해야할 듯 이해가 안되네.
"""
P = ParamSpec("P")  

class BackgroundTask:
    def __init__(
        self, func: typing.Callable[P, typing.Any], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.is_async = is_async_callable(func)

    async def __call__(self) -> None:
        if self.is_async:
            await self.func(*self.args, **self.kwargs)
        else:
            await run_in_threadpool(self.func, *self.args, **self.kwargs)

class BackgroundTasks(BackgroundTask):
    def __init__(self, tasks: typing.Optional[typing.Sequence[BackgroundTask]] = None):
        self.tasks = list(tasks) if tasks else []
    
    def add_task(
        self, func: typing.Callable[P, typing.Any], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        task = BackgroundTask(func, *args, **kwargs)
        self.tasks.append(task)

    async def __call__(self) -> None:
        for task in self.tasks:
            await task()