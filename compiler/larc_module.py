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
        for decr in "public", "native", "final", "abstract":
            if t.is_reserved(decr):
                if decr in decr_set:
                    t.syntax_err("重复的修饰'%s'" % decr)
                decr_set.add(decr)
                token_list.pop()
                break
        else:
            return decr_set

def _parse_arg_map(token_list, dep_module_set):
    arg_map = larc_common.OrderedDict()
    if token_list.peek().is_sym(")"):
        return arg_map
    while True:
        if token_list.peek().is_reserved("ref"):
            token_list.pop()
            is_ref = True
        else:
            is_ref = False
        type = larc_type.parse_type(token_list, dep_module_set, is_ref = is_ref)
        if type.name == "void":
            type.token.syntax_err("参数类型不可为void")
        t, name = token_list.pop_name()
        if name in arg_map:
            t.syntax_err("参数名重定义")
        if name in dep_module_set:
            t.syntax_err("参数名和导入模块名冲突")
        arg_map[name] = type
        t = token_list.peek()
        if t.is_sym(","):
            token_list.pop_sym(",")
            continue
        if t.is_sym(")"):
            return arg_map
        t.syntax_err("需要','或')'")

class _Method:
    def __init__(self, name, cls, decr_set, type, arg_map, block_token_list, super_construct_expr_list_token_list = None):
        self.name = name
        self.cls = cls
        self.decr_set = decr_set
        self.type = type
        self.arg_map = arg_map
        self.block_token_list = block_token_list
        self.super_construct_expr_list_token_list = super_construct_expr_list_token_list

    def check_type(self):
        self.type.check(self.cls.module, self.cls)
        for tp in self.arg_map.itervalues():
            tp.check(self.cls.module, self.cls)

    def compile(self):
        //todo
        '''
        if self.super_construct_expr_list_token_list is None:
            self.super_construct_expr_list, self.super_construct_method = None, None
        else:
            self.super_construct_expr_list, self.super_construct_method = cocc_expr.parse_super_construct_expr_list(self)
            self.super_construct_expr_list_token_list.pop_sym(")")
            assert not self.super_construct_expr_list_token_list
        del self.super_construct_expr_list_token_list

        if self.block_token_list is None:
            self.stmt_list = None
        else:
            self.stmt_list = cocc_stmt.parse_stmt_list(self.block_token_list, self.cls.module, self.cls, (self.arg_map.copy(),), 0, self.type)
            self.block_token_list.pop_sym("}")
            assert not self.block_token_list
            self.stmt_list.analyze_non_raw_var((), self.super_construct_method, self.super_construct_expr_list)
        del self.block_token_list
        '''

class _Attr:
    def __init__(self, name, cls, decr_set, type):
        self.name = name
        self.cls = cls
        self.decr_set = decr_set
        self.type = type

    def check_type(self):
        self.type.check(self.cls.module, self.cls)

class _Class:
    def __init__(self, module, decr_set, name, base_cls_type, gtp_name_list):
        assert "native" not in decr_set
        self.module = module
        self.decr_set = decr_set
        self.name = name
        self.base_cls_type = base_cls_type
        self.gtp_name_list = gtp_name_list
        self.construct_method = None
        self.attr_map = cocc_common.OrderedDict()
        self.method_map = cocc_common.OrderedDict()

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def parse(self, token_list):
        while True:
            t = token_list.peek()
            if t.is_sym("}"):
                break

            #解析修饰
            decr_set = _parse_decr_set(token_list)
            if "native" in decr_set:
                t.syntax_err("类属性或方法定义不可使用native修饰")

            t = token_list.peek()
            if t.is_name and t.value == self.name:
                t, name = token_list.pop_name()
                if token_list.peek().is_sym("("):
                    #构造方法
                    if set(["final", "abstract"]) & decr_set:
                        t.syntax_err("构造方法不可用final或abstract修饰")
                    token_list.pop_sym("(")
                    self._parse_method(decr_set, larc_type.VOID_TYPE, name, token_list)
                    continue
                token_list.revert()

            if "abstract" in decr_set:
                if "final" in decr_set:
                    t.syntax_err("final和abstract不可同时修饰")
                if "final" in self.decr_set:
                    t.syntax_err("final类的方法不可修饰为abstract")

            #解析属性或方法
            type = larc_type.parse_type(token_list, self.module.dep_module_set)
            t, name = token_list.pop_name()
            if name == self.name:
                t.syntax_err("属性或方法不可与类同名")
            self._check_redefine(t, name)
            sym_t, sym = token_list.pop_sym()
            if sym == "(":
                #方法
                self._parse_method(decr_set, type, name, token_list)
                continue
            if sym in (";", ","):
                #属性
                if type.name == "void":
                    t.syntax_err("属性类型不可为void")
                while True:
                    if set(["final", "abstract"]) & decr_set:
                        t.syntax_err("属性不可用final或abstract修饰")
                    self.attr_map[name] = _Attr(name, self, decr_set, type)
                    if sym == ";":
                        break
                    #多属性定义
                    assert sym == ","
                    t, name = token_list.pop_name()
                    self._check_redefine(t, name)
                    sym_t, sym = token_list.pop_sym()
                    if sym not in (";", ","):
                        t.syntax_err()
                continue
            t.syntax_err()
        if self.construct_method is None:
            t.syntax_err("类'%s'缺少构造函数定义" % self)

    def _check_redefine(self, t, name):
        if name in self.module.dep_module_set:
            t.syntax_err("属性或方法名不能与导入模块名相同")
        for i in self.attr_map, self.method_map:
            if name in i:
                t.syntax_err("属性或方法名重定义")

    def _parse_method(self, decr_set, type, name, token_list):
        start_token = token_list.peek()
        arg_map = _parse_arg_map(token_list, self.module.dep_module_set)
        token_list.pop_sym(")")
        if "abstract" in decr_set:
            assert not (name == self.name and type is larc_type.VOID_TYPE) #不可能是构造函数
            token_list.pop_sym(";")
            block_token_list = None
        else:
            if name == self.name and type is larc_type.VOID_TYPE:
                #构造方法，若为子类则强制要求指定基类构造方法
                if self.base_cls_type is None:
                    super_construct_expr_list_token_list = None
                else:
                    token_list.pop_sym(":")
                    t = token_list.pop()
                    if not t.is_reserved("super"):
                        t.syntax_err("需要显式super(...)调用基类构造方法")
                    token_list.pop_sym("(")
                    super_construct_expr_list_token_list = _parse_expr_list_token_list(token_list)
            token_list.pop_sym("{")
            block_token_list, sym = larc_token.parse_token_list_until_sym(token_list, ("}",))
            assert sym == "}"
        if name == self.name:
            #构造方法
            assert type is larc_type.VOID_TYPE:
            self.construct_method = _Method(name, self, decr_set, cocc_type.VOID_TYPE, arg_map, block_token_list,
                                            super_construct_expr_list_token_list)
        else:
            self.method_map[name] = _Method(name, self, decr_set, type, arg_map, block_token_list)

    def compile(self):
        self.construct_method.compile()
        for method in self.method_map.itervalues():
            method.compile()

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
        self._check_name_hide()

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

    def _check_name_hide(self):
        #todo

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
        if sym == "<":
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
            base_cls_type = larc_type.parse_type(token_list, self.dep_module_set)
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
