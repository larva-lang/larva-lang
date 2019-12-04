#coding=utf8

"""
将模块解析为token列表
"""

import os, re, math, platform, copy
import larc_common

#用于解析token的正则表达式
_TOKEN_RE = re.compile(
    #浮点数
    r"""(\d+\.?\d*[eE][+-]?\w+|"""
    r"""\.\d+[eE][+-]?\w+|"""
    r"""\d+\.\w*|"""
    r"""\.\d\w*)|"""
    #十六进制浮点数
    r"""(0[xX][0-9A-Fa-f]+\.?[0-9A-Fa-f]*[pP][+-]?\w+|"""
    r"""0[xX]\.[0-9A-Fa-f]+[pP][+-]?\w+|"""
    r"""0[xX][0-9A-Fa-f]+\.\w*|"""
    r"""0[xX]\.[0-9A-Fa-f]\w*)|"""
    #符号
    r"""(!==|===|!=|==|<<=|<<|<=|>>=|>>|>=|\.\.|[-%^&*+|/]=|&&|\|\||\+\+|--|\W)|"""
    #整数
    r"""(\d\w*)|"""
    #词，关键字或标识符
    r"""([a-zA-Z_]\w*)""")

ASSIGN_SYM_SET = set(["=", "%=", "^=", "&=", "*=", "-=", "+=", "|=", "/=", "<<=", ">>="])
INC_DEC_SYM_SET = set(["++", "--"])
BINOCULAR_OP_SYM_SET = set(["%", "^", "&", "*", "-", "+", "|", "<", ">", "/", "!=", "==", "!==", "===", "<<", "<=", ">>", ">=", "&&", "||"])

#合法的符号集
_SYM_SET = (set("""~!%^&*()-+|{}[]:;"'<,>./""") | set(["!=", "==", "!==", "===", "<<", "<=", ">>", ">=", "&&", "||", ".."]) | ASSIGN_SYM_SET |
            INC_DEC_SYM_SET)

#保留字集
_RESERVED_WORD_SET = set(["import", "class", "void", "bool", "schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "float",
                          "double", "ref", "for", "while", "if", "else", "return", "nil", "true", "false", "break", "continue", "this",
                          "public", "interface", "new", "usemethod", "var", "defer", "final", "foreach", "from", "_", "cast"])

#编译控制命令集
_COMPILING_CTRL_CMD_SET = set(["use", "oruse", "else", "enduse", "error", "if", "elif", "endif"])
_INTERNAL_COMPILING_CTRL_CMD_SET = _COMPILING_CTRL_CMD_SET - set(["else"]) | set(["else_of_use", "else_of_if"])

class _Token:
    def __init__(self, type, value, src_file, line_no, pos):
        self.id = larc_common.new_id()

        self.type = type
        self.value = value
        self.src_file = src_file
        self.line_no = line_no
        self.pos = pos

        self._set_is_XXX()

        self._freeze()

    def _freeze(self):
        self.is_freezed = True

    def _unfreeze(self):
        assert self.is_freezed
        del self.__dict__["is_freezed"]

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
        self.is_ccc_name = self.type == "word" and self.value in _COMPILING_CTRL_CMD_SET
        self.is_ccc_func_name = self.type == "word"

        class IsCcc:
            def __init__(self, token):
                self.token = token
            def __nonzero__(self):
                return self.token.type == "ccc"
            def __call__(self, ccc):
                assert ccc in _INTERNAL_COMPILING_CTRL_CMD_SET, str(ccc)
                return self and self.token.value == ccc
        self.is_ccc = IsCcc(self)

        self.is_native_code = self.type == "native_code"

        self.is_sub_token_list = self.type == "sub_token_list"

        self.is_end_tag = self.type == "end_tag"

    def __str__(self):
        return """<token %r, %d, %d, %r>""" % (self.src_file, self.line_no, self.pos + 1, self.value)
    __repr__ = __str__

    def __setattr__(self, name, value):
        if self.__dict__.get("is_freezed", False):
            raise Exception("Bug")
        self.__dict__[name] = value

    def __delattr__(self, name):
        if self.__dict__.get("is_freezed", False):
            raise Exception("Bug")
        del self.__dict__[name]

    def copy_on_pos(self, t):
        #用t的位置构建一个自身的副本，用于泛型替换等场景
        return _Token(self.type, self.value, t.src_file, t.line_no, t.pos)

    def copy(self):
        return self.copy_on_pos(self)

    def syntax_err(self, msg = ""):
        larc_common.exit("%s %s" % (self.pos_desc(), msg))

    def warning(self, msg):
        larc_common.warning("%s %s" % (self.pos_desc(), msg))

    def pos_desc(self):
        return "文件[%s]行[%d]列[%d]" % (self.src_file, self.line_no, self.pos + 1)

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
        return copy.deepcopy(self)

    def peek(self, start_idx = 0):
        try:
            return self.l[self.i + start_idx]
        except IndexError:
            larc_common.exit("文件[%s]代码意外结束" % self.src_file)

    def peek_name(self):
        t = self.peek()
        if not t.is_name:
            t.syntax_err("需要标识符")
        return t.value

    def revert(self, i = None):
        if i is None:
            assert self.i > 0
            self.i -= 1
            t = self.l[self.i]
            if t.is_sub_token_list:
                t.value.revert(0)
        else:
            assert 0 <= i <= self.i < len(self.l)
            for t in self.l[i : self.i]:
                if t.is_sub_token_list:
                    t.value.revert(0)
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
        return t

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
            if t.is_sub_token_list:
                t.value.join_str_literal()
            if first is not None:
                #正在合并
                if t.type == first.type:
                    first._unfreeze()
                    first.value += t.value
                    first._freeze()
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
    larc_common.exit("文件[%s]行[%d]列[%d] %s" % (src_file, line_no, pos + 1, msg))

