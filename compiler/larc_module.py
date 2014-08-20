#coding=utf8

"""
编译larva模块
"""

import os
import larc_common
import larc_token
import larc_stmt
import larc_expr

class _Func:
    def __init__(self, func_name, arg_list, global_var_set, stmt_list,
                 name_token):
        self.name = func_name
        self.arg_list = arg_list
        self.global_var_set = global_var_set
        self.stmt_list = stmt_list
        self.name_token = name_token

        #检查参数的global声明
        for var_name in arg_list:
            if var_name in global_var_set:
                self.syntax_err("参数'%s'被global声明" % (func_name, var_name))

        #提取局部变量
        self.local_var_set = set(arg_list)
        self._search_local_var(stmt_list)
        assert not (self.local_var_set & self.global_var_set)

        larc_stmt.check_last_return(self.stmt_list)

    def _search_local_var(self, stmt_list):
        #局部变量条件：赋值或for的左值是一个名字
        #对于嵌套stmt_list的语句递归搜索
        for stmt in stmt_list:
            if (stmt.type in ("=", "%=", "^=", "&=", "*=", "-=", "+=", "|=",
                              "/=", "<<=", ">>=", ">>>=", "for") and
                stmt.lvalue.op == "name"):
                if stmt.lvalue.arg.value not in self.global_var_set:
                    self.local_var_set.add(stmt.lvalue.arg.value)
            if stmt.type in ("for", "while"):
                self._search_local_var(stmt.stmt_list)
            if stmt.type == "if":
                for expr, if_stmt_list in stmt.if_list:
                    self._search_local_var(if_stmt_list)
                if stmt.else_stmt_list is not None:
                    self._search_local_var(stmt.else_stmt_list)

    def syntax_err(self, msg):
        self.name_token.syntax_err("[函数'%s']%s" % (self.name, msg))

    def link(self, curr_module, module_map):
        for stmt in self.stmt_list:
            stmt.link(curr_module, module_map, self.local_var_set)

class Module:
    def __init__(self, file_path_name):
        self.dir, file_name = os.path.split(file_path_name)
        assert file_name.endswith(".lar")
        self.name = file_name[: -4]
        self._compile(file_path_name)
        self._check_undefined_global_var()
        self.func_name_set = set([name for name, arg_count in self.func_map])

    def link(self, module_map):
        self.const_map = larc_common.OrderedDict()
        for expr in self.global_var_map.itervalues():
            expr.link(self, module_map)
        for func in self.func_map.itervalues():
            func.link(self, module_map)

    def _check_undefined_global_var(self):
        #检查被global声明但没有定义的全局变量
        for func in self.func_map.itervalues():
            for var_name in func.global_var_set:
                if var_name not in self.global_var_map:
                    func.syntax_err("声明的全局变量'%s'未定义" % var_name)

    def _compile(self, file_path_name):
        #解析token列表，解析正文
        token_list = larc_token.parse_token_list(file_path_name)
        self._parse_text(token_list)

    def _parse_text(self, token_list):
        self.dep_module_set = set()
        import_end = False
        self.func_map = larc_common.OrderedDict()
        self.global_var_map = larc_common.OrderedDict()
        while token_list:
            token_list.pop_indent(0)
            t = token_list.pop()
            if t.is_import:
                #import
                if import_end:
                    t.syntax_err("import必须在模块代码最前面")
                self._parse_import(token_list)
                continue
            import_end = True
            if t.is_func:
                #函数定义
                self._parse_func(token_list)
                continue
            if t.is_name:
                #全局变量
                self._parse_global_var(token_list, t)
                continue
            t.syntax_err()

    def _parse_import(self, token_list):
        t = token_list.pop()
        if not t.is_name:
            t.syntax_err("非法的模块名")
        if t.value in self.dep_module_set:
            t.syntax_err("模块重复import")
        self.dep_module_set.add(t.value)

    def _parse_func_arg_list(self, token_list):
        arg_list = []
        #解析参数列表
        while True:
            t = token_list.pop()
            if t.is_sym(")"):
                #解析完成
                break
            if not t.is_name:
                t.syntax_err("需要参数名")
            if t.value in arg_list:
                t.syntax_err("重名参数")
            arg_list.append(t.value)
            t = token_list.pop()
            if t.is_sym(")"):
                #解析完成
                break
            if t.is_sym(","):
                #继续解析
                continue
            t.syntax_err("需要','或')'")
        token_list.pop_sym(":")
        return arg_list

    def _parse_func(self, token_list):
        name_token = token_list.pop()
        if not name_token.is_name:
            name_token.syntax_err("非法的函数名")
        func_name = name_token.value
        if func_name in self.dep_module_set:
            name_token.syntax_err("函数名和模块名重复")
        if func_name in self.global_var_map:
            name_token.syntax_err("函数名和全局变量名重复")
        token_list.pop_sym("(")
        arg_list = self._parse_func_arg_list(token_list)
        func_key = func_name, len(arg_list)
        if func_key in self.func_map:
            name_token.syntax_err("函数重复定义")
        stmt_list, global_var_set = larc_stmt.parse_stmt_list(token_list, 0, 0)
        self.func_map[func_key] = (
            _Func(func_name, arg_list, global_var_set, stmt_list, name_token))

    def _parse_global_var(self, token_list, name_token):
        var_name = name_token.value
        if var_name in self.dep_module_set:
            name_token.syntax_err("全局变量名和模块名重复")
        for func_name, arg_count in self.func_map:
            if func_name == var_name:
                name_token.syntax_err("全局变量名和函数名重复")
        if var_name in self.global_var_map:
            name_token.syntax_err("全局变量重复定义")
        t = token_list.pop()
        if not t.is_sym("="):
            t.syntax_err("需要'='")
        self.global_var_map[var_name] = larc_expr.parse_expr(token_list)

