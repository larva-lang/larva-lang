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

class _Method:
    def __init__(self, cls, arg_set, stmt_list):
        self.cls = cls
        self.arg_set = arg_set
        self.stmt_list = stmt_list

class _Class:
    def __init__(self, module, name, is_native):
        self.module = module
        self.name = name
        self.is_native = is_native
        self.attr_set = larc_common.OrderedSet()
        self.method_map = larc_common.OrderedDict()

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
            stmt_list = None
        else:
            token_list.pop_sym("{")
            stmt_list = larc_stmt.parse_stmt_list(token_list)
            token_list.pop_sym("}")
        self.method_map[(name, len(arg_set))] = _Method(self, arg_set, stmt_list)

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

class Module:
    def __init__(self, file_path_name):
        self.dir, file_name = os.path.split(file_path_name)
        assert file_name.endswith(".lar")
        self.name = file_name[: -4]
        self._compile(file_path_name)

    def _compile(self, file_path_name):
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
        token_list.pop_sym("{")
        func = _Func(self, func_name, arg_set, is_native)
        func.parse(token_list)
        token_list.pop_sym("}")
        self.func_map[(func_name, len(arg_set))] = func

    def _parse_global_var(self, token_list, is_native):
        for t, var_name, expr in larc_stmt.parse_var_define(token_list):
            if isinstance(var_name, str):
                self._check_redefine(t, var_name)
                self.global_var_map[var_name] = is_native
                self.global_var_init_map[var_name] = expr
            else:
                for vn in var_name:
                    self._check_redefine(t, vn)
                    self.global_var_map[vn] = is_native
                self.global_var_init_map[tuple(var_name)] = expr
        token_list.pop_sym(";")
