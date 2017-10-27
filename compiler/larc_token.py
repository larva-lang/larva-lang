#coding=utf8

"""
将模块解析为token列表
"""

import os
import re
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
    r"""(!=|==|<<=|<<|<=|>>=|>>|>=|[-%^&*+|/]=|&&|\|\||\+\+|--|\W)|""" +
    #整数
    r"""(\d\w*)|""" +
    #词，关键字或标识符
    r"""([a-zA-Z_]\w*)""")

ASSIGN_SYM_SET = set(["=", "%=", "^=", "&=", "*=", "-=", "+=", "|=", "/=", "<<=", ">>="])
INC_DEC_SYM_SET = set(["++", "--"])
BINOCULAR_OP_SYM_SET = set(["%", "^", "&", "*", "-", "+", "|", "<", ">", "/", "!=", "==", "<<", "<=", ">>", ">=", "&&", "||"])

#合法的符号集
_SYM_SET = set("""~!%^&*()-+|{}[]:;"'<,>.?/""") | set(["!=", "==", "<<", "<=", ">>", ">=", "&&", "||"]) | ASSIGN_SYM_SET | INC_DEC_SYM_SET

#保留字集
_RESERVED_WORD_SET = set(["import", "class", "void", "bool", "schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "float",
                          "double", "ref", "for", "while", "if", "else", "return", "nil", "true", "false", "break", "continue", "this",
                          "public", "interface", "new", "final", "usemethod", "native", "var"])

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
           如果实现为方法，可能会因偶尔的手误导致莫名其妙的错误，比如：if token.is_literal()写成了if token.is_literal，导致bug
           这里实现为属性，规避下风险，且literal、sym等词法元素的判断实现为方法和属性都可以，即：token.is_sym和token.is_sym(sym)都可以工作"""

        class IsLiteral:
            def __init__(self, token):
                self.token = token
            def __nonzero__(self):
                return self.token.type.startswith("literal_")
            def __call__(self, type):
                assert type in ("nil", "bool", "char", "int", "uint", "long", "ulong", "float", "double", "str")
                return self and self.token.type == "literal_" + type
        self.is_literal = IsLiteral(self)

        class IsSym:
            def __init__(self, token):
                self.token = token
            def __nonzero__(self):
                return self.token.type == "sym"
            def __call__(self, sym):
                assert sym in _SYM_SET
                return self and self.token.value == sym
        self.is_sym = IsSym(self)

        class IsReserved:
            def __init__(self, token):
                self.token = token
            def __nonzero__(self):
                return self.token.type == "word" and self.token.value in _RESERVED_WORD_SET
            def __call__(self, word):
                assert word in _RESERVED_WORD_SET, str(word)
                return self and self.token.value == word
        self.is_reserved = IsReserved(self)
        self.is_name = self.type == "word" and self.value not in _RESERVED_WORD_SET

    def __str__(self):
        return """<token %r, %d, %d, %r>""" % (self.src_file, self.line_no, self.pos + 1, self.value)

    def __repr__(self):
        return self.__str__()

    def copy_on_pos(self, t):
        #用t的位置构建一个自身的副本，用于泛型替换等场景
        return _Token(self.type, self.value, t.src_file, t.line_no, t.pos)

    def copy(self):
        return self.copy_on_pos(self)

    def syntax_err(self, msg = ""):
        larc_common.exit("语法错误：文件[%s]行[%d]列[%d]%s" % (self.src_file, self.line_no, self.pos + 1, msg))

    def warning(self, msg):
        larc_common.warning("文件[%s]行[%d]列[%d]%s" % (self.src_file, self.line_no, self.pos + 1, msg))

class TokenList:
    def __init__(self, src_file):
        self.src_file = src_file
        self.l = []
        self.i = 0

    def __nonzero__(self):
        return self.i < len(self.l)

    def __iter__(self):
        for i in xrange(self.i, len(self.l)):
            yield self.l[i]

    def copy(self):
        #拷贝时候也拷贝当前解析到的状态
        c = TokenList(self.src_file)
        c.l = self.l[:]
        c.i = self.i
        return c

    def peek(self):
        if not self:
            larc_common.exit("语法错误：文件[%s]代码意外结束" % self.src_file)
        return self.l[self.i]

    def peek_name(self):
        t = self.peek()
        if not t.is_name:
            t.syntax_err("需要标识符")
        return t.value

    def revert(self, i = None):
        if i is None:
            assert self.i > 0
            self.i -= 1
        else:
            assert 0 <= i < len(self.l)
            self.i = i

    def pop(self):
        t = self.peek()
        self.i += 1
        return t

    def pop_sym(self, sym = None):
        t = self.pop()
        if not t.is_sym:
            if sym is None:
                t.syntax_err("需要符号")
            else:
                t.syntax_err("需要符号'%s'" % sym)
        if sym is None:
            return t, t.value
        if t.value != sym:
            t.syntax_err("需要'%s'" % sym)

    def pop_name(self):
        t = self.pop()
        if not t.is_name:
            t.syntax_err("需要标识符")
        return t, t.value

    def append(self, t):
        assert isinstance(t, _Token)
        self.l.append(t)

    def _remove_None(self):
        self.l = [t for t in self.l if t is not None]

    def join_str_literal(self):
        #合并同表达式中相邻的字符串，即"abc""def""123"合并为"abcdef123"
        first = None
        for i, t in enumerate(self.l):
            if first is not None:
                #正在合并
                if t.type == first.type:
                    first.value += t.value
                    self.l[i] = None
                else:
                    #其他token，结束流程
                    first = None
            elif t.is_literal("str"):
                #开始流程
                first = t
        self._remove_None()

    def split_shr_sym(self):
        assert self.i > 0
        t = self.l[self.i - 1]
        assert t.is_sym(">>")
        self.l[self.i - 1] = _Token("sym", ">", t.src_file, t.line_no, t.pos)
        self.l.insert(self.i, _Token("sym", ">", t.src_file, t.line_no, t.pos + 1))

def _syntax_err(src_file, line_no, pos, msg):
    larc_common.exit("语法错误：文件[%s]行[%d]列[%d]%s" % (src_file, line_no, pos + 1, msg))

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
            _syntax_err(src_file, line_no, pos, "八进制换码序列值过大[\\%s]" % k)
        return chr(i), s[len(k) :]

    if s[0] == "x":
        #十六进制换码序列，两位HH
        if len(s) < 3:
            _syntax_err(src_file, line_no, pos, "十六进制换码序列长度不够")
        try:
            i = int(s[1 : 3], 16)
        except ValueError:
            _syntax_err(src_file, line_no, pos, "十六进制换码序列值错误[\\%s]" % s[: 3])
        return chr(i), s[3 :]

    _syntax_err(src_file, line_no, pos, "非法的转义字符[%s]" % s[0])

def _parse_str(s, src_file, line_no, pos):
    #解析代码中的字符串
    s_len = len(s)
    quota = s[0]
    s = s[1 :]

    l = [] #字符列表

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
        else:
            #普通字符
            if ord(c) < 32:
                _syntax_err(src_file, line_no, pos, "字符串中出现ascii控制码[0x%02X]" % ord(c))
        l.append(c) #添加到列表
    else:
        _syntax_err(src_file, line_no, pos, "字符串不完整")

    #返回字面量和消耗的源代码长度
    return "".join(l), s_len - len(s)

def _parse_token(src_file, line_no, line, pos):
    s = line[pos :]
    m = _TOKEN_RE.match(s)
    if m is None:
        _syntax_err(src_file, line_no, pos, "")

    f, sym, i, w = m.groups()

    if f is not None:
        #浮点数
        if f[-1].upper() == "F":
            try:
                value = float(f[: -1])
                if math.isnan(value) or math.isinf(value):
                    raise ValueError
                if value < float.fromhex("0x1p-126"):
                    value = 0
                elif value > float.fromhex("0x1.FFFFFEp127"):
                    raise ValueError
            except ValueError:
                _syntax_err(src_file, line_no, pos, "非法的float字面量'%s'" % f)
            return _Token("literal_float", value, src_file, line_no, pos), len(f)
        else:
            try:
                value = float(f)
                if math.isnan(value) or math.isinf(value):
                    raise ValueError
            except ValueError:
                _syntax_err(src_file, line_no, pos, "非法的double字面量'%s'" % f)
            return _Token("literal_double", value, src_file, line_no, pos), len(f)

    if sym is not None:
        #符号
        if sym not in _SYM_SET:
            _syntax_err(src_file, line_no, pos, "非法的符号'%s'" % sym)

        if sym in ("'", '"'):
            #字符或字符串
            value, token_len = _parse_str(s, src_file, line_no, pos)
            if sym == '"':
                #字符串
                return _Token("literal_str", value, src_file, line_no, pos), token_len
            #字符
            if len(value) != 1:
                _syntax_err(src_file, line_no, pos, "字符字面量长度必须为1")
            return _Token("literal_char", ord(value), src_file, line_no, pos), token_len

        #普通符号token
        return _Token("sym", sym, src_file, line_no, pos), len(sym)

    if i is not None:
        #整数
        try:
            if i[-2 :].upper() == "UL":
                value = int(i[: -2], 0)
                if value >= 2 ** 64:
                    _syntax_err(src_file, line_no, pos, "过大的ulong字面量'%s'" % i)
                type = "ulong"
            elif i[-1].upper() == "L":
                value = int(i[: -1], 0)
                if value >= 2 ** 63:
                    _syntax_err(src_file, line_no, pos, "过大的long字面量'%s'" % i)
                type = "long"
            elif i[-1].upper() == "U":
                value = int(i[: -1], 0)
                if value >= 2 ** 32:
                    _syntax_err(src_file, line_no, pos, "过大的uint字面量'%s'" % i)
                type = "uint"
            else:
                value = int(i, 0)
                if value >= 2 ** 31:
                    _syntax_err(src_file, line_no, pos, "过大的int字面量'%s'" % i)
                type = "int"
        except ValueError:
            _syntax_err(src_file, line_no, pos, "非法的整数字面量'%s'" % i)
        return _Token("literal_" + type, value, src_file, line_no, pos), len(i)

    if w is not None:
        if w in ("true", "false"):
            return _Token("literal_bool", w, src_file, line_no, pos), len(w)
        if w == "nil":
            return _Token("literal_nil", w, src_file, line_no, pos), len(w)
        return _Token("word", w, src_file, line_no, pos), len(w)

    raise Exception("Bug")

def parse_token_list(src_file):
    f = open(src_file)
    f.seek(0, os.SEEK_END)
    if f.tell() > 100 * 1024 ** 2:
        larc_common.exit("源代码文件[%s]过大" % src_file)
    f.seek(0, os.SEEK_SET)
    line_list = f.read().splitlines()

    token_list = TokenList(src_file)
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
            pos = 0

        #解析当前行token
        while pos < len(line):
            #跳过空格
            while pos < len(line) and line[pos] in "\t\x20":
                pos += 1
            if pos >= len(line):
                #行结束
                break

            if line[pos : pos + 2] == "//":
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
            token, token_len = _parse_token(src_file, line_no, line, pos)
            token_list.append(token)
            pos += token_len

    if in_comment:
        _syntax_err(src_file, len(line_list), len(line_list[-1]), "存在未结束的块注释")

    token_list.join_str_literal()

    return token_list

def parse_token_list_until_sym(token_list, end_sym_set):
    sub_token_list = TokenList(token_list.src_file)
    stk = []
    while True:
        t = token_list.pop()
        sub_token_list.append(t)
        if t.is_sym and t.value in end_sym_set and not stk:
            return sub_token_list, t.value
        if t.is_sym and t.value in ("(", "[", "{"):
            stk.append(t)
        if t.is_sym and t.value in (")", "]", "}"):
            if not stk or t.value != {"(" : ")", "[" : "]", "{" : "}"}[stk[-1].value]:
                t.syntax_err("未匹配的'%s'" % t.value)
            stk.pop()
