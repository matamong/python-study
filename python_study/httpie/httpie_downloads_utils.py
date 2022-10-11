from pprint import pformat


def repr_dict(d: dict) -> str:
    return pformat(d)


def humanize_bytes(n, precision=2):
    # Author: Doug Latornell
    # Licence: MIT
    # URL: https://code.activestate.com/recipes/577081/
    """
    숫자 bytes의 표현을 인간이 읽기 쉽게 반환해줌

    >>> humanize_bytes(1)
    '1 B'
    >>> humanize_bytes(1024, precision=1)
    '1.0 kB'
    >>> humanize_bytes(1024 * 123, precision=1)
    '123.0 kB'
    >>> humanize_bytes(1024, 12342, precision=1)
    '12.1 MB'
    >>> humanize_bytes(1024 * 12342, precision=2)
    '12.05 MB'
    >>> humanize_bytes(1024 * 1234, precision=2)
    '1.21 MB'
    >>> humanize_bytes(1024 * 1234 * 1111, precision=2)
    '1.31 GB'
    >>> humanize_bytes(1024 * 1234 * 1111, precision=1)
    '1.3 GB'

    """
    abbrevs = [
        (1 << 50, 'PB'),
        (1 << 40, 'TB'),
        (1 << 30, 'GB'),
        (1 << 20, 'MB'),
        (1 << 10, 'kB'),
        (1, 'B')
    ]
    """
    >>, << : python bit shift
    2진수 형태로 저장된 값들을 왼쪽이나 오른쪽으로 지정한 비트 수만큼 밈.
    2배씩, 1/2씩 줄어듬.
    python 에서는 실수 값에 대한 bit shift 연산 안 됨.
    
    10 2진수  =>  1010
    
    10 << 1  =>  10100   =>    20 
    10 >> 1  =>  101     =>    5
    """

    if n == 1:
        return '1 B'

    for factor, suffix in abbrevs:
        if n >= factor:
            break

    return f'{n / factor:.{precision}f} {suffix}'


if __name__ == '__main__':
    n = input('n 값 입력 : ')
    bytes = humanize_bytes(int(n))
    print(bytes)
