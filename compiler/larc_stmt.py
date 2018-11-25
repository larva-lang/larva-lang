#coding=utf8

"""
编译larva语句
"""

import os
import sys

import larc_common
import larc_token
import larc_expr
import larc_type
import larc_module

class _Stmt:
    def __init__(self, type, **kw_arg):
        self.type = type
        for k, v in kw_arg.iteritems():
            setattr(self, k, v)

class _StmtList(list):
    def __init__(self, var_map):
        list.__init__(self)
        self.var_map = var_map

    def has_defer(self):
        for stmt in self:
            if stmt.type in ("defer_block", "defer_expr"):
                return True
        return False

class _SeExpr(larc_expr.ExprBase):
    def __init__(self, lvalue, op, expr):
        larc_expr.ExprBase.__init__(self, "se_expr")
        self.lvalue = lvalue
        self.op = op
        self.expr = expr
        self.pos_info = lvalue.pos_info

class Parser:
    def __init__(self, token_list, module, dep_module_map, cls, gtp_map, fom):
        self.token_list = token_list
        self.module = module
        self.dep_module_map = dep_module_map
        self.cls = cls
        self.gtp_map = gtp_map
        self.fom = fom
        self.expr_parser = larc_expr.Parser(token_list, module, dep_module_map, cls, gtp_map, fom)
        self.ccc_use_deep = 0

    def parse(self, var_map_stk, loop_deep, defer_deep):
        assert var_map_stk
        stmt_list = _StmtList(var_map_stk[-1])
        top_ccc_use_deep = self.ccc_use_deep
        while True:
            if self.token_list.peek().is_sym("}"):
                assert self.ccc_use_deep == top_ccc_use_deep
                break

            t = self.token_list.pop()

            def ccc_jmp():
                #跳过ccc块，返回跳过的块的结束ccc token
                nested_ccc_use_deep = 0
                while True:
                    t = self.token_list.pop()
                    if t.is_ccc("use"):
                        nested_ccc_use_deep += 1
                    elif t.is_ccc("oruse") or t.is_ccc("enduse"):
                        if nested_ccc_use_deep == 0:
                            return t
                        if t.is_ccc("enduse"):
                            nested_ccc_use_deep -= 1
            if t.is_ccc("use"):
                self.ccc_use_deep += 1
                while True:
                    fd_r, fd_w = os.pipe()
                    pid = os.fork()
                    if pid == 0:
                        #子进程，注册管道fd后继续尝试编译
                        os.close(fd_r)
                        larc_common.reg_err_report_fd(fd_w)
                        work_ccc_use_deep = self.ccc_use_deep #记录子进程工作的deep
                        break
                    #父进程，等待子进程的编译结果，若失败则继续下一个use block
                    os.close(fd_w)
                    compile_result = os.read(fd_r, 1)
                    assert compile_result in ("0", "1")
                    if compile_result == "1":
                        #成功，父进程在这个point继续编译
                        break
                    #失败了，跳过这个use block继续尝试下一个
                    revert_idx = self.token_list.i #用于最后一个use block的回滚
                    t = ccc_jmp()
                    if t.is_ccc("enduse"):
                        #已经是最后一个了，以这个为准
                        self.token_list.revert(revert_idx)
                        break
                continue
            if t.is_ccc and t.value in ("oruse", "enduse"):
                assert self.ccc_use_deep > top_ccc_use_deep
                fd = larc_common.get_err_report_fd()
                if fd >= 0 and self.ccc_use_deep == work_ccc_use_deep:
                    #子进程尝试成功，汇报给父进程
                    os.write(fd, "1")
                    sys.exit(0)
                #当前进程为一个父进程，成功选择了一个use block，跳到enduse继续编译
                self.token_list.revert()
                while not ccc_jmp().is_ccc("enduse"):
                    pass
                self.ccc_use_deep -= 1
                continue

            if t.is_sym(";"):
                continue
            if t.is_sym("{"):
                #新代码块
                stmt_list.append(_Stmt("block", stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep, defer_deep)))
                self.token_list.pop_sym("}")
                continue
            if t.is_reserved and t.value in ("break", "continue"):
                if loop_deep == 0:
                    if defer_deep == 0:
                        t.syntax_err("循环外的%s" % t.value)
                    else:
                        t.syntax_err("不允许从defer代码中向外部%s" % t.value)
                stmt_list.append(_Stmt(t.value))
                continue
            if t.is_reserved("return"):
                if defer_deep > 0:
                    t.syntax_err("不允许在defer代码中return")
                stmt_list.append(_Stmt("return", expr = self._parse_return(var_map_stk)))
                continue
            if t.is_reserved("for"):
                for_var_map, init_expr_list, judge_expr, loop_expr_list = self._parse_for_prefix(var_map_stk)
                self.token_list.pop_sym("{")
                for_stmt_list = self.parse(var_map_stk + (for_var_map.copy(),), loop_deep + 1, defer_deep)
                self.token_list.pop_sym("}")
                stmt_list.append(_Stmt("for", for_var_map = for_var_map, init_expr_list = init_expr_list, judge_expr = judge_expr,
                                       loop_expr_list = loop_expr_list, stmt_list = for_stmt_list))
                continue
            if t.is_reserved("foreach"):
                var_tp, var_name, iter_expr = self._parse_foreach_prefix(var_map_stk)
                foreach_var_map = larc_common.OrderedDict()
                foreach_var_map[var_name] = var_tp
                self.token_list.pop_sym("{")
                foreach_stmt_list = self.parse(var_map_stk + (foreach_var_map,), loop_deep + 1, defer_deep)
                self.token_list.pop_sym("}")
                stmt_list.append(_Stmt("foreach", var_tp = var_tp, var_name = var_name, iter_expr = iter_expr, stmt_list = foreach_stmt_list))
                continue
            if t.is_reserved("while"):
                self.token_list.pop_sym("(")
                expr = self.expr_parser.parse(var_map_stk, larc_type.BOOL_TYPE)
                self.token_list.pop_sym(")")
                self.token_list.pop_sym("{")
                while_stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep + 1, defer_deep)
                self.token_list.pop_sym("}")
                stmt_list.append(_Stmt("while", expr = expr, stmt_list = while_stmt_list))
                continue
            if t.is_reserved("if"):
                if_expr_list = []
                if_stmt_list_list = []
                else_stmt_list = None
                while True:
                    self.token_list.pop_sym("(")
                    expr = self.expr_parser.parse(var_map_stk, larc_type.BOOL_TYPE)
                    self.token_list.pop_sym(")")
                    self.token_list.pop_sym("{")
                    if_stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep, defer_deep)
                    self.token_list.pop_sym("}")
                    if_expr_list.append(expr)
                    if_stmt_list_list.append(if_stmt_list)
                    if not self.token_list.peek().is_reserved("else"):
                        break
                    self.token_list.pop()
                    t = self.token_list.pop()
                    if t.is_reserved("if"):
                        continue
                    if not t.is_sym("{"):
                        t.syntax_err("需要'{'")
                    else_stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep, defer_deep)
                    self.token_list.pop_sym("}")
                    break
                stmt_list.append(_Stmt("if", if_expr_list = if_expr_list, if_stmt_list_list = if_stmt_list_list,
                                       else_stmt_list = else_stmt_list))
                continue
            if t.is_reserved("var"):
                while True:
                    tp, name, expr, end_sym = self._parse_var(None, var_map_stk)
                    stmt_list.append(_Stmt("var", name = name, expr = expr))
                    if end_sym == ";":
                        break
                    assert end_sym == ","
                continue
            if t.is_reserved("defer"):
                if self.token_list.peek().is_sym("{"):
                    #解析stmt_list时，外层loop_deep清零，defer_deep加一
                    self.token_list.pop_sym("{")
                    stmt_list.append(
                        _Stmt("defer_block", stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), 0, defer_deep + 1)))
                    self.token_list.pop_sym("}")
                else:
                    #单条call表达式的defer
                    expr = self.expr_parser.parse(var_map_stk, None)
                    if expr.op not in ("call_method", "call_func"):
                        t.syntax_err("defer表达式必须是一个函数或方法调用")
                    stmt_list.append(_Stmt("defer_expr", expr = expr))
                continue

            self.token_list.revert()
            tp = larc_type.try_parse_type(self.token_list, self.module, self.dep_module_map, self.gtp_map, var_map_stk)
            if tp is not None:
                #变量定义
                while True:
                    _, name, expr, end_sym = self._parse_var(tp, var_map_stk)
                    stmt_list.append(_Stmt("var", name = name, expr = expr))
                    if end_sym == ";":
                        break
                    assert end_sym == ","
                continue

            #表达式
            expr = self._parse_expr_with_se(var_map_stk)
            self._check_valid_expr_stmt(t, expr)
            stmt_list.append(_Stmt("expr", expr = expr))
            self.token_list.pop_sym(";")
            continue

        return stmt_list

    def _parse_var(self, var_tp, var_map_stk):
        t, name = self.token_list.pop_name()
        self._check_var_redefine(t, name, var_map_stk)
        if var_tp is None:
            #var语法
            self.token_list.pop_sym("=")
            t = self.token_list.peek()
            expr = self.expr_parser.parse(var_map_stk, None)
            if expr.type.is_void:
                t.syntax_err("变量类型不能为void")
            if expr.type.is_nil:
                t.syntax_err("var定义的变量不能用无类型的nil初始化")
            if expr.type.is_literal_int:
                tp = larc_type.INT_TYPE
            else:
                tp = expr.type
        else:
            #指定类型
            if var_tp.is_void:
                t.syntax_err("变量类型不能为void")
            t = self.token_list.pop()
            if not t.is_sym or t.value not in ("=", ",", ";"):
                t.syntax_err("需要'='、';'或','")
            if t.value == "=":
                expr = self.expr_parser.parse(var_map_stk, var_tp)
            else:
                expr = None
                self.token_list.revert()
            tp = var_tp
        var_map_stk[-1][name] = tp
        t = self.token_list.pop()
        if not t.is_sym or t.value not in (";", ","):
            t.syntax_err("需要';'或','")
        return tp, name, expr, t.value

    def _is_valid_expr_stmt(self, expr):
        return isinstance(expr, _SeExpr) or expr.op in ("new", "call_array.method", "call_method", "call_func")

    def _check_valid_expr_stmt(self, t, expr):
        if not self._is_valid_expr_stmt(expr):
            t.syntax_err("表达式求值后未使用")

    def _check_var_redefine(self, t, name, var_map_stk):
        if name in self.dep_module_map:
            t.syntax_err("变量名和导入模块重名")
        if name in var_map_stk[-1]:
            t.syntax_err("变量名重定义")
        for var_map in var_map_stk[: -1]:
            if name in var_map:
                t.syntax_err("与上层的变量名冲突")
        if self.gtp_map is not None and name in self.gtp_map:
            t.syntax_err("变量名与泛型参数名冲突")
        for m in self.module, larc_module.builtins_module:
            elem = m.get_elem(name, public_only = m is larc_module.builtins_module)
            if elem is not None:
                t.syntax_err("变量名与'%s'名字冲突" % elem)

    def _parse_return(self, var_map_stk):
        if self.fom.type.is_void:
            self.token_list.pop_sym(";")
            return None
        t = self.token_list.peek()
        if t.is_sym(";"):
            t.syntax_err("需要表达式")
        expr = self.expr_parser.parse(var_map_stk, self.fom.type)
        self.token_list.pop_sym(";")
        return expr

    def _parse_foreach_prefix(self, var_map_stk):
        self.token_list.pop_sym("(")

        if self.token_list.peek().is_reserved("var"):
            #foreach (var var_name : iter_expr)
            self.token_list.pop()
            var_tp = None
        else:
            #foreach (var_tp var_name : iter_expr)
            t = self.token_list.peek()
            var_tp = larc_type.try_parse_type(self.token_list, self.module, self.dep_module_map, self.gtp_map, var_map_stk)
            if var_tp is None:
                t.syntax_err("需要变量定义")

        var_name_token, var_name = self.token_list.pop_name()
        self._check_var_redefine(var_name_token, var_name, var_map_stk)

        self.token_list.pop_sym(":")
        iter_expr_start_token = self.token_list.peek()
        iter_expr = self.expr_parser.parse(var_map_stk, None)

        #解析出其get方法返回的类型，代入_Iter<E>类型，检查是否为一个迭代器
        iter_tp = iter_expr.type
        iter_elem_tp = None
        if iter_tp.is_coi_type:
            coi = iter_tp.get_coi()
            if coi.has_method("get"):
                elem_tp = coi.get_method("get", iter_expr_start_token).type
                if elem_tp != larc_type.VOID_TYPE:
                    internal_iter_tp = larc_type.gen_internal_iter_type(elem_tp, iter_expr_start_token)
                    if internal_iter_tp.can_convert_from(iter_tp):
                        iter_elem_tp = elem_tp
        if iter_elem_tp is None:
            iter_expr_start_token.syntax_err("需要迭代器类型")

        #若为var定义，则设置var_tp，否则检查var_tp的类型是否匹配
        if var_tp is None:
            var_tp = iter_elem_tp
        else:
            if not var_tp.can_convert_from(iter_elem_tp):
                var_name_token.syntax_err("迭代器的元素类型'%s'不能隐式转为类型'%s'" % (iter_elem_tp, var_tp))

        self.token_list.pop_sym(")")

        return var_tp, var_name, iter_expr

    def _parse_for_prefix(self, var_map_stk):
        self.token_list.pop_sym("(")

        for_var_map = larc_common.OrderedDict()
        init_expr_list = []
        if self.token_list.peek().is_reserved("var"):
            #第一部分为var变量定义
            self.token_list.pop()
            while True:
                _, _, expr, end_sym = self._parse_var(None, var_map_stk + (for_var_map,))
                init_expr_list.append(expr)
                if end_sym == ";":
                    break
                assert end_sym == ","
        else:
            tp = larc_type.try_parse_type(self.token_list, self.module, self.dep_module_map, self.gtp_map, var_map_stk)
            if tp is None:
                #第一部分为表达式列表
                if not self.token_list.peek().is_sym(";"):
                    init_expr_list += self._parse_expr_list_with_se(var_map_stk + (for_var_map,))
                self.token_list.pop_sym(";")
            else:
                #第一部分为若干指定类型的变量定义
                while True:
                    _, _, expr, end_sym = self._parse_var(tp, var_map_stk + (for_var_map,))
                    init_expr_list.append(expr)
                    if end_sym == ";":
                        break
                    assert end_sym == ","

        if self.token_list.peek().is_sym(";"):
            #没有第二部分
            judge_expr = None
        else:
            judge_expr = self.expr_parser.parse(var_map_stk + (for_var_map,), larc_type.BOOL_TYPE)
        self.token_list.pop_sym(";")

        loop_expr_list = []
        if not self.token_list.peek().is_sym(")"):
            loop_expr_list += self._parse_expr_list_with_se(var_map_stk + (for_var_map,))

        self.token_list.pop_sym(")")

        return for_var_map, init_expr_list, judge_expr, loop_expr_list

    def _parse_expr_with_se(self, var_map_stk):
        def check_lvalue(lvalue):
            if not lvalue.is_lvalue:
                t.syntax_err("需要左值")
            if lvalue.op == "global_var":
                global_var = lvalue.arg
                if "final" in global_var.decr_set:
                    t.syntax_err("final修饰的全局变量'%s'不可修改" % global_var)

        def build_inc_dec_expr(op, lvalue, t):
            check_lvalue(lvalue)
            return _SeExpr(lvalue, op, None)

        t = self.token_list.peek()
        if t.is_sym and t.value in larc_token.INC_DEC_SYM_SET:
            #前缀自增自减
            op = t.value
            self.token_list.pop_sym(op)
            t = self.token_list.peek()
            return build_inc_dec_expr(op, self.expr_parser.parse(var_map_stk, None), t)

        expr = self.expr_parser.parse(var_map_stk, None)
        t = self.token_list.pop()
        if t.is_sym and t.value in larc_token.INC_DEC_SYM_SET:
            #后缀自增自减
            op = t.value
            return build_inc_dec_expr(op, expr, t)

        if t.is_sym and t.value in larc_token.ASSIGN_SYM_SET:
            #赋值
            if t.value != "=":
                assert t.value.endswith("=")
                op = t.value[: -1]

                class _InvalidType(Exception):
                    pass

                try:
                    if op in ("+", "-", "*", "/"):
                        if not expr.type.is_number_type:
                            raise _InvalidType()
                    elif op in ("%", "&", "|", "^", "<<", ">>"):
                        if not expr.type.is_integer_type:
                            raise _InvalidType()
                    else:
                        raise Exception("Bug")

                except _InvalidType:
                    t.syntax_err("类型'%s'无法做增量赋值'%s'" % (expr.type, t.value))

            op = t.value
            lvalue = expr
            check_lvalue(lvalue)
            if op in ("<<=", ">>="):
                need_type = [larc_type.CHAR_TYPE, larc_type.USHORT_TYPE, larc_type.UINT_TYPE, larc_type.ULONG_TYPE]
            else:
                need_type = lvalue.type
            expr = self.expr_parser.parse(var_map_stk, need_type)
            return _SeExpr(lvalue, op, expr)

        self.token_list.revert()
        return expr

    def _parse_expr_list_with_se(self, var_map_stk):
        expr_list = []
        while True:
            t = self.token_list.peek()
            expr = self._parse_expr_with_se(var_map_stk)
            self._check_valid_expr_stmt(t, expr)
            expr_list.append(expr)
            if not self.token_list.peek().is_sym(","):
                return expr_list
            self.token_list.pop_sym(",")
