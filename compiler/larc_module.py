#coding=utf8

"""
编译larva模块
"""

import os
import larc_common
import larc_token
import larc_stmt
import larc_expr

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
        self.global_var_set = larc_common.OrderedSet()
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

            if t.is_reserved("extern"):
                is_extern = True
                t = token_list.pop()
            else:
                is_extern = False

            if t.is_reserved("class"):
                #类定义
                self._parse_class(token_list, is_extern)
                continue

            if t.is_reserved("func"):
                #类定义
                self._parse_func(token_list, is_extern)
                continue

            if t.is_reserved("var"):
                #全局变量
                self._parse_global_var(token_list, is_extern)
                continue

            t.syntax_err()

    def _check_redefine(self, t, name, func_arg_count = None):
        for i in self.dep_module_set, self.class_map, self.global_var_set:
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

    def _parse_class(self, token_list):
        t, cls_name = token_list.pop_name()
        self._check_redefine(t, cls_name)
        token_list.pop_sym("{")
        cls = _Class(self, cls_name)
        cls.parse(token_list)
        token_list.pop_sym("}")
        self.class_map[cls_name] = cls

    def _parse_func(self, token_list):
        t, func_name = token_list.pop_name()
        token_list.pop_sym("(")
        arg_set = _parse_arg_set(token_list)
        token_list.pop_sym(")")
        self._check_redefine(t, func_name, len(arg_set))
        token_list.pop_sym("{")
        func = _Func(self, func_name, arg_set)
        func.parse(token_list)
        token_list.pop_sym("}")
        self.func_map[(func_name, len(arg_set))] = func

    def _parse_global_var(self, token_list):
        for t, var_name, expr in larc_stmt.parse_var_define(token_list):
            if isinstance(var_name, str):
                self._check_redefine(t, var_name)
                self.global_var_set.add(var_name)
                self.global_var_init_map[var_name] = expr
            else:
                for vn in var_name:
                    self._check_redefine(t, vn)
                    self.global_var_set.add(vn)
                self.global_var_init_map[tuple(var_name)] = expr
        token_list.pop_sym(";")
