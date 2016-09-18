#coding=utf8

"""
编译larva模块
"""

import os
import larc_common
import larc_token
import larc_stmt
import larc_expr

module_map = larc_common.OrderedDict()

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

    __repr__ = __str__ = lambda self : self.name

    def _precompile(self, file_path_name):
        #解析token列表，解析正文
        token_list = larc_token.parse_token_list(file_path_name)
        self._parse_text(token_list)

    def _parse_text(self, token_list):
        self.dep_module_set = set()
        import_end = False
        self.class_map = larc_common.OrderedDict()
        self.func_map = larc_common.OrderedDict()
        self.global_var_map = larc_common.OrderedDict()
        self.global_var_init_map = larc_common.OrderedDict()
        while token_list:
            #解析import
            t = token_list.pop()
            if t.is_reserved("import"):
                #import
                if import_end:
                    t.syntax_err("import必须在模块代码最前面")
                if self.name == "__builtins":
                    t.syntax_err("模块'__builtins'不可以import其他模块")
                self._parse_import(token_list)
                continue
            import_end = True

            if t.is_reserved("native"):
                is_native = True
                t = token_list.pop()
            else:
                is_native = False

            if t.is_reserved("class"):
                #类定义
                self._parse_class(token_list, is_native)
                continue

            if t.is_reserved("func"):
                #类定义
                self._parse_func(token_list, is_native)
                continue

            if t.is_reserved("var"):
                #全局变量
                self._parse_global_var(token_list, is_native)
                continue

            t.syntax_err()

    def _check_redefine(self, t, name, func_arg_count = None):
        for i in self.dep_module_set, self.class_map, self.global_var_map:
            if name in i:
                t.syntax_err("名字重定义")
        for func_name, arg_count in self.func_map:
            if name == func_name and (func_arg_count is None or func_arg_count == arg_count):
                t.syntax_err("名字重定义")

    def _parse_import(self, token_list):
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

    def _parse_class(self, token_list, is_native):
        t, cls_name = token_list.pop_name()
        self._check_redefine(t, cls_name)
        token_list.pop_sym("{")
        cls = _Class(self, cls_name, is_native)
        cls.parse(token_list)
        token_list.pop_sym("}")
        self.class_map[cls_name] = cls

    def _parse_func(self, token_list, is_native):
        t, func_name = token_list.pop_name()
        token_list.pop_sym("(")
        arg_set = _parse_arg_set(token_list, self.dep_module_set)
        token_list.pop_sym(")")
        self._check_redefine(t, func_name, len(arg_set))
        if is_native:
            token_list.pop_sym(";")
            block_token_list = None
        else:
            token_list.pop_sym("{")
            block_token_list = _parse_block_token_list(token_list)
        self.func_map[(func_name, len(arg_set))] = _Func(self, func_name, arg_set, is_native, block_token_list)

    def _parse_global_var(self, token_list, is_native):
        for t, var_name, expr_token_list in larc_stmt.parse_var_define(token_list, None, None, None, None, ret_expr_token_list = True):
            if is_native and expr_token_list is not None:
                t.syntax_err("native全局变量不可初始化")
            for vn in larc_stmt.iter_var_name(var_name):
                self._check_redefine(t, vn)
                self.global_var_map[vn] = _GlobalVar(self, vn, is_native)
            self.global_var_init_map[var_name] = expr_token_list

    def _items(self):
        for map in self.class_map, self.func_map, self.global_var_map:
            for i in map.itervalues():
                yield i

    def compile(self):
        self.literal_set = set()
        for i in self._items():
            i.compile()
        non_local_var_used_map = larc_common.OrderedDict()
        for var_name, expr_token_list in self.global_var_init_map.iteritems():
            if expr_token_list is not None:
                self.global_var_init_map[var_name] = (
                    larc_expr.parse_expr(expr_token_list, self, None, (), non_local_var_used_map, end_at_comma = True))
                t, sym = expr_token_list.pop_sym()
                assert not expr_token_list and sym in (",", ";")
            for vn in larc_stmt.iter_var_name(var_name):
                if vn in non_local_var_used_map:
                    non_local_var_used_map[vn].syntax_err("全局变量'%s'在定义前使用" % vn)

    def has_cls(self, name):
        return name in self.class_map
    def get_cls(self, name):
        return self.class_map[name]

    def has_func(self, name, arg_count = None):
        if arg_count is None:
            return name in [func_name for func_name, arg_count in self.func_map]
        return (name, arg_count) in self.func_map
    def get_func(self, name, arg_count):
        return self.func_map[(name, arg_count)]

    def has_global_var(self, name):
        return name in self.global_var_map
    def get_global_var(self, name):
        return self.global_var_map[name]

    def has_native_item(self):
        for i in self._items():
            if i.is_native:
                return True
        return False