class ExternModule:
    def __init__(self, file_path_name):
        self.dir, file_name = os.path.split(file_path_name)
        assert file_name.endswith(".lar_ext")
        self.name = file_name[: -8]
        self._compile(file_path_name)
        self.func_name_set = set([name for name, arg_count in self.func_map])

    def _compile(self, file_path_name):
        #解析token列表，解析正文
        token_list = larc_token.parse_token_list(file_path_name)
        self._parse_text(token_list)

    def _parse_text(self, token_list):
        self.dep_module_set = set()
        import_end = False
        self.func_map = larc_common.OrderedDict()
        self.global_var_map = larc_common.OrderedDict()
        while token_list:
            token_list.pop_indent(0)
            t = token_list.pop()
            if t.is_import:
                #import
                if import_end:
                    t.syntax_err("import必须在模块代码最前面")
                self._parse_import(token_list)
                continue
            import_end = True
            if t.is_func:
                #函数声明
                self._parse_func(token_list)
                continue
            if t.is_global:
                #全局变量声明
                self._parse_global_var(token_list)
                continue
            t.syntax_err()

    def _parse_import(self, token_list):
        t = token_list.pop()
        if not t.is_name:
            t.syntax_err("非法的模块名")
        if t.value in self.dep_module_set:
            t.syntax_err("模块重复import")
        self.dep_module_set.add(t.value)

    def _parse_func_arg_list(self, token_list):
        arg_list = []
        #解析参数列表
        while True:
            t = token_list.pop()
            if t.is_sym(")"):
                #解析完成
                break
            if not t.is_name:
                t.syntax_err("需要参数名")
            if t.value in arg_list:
                t.syntax_err("重名参数")
            arg_list.append(t.value)
            t = token_list.pop()
            if t.is_sym(")"):
                #解析完成
                break
            if t.is_sym(","):
                #继续解析
                continue
            t.syntax_err("需要','或')'")
        return arg_list

    def _parse_func(self, token_list):
        name_token = token_list.pop()
        if not name_token.is_name:
            name_token.syntax_err("非法的函数名")
        func_name = name_token.value
        if func_name in self.dep_module_set:
            name_token.syntax_err("函数名和模块名重复")
        if func_name in self.global_var_map:
            name_token.syntax_err("函数名和全局变量名重复")
        token_list.pop_sym("(")
        arg_list = self._parse_func_arg_list(token_list)
        func_key = func_name, len(arg_list)
        if func_key in self.func_map:
            name_token.syntax_err("函数重复声明")
        self.func_map[func_key] = None

    def _parse_global_var(self, token_list):
        while True:
            t = token_list.pop()
            if not t.is_name:
                t.syntax_err("需要标识符")
            var_name = t.value
            if var_name in self.dep_module_set:
                t.syntax_err("全局变量名和模块名重复")
            for func_name, arg_count in self.func_map:
                if func_name == var_name:
                    t.syntax_err("全局变量名和函数名重复")
            self.global_var_map[var_name] = None
            if not token_list or token_list.peek().is_indent:
                return
            token_list.pop_sym(",")
