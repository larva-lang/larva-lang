#coding=utf8

"""
将模块解析为token列表
"""

import re
import codecs
import math
import larc_common

#用于解析token的正则表达式
_TOKEN_RE = re.compile(
    #浮点数
    r"""(\d+\.?\d*[eE][+-]?\w+|""" +
    r"""\.\d+[eE][+-]?\w+|""" +
    r"""\d+\.\w*|""" +
    r"""\.\d\w*)|""" +
    #符号
    r"""(b"|b'|!=|==|<<=|<<|<=|>>>=|>>>|>>=|>>|>=|\W=|\W)|""" +
    #整数
    r"""(\d\w*)|""" +
    #词，关键字或标识符
    r"""([a-zA-Z_]\w*)""")

#合法的符号集
_SYM_SET = (set("""~%^&*()-+=|{}[]:"'<,>/.""") |
            set(['b"', "b'", "!=", "==", "<<=", "<<", "<=", ">>>=", ">>>",
                 ">>=", ">>", ">="]) |
            set(["%=", "^=", "&=", "*=", "-=", "+=", "|=", "/="]))

#保留字集
_RESERVED_WORD_SET = set(["if", "elif", "else", "while", "return", "break",
                          "continue", "for", "in", "not", "and", "or", "nil",
                          "print", "func", "import", "global", "true", "false",
                          "pass"])

_TOKEN_TYPE_INDENT = object()
_TOKEN_TYPE_FLOAT = object()
_TOKEN_TYPE_SYM = object()
_TOKEN_TYPE_LONG = object()
_TOKEN_TYPE_INT = object()
_TOKEN_TYPE_WORD = object()
_TOKEN_TYPE_STR = object()
_TOKEN_TYPE_BYTE = object()

class _Token:
    def __init__(self, type, value, src_file, line_no, pos):
        self.type = type
        self.value = value
        self.src_file = src_file
        self.line_no = line_no
        self.pos = pos

        self._set_is_XXX()

    def _set_is_XXX(self):
        """设置各种is_XXX属性
           如果实现为方法，可能会因偶尔的手误导致莫名其妙的错误
           比如：if token.is_const()写成了if token.is_const，导致bug
           这里实现为属性，规避下风险
           is_indent和is_sym的判断实现为方法和属性都可以，即：
           token.is_indent和token.is_indent(count)都可以工作"""

        class IsIndent:
            def __init__(self, token):
                self.token = token

            def __nonzero__(self):
                return self.token.type == _TOKEN_TYPE_INDENT

            def __call__(self, count):
                return (self.token.type == _TOKEN_TYPE_INDENT and
                        self.token.value == count)

        self.is_indent = IsIndent(self)

        self.is_const = False
        for const_type in "float", "long", "int", "str", "byte":
            if self.type == globals()["_TOKEN_TYPE_" + const_type.upper()]:
                self.is_const = True
                setattr(self, "is_" + const_type, True)
            else:
                setattr(self, "is_" + const_type, False)

        class IsSym:
            def __init__(self, token):
                self.token = token

            def __nonzero__(self):
                return self.token.type == _TOKEN_TYPE_SYM

            def __call__(self, sym):
                return (self.token.type == _TOKEN_TYPE_SYM and
                        self.token.value == sym)

        self.is_sym = IsSym(self)

        self.is_reserved = False
        self.is_name = False
        for w in _RESERVED_WORD_SET:
            setattr(self, "is_" + w, False)
        if self.type == _TOKEN_TYPE_WORD:
            self.is_reserved = self.value in _RESERVED_WORD_SET
            self.is_name = not self.is_reserved
            if self.is_reserved:
                setattr(self, "is_" + self.value, True)
                if self.value in ("true", "false", "nil"):
                    self.is_const = True

    def __str__(self):
        return ("""<token %r, %d, %d, %r>""" %
                (self.src_file, self.line_no, self.pos, self.value))

    def __repr__(self):
        return self.__str__()

    def syntax_err(self, msg = ""):
        larc_common.exit("语法错误：文件[%s]行[%d]列[%d]%s" %
                         (self.src_file, self.line_no, self.pos + 1, msg))

    def indent_err(self):
        self.syntax_err("缩进错误")

