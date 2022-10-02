import unittest
# from shorthand_parser import ShorthandParser
from old_shorthand_parser import ShorthandParser

# unittest로 변경해보기
# https://docs.python.org/ko/3/library/unittest.html
class TestShorthandParser(unittest.TestCase):
    def test_parse(self):
        # 단일 값 Key val 쌍
        self.can_parse('foo=bar', {'foo': 'bar'})
        self.can_parse('foo=bar,baz=qux', {'foo': 'bar', 'baz': 'qux'})
        self.can_parse('a=b,c=d,e=f', {'a': 'b', 'c': 'd', 'e': 'f'})

        # 빈 값도 허용
        self.can_parse('foo=', {'foo': ''})
        self.can_parse('foo=,bar=', {'foo': '', 'bar': ''})

        # 유니코드도 허용
        self.can_parse(u'foo=\u2713', {'foo': u'\u2713'})
        self.can_parse(u'foo=\u2713,\u2713', {'foo': [u'\u2713', u'\u2713']})

        # csv 값 쌍
        self.can_parse('foo=a,b', {'foo': ['a', 'b']})
        self.can_parse('foo=a,b,c', {'foo': ['a', 'b', 'c']})
        self.can_parse('foo=a,b,bar=c,d', {'foo': ['a', 'b'],
                                           'bar': ['c', 'd']})
        self.can_parse('foo=a,b,c,bar=d,e,f',
           {'foo': ['a', 'b', 'c'], 'bar': ['d', 'e', 'f']})

        # 값에 띄워쓰기 허용
        self.can_parse('foo=a,b=with space', {'foo': 'a', 'b': 'with space'})

        # 후행에 띄워쓰기 무시
        self.can_parse('foo=a,b=with trailing space  ',
           {'foo': 'a', 'b': 'with trailing space'})
        self.can_parse('foo=first space',
           {'foo': 'first space'})
        self.can_parse('foo=a space,bar=a space,baz=a space',
           {'foo': 'a space', 'bar': 'a space', 'baz': 'a space'})

    def can_parse(self, data, expected):
        # actual = ShorthandParser().parse(data)
        actual = ShorthandParser().parse(data)
        self.assertEqual(actual, expected)