def _syntax_warning(src_file, line_no, pos, msg):
    larc_common.warning("文件[%s]行[%d]列[%d] %s" % (src_file, line_no, pos + 1, msg))

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
        l.append(c) #添加到列表
    else:
        _syntax_err(src_file, line_no, pos, "字符串不完整")

    #返回字面量和消耗的源代码长度
    return "".join(l), s_len - len(s)

def _parse_token(module_name, src_file, line_no, line, pos):
    s = line[pos :]
    m = _TOKEN_RE.match(s)
    if m is None:
        _syntax_err(src_file, line_no, pos, "")

    f, hex_f, sym, i, w = m.groups()

    if f is not None or hex_f is not None:
        #浮点数
        if f is None:
            f = hex_f
        if f[-1].upper() == "F":
            try:
                value = float(f[: -1]) if hex_f is None else float.fromhex(f[: -1])
                if math.isnan(value) or math.isinf(value):
                    raise ValueError
                if value < float.fromhex("0x1p-126"):
                    value = 0.0
                elif value > float.fromhex("0x1.FFFFFEp127"):
                    raise ValueError
            except ValueError:
                _syntax_err(src_file, line_no, pos, "非法的float字面量'%s'" % f)
            return _Token("literal_float", value, src_file, line_no, pos), len(f)
        else:
            try:
                value = float(f) if hex_f is None else float.fromhex(f)
                if math.isnan(value) or math.isinf(value):
                    raise ValueError
            except ValueError:
                _syntax_err(src_file, line_no, pos, "非法的double字面量'%s'" % f)
            return _Token("literal_double", value, src_file, line_no, pos), len(f)

    if sym is not None:
        #符号
        if sym not in _SYM_SET:
            _syntax_err(src_file, line_no, pos, "非法的符号'%r'" % sym)

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
        if is_builtin_macro_like(w):
            if w == "__PLATFORM__":
                return _Token("literal_str", platform.platform(), src_file, line_no, pos), len(w)
            if w == "__MACHINE__":
                return _Token("literal_str", platform.machine(), src_file, line_no, pos), len(w)
            if w == "__SYSTEM__":
                return _Token("literal_str", platform.system(), src_file, line_no, pos), len(w)
            if w == "__MODULE__":
                return _Token("literal_str", module_name, src_file, line_no, pos), len(w)
            if w == "__FILE__":
                return _Token("literal_str", src_file, src_file, line_no, pos), len(w)
            if w == "__LINE__":
                return _Token("literal_int", line_no, src_file, line_no, pos), len(w)
            if w == "__TIMESTAMP__":
                return _Token("literal_long", larc_common.COMPILING_TIMESTAMP, src_file, line_no, pos), len(w)
            _syntax_err(src_file, line_no, pos, "非法的内建宏'%s'" % w)
        return _Token("word", w, src_file, line_no, pos), len(w)

    raise Exception("Bug")

class _RawStr:
    def __init__(self, value, src_file, line_no, pos):
        self.value = value
        self.src_file = src_file
        self.line_no = line_no
        self.pos = pos

    def check(self):
        if "\t\n" in self.value or "\x20\n" in self.value:
            _syntax_warning(self.src_file, self.line_no, self.pos, "原始字符串含有空格或制表符结尾的行")

class _NativeCode:
    def __init__(self, src_file, line_no, pos):
        self.src_file = src_file
        self.line_no = line_no
        self.pos = pos
        self.line_list = []