class _TokenList:
    def __init__(self, src_file):
        self.src_file = src_file
        self.l = []
        self.tail_indent = None
        self.i = 0

    def __nonzero__(self):
        return self.i < len(self.l)

    def peek(self):
        if not self:
            larc_common.exit("语法错误：文件[%s]代码意外结束" % self.src_file)
        return self.l[self.i]

    def peek_indent(self, count = None):
        t = self.peek()
        if not t.is_indent:
            t.syntax_err("需要缩进")
        if count is None:
            return t.value
        if t.value != count:
            t.indent_err()

    def peek_name(self):
        t = self.peek()
        if not t.is_name:
            t.syntax_err("需要标识符")
        return t.value

    def revert(self):
        assert self.i > 0
        self.i -= 1

    def pop(self):
        t = self.peek()
        self.i += 1
        return t

    def pop_indent(self, count = None):
        t = self.pop()
        if not t.is_indent:
            t.syntax_err("需要缩进")
        if count is None:
            return t.value
        if t.value != count:
            t.indent_err()

    def pop_sym(self, sym = None):
        t = self.pop()
        if not t.is_sym:
            t.syntax_err("需要符号")
        if sym is None:
            return t.value
        if t.value != sym:
            t.syntax_err("需要'%s'" % sym)

    def pop_name(self):
        t = self.pop()
        if not t.is_name:
            t.syntax_err("需要标识符")
        return t.value

    def append(self, t):
        assert isinstance(t, _Token)
        if t.is_indent:
            #连续的缩进只取最后一个，这个机制同时防止了末尾缩进进入编译过程
            self.tail_indent = t
        else:
            if self.tail_indent is not None:
                self.l.append(self.tail_indent)
                self.tail_indent = None
            self.l.append(t)

    def _remove_None(self):
        self.l = [t for t in self.l if t is not None]

    def join_multi_line(self):
        #处理折行，同时检查括号匹配
        stk = []
        for i, t in enumerate(self.l):
            if stk and t.is_indent:
                #去掉所有括号中的缩进
                self.l[i] = None
                continue
            if t.is_sym("(") or t.is_sym("[") or t.is_sym("{"):
                #正括号压栈
                stk.append(t)
                continue
            for k, v in {")" : "(",
                         "]" : "[",
                         "}" : "{"}.iteritems():
                if t.is_sym(k):
                    #反括号，检查匹配情况
                    if stk and stk[-1].is_sym(v):
                        stk.pop()
                        break
                    t.syntax_err("未匹配的括号'%s'" % k)
        if stk:
            stk[-1].syntax_err("未匹配的括号'%s'" % stk[-1].value)
        self._remove_None()

    def join_str_or_byte_const(self):
        #合并同表达式中相邻的字符串或字节串，即"abc""def""123"合并为"abcdef123"
        first = None
        for i, t in enumerate(self.l):
            if first is not None:
                #正在合并
                if t.type == first.type:
                    first.value += t.value
                    self.l[i] = None
                    continue
                if t.is_str or t.is_byte:
                    t.syntax_err("字符串和字节串不可连接")
                #其他token，结束流程
                first = None
                continue
            if t.is_str or t.is_byte:
                #开始流程
                first = t
        self._remove_None()

def _get_encoding(src_file, line):
    encoding = "ascii" #默认用ascii编码
    if line.startswith("\xEF\xBB\xBF"):
        #utf-8 bom
        line = line[3 :]
        encoding = "utf8"
        utf8_bom = True
    else:
        utf8_bom = False
    m = re.match(r"#.*coding[=:]\s*([-\w.]+)", line)
    if m is not None:
        #指定了编码
        if utf8_bom:
            larc_common.warning(
                "警告：文件[%s]使用了utf8 bom，忽略指定的coding" % src_file)
        else:
            encoding = m.groups()[0]

    try:
        codecs.lookup(encoding)
    except LookupError:
        larc_common.exit("文件[%s]指定了不支持的编码[%s]" %
                         (src_file, encoding))

    return encoding, line

def _parse_indent(line):
    indent = 0
    for pos in xrange(len(line)):
        if line[pos] == " ":
            indent += 1
        elif line[pos] == "\t":
            #向前缩进至最近一个8的整数倍
            indent += 8 - indent % 8
        else:
            break
    else:
        pos = len(line)
    return indent, pos

def _syntax_err(src_file, line_no, pos, msg):
    larc_common.exit("语法错误：文件[%s]行[%d]列[%d]%s" %
                     (src_file, line_no, pos + 1, msg))

