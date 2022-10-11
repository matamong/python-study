import curses   # 텍스트 기반 터미널 스크린 페인팅과 키보드 처리 기능 제공.
import sys
import os
from pathlib import Path
from typing import IO, Optional
from httpie_downloads_utils import repr_dict


class Environment:
    """"
    실행 context에 대한 정보. (standard streams, config directory, etc)

    디폴트로 실제 환경을 나타내며 모든 attribute는 테스트를 사용할 때 덮어씌워질 수 있음
    """
    is_windows: bool = is_windows
    config_dir: Path = DEFAULT_CONFIG_DIR
    stdin: Optional[IO] = sys.stdin   # fd 클로즈되면 'None' 됨
    stdin_isatty: bool = stdin.isatty()    # isatty : 터미널 장치에 연결했는지 확인
    stdin_encoding: str = None
    stdout: IO = sys.stdout
    stdout_isatty: bool = stdout.isatty()
    stdout_encoding: str = None
    stderr: IO = sys.stderr    # stout(표준출력)과 다르게 stderr은 표준 에러다. 에러로그로 활용
    stderr_isatty: bool = stderr.isatty()
    colors = 256
    program_name: str = 'http'
    if not is_windows:
        if curses:
            try:
                curses.setupterm()
                colors = curses.tigetnum('colors')
            except curses.error:
                pass
    else:
        import colorama.initialise  # ANSI 이스케이프 문자 시퀀스를 windows에서도 사용할 수 있게
        stdout = colorama.initialise.wrap_stream(
            stdout, convert=None, strip=None,
            autoreset=True, wrap=True
        )
        dtderr = colorama.initialise.wrap_stream(
            stderr, convert=None, strip=None,
            autoreset=True, wrap=True
        )
        del colorama

    def __init__(self, devnull=None, **kwargs):
        """
        키워드 인수를 사용해서 이 인스턴스의 클래스 속성을 덮어씀.
        """
        assert all(hasattr(type(self), attr) for attr in kwargs.keys())
        self.__dict__.update(**kwargs)

        # 기존 STDERR은 --quiet’ing을 통해 영향을 안 미친다.
        self._orig_stderr = self.stderr
        self._devnull = devnull

        # Keyword arguments > stream.encoding > default utf8
        if self.stdin and self.stdin_encoding is None:
            self.stdin_encoding = getattr(
                self.stdin, 'encoding', None
            ) or 'utf8' # or 쓰면 앞에 값이 falsy하면 뒤에 값!
        if self.stdout_encoding is None:
            actual_stdout = self.stdout
            if is_windows:
                pass

    def __str__(self):
        defaults = dict(type(self).__dict__)
        actual = dict(defaults)
        actual.update(self.__dict__)
        actual['config'] = self.config_dir
        return repr_dict({
            key: value
            for key, value in actual.items()
            if not key.startswith('_')
        })

    def __repr__(self):
        return f'<{type(self).__name__} {self}>'

    _config: Config = None

    @property
    def config(self) -> Config:
        config = self._config
        if not config:
            self._config = config = Config(directory=self.config_dir)
