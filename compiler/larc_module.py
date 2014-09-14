#coding=utf8

"""
编译larva模块
"""

import os
import larc_common
import larc_token
import larc_stmt
import larc_expr

_BUILTIN_METHOD_NAME_SET = set(map(lambda x : "__%s__" % x, ["init"]))

class _Func:
    def __init__(self, name, arg_list, global_var_set, stmt_list, name_token):
        self.name = name
        self.arg_list = arg_list
        self.global_var_set = global_var_set
        self.stmt_list = stmt_list
        self.name_token = name_token

        #检查参数的global声明
        for var_name in arg_list:
            if var_name in global_var_set:
                self.syntax_err("参数'%s'被global声明" % (name, var_name))

        #提取局部变量
        self.local_var_set = set(arg_list)
        self._search_local_var(stmt_list)
        assert not (self.local_var_set & self.global_var_set)

        larc_stmt.check_last_return(self.stmt_list)

        #初始化类型推导相关信息
        self.local_var_type_info = (
            dict(map(lambda x : (x, None), self.local_var_set)))
        self.ret_expr_list = []
        self._search_ret_expr(self.stmt_list)
        if None in self.ret_expr_list:
            #先处理隐式return nil
            self.ret_type = "object"
            self.ret_expr_list = []
        else:
            self.ret_type = None

    def _search_ret_expr(self, stmt_list):
        #搜索所有return的表达式
        for stmt in stmt_list:
            if stmt.type == "return":
                self.ret_expr_list.append(stmt.expr)
            if stmt.type in ("for", "while"):
                self._search_ret_expr(stmt.stmt_list)
            if stmt.type == "if":
                for expr, if_stmt_list in stmt.if_list:
                    self._search_ret_expr(if_stmt_list)
                if stmt.else_stmt_list is not None:
                    self._search_ret_expr(stmt.else_stmt_list)

    def _search_local_var(self, stmt_list):
        #局部变量条件：赋值或for的左值是一个名字或在unpack表达式查找名字
        #对于嵌套stmt_list的语句递归搜索
        for stmt in stmt_list:
            if stmt.type in ("=", "%=", "^=", "&=", "*=", "-=", "+=", "|=",
                             "/=", "<<=", ">>=", ">>>=", "for"):
                def _search_local_var_in_lvalue(lvalue):
                    if lvalue.op == "name":
                        if lvalue.arg.value not in self.global_var_set:
                            self.local_var_set.add(lvalue.arg.value)
                    elif lvalue.op in ("tuple", "list"):
                        for unpack_lvalue in lvalue.arg:
                            _search_local_var_in_lvalue(unpack_lvalue)
                _search_local_var_in_lvalue(stmt.lvalue)
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

class _Method(_Func):
    def __init__(self, name, arg_list, global_var_set, stmt_list, name_token):
        if name.startswith("__") and name.endswith("__"):
            #检查内置方法
            if name not in _BUILTIN_METHOD_NAME_SET:
                name_token.syntax_err("非法的内置方法名'%s'" % name)
        _Func.__init__(self, name, arg_list, global_var_set, stmt_list,
                       name_token)
        #method输入参数和返回类型都是object
        for arg_name in arg_list:
            self.local_var_type_info[arg_name] = "object"
        self.ret_type = "object"
        self.ret_expr_list = []

    def syntax_err(self, msg):
        self.name_token.syntax_err("[方法'%s']%s" % (self.name, msg))

    def link(self, curr_module, module_map, curr_class):
        for stmt in self.stmt_list:
            stmt.link(curr_module, module_map, self.local_var_set, curr_class)

