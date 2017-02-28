#coding=utf8

"""
编译larva模块
"""

import os
import larc_common
import larc_token
import larc_stmt
import larc_expr

builtins_module = None
module_map = larc_common.OrderedDict()

def _parse_decr_set(token_list):
    decr_set = set()
    while True:
        t = token_list.peek()
        for decr in "public", "native", "final", "static":
            if t.is_reserved(decr):
                if decr in decr_set:
                    t.syntax_err("重复的修饰'%s'" % decr)
                decr_set.add(decr)
                token_list.pop()
                break
        else:
            return decr_set

def _parse_arg_set(token_list, dep_module_set):
    arg_set = larc_common.OrderedSet()
    if token_list.peek().is_sym(")"):
        return arg_set
    while True:
        t, name = token_list.pop_name()
        if name in arg_set:
            t.syntax_err("参数名重定义")
        if name in dep_module_set:
            t.syntax_err("参数名和导入模块名冲突")
        arg_set.add(name)
        t = token_list.peek()
        if t.is_sym(","):
            token_list.pop_sym(",")
            continue
        if t.is_sym(")"):
            return arg_set
        t.syntax_err("需要','或')'")

def _parse_block_token_list(token_list):
    block_token_list, sym = larc_token.parse_token_list_until_sym(token_list, ("}",))
    assert sym == "}"
    return block_token_list

class _Method:
    def __init__(self, cls, name, arg_set, block_token_list):
        self.cls = cls
        self.name = name
        self.arg_set = arg_set
        self.block_token_list = block_token_list

    __repr__ = __str__ = lambda self : "%s.%s(...%d args)" % (self.cls, self.name, len(self.arg_set))

    def compile(self):
        if self.block_token_list is None:
            self.stmt_list = None
        else:
            self.stmt_list = larc_stmt.parse_stmt_list(self.block_token_list, self.cls.module, self.cls, (self.arg_set.copy(),), 0)
            self.block_token_list.pop_sym("}")
            assert not self.block_token_list
        del self.block_token_list

class _Class:
    def __init__(self, module, name, is_native):
        self.module = module
        self.name = name
        self.is_native = is_native
        self.attr_set = larc_common.OrderedSet()
        self.method_map = larc_common.OrderedDict()

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def parse(self, token_list):
        while True:
            t = token_list.pop()
            if t.is_sym("}"):
                token_list.revert()
                return

            if t.is_reserved("func"):
                self._parse_method(token_list)
                continue

            if t.is_reserved("var"):
                self._parse_attr(token_list)
                continue

            t.syntax_err()

    def _parse_method(self, token_list):
        t, name = token_list.pop_name()
        token_list.pop_sym("(")
        arg_set = _parse_arg_set(token_list, self.module.dep_module_set)
        token_list.pop_sym(")")
        self._check_redefine(t, name, len(arg_set))
        if self.is_native:
            token_list.pop_sym(";")
            block_token_list = None
        else:
            token_list.pop_sym("{")
            block_token_list = _parse_block_token_list(token_list)
        self.method_map[(name, len(arg_set))] = _Method(self, name, arg_set, block_token_list)

    def _parse_attr(self, token_list):
        while True:
            t, name = token_list.pop_name()
            self._check_redefine(t, name)
            self.attr_set.add(name)
            t, sym = token_list.pop_sym()
            if t.is_sym(","):
                continue
            if t.is_sym(";"):
                return
            t.syntax_err("需要','或';'")

    def _check_redefine(self, t, name, method_arg_count = None):
        for i in self.module.dep_module_set, self.attr_set:
            if name in i:
                t.syntax_err("名字重定义")
        for method_name, arg_count in self.method_map:
            if name == method_name and (method_arg_count is None or method_arg_count == arg_count):
                t.syntax_err("名字重定义")

    def compile(self):
        for method in self.method_map.itervalues():
            method.compile()

    def has_attr(self, name):
        return name in self.attr_set

    def has_method(self, name, arg_count = None):
        if arg_count is None:
            return name in [method_name for method_name, arg_count in self.method_map]
        return (name, arg_count) in self.method_map
    def get_method(self, name, arg_count):
        return self.method_map[(name, arg_count)]

class _Func:
    def __init__(self, module, name, arg_set, is_native, block_token_list):
        self.module = module
        self.name = name
        self.arg_set = arg_set
        self.is_native = is_native
        self.block_token_list = block_token_list

    __repr__ = __str__ = lambda self : "%s.%s(...%d args)" % (self.module, self.name, len(self.arg_set))

    def compile(self):
        if self.block_token_list is None:
            self.stmt_list = None
        else:
            self.stmt_list = larc_stmt.parse_stmt_list(self.block_token_list, self.module, None, (self.arg_set.copy(),), 0)
            self.block_token_list.pop_sym("}")
            assert not self.block_token_list
        del self.block_token_list

class _GlobalVar:
    def __init__(self, module, name, is_native):
        self.module = module
        self.name = name
        self.is_native = is_native

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def compile(self):
        pass

