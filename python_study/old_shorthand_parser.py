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

# shorthand_parser 커밋 히스토리 따라가보기
# shorthand_parser initial 커밋
# https://github.com/jamesls/aws-cli/commit/a4da9057c3542a1599e6c14bfc6dd6c0f9f98101    <- here

# 참고사이트

## regex 사이트
###  https://wikidocs.net/4308 or https://regexr.com/ or https://regex101.com/r/OVdomu/1/

import re
import string

_EOF = object()


class _NamedRegex(object):
    """
    특정 regex 담아두는 클래스인듯
    """
    def __init__(self, name, regex_str):
        self.name = name
        self.regex = re.compile(regex_str, re.UNICODE)

    def match(self, value):
        return self.regex.match(value)


class ShorthandParseError(Exception):
    def __init__(self, value, expected, actual, index):
        self.value = value
        self.expected = expected
        self.actual = actual
        self.index = index
        msg = self._construct_msg()
        super(ShorthandParseError, self).__init__(msg)

    def _construct_msg(self):
        if '\n' in self.value:
            last_newline = self.value[:self.index].rindex('\n')
            num_spaces = self.index - last_newline - 1
        else:
            num_spaces = self.index
        msg = (
            "Expected: '%s', received: '%s' for input:\n"
            "%s\n"
            "%s\n"
        ) % (self.expected, self.actual, self.value,
             ' ' * num_spaces + '^')
        return msg


class ShorthandParser(object):
    _SINGLE_QUOTED = _NamedRegex('singled quoted', r'\'(?:\\\\|\\\'|[^\'])*\'')   # ' <- single quote로 감싸져있는 것
    _DOUBLE_QUOTED = _NamedRegex('double quoted', r'"(?:\\\\|\\"|[^"])*"')    # " <- double quote로 감싸져있는 것
    # python 3.x부터 ur 안 씀
    _FIRST_VALUE = _NamedRegex('first', u'[\!\#-&\(-\+\--\<\>-Z\\\\-z\u007c-\uffff]'
                               u'[\!\#-&\(-\+\--\\\\\^-\|~-\uffff]*')
    _SECOND_VALUE = _NamedRegex('second', u'[\!\#-&\(-\+\--\<\>-Z\\\\-z\u007c-\uffff]'
                                u'[\!\#-&\(-\+\--\<\>-\uffff]*')

    def __init__(self):
        self._tokens = []

    def parse(self, value):
        self._input_value = value
        self._index = 0
        return self._parameter()

    def _parameter(self):
        # parameter = keyval *("," keyval)
        params = {}
        params.update(self._keyval())
        while self._index < len(self._input_value):
            self._consume_whitespace()
            self._expect(',')
            self._consume_whitespace()
            params.update(self._keyval())
        return params

    def _keyval(self):
        # keyval = key "=" [values]
        key = self._key()
        self._consume_whitespace()
        self._expect("=")
        self._consume_whitespace()
        values = self._values()
        return {key: values}

    def _key(self):
        # key = 1*(alpha / %x30-39) ; [a-zA-Z0-9]
        valid_chars = string.ascii_letters + string.digits
        start = self._index
        while not self._at_eof():
            if self._current() not in valid_chars:
                break
            self._index += 1
        return self._input_value[start:self._index]

    def _values(self):
        # values = csv-list / explicit-list  / hash-literal
        if self._at_eof():
            return ''
        elif self._current() == '[':
            return self._explicit_list()
        elif self._current() == '{':
            return self._hash_literal
        else:
            return self._csv_value()

    def _csv_list(self):
        first_value = self._first_value()
        self._consume_whitespace()
        if self._at_eof() or self._input_value[self._index] != ',':
            return first_value
        self._consume_whitespace()
        self._expect(',')
        self._consume_whitespace()
        csv_list = [first_value]
        while True:
            try:
                current = self._second_value()
                if current is None:
                    break
                self._consume_whitespace()
                if self._at_eof():
                    csv_list.append(current)
                    break
                self._expect(',')
                self._consume_whitespace()
                csv_list.append(current)
            except ShorthandParseError:
                # 이전 콤마를 백트랙킹
                self._backtrack_to(',')
                break
        if len(csv_list) == 1:
            return first_value
        return csv_list

    def _value(self):
        result = self._FIRST_VALUE.match(self._input_value[self._index:])
        if result is not None:
            return self._consume_matched_regex(result)
        return ''

    def _explicit_list(self):
        # explicit-list = "[" [value *(",' value)] "]"
        self._expect('[')
        self._consume_whitespace()
        values = []
        while self._current() != ']':
            """
            여기서 그들은 이걸 바꿔도 되는지 망설였따. 왜냐믄 nested list/hashes를 지원하고 싶었었나봄
            여기는 string 리스트를 파싱하는디 nested lists/hashes를 지원하려는 경우 동작이 변경되기 때문임. 
            원래는 foo=[{a=b},{c=d}]를 
            {'foo':['{a=b}', '{c=d}']}로 바꿨다면 이제
            {'foo': [{'a': 'b'}, {'c': 'd'}]} 이렇게 바뀔 것임
            지금은 이전 동작이 유지되게끔함.
            """
            val = self._value()
            values.append(val)
            self._consume_whitespace()
            if self._current() != ']':
                self._expect(',')
                self._consume_whitespace()
        self._expect(']')
        return values

    def _hash_literal(self):
        self._expect('{')
        self._consume_whitespace()
        keyvals = {}
        while self._current() != '}':
            key = self._key()
            self._consume_whitespace()
            self._expect('=')
            self._consume_whitespace()
            if self._current() == '[':
                v = self._explicit_list()
            elif self._current() == '{':
                v = self._explicit_list()
            else:
                # 아닐 경우에는 스칼라값
                v = self._first_value()
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
        # val-escaped-single  = %x20-26 / %x28-7F / escaped-escape / (escape single-quote)
        return self._consume_quoted(self._SINGLE_QUOTED, escaped_char="'")

    def _double_quoted_value(self):
        return self._consume_quoted(self._DOUBLE_QUOTED, escaped_char='"')

    def _second_value(self):
        if self._current() == "'":
            return self._single_quoted_value()
        elif self._current() == '"':
            return self._double_quoted_value()
        else:
            return self._must_consume_regex(self._SECOND_VALUE)

    def _expect(self, char):
        if self._index >= len(self._input_value):
            raise ShorthandParseError(self._input_value, char, 'EOF', self._index)
        actual = self._input_value[self._index]
        if actual != char:
            raise ShorthandParseError(self._input_value, char, actual, self._index)
        self._index += 1    # index를 왜 1 올리징

    def _must_consume_regex(self, regex):
        result = regex.match(self._input_value[self._index:])
        if result is not None:
            return self._consume_matched_regex(result)
        raise ShorthandParseError(self._input_value, '<%s>' % regex.name, '<none>', self._index)

    ## 흠 이해안된
    def _consume_matched_regex(self, result):
        start, end = result.span()
        v = self._input_value[self._index+start:self._index+end]
        self._index += (end - start)
        return v

    def _current(self):
        # 인덱스가 입력 값의 끝이라면 _EOF가 리턴됨
        if self._index < len(self._input_value):
            return self._input_value[self._index]
        return _EOF

    def _at_eof(self):
        return self._index >= len(self._input_value)

    def _backtrack_to(self, char):
        while self._index >= 0 and self._input_value[self._index] != char:
            self._index -= 1

    def _consume_whitespace(self):
        while self._current() != _EOF and self._current() in string.whitespace:
            self._index += 1