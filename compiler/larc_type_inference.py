#coding=utf8

"""
larva程序的类型推导优化
"""

"""
使用简化版的类型推导算法：
1 推导仅针对int类型
2 优化对象：
  模块非导出全局变量、函数，函数和方法中与导出接口无关的局部变量
3 由于是动态类型语言，且考虑到外部模块的实现不可控，
  规定：导出变量、函数，以及所有属性、方法相关变量均为object
4 容器（list、dict、tuple）的元素统一为object

算法简述：
1 反复迭代分析，标记所有object类型变量、函数返回
2 指派剩余变量类型int
3 推导剩余函数返回类型
同时int使用的合法性检查

进一步的优化设计为人工指定，即引入一些静态化语法
"""

_UNARY_OP_SET = set(["~", "not", "neg", "pos"])
_BINOCULAR_OP_SET = set(["%", "^", "&", "*", "-", "+", "|", "<", ">", "/",
                         "!=", "and", "==", "or", "<<", "<=", ">>", ">>>",
                         ">=", "in", "not in"])

class Device:
    def __init__(self, module):
        #module所有元素的type_info已在编译阶段初始化完毕
        self.module = module

    def work(self):
        #标记所有object变量
        self.mark_object_finished = False
        while not self.mark_object_finished:
            self.mark_object_finished = True
            self._mark_object_type()

        #剩余变量标记为int
        self._mark_int_type()

    def _mark_int_type(self):
        #全局变量
        for var_name in self.module.global_var_type_info:
            if self.module.global_var_type_info[var_name] is None:
                self.module.global_var_type_info[var_name] = "int"

        #函数和方法
        for func in self.module.func_map.itervalues():
            for var_name in func.local_var_type_info:
                if func.local_var_type_info[var_name] is None:
                    func.local_var_type_info[var_name] = "int"
            if func.ret_type is None:
                func.ret_type = "int"
        for cls in self.module.class_map.itervalues():
            for method in cls.method_map.itervalues():
                for var_name in method.local_var_type_info:
                    if method.local_var_type_info[var_name] is None:
                        method.local_var_type_info[var_name] = "int"

    def _mark_object_type(self):
        #全局变量
        for var_name, expr in self.module.global_var_map.iteritems():
            if self.module.global_var_type_info[var_name] is None:
                if self._expr_type_is_object(expr, None):
                    self.module.global_var_type_info[var_name] = "object"
                    self.mark_object_finished = False

        #函数和方法
        for func in self.module.func_map.itervalues():
            self._mark_object_type_in_stmt_list(
                func.stmt_list, func.local_var_type_info)
            if func.ret_type is None:
                for e in func.ret_expr_list:
                    if self._expr_type_is_object(e, func.local_var_type_info):
                        func.ret_type = "object"
                        self.mark_object_finished = False
                        break
        for cls in self.module.class_map.itervalues():
            for method in cls.method_map.itervalues():
                self._mark_object_type_in_stmt_list(
                    method.stmt_list, method.local_var_type_info)

    def _mark_object_type_lvalue(self, lvalue, local_var_type_info):
        #对左值标记为object
        if lvalue.op == "local_name":
            if local_var_type_info[lvalue.arg.value] is None:
                local_var_type_info[lvalue.arg.value] = "object"
                self.mark_object_finished = False
        elif lvalue.op == "global_name":
            if self.module.global_var_type_info[lvalue.arg.value] is None:
                self.module.global_var_type_info[lvalue.arg.value] = "object"
                self.mark_object_finished = False
        elif lvalue.op in ("tuple", "list"):
            for unpack_lvalue in lvalue.arg:
                self._mark_object_type_lvalue(unpack_lvalue,
                                              local_var_type_info)

    def _mark_object_type_in_stmt_list(self, stmt_list, local_var_type_info):
        """分析stmt_list并标记object类型
           需要标记的情况：
           1 局部变量赋值
           2 全局变量赋值
           3 函数调用传参
           因此需要分析所有赋值语句及所有表达式"""

        for stmt in stmt_list:
            #先分析赋值语句
            if stmt.type in ("=", "for"):
                if stmt.lvalue.op in ("tuple", "list"):
                    #unpack的所有左值都是object类型
                    self._mark_object_type_lvalue(stmt.lvalue,
                                                  local_var_type_info)
                else:
                    #左值非unpack，根据具体expr
                    if stmt.type == "=":
                        if self._expr_type_is_object(stmt.expr,
                                                     local_var_type_info):
                            self._mark_object_type_lvalue(
                                stmt.lvalue, local_var_type_info)
                    else:
                        #for语句对range特殊处理
                        if (stmt.expr.op != "call_builtin_if" or
                            stmt.expr.arg[0].value != "range"):
                            self._mark_object_type_lvalue(
                                stmt.lvalue, local_var_type_info)
            elif stmt.type in ("%=", "^=", "&=", "*=", "-=", "+=", "|=",
                               "/=", "<<=", ">>=", ">>>="):
                #增量赋值，左值参与运算，但只需判断右值
                if self._expr_type_is_object(stmt.expr, local_var_type_info):
                    self._mark_object_type_lvalue(stmt.lvalue,
                                                  local_var_type_info)

            #分析表达式，对嵌套stmt_list递归处理
            if stmt.type == "print":
                for e in stmt.expr_list:
                    self._mark_object_type_for_func_arg(
                        e, local_var_type_info)
            if stmt.type == "return":
                if stmt.expr is not None:
                    self._mark_object_type_for_func_arg(
                        stmt.expr, local_var_type_info)
            if stmt.type in ("expr", "for", "while", "=", "%=", "^=", "&=",
                             "*=", "-=", "+=", "|=", "/=", "<<=", ">>=",
                             ">>>="):
                self._mark_object_type_for_func_arg(
                    stmt.expr, local_var_type_info)
            if stmt.type in ("for", "=", "%=", "^=", "&=", "*=", "-=", "+=",
                             "|=", "/=", "<<=", ">>=", ">>>="):
                self._mark_object_type_for_func_arg(
                    stmt.lvalue, local_var_type_info)
            if stmt.type in ("for", "while"):
                self._mark_object_type_in_stmt_list(
                    stmt.stmt_list, local_var_type_info)
            if stmt.type == "if":
                for e, if_stmt_list in stmt.if_list:
                    self._mark_object_type_for_func_arg(
                        e, local_var_type_info)
                    self._mark_object_type_in_stmt_list(
                        if_stmt_list, local_var_type_info)
                if stmt.else_stmt_list is not None:
                    self._mark_object_type_in_stmt_list(
                        stmt.else_stmt_list, local_var_type_info)

    def _mark_object_type_for_func_arg(self, expr, local_var_type_info):
        #分析表达式，标记函数参数的object类型
        if expr.op in ("const", "const_idx", "local_name", "global_name",
                       "module.global", "this.attr"):
            return
        if expr.op == "dict":
            for ek, ev in expr.arg:
                self._mark_object_type_for_func_arg(ek, local_var_type_info)
                self._mark_object_type_for_func_arg(ev, local_var_type_info)
            return
        if expr.op == "()":
            ec, el = expr.arg
            self._mark_object_type_for_func_arg(ec, local_var_type_info)
            for e in el:
                self._mark_object_type_for_func_arg(e, local_var_type_info)
            return
        if expr.op == "int()":
            for e in expr.arg:
                self._mark_object_type_for_func_arg(e, local_var_type_info)
            return
        if expr.op in ("call_func", "call_class", "call_method",
                       "call_module_func", "call_module_class",
                       "call_builtin_if", "call_this_method",
                       "call_super_method"):
            for e in expr.arg[-1]:
                self._mark_object_type_for_func_arg(e, local_var_type_info)
            if expr.op == "call_method":
                self._mark_object_type_for_func_arg(
                    expr.arg[0], local_var_type_info)
            if expr.op == "call_func":
                func_name_token, el = expr.arg
                func_key = func_name_token.value, len(el)
                func = self.module.func_map[func_key]
                assert len(el) == len(func.arg_list)
                for i, e in enumerate(el):
                    var_name = func.arg_list[i]
                    if self._expr_type_is_object(e, local_var_type_info):
                        if func.local_var_type_info[var_name] is None:
                            func.local_var_type_info[var_name] = "object"
                            self.mark_object_finished = False
            return
        if expr.op == ".":
            self._mark_object_type_for_func_arg(
                expr.arg[0], local_var_type_info)
            return
        if expr.op == "[:]":
            eo, el = expr.arg
            self._mark_object_type_for_func_arg(eo, local_var_type_info)
            for e in el:
                if e is not None:
                    self._mark_object_type_for_func_arg(
                        e, local_var_type_info)
            return
        if expr.op == "list_compr":
            for_in_expr, compr_local_var_set, e, lvalue, name_set, if_expr = (
                expr.arg)
            self._mark_object_type_for_func_arg(
                for_in_expr, local_var_type_info)
            self._mark_object_type_for_func_arg(e, local_var_type_info)
            if if_expr is not None:
                self._mark_object_type_for_func_arg(
                    if_expr, local_var_type_info)
            return
        if expr.op == "dict_compr":
            (for_in_expr, compr_local_var_set, ek, ev, lvalue, name_set,
             if_expr) = expr.arg
            self._mark_object_type_for_func_arg(
                for_in_expr, local_var_type_info)
            self._mark_object_type_for_func_arg(ek, local_var_type_info)
            self._mark_object_type_for_func_arg(ev, local_var_type_info)
            if if_expr is not None:
                self._mark_object_type_for_func_arg(
                    if_expr, local_var_type_info)
            return
        if expr.op == "lambda":
            lambda_local_var_set, arg_list, e = expr.arg
            self._mark_object_type_for_func_arg(e, local_var_type_info)
            return
        if expr.op in ("this", "super"):
            return
        if expr.op == ".int":
            self._mark_object_type_for_func_arg(expr.arg, local_var_type_info)
            return

        #其余类型，包括单目、双目运算、下标、tuple和list构造等
        assert (expr.op in _UNARY_OP_SET or expr.op in _BINOCULAR_OP_SET or
                expr.op in ("[]", "[].int", "tuple", "list")), expr.op
        for e in expr.arg:
            self._mark_object_type_for_func_arg(e, local_var_type_info)

    def _expr_type_is_object(self, expr, local_var_type_info):
        if expr.op in ("const", "module.global", "this.attr", "dict", "()",
                       "call_class", "call_method", "call_module_func",
                       "call_module_class", "call_builtin_if",
                       "call_this_method", "call_super_method", ".", "[:]",
                       "list_compr", "dict_compr", "lambda", "this", "super",
                       "[]", "tuple", "list", "not", "<", ">", "!=", "and",
                       "==", "or", "<=", ">=", "in", "not in"):
            if expr.op == "const":
                assert (expr.arg.is_true or expr.arg.is_false or
                        expr.arg.is_nil)
            return True
        if expr.op == "const_idx":
            #非int常量都是object
            const_type, value = self.module.const_map.key_at(expr.arg)
            return const_type != "int"
        if expr.op == "local_name":
            return local_var_type_info[expr.arg.value] == "object"
        if expr.op == "global_name":
            return self.module.global_var_type_info[expr.arg.value] == "object"
        if expr.op in ("int()", ".int", "[].int"):
            return False
        if expr.op == "call_func":
            func_name = expr.arg[0].value
            func_key = func_name, len(expr.arg[1])
            func = self.module.func_map[func_key]
            return func.ret_type == "object"
        if expr.op in ("~", "neg", "pos"):
            e = expr.arg[0]
            return self._expr_type_is_object(e, local_var_type_info)
        if expr.op in ("%", "^", "&", "*", "-", "+", "|", "/", "<<", ">>",
                       ">>>"):
            ea, eb = expr.arg
            return (self._expr_type_is_object(ea, local_var_type_info) or
                    self._expr_type_is_object(eb, local_var_type_info))

        raise Exception("unreachable[%s]" % expr.op)