def _get_escape_char(s, src_file, line_no, pos):
    if s[0] in "abfnrtv":
        #特殊符号转义
        return eval("'\\" + s[0] + "'"), s[1 :]

    if s[0] in ("\\", "'", '"'):
        #斜杠和引号转义
        return s[0], s[1 :]

    if s[0] >= "0" and s[0] <= "7":
        #八进制换码序列，1到3位数字
        for k in s[: 3], s[: 2], s[0]:
            try:
                i = int(k, 8)
                break
            except ValueError:
                pass
        if i > 255:
            _syntax_err(src_file, line_no, pos,
                        "八进制换码序列值过大[\\%s]" % k)
        return chr(i), s[len(k) :]

    if s[0] == "x":
        #十六进制换码序列，两位HH
        if len(s) < 3:
            _syntax_err(src_file, line_no, pos, "十六进制换码序列长度不够")
        try:
            i = int(s[1 : 3], 16)
        except ValueError:
            _syntax_err(src_file, line_no, pos,
                        "十六进制换码序列值错误[\\%s]" % s[: 3])
        return chr(i), s[3 :]

    if s[0] == "u":
        #unicode16换码序列，四位HHHH
        if len(s) < 5:
            _syntax_err(src_file, line_no, pos, "unicode16换码序列长度不够")
        try:
            i = int(s[1 : 5], 16)
        except ValueError:
            _syntax_err(src_file, line_no, pos,
                        "unicode16换码序列值错误[\\%s]" % s[: 5])
        return unichr(i), s[5 :]

    if s[0] == "U":
        #unicode32换码序列，八位HHHHHHHH
        if len(s) < 9:
            _syntax_err(src_file, line_no, pos, "unicode32换码序列长度不够")
        try:
            i = int(s[1 : 9], 16)
        except ValueError:
            _syntax_err(src_file, line_no, pos,
                        "unicode32换码序列值错误[\\%s]" % s[: 9])
        if i > 0x10FFFF:
            _syntax_err(src_file, line_no, pos,
                        "unicode32换码序列值过大[\\%s]" % s[: 9])
        return eval("u'\U%08X'" % i), s[9 :]

    _syntax_err(src_file, line_no, pos, "非法的转义字符[%s]" % s[0])

def _parse_str(s, src_file, line_no, pos, encoding):
    #解析代码中的字符串到unicode内部表示
    s_len = len(s)
    quota = s[0]
    s = s[1 :]

    l = [] #字符串列表

    while s:
        c = s[0]
        s = s[1 :]
        if c == quota:
            break
        if c == "\\":
            #转义字符
            if s == "":
                _syntax_err(src_file, line_no, pos, "字符串在转义处结束")
            c, s = _get_escape_char(s, src_file, line_no, pos)
            if isinstance(c, unicode):
                l.append(c)
            else:
                l.append(unichr(ord(c)))
            continue
        #普通字符
        if ord(c) < 32:
            _syntax_err(src_file, line_no, pos,
                        "字符串中出现ascii控制码[0x%02X]" % ord(c))
        if l and isinstance(l[-1], str):
            l[-1] += c
        else:
            l.append(c)
    else:
        _syntax_err(src_file, line_no, pos, "字符串不完整")

    for i in xrange(len(l)):
        if isinstance(l[i], str):
            try:
                l[i] = l[i].decode(encoding)
            except UnicodeDecodeError:
                _syntax_err(src_file, line_no, pos,
                            "字符串通过[%s]解码失败" % encoding)

    return u"".join(l), s_len - len(s)

def _parse_byte(s, src_file, line_no, pos):
    #解析字节串
    s_len = len(s)
    quota = s[1]
    s = s[2 :]

    b = ""

    while s:
        c = s[0]
        s = s[1 :]
        if c == quota:
            break
        if c == "\\":
            #转义字符
            if s == "":
                _syntax_err(src_file, line_no, pos, "字节串在转义处结束")
            c, s = _get_escape_char(s, src_file, line_no, pos)
            if isinstance(c, unicode):
                _syntax_err(src_file, line_no, pos,
                            "字节串包含unicode换码序列")
            b += c
            continue
        #普通字符
        if ord(c) < 32:
            _syntax_err(src_file, line_no, pos,
                        "字节串中出现ascii控制码[0x%02X]" % ord(c))
        if ord(c) > 127:
            _syntax_err(src_file, line_no, pos,
                        "字节串中出现扩展ascii码[0x%02X]" % ord(c))
        b += c
    else:
        _syntax_err(src_file, line_no, pos, "字节串不完整")

    return b, s_len - len(s)

