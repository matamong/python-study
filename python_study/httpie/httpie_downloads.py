import threading
from typing import IO   # typing: 타입 힌트를 지원. 효력은 없음.
from time import sleep, time
from httpie_downloads_utils import *

# HTTPie - Reporting Download Progress 오픈소스를 뜯어보고 따라치면서 공부
# https://github.com/httpie/httpie/blob/64c31d554a367abf876bd355f07dca6e41476c3f/httpie/downloads.py#L369-L480

CLEAR_LINE = '\r\033[K'
PROGRESS = (
    '{percentage: 6.2f} %'
    ' {downloaded: >10}'
    ' {speed: >10}/s'
    ' {eta: >8} ETA'
)
PROGRESS_NO_CONTENT_LENGTH = '{downloaded: >10} {speed: >10}/s'
SUMMARY = 'Done. {downloaded} in {time:0.5f}s ({speed}/s)\n'
SPINNER = '|/-\\'


class DownloadStatus:
    """다운로드 상태에 대한 디테일들을 가지고있음(holds)"""

    def __init__(self):
        self.downloaded = 0
        self.total_size = None
        self.resumed_from = 0
        self.time_started = None
        self.time_finished = None

    def started(self, resumed_from=0, total_size=None):
        assert self.time_started is None
        self.total_size = total_size
        self.downloaded = self.resumed_from = resumed_from
        self.time_started = time()

    def chunk_downloaded(self, size):
        assert self.time_finished is None
        self.downloaded += size

    @property
    def has_finished(self):
        return self.time_finished is not None

    def finished(self):
        assert self.time_started is not None
        assert self.time_finished is None
        self.time_finished = time()


class ProgressReporterThread(threading.Thread):
    """
    상태에 따라서 다운로드 프로그레스를 보고한다.
    상태를 주기적으로 업데이트 하기 위해서 스레딩을 함 (스피드같은거)
    """

    def __init__(self, status: DownloadStatus, output: IO, tick=.1, update_interval=1):
        super().__init__()
        self.status = status
        self.output = output
        self._tick = tick
        self._update_interval = update_interval
        self._spinner_pos = ''
        self._status_line = ''
        self._prev_bytes = 0
        self._prev_time = time()
        self._should_stop = threading.Event()

    def stop(self):
        """다음 틱에 보고를 멈춤"""
        self._should_stop.set()

    def run(self):
        while not self._should_stop.is_set():
            if self.status.has_finished:
                self.sum_up()
                sleep(self._tick)
                break

            self.report_speed()
            sleep(self._tick)

    def report_speed(self):

        now = time()

        if now - self._prev_time >= self._update_interval:
            downloaded = self.status.downloaded
            try:
                speed = ((downloaded - self._prev_bytes) / (now - self._prev_time))
            except ZeroDivisionError:
                speed = 0

            if not self.status.total_size:
                self._status_line = PROGRESS_NO_CONTENT_LENGTH.format(
                    downloaded=humanize_bytes(downloaded),
                    speed=humanize_bytes(speed),
                )
            else:
                try:
                    percentage = downloaded / self.status.total_size * 100

                except ZeroDivisionError:
                    percentage = 0

                if not speed:
                    eta = '-:--:--'
                else:
                    s = int((self.status.total_size - downloaded) / speed)
                    h, s = divmod(s, 60 * 60)
                    m, s = divmod(s, 60)
                    eta = f'{h}:{m:0>2}:{s:0>2}'

                self._status_line = PROGRESS.format(
                    percentage=percentage,
                    downloaded=humanize_bytes(downloaded),
                    speed=humanize_bytes(speed),
                    eta=eta,
                )

            self._prev_time = now
            self._prev_bytes = downloaded

        self.output.write(f'{CLEAR_LINE}  {SPINNER[self._spinner_pos]}  {self._status_line}')
        self.output.flush()

        self._spinner_pos = (self._spinner_pos + 1 if self._spinner_pos + 1 != len(SPINNER) else 0)

    def sum_up(self):
        actually_downloaded = (self.status.downloaded - self.status.resumed_from)
        time_taken = self.status.time_finished - self.status.time_started

        self.output.write(CLEAR_LINE)

        try:
            speed = actually_downloaded / time_taken
        except ZeroDivisionError:
            # 아무 것도 다운되지 않았거나, 둘 다 0일 때(모든 시스템이 `time.time`을 1초보다 더 나은 정밀도로 제공하는 것은 아님
            speed = actually_downloaded

        self.output.write(SUMMARY.format(
            downloaded=humanize_bytes(actually_downloaded),
            total=(self.status.total_size and humanize_bytes(self.status.total_size)),
            speed=humanize_bytes(speed),
            time=time_taken,
        ))
        self.output.flush()


if __name__ == '__main__':
    thread = ProgressReporterThread()
    print(thread.status())