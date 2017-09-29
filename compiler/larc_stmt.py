#coding=utf8

"""
编译larva语句
"""

import larc_common
import larc_token
import larc_expr
import larc_type

class _Stmt:
    def __init__(self, type, **kw_arg):
        self.type = type
        for k, v in kw_arg.iteritems():
            setattr(self, k, v)

class _StmtList(list):
    def __init__(self, var_map):
        list.__init__(self)
        self.var_map = var_map

class _SeExpr(larc_expr.ExprBase):
    def __init__(self, lvalue, op, expr):
        larc_expr.ExprBase.__init__(self, "se_expr")
        self.lvalue = lvalue
        self.op = op
        self.expr = expr

class Parser:
    def __init__(self, token_list, module, cls, gtp_map, ret_type):
        self.token_list = token_list
        self.module = module
        self.cls = cls
        self.gtp_map = gtp_map
        self.ret_type = ret_type
        self.expr_parser = larc_expr.Parser(token_list, module, cls, gtp_map)

    def parse(self, var_map_stk, loop_deep):
        assert var_map_stk
        stmt_list = _StmtList(var_map_stk[-1])
        while True:
            if self.token_list.peek().is_sym("}"):
                break

            t = self.token_list.pop()
            if t.is_sym(";"):
                continue
            if t.is_sym("{"):
                #新代码块
                stmt_list.append(_Stmt("block", stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep)))
                self.token_list.pop_sym("}")
                continue
            if t.is_reserved and t.value in ("break", "continue"):
                if loop_deep == 0:
                    t.syntax_err("循环外的'%s'" % t.value)
                stmt_list.append(_Stmt(t.value))
                continue
            if t.is_reserved("return"):
                stmt_list.append(_Stmt("return", expr = self._parse_return(var_map_stk)))
                continue
            if t.is_reserved("for"):
                for_var_map, init_expr_list, judge_expr, loop_expr_list = self._parse_for_prefix(var_map_stk)
                self.token_list.pop_sym("{")
                for_stmt_list = self.parse(var_map_stk + (for_var_map.copy(),), loop_deep + 1)
                self.token_list.pop_sym("}")
                stmt_list.append(_Stmt("for", for_var_map = for_var_map, init_expr_list = init_expr_list, judge_expr = judge_expr,
                                       loop_expr_list = loop_expr_list, stmt_list = for_stmt_list))
                continue
            if t.is_reserved("while"):
                self.token_list.pop_sym("(")
                expr = self.expr_parser.parse(var_map_stk, larc_type.BOOL_TYPE)
                self.token_list.pop_sym(")")
                self.token_list.pop_sym("{")
                while_stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep + 1)
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
                    if_stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep)
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
                    else_stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep)
                    self.token_list.pop_sym("}")
                    break
                stmt_list.append(_Stmt("if", if_expr_list = if_expr_list, if_stmt_list_list = if_stmt_list_list,
                                       else_stmt_list = else_stmt_list))
                continue

            self.token_list.revert()
            t = self.token_list.peek()
            tp = larc_type.try_parse_type(self.token_list, self.module, self.gtp_map)
            if tp is not None:
                #变量定义
                if tp.is_void:
                    t.syntax_err("变量类型不能为void")
                while True:
                    t, name = self.token_list.pop_name()
                    if name in self.module.dep_module_set:
                        t.syntax_err("变量名和导入模块重名")
                    if name in var_map_stk[-1]:
                        t.syntax_err("变量名重定义")
                    for var_map in var_map_stk[: -1]:
                        if name in var_map:
                            t.syntax_err("与上层的变量名冲突")
                    var_map_stk[-1][name] = tp
                    t = self.token_list.pop()
                    if not t.is_sym or t.value not in ("=", ",", ";"):
                        t.syntax_err("需要'='、';'或','")
                    if t.value == "=":
                        expr = self.expr_parser.parse(var_map_stk, tp)
                    else:
                        expr = None
                        self.token_list.revert()
                    stmt_list.append(_Stmt("var", name = name, expr = expr))
                    t = self.token_list.peek()
                    if not t.is_sym or t.value not in (";", ","):
                        t.syntax_err("需要';'或','")
                    if t.is_sym(";"):
                        break
                    self.token_list.pop_sym(",")
                self.token_list.pop_sym(";")
                continue

            #表达式
            expr = self._parse_expr_with_se(var_map_stk)
            stmt_list.append(_Stmt("expr", expr = expr))
            self.token_list.pop_sym(";")

        return stmt_list

    def _parse_return(self, var_map_stk):
        if self.token_list.peek().is_sym(";"):
            expr = None
            if not self.ret_type.is_void:
                token_list.peek().syntax_err("需要表达式")
        else:
            expr = self.expr_parser.parse(var_map_stk, self.ret_type)
        self.token_list.pop_sym(";")
        return expr

    def _parse_for_prefix(self, var_map_stk):
        self.token_list.pop_sym("(")

        for_var_map = larc_common.OrderedDict()
        tp = larc_type.try_parse_type(self.token_list, self.module, self.gtp_map)
        if tp is None:
            #第一部分为表达式列表
            init_expr_list = []
            if not self.token_list.peek().is_sym(";"):
                init_expr_list += self._parse_expr_list_with_se(var_map_stk + (for_var_map,))
        else:
            #第一部分为若干变量定义
            init_expr_list = []
            while True:
                t, name = self.token_list.pop_name()
                if name in self.module.dep_module_set:
                    t.syntax_err("变量名和导入模块重名")
                if name in for_var_map:
                    t.syntax_err("变量名重定义")
                for var_map in var_map_stk:
                    if name in var_map:
                        t.syntax_err("与上层的变量名冲突")
                t = self.token_list.pop()
                if not t.is_sym("="):
                    t.syntax_err("for语句定义的变量必须显式初始化")
                expr = self.expr_parser.parse(var_map_stk + (for_var_map,), tp)
                for_var_map[name] = tp
                init_expr_list.append(expr)
                if self.token_list.peek().is_sym(";"):
                    break
                self.token_list.pop_sym(",")
        self.token_list.pop_sym(";")

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
            expr = self._parse_expr_with_se(var_map_stk)
            expr_list.append(expr)
            if not self.token_list.peek().is_sym(","):
                return expr_list
            self.token_list.pop_sym(",")