class Module:
    def __init__(self, file_path_name):
        self.dir, file_name = os.path.split(file_path_name)
        assert file_name.endswith(".lar")
        self.name = file_name[: -4]
        self._precompile(file_path_name)
        if self.name == "__builtins":
            #内建模块需要做一些必要的检查
            if "String" not in self.class_map: #必须有String类
                larc_common.exit("内建模块缺少String类")
            str_cls = self.class_map["String"]
            if "format" in str_cls.attr_map or "format" in str_cls.method_map:
                larc_common.exit("String类的format方法属于内建保留方法，禁止显式定义")

    __repr__ = __str__ = lambda self : self.name

    def _precompile(self, file_path_name):
        #解析token列表，解析正文
        token_list = larc_token.parse_token_list(file_path_name)
        self._parse_text(token_list)

    def _parse_text(self, token_list):
        self.dep_module_set = set()
        import_end = False
        self.class_map = larc_common.OrderedDict()
        self.gcls_inst_map = larc_common.OrderedDict()
        self.typedef_map = larc_common.OrderedDict()
        self.func_map = larc_common.OrderedDict()
        self.global_var_map = larc_common.OrderedDict()
        while token_list:
            #解析import
            t = token_list.peek()
            if t.is_reserved("import"):
                #import
                if import_end:
                    t.syntax_err("import必须在模块代码最前面")
                self._parse_import(token_list)
                continue
            import_end = True

            #解析修饰
            decr_set = _parse_decr_set(token_list)

            #解析各种定义
            t = token_list.peek()
            if t.is_reserved("class"):
                #解析类
                if decr_set - set(["public", "final"]):
                    t.syntax_err("类只能用public和final修饰")
                self._parse_class(decr_set, token_list)
                continue

            if t.is_reserved("typedef"):
                #解析typedef
                if decr_set - set(["public"]):
                    t.syntax_err("typedef只能用public修饰")
                self._parse_typedef(decr_set, token_list)
                continue

            #可能是函数或全局变量
            type = larc_type.parse_type(token_list, self.dep_module_set)
            t, name = token_list.pop_name()
            self._check_redefine(t, name)
            t, sym = token_list.pop_sym()
            if sym == "(":
                #函数
                if decr_set - set(["public", "native"]):
                    t.syntax_err("函数只能用public和native修饰")
                self._parse_func(decr_set, type, name, token_list)
                continue
            if sym in (";", "=", ","):
                #全局变量
                if decr_set - set(["public", "native", "final"]):
                    t.syntax_err("全局变量只能用public、native和final修饰")
                if type.name == "void":
                    t.syntax_err("变量类型不可为void")
                while True:
                    if sym == "=":
                        if "native" in decr_set:
                            t.syntax_err("不能初始化native全局变量")
                        expr_token_list, sym = larc_token.parse_token_list_until_sym(token_list, (";", ","))
                    else:
                        if "native" not in decr_set:
                            t.syntax_err("非native全局变量必须显式初始化")
                        expr_token_list = None
                    self.global_var_map[name] = _GlobalVar(name, self, decr_set, type, expr_token_list)
                    if sym == ";":
                        break
                    #定义了多个变量，继续解析
                    assert sym == ","
                    t, name = token_list.pop_name()
                    self._check_redefine(t, name)
                    t, sym = token_list.pop_sym()
                    if sym not in (";", "=", ","):
                        t.syntax_err()
                continue
            t.syntax_err()

    def _check_redefine(self, t, name):
        for i in self.dep_module_set, self.class_map, self.global_var_map, self.func_map:
            if name in i:
                t.syntax_err("名字重定义")

    def _parse_import(self, token_list):
        t = token_list.pop()
        assert t.is_reserved("import")
        while True:
            t, name = token_list.pop_name()
            if name in self.dep_module_set:
                t.syntax_err("模块重复import")
            self.dep_module_set.add(name)
            t, sym = token_list.pop_sym()
            if sym == ";":
                return
            if sym != ",":
                t.syntax_err("需要';'或','")

    def _parse_class(self, cls_decr_set, token_list):
        t = token_list.pop()
        assert t.is_reserved("class")
        t, cls_name = token_list.pop_name()
        self._check_redefine(t, cls_name)
        gtp_name_list = []
        t, sym = token_list.pop_sym()
        #todo
        if sym == "<":
            if "native" not in cls_decr_set:
                t.syntax_err("泛型类必须是native实现")
            while True:
                t, name = token_list.pop_name()
                if name in self.dep_module_set:
                    t.syntax_err("泛型名与导入模块重名")
                gtp_name_list.append(name)
                t, sym = token_list.pop_sym()
                if sym == ",":
                    continue
                if sym == ">":
                    break
                t.syntax_err("需要'>'或','")
            t, sym = token_list.pop_sym()
        base_cls_type = None
        if sym == ":":
            #存在继承关系
            t = token_list.peek()
            base_cls_type = cocc_type.parse_type(token_list, self.dep_module_set)
            if base_cls_type.is_array:
                t.syntax_err("无法继承数组")
            if base_cls_type.token.is_reserved:
                t.syntax_err("无法继承类型'%s'" % base_cls_type.name)
            t, sym = token_list.pop_sym()
        if sym != "{":
            t.syntax_err("需要'{'")
        cls = _Class(self, cls_decr_set, cls_name, base_cls_type, gtp_name_list)
        cls.parse(token_list)
        token_list.pop_sym("}")
        self.class_map[cls_name] = cls
