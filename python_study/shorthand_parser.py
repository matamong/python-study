# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.


# 오픈소스인 AWS CLI - Shorthand Parser 코드를 뜯어보고 따라치면서 공부
# https://github.com/aws/aws-cli/blob/2f09fcc0e28784affb472d9aa0d3dd2c3ab513de/awscli/shorthand.py#L116-L384
#
#

import re
import string

_EOF = object()   # object()는 모든 클래스의 기반이 되는 기능이 없는 객체를 반환함


class _NamedRegex(object):
    def __init__(self, name, regex_str):
        self.name = name
        self.regex = re.compile(regex_str, re.UNICODE)

    def match(self, value):
        return self.regex.match(value)


class ShorthandParser(object):
    """
    CLI의 간단한 문법을 파싱해줌.
    JSON models에 의존하지않는 점 주의.
    """

    _SINGLE_QUOTED = _NamedRegex('singled quoted', r'\'(?:\\\\|\\\'|[^\'])*\'')
    _DOUBLE_QUOTED = _NamedRegex('double quoted', r'"(?:\\\\|\\"|[^"])*"')
    _START_WORD = u'\!\#-&\(-\+\--\<\>-Z\\\\-z\u007c-\uffff'
    _FIRST_FOLLOW_CHARS = u'\s\!\#-&\(-\+\--\\\\\^-\|~-\uffff'
    _SECOND_FOLLOW_CHARS = u'\s\!\#-&\(-\+\--\<\>-\uffff'
    _ESCAPED_COMMA = '(\\\\,)'
    _FIRST_VALUE = _NamedRegex(
        'first',
        u'({escaped_comma}|[{start_word}])'
        u'({escaped_comma}|[{follow_chars}])*'.format(
            escaped_comma=_ESCAPED_COMMA,
            start_word=_START_WORD,
            follow_chars=_FIRST_FOLLOW_CHARS,
        ))
    _SECOND_VALUE = _NamedRegex(
        'second',
        u'({escaped_comma}|[{start_word}])'
        u'({escaped_comma}|[{follow_chars}])*'.format(
            escaped_comma=_ESCAPED_COMMA,
            start_word=_START_WORD,
            follow_chars=_SECOND_FOLLOW_CHARS,
        ))

    def __init__(self):
        self._tokens = []

    def parse(self, value):
        """
        요약한 구문을 파싱
        example:
            parser = ShorthandParser()
            parser.parse('a=b')    # {'a': 'b'}
            parser.parse('a=b,c')  # {'a': ['b', 'c']}
        :type value: str
        :param value: 파싱할 수 있는 아무 값
        :return: dictionary 형태의 파싱된 값
        """
        self._input_value = value
        self._index = 0
        return self._parameter()

    def _parameter(self):
        # parameter = keyval *("," keyval)
        params = {}
        key, val = self._keyval()
        params[key] = val
        last_index = self._index
        while self._index < len(self._input_value):
            self._expect(',', consume_whitespace=True)
            key, val = self._keyval()
            # key가 이미 정의됐다면 인자가 이상하게 적힌것임. 유저가 알 수 있도록 에러내기
            if key in params:
                raise DuplicateKeyInObjectError(
                    key, self._input_value, last_index + 1
                )
            params[key] = val
            last_index = self._index
        return params

    def _keyval(self):
        # keyval = key "=" [values]
        key = self._key()
        self._expect('=', consume_whitespace=True)
        values = self._values()
        return key, values

    def _expect(self, char, consume_whitespace=False):
        if consume_whitespace:
            self._consume_whitespace()
        if self._index >= len(self._input_value):
            raise ShorthandParseSyntaxError(self._input_value, char,
                                            'EOF', self._index)
        actual = self._input_value[self._index]
        if actual != char:
            raise ShorthandParseSyntaxError(self._input_value, char,
                                            actual, self._index)
        self._index += 1
        if consume_whitespace:
            self._consume_whitespace()

    def _key(self):
        # key = 1*(alpha / %x30-39 / %x5f / %x2e / %x23)    ; [a-zA-Z0-9\-_.#/]
        valid_chars = string.ascii_letters + string.digits + '-_.#/:'
        start = self._index
        while not self._at_eof():
            if self._current() not in valid_chars:
                break
            self._index += 1
        return self._input_value[start:self._index]

    def _values(self):
        # values = csv-list / explicit-list / hash-literal
        if self._at_eof():
            return ''
        elif self._current() == '[':
            return self._explicit_list()
        elif self._current() == '{':
            return self._hash_literal()
        else:
            return self._csv_value()

    def _csv_value(self):
        # 다음 두 상황을 서포트한다잉
        # foo=bar   -> 'bar'
        #      ^
        # foo=bar,baz = > ['bar', 'baz']
        #      ^
        first_value = self._first_value()
        self._consume_whitespace()
        if self._at_eof() or self._input_value[self._index] != ',':
            return first_value
        self._expect(',', consume_whitespace=True)
        csv_list = [first_value]
        # 남은 리스트 값을 파싱해보자.
        # 아무것도 파싱안하는 경우도 있음
        # a=b,c=d
        #     ^-여기
        # 위의 상황이면 ShorhandParser를 부르고, 콤마로 돌아가서 단일 스칼라인 'b'값을 반환한다.
        while True:
            try:
                current = self._second_value()
                self._consume_whitespace()
                if self._at_eof():
                    csv_list.append(current)
                    break
                self._expect(',', consume_whitespace=True)
                csv_list.append(current)
            except ShorthandParseSyntaxError:
                # 이전 콤마를 다시 트랙킹한다.
                # 요런 상황이 나올 수 있음
                # foo=a,b,c=d,e=f
                #     ^-시작
                # foo=a,b,c=d,e=f
                #          ^-에러, "expected ',' received '='
                # foo=a,b,c=d,e=f
                #        ^-요기를 다시 백트랙킹
                if self._at_eof():
                    raise
                self._backtrack_to(',')
                break
        if len(csv_list) == 1:
            # 요것은 foo=bar 케이스이므로 스칼라 값 'bar', 즉 {"bar":["bar"]} 대신 {"foo":"bar"}로 해야함
            return first_value
        return csv_list

    def _at_eof(self):
        return self._index >= len(self._input_value)

    def _current(self):
        # 인덱스가 인풋값의 끝이라면 _EOF가 반화된다.
        if self._index < len(self._input_value):
            return self._input_value[self._index]
        return _EOF

    def _value(self):
        result = self._FIRST_VALUE.match(self._input_value[self._index:])
        if result is not None:
            consumed = self._consume_matched_regex(result)
            return consumed.replace('\\,', ',').rstrip()    # rstrip(): 오른쪽 공백 제거
        return ''

    def _explicit_list(self):
        # explicit-list "[" [value *(",' value)] "]"
        self._expect('[', consume_whitespace=True)
        values = []
        while self._current() != ']':
            val = self._explicit_values()
            values.append(val)
            self._consume_whitespace()
            if self._current() != ']':
                self._expect(',')
                self._consume_whitespace()
        self._expect(']')
        return values

    def _explicit_values(self):
        # values = csv-list / explicit-list / hash-literal
        if self._current() == '[':
            return self._explicit_list()
        elif self._current() == '{':
            return self._hash_literal()
        else:
            return self._first_values()

    def _hash_literal(self):
        self._expect('{', consume_whitespace=True)
        keyvals = {}
        while self._current() != '}':
            key = self._key()
            self._expect('=', consume_whitespace=True)
            v = self._explicit_values()
            self._consume_whitespace()
            if self._current() != '}':
                self._expect(',')
                self._consume_whitespace()
            keyvals[key] = v
        self._expect('}')
        return keyvals

    def _first_value(self):
        # first-value = value / single-quoted-val / double-quoted-val
        if self._current() == "'":
            return self._single_quoted_value()
        elif self._current() == '"':
            return self._double_quoted_value()
        return self._value()

    def _single_quoted_value(self):
        # single-quoted-value = %x27 *(val-escaped-single) %x27
        # val-escaped-single = %x20-26 / %x28-7F / escaped-escape / (escape single-quote)
        return self._consume_quoted(self._SINGLE_QUOTED, escaped_char="'")

    def _consume_quoted(self, regex, escaped_char=None):
        value = self._must_consume_regex(regex)[1:-1]
        if escaped_char is not None:
            value = value.replace("\\%s" % escaped_char, escaped_char)
            value = value.replace("\\\\", "\\")
        return value

    def _double_quoted_value(self):
        return self._consume_quoted(self._DOUBLE_QUOTED, escaped_char='"')

    def _second_value(self):
        if self._current() == "'":
            return self._single_quoted_value()
        elif self._current() == '"':
            return self._double_quoted_value()
        else:
            consumed = self._must_consume_regex(self._SECOND_VALUE)
            return consumed.replace('\\,', ',').rstrip()

    def _must_consume_regex(self, regex):
        result = regex.match(self._input_value[self._index:])
        if result is not None:
            return self._consume_matched_regex(result)
        raise ShorthandParseSyntaxError(self._input_value, '<%s>' % regex.name, '<none>', self._index)

    def _consume_matched_regex(self, result):
        start, end = result.span()  # 매치된 문자열의 (시작, 끝)에 해당하는 튜플을 돌려준다.
        v = self._input_value[self._index+start:self._index+end]
        self._index += (end - start)
        return v

    def _backtrack_to(self, char):
        while self._index >= 0 and self._input_value[self._index] != char:
            self._index -= 1

    def _consume_whitespace(self):
        while self._current() != _EOF and self._current() in string.whitespace:
            self._index += 1