def _parse_line(module_name, src_file, line_no, line, pos):
    token_list = [] #因为是临时解析的一个token列表，需要做分析合并等操作，简单起见直接用list
    uncompleted_comment_start_pos = None
    raw_str = None

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
                uncompleted_comment_start_pos = pos - 2
                break
            #注释在本行结束，跳过它
            pos += comment_end_pos + 2
            continue
        if line[pos] == "`":
            #原始字符串
            raw_str = _RawStr("", src_file, line_no, pos)
            pos += 1
            raw_str_end_pos = line[pos :].find("`")
            if raw_str_end_pos < 0:
                #跨行了，追加内容并进行下一行
                raw_str.value += line[pos :] + "\n"
                break
            #在本行结束
            raw_str.value += line[pos : pos + raw_str_end_pos]
            raw_str.check()
            token_list.append(_Token("literal_str", raw_str.value, raw_str.src_file, raw_str.line_no, raw_str.pos))
            pos += raw_str_end_pos + 1
            raw_str = None
            continue

        #解析token
        token, token_len = _parse_token(module_name, src_file, line_no, line, pos)
        token_list.append(token)
        pos += token_len

    return token_list, uncompleted_comment_start_pos, raw_str

def parse_token_list(module_name, src_file):
    line_list = larc_common.open_src_file(src_file).read().splitlines()

    token_list = TokenList(src_file)
    in_comment = False
    raw_str = None
    native_code = None
    for line_no, line in enumerate(line_list):
        line_no += 1

        for pos, c in enumerate(line):
            assert c not in ("\r", "\n")
            if ord(c) < 32 and c not in ("\t",):
                _syntax_err(src_file, line_no, pos, "含有非法的ascii控制码‘%r’" % c)

        if in_comment:
            #有未完的注释
            pos = line.find("*/")
            if pos < 0:
                #整行都是注释，忽略
                continue
            pos += 2
            in_comment = False
        elif raw_str is not None:
            #有未完的原始字符串
            pos = line.find("`")
            if pos < 0:
                #整行都是字符串内容，追加
                raw_str.value += line + "\n"
                continue
            #在本行结束
            raw_str.value += line[: pos]
            raw_str.check()
            token_list.append(_Token("literal_str", raw_str.value, raw_str.src_file, raw_str.line_no, raw_str.pos))
            pos += 1
            raw_str = None
        elif native_code is not None:
            if line.strip() == "!>>":
                #native code结束
                token_list.append(_Token("native_code", native_code.line_list, native_code.src_file, native_code.line_no, native_code.pos))
                native_code = None
            else:
                native_code.line_list.append(line)
            continue
        else:
            pos = 0
            if line.lstrip("\t\x20").startswith("#"):
                #编译控制命令
                pos = line.find("#")
                assert pos >= 0
                ccc_tl, uncompleted_comment_start_pos, uncompleted_raw_str = _parse_line(module_name, src_file, line_no, line, pos + 1)
                if uncompleted_comment_start_pos is not None:
                    _syntax_err(src_file, line_no, uncompleted_comment_start_pos, "编译控制命令行不能含跨行的块注释")
                if uncompleted_raw_str is not None:
                    _syntax_err(src_file, line_no, uncompleted_raw_str.pos, "编译控制命令行不能含跨行的原始字符串")
                if not ccc_tl:
                    _syntax_err(src_file, line_no, pos + 1, "需要编译控制命令")
                ccc_name_token = ccc_tl[0]
                if ccc_name_token.is_ccc_name:
                    ccc = ccc_name_token.value
                else:
                    ccc_name_token.syntax_err("非法的编译控制命令")
                token_list.append(_Token("ccc", ccc, src_file, line_no, pos))
                ccc_arg_tl = ccc_tl[1 :]
                if ccc == "error":
                    if not (len(ccc_arg_tl) == 1 and ccc_arg_tl[0].is_literal("str")):
                        ccc_name_token.syntax_err("error命令需要一个字符串参数")
                    token_list.append(ccc_arg_tl[0])
                elif ccc in ("if", "elif"):
                    ccc_arg_token_list = TokenList(src_file)
                    for t in ccc_arg_tl:
                        ccc_arg_token_list.append(t)
                    #需要加一个结束标记token，保证单独编译子token列表的时候的报错信息正常（“需要‘xxx’”而不是“文件意外结束）
                    ccc_arg_token_list.append(_Token("end_tag", None, src_file, line_no, len(line)))
                    token_list.append(_Token("sub_token_list", ccc_arg_token_list, src_file, line_no, pos))
                else:
                    if ccc_arg_tl:
                        ccc_arg_tl[0].syntax_err("无效的命令参数")
                continue
            if line.strip() == "!<<":
                #native code开始
                native_code = _NativeCode(src_file, line_no, line.find("!<<"))
                continue

        line_tl, uncompleted_comment_start_pos, raw_str = _parse_line(module_name, src_file, line_no, line, pos)
        for t in line_tl:
            token_list.append(t)
        if uncompleted_comment_start_pos is not None:
            assert raw_str is None
            in_comment = True

    if in_comment:
        _syntax_err(src_file, len(line_list), len(line_list[-1]), "存在未结束的块注释")
    if raw_str is not None:
        _syntax_err(src_file, len(line_list), len(line_list[-1]), "存在未结束的原始字符串")
    if native_code is not None:
        _syntax_err(src_file, len(line_list), len(line_list[-1]), "存在未结束的native code")

    token_list.join_str_literal()

    return token_list