class _Class:
    def __init__(self, name, name_token, base_class_module, base_class_name):
        self.name = name
        self.name_token = name_token
        self.base_class_module = base_class_module
        self.base_class_name = base_class_name
        self.method_map = larc_common.OrderedDict()

    def link_extends(self, curr_module, module_map):
        if self.base_class_name is not None:
            #有继承，检查并定向基类
            if self.base_class_module is None:
                #基类在当前模块
                if self.base_class_name not in curr_module.class_map:
                    self.syntax_err("找不到基类'%s'" % self.base_class_name)
                else:
                    self.base_class = (
                        curr_module.class_map[self.base_class_name])
            else:
                #基类在其它模块
                if self.base_class_module not in curr_module.dep_module_set:
                    self.syntax_err("找不到模块名'%s'" % self.base_class_module)
                module = module_map[self.base_class_module]
                if self.base_class_name not in module.export_class_set:
                    self.syntax_err(
                        "找不到基类'%s.%s'" %
                        (self.base_class_module, self.base_class_name))
                else:
                    self.base_class = module.class_map[self.base_class_name]
        else:
            self.base_class = None

    def _check_cycle_extends(self):
        #检查循环继承
        cls = self
        s = set([cls])
        while True:
            base_class = cls.base_class
            if base_class is None:
                return
            if base_class in s:
                self.syntax_err("存在循环继承")
            cls = base_class
            s.add(cls)

    def link(self, curr_module, module_map):
        self._check_cycle_extends()
        if "__init__" not in [name for name, arg_count in self.method_map]:
            #增加默认构造函数
            self.method_map[("__init__", 0)] = (
                _Method("__init__", [], set(), [], self.name_token))
        self.attr_set = larc_common.OrderedSet()
        for method in self.method_map.itervalues():
            method.link(curr_module, module_map, self)

    def syntax_err(self, msg):
        self.name_token.syntax_err("[类'%s']%s" % (self.name, msg))