class ShorthandParseError(Exception):
    def _error_location(self):
        consumed, remaining, num_spaces = self.value, '', self.index
        if '\n' in self.value[:self.index]:
            # 사용된 표현식에 줄바꿈이 있으면 마지막 줄 바꿈부터 다시 카운팅할것임
            # foo=bar, \n
            # bar==baz
            #     ^
            last_newline = self.value[:self.index].rindex('n')   # rindex() : 문자열의 마지막 위치 반환 (없으면 exception)
            num_spaces = self.index - last_newline - 1
        if '\n' in self.value[self.index:]:
            # 나머지에 줄 바꿈이 있으면 값을 소모된 값과 남은 값으로 나눈다.
            # foo==bar,\n
            #     ^
            # bar=baz
            next_newline = self.index + self.value[self.index:].index('\n')
            consumed = self.value[:next_newline]
            remaining = self.value[next_newline:]
        return '%s\n%s%s' % (consumed, (' ' * num_spaces) + '^', remaining)


class ShorthandParseSyntaxError(ShorthandParseError):
    def __init__(self, value, expected, actual, index):
        self.value = value
        self.expected = expected
        self.actual = actual
        self.index = index
        msg = self._construct_msg()
        super(ShorthandParseSyntaxError, self).__init__(msg)     # super(msg)로 될 수 있을 듯? python 3.0부터 된다든디

    def _construct_msg(self):
        msg = (
            "Expected: '%s', received: '%s' for input:\n"
            "%s"
        ) % (self.expected, self.actual, self._error_location())
        return msg


class DuplicateKeyInObjectError(ShorthandParseError):
    def __init__(self, key, value, index):
        self.key = key
        self.value = value
        self.index = index
        msg = self._construct_msg()
        super(DuplicateKeyInObjectError, self).__init__(msg)

    def _construct_msg(self):
        msg = (
            "Second instance of key \"%s\" encountered for input:\n%s\n"
            "This is often because there is a preceeding \",\" instead of a"
            "space."
        ) % (self.key, self._error_location())
        return msg