def parse_token_list_until_sym(token_list, end_sym_set):
    bracket_map = {"(" : ")", "[" : "]", "{" : "}"}
    sub_token_list = TokenList(token_list.src_file)
    stk = []
    in_top_level_new = False #是否刚解析过第一层的new且还没碰到括号，用于解决解析全局变量初始化expr token list时碰到泛型参数分隔的逗号停止的bug
    while True:
        t = token_list.pop()
        sub_token_list.append(t)
        if t.is_sym and t.value in end_sym_set and not stk:
            return sub_token_list, t.value
        if t.is_sym and t.value in bracket_map:
            stk.append(t)
            in_top_level_new = False
        if t.is_sym and t.value in bracket_map.values():
            if not (stk and stk[-1].is_sym and t.value == bracket_map.get(stk[-1].value)):
                t.syntax_err("未匹配的'%s'" % t.value)
            stk.pop()
        if t.is_ccc("use"):
            stk.append(t)
            in_top_level_new = False
        if t.is_ccc("oruse"):
            if not (stk and stk[-1].is_ccc("use")):
                t.syntax_err("未匹配的'#oruse'")
        if t.is_ccc("enduse"):
            if stk and stk[-1].is_ccc("use"):
                t.syntax_err("'#enduse'前缺少'#else'")
            if not (len(stk) >= 2 and stk[-1].is_ccc("else_of_use") and stk[-2].is_ccc("use")):
                t.syntax_err("未匹配的'#enduse'")
            stk.pop()
            stk.pop()
        if t.is_ccc("if"):
            stk.append(t)
            in_top_level_new = False
        if t.is_ccc("elif"):
            if not (stk and stk[-1].is_ccc("if")):
                t.syntax_err("未匹配的'#elif'")
        if t.is_ccc("endif"):
            if stk and stk[-1].is_ccc("if"):
                t.syntax_err("'#endif'前缺少'#else'")
            if not (len(stk) >= 2 and stk[-1].is_ccc("else_of_if") and stk[-2].is_ccc("if")):
                t.syntax_err("未匹配的'#endif'")
            stk.pop()
            stk.pop()
        if t.is_ccc and t.value == "else": #不能直接is_ccc("else")判断
            if not (stk and (stk[-1].is_ccc("use") or stk[-1].is_ccc("if"))):
                t.syntax_err("未匹配的'#else'")
            t._unfreeze()
            t.value = "else_of_" + stk[-1].value #将else改为对应控制命令的特化else_of，方便后面的编译过程
            t._freeze()
            stk.append(t)
        if t.is_reserved("new") and not stk:
            in_top_level_new = True
        if t.is_sym("<") and (in_top_level_new or (stk and stk[-1].is_sym("<"))):
            stk.append(t)
            in_top_level_new = False
        if t.is_sym and t.value in (">", ">>") and (stk and stk[-1].is_sym("<")):
            for _ in xrange(len(t.value)):
                if not (stk and stk[-1].is_sym("<")):
                    t.syntax_err("未匹配的'>'")
                stk.pop()

def gen_empty_token_list(end_sym):
    token_list = TokenList("EMPTY")
    token_list.append(_Token("sym", end_sym, "EMPTY", -1, -1))
    return token_list

def is_valid_name(name):
    return re.match("^[a-zA-Z_]\w*$", name) is not None and not (name in ("nil", "true", "false") or is_builtin_macro_like(name))

def is_builtin_macro_like(name):
    return name.startswith("__") and name.endswith("__")

def make_fake_token_reserved(w):
    t = _Token("word", w, "<nil>", 0, -1)
    t._unfreeze()
    t.is_reserved = lambda r: r == w
    t.is_name = False
    t._freeze()
    return t

def make_fake_token_name(w):
    assert w not in _RESERVED_WORD_SET
    t = _Token("word", w, "<nil>", 0, -1)
    return t