class Module:
    def __init__(self, file_path_name):
        self.dir, file_name = os.path.split(file_path_name)
        assert file_name.endswith(".lar")
        self.name = file_name[: -4]
        self._compile(file_path_name)
        self._check_undefined_global_var()

    def link(self, module_map):
        self.const_map = larc_common.OrderedDict()
        for cls in self.class_map.itervalues():
            cls.link(self, module_map)
        for expr in self.global_var_map.itervalues():
            expr.link(self, module_map)
        for func in self.func_map.itervalues():
            func.link(self, module_map)

    def link_class_extends(self, module_map):
        for cls in self.class_map.itervalues():
            cls.link_extends(self, module_map)

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
        self.class_map = larc_common.OrderedDict()
        self.export_class_set = set()
        self.func_map = larc_common.OrderedDict()
        self.export_func_set = set()
        self.global_var_map = larc_common.OrderedDict()
        self.global_var_type_info = {}
        self.export_global_var_set = set()
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
            if t.is_export:
                export = True
                t = token_list.pop()
            else:
                export = False
            if t.is_class:
                #类定义
                self._parse_class(token_list, export)
                continue
            if t.is_func:
                #函数定义
                self._parse_func(token_list, export)
                continue
            if t.is_name:
                #全局变量
                self._parse_global_var(token_list, t, export)
                continue
            t.syntax_err()

    def _parse_import(self, token_list):
        t = token_list.pop()
        if not t.is_name:
            t.syntax_err("非法的模块名")
        if t.value in self.dep_module_set:
            t.syntax_err("模块重复import")
        self.dep_module_set.add(t.value)

    def _parse_class(self, token_list, export):
        name_token = token_list.pop()
        if not name_token.is_name:
            name_token.syntax_err("非法的类名")
        class_name = name_token.value
        if class_name in self.dep_module_set:
            name_token.syntax_err("类名和模块名重复")
        if class_name in self.global_var_map:
            name_token.syntax_err("类名和全局变量名重复")
        for func_name, arg_count in self.func_map:
            if func_name == class_name:
                name_token.syntax_err("类名和函数名重复")
        if class_name in self.class_map:
            name_token.syntax_err("类重复定义")
        base_class_module = None
        base_class_name = None
        if token_list.peek().is_extends:
            #有继承，格式extends CLASS或extends MODULE.CLASS
            token_list.pop()
            base_class_name = token_list.pop_name()
            if token_list.peek().is_sym("."):
                #MODULE.CLASS
                base_class_module = base_class_name
                token_list.pop_sym(".")
                base_class_name = token_list.pop_name()
        token_list.pop_sym(":")
        self.class_map[class_name] = cls = (
            _Class(class_name, name_token, base_class_module, base_class_name))
        if export:
            self.export_class_set.add(class_name)
        curr_indent_count = token_list.peek_indent()
        if curr_indent_count == 0:
            token_list.peek().indent_err()
        while token_list:
            indent_count = token_list.peek_indent()
            if indent_count < curr_indent_count:
                return
            token_list.pop_indent(curr_indent_count)
            t = token_list.pop()
            if t.is_pass:
                #允许定义空类
                continue
            if t.is_func:
                #类方法
                self._parse_method(token_list, cls, curr_indent_count)
                continue
            t.syntax_err()

    def _parse_method(self, token_list, cls, class_blk_indent_count):
        name_token = token_list.pop()
        if not name_token.is_name:
            name_token.syntax_err("非法的方法名")
        method_name = name_token.value
        token_list.pop_sym("(")
        arg_list = self._parse_func_arg_list(token_list)
        method_key = method_name, len(arg_list)
        if method_key in cls.method_map:
            name_token.syntax_err("方法重复定义")
        stmt_list, global_var_set = (
            larc_stmt.parse_stmt_list(token_list, class_blk_indent_count, 0))
        cls.method_map[method_key] = (
            _Method(method_name, arg_list, global_var_set, stmt_list,
                    name_token))

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

    def _parse_func(self, token_list, export):
        name_token = token_list.pop()
        if not name_token.is_name:
            name_token.syntax_err("非法的函数名")
        func_name = name_token.value
        if func_name in self.dep_module_set:
            name_token.syntax_err("函数名和模块名重复")
        if func_name in self.global_var_map:
            name_token.syntax_err("函数名和全局变量名重复")
        if func_name in self.class_map:
            name_token.syntax_err("函数名和类名重复")
        token_list.pop_sym("(")
        arg_list = self._parse_func_arg_list(token_list)
        func_key = func_name, len(arg_list)
        if func_key in self.func_map:
            name_token.syntax_err("函数重复定义")
        stmt_list, global_var_set = larc_stmt.parse_stmt_list(token_list, 0, 0)
        self.func_map[func_key] = (
            _Func(func_name, arg_list, global_var_set, stmt_list, name_token))
        if export:
            self.export_func_set.add(func_key)

    def _parse_global_var(self, token_list, name_token, export):
        var_name = name_token.value
        if var_name in self.dep_module_set:
            name_token.syntax_err("全局变量名和模块名重复")
        if var_name in self.class_map:
            name_token.syntax_err("全局变量名和类名重复")
        for func_name, arg_count in self.func_map:
            if func_name == var_name:
                name_token.syntax_err("全局变量名和函数名重复")
        if var_name in self.global_var_map:
            name_token.syntax_err("全局变量重复定义")
        t = token_list.pop()
        if not t.is_sym("="):
            t.syntax_err("需要'='")
        self.global_var_map[var_name] = larc_expr.parse_expr(token_list)
        self.global_var_type_info[var_name] = None
        if export:
            self.export_global_var_set.add(var_name)
            self.global_var_type_info[var_name] = "object"

class ExternModule:
    def __init__(self, file_path_name):
        self.dir, file_name = os.path.split(file_path_name)
        assert file_name.endswith(".lar_ext")
        self.name = file_name[: -8]
        self._compile(file_path_name)

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
            if t.is_export:
                if token_list.peek().is_func:
                    #函数声明
                    token_list.pop()
                    self._parse_func(token_list)
                    continue
                #全局变量声明
                self._parse_global_var(token_list)
                continue
            t.syntax_err()
        #外部模块只含有导出变量和函数
        self.export_func_set = set(self.func_map)
        self.export_global_var_set = set(self.global_var_map)

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