def _parse_token(src_file, line_no, line, pos, encoding):
    s = line[pos :]
    m = _TOKEN_RE.match(s)
    if m is None:
        _syntax_err(src_file, line_no, pos, "")

    f, sym, i, w = m.groups()

    if f is not None:
        #浮点数
        try:
            value = float(f)
            if math.isnan(value) or math.isinf(value):
                raise ValueError
        except ValueError:
            _syntax_err(src_file, line_no, pos, "非法的浮点数'%s'" % f)
        return _Token(_TOKEN_TYPE_FLOAT, value, src_file, line_no, pos), len(f)

    if sym is not None:
        #符号
        if sym not in _SYM_SET:
            _syntax_err(src_file, line_no, pos, "非法的符号'%s'" % sym)

        if sym in ("'", '"'):
            #字符串
            value, token_len = _parse_str(s, src_file, line_no, pos, encoding)
            return (_Token(_TOKEN_TYPE_STR, value, src_file, line_no, pos),
                    token_len)

        if sym in ("b'", 'b"'):
            #字节串
            value, token_len = _parse_byte(s, src_file, line_no, pos)
            return (_Token(_TOKEN_TYPE_BYTE, value, src_file, line_no, pos),
                    token_len)

        #普通符号token
        return _Token(_TOKEN_TYPE_SYM, sym, src_file, line_no, pos), len(sym)

    if i is not None:
        #整数
        if i[-1] == "L":
            #长整数
            try:
                value = int(i[: -1], 0)
            except ValueError:
                _syntax_err(src_file, line_no, pos, "非法的长整数'%s'" % i)
            return (_Token(_TOKEN_TYPE_LONG, value, src_file, line_no, pos),
                    len(i))

        #普通整数
        try:
            value = int(i, 0)
        except ValueError:
            _syntax_err(src_file, line_no, pos, "非法的整数'%s'" % i)
        if i[0] == "0":
            #非10进制，作为uint64解析，转换为int
            if value > 2 ** 64 - 1:
                _syntax_err(src_file, line_no, pos, "过大的整数'%s'" % i)
            if value > 2 ** 63 - 1:
                value -= 2 ** 64
        else:
            #10进制
            if value > 2 ** 63 - 1:
                _syntax_err(src_file, line_no, pos, "过大的整数'%s'" % i)
        return _Token(_TOKEN_TYPE_INT, value, src_file, line_no, pos), len(i)

    if w is not None:
        return _Token(_TOKEN_TYPE_WORD, w, src_file, line_no, pos), len(w)

def parse_token_list(src_file):
    line_list = open(src_file).read().splitlines()

    #从第一行获取编码信息
    encoding, line_list[0] = _get_encoding(src_file, line_list[0])

    token_list = _TokenList(src_file)
    in_comment = False
    for line_no, line in enumerate(line_list):
        line_no += 1

        if in_comment:
            #有未完的注释
            pos = line.find("*/")
            if pos < 0:
                #整行都是注释，忽略
                continue
            pos += 2
            in_comment = False
        else:
            #正常的行，先解析缩进
            indent, pos = _parse_indent(line)
            token_list.append(_Token(_TOKEN_TYPE_INDENT, indent, src_file,
                                     line_no, 0))

        #解析当前行token
        while pos < len(line):
            pos += len(line) - pos - len(line[pos :].lstrip(" \t")) #跳过空格
            if pos >= len(line):
                break
            if line[pos] == "#" or line[pos : pos + 2] == "//":
                #单行注释，略过本行
                break
            if line[pos : pos + 2] == "/*":
                #块注释
                pos += 2
                comment_end_pos = line[pos :].find("*/")
                if comment_end_pos < 0:
                    #注释跨行了，设置标记略过本行
                    in_comment = True
                    break
                #注释在本行结束，跳过它
                pos += comment_end_pos + 2
                continue

            #解析token
            token, token_len = _parse_token(src_file, line_no, line, pos,
                                            encoding)
            token_list.append(token)
            pos += token_len

    if in_comment:
        _syntax_err(src_file, len(line_list), len(line_list[-1]),
                    "存在未结束的块注释")

    token_list.join_multi_line()
    token_list.join_str_or_byte_const()

    return token_list
