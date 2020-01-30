#coding=utf8

"""
编译larva语句
"""

import os, sys, copy

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
        self.file_name = self.fom.file_name if self.cls is None else self.cls.file_name
        self.expr_parser = larc_expr.Parser(token_list, module, self.file_name, dep_module_map, cls, gtp_map, fom)
        self.ccc_use_deep = 0

    def parse(self, var_map_stk, loop_deep):
        assert var_map_stk
        stmt_list = _StmtList(var_map_stk[-1])
        def new_closure_hook(closure):
            stmt_list.append(_Stmt("def_closure_method", closure = closure))
        self.expr_parser.push_new_closure_hook(new_closure_hook)
        self._parse(var_map_stk, loop_deep, stmt_list)
        self.expr_parser.pop_new_closure_hook()
        return stmt_list

    def _parse(self, var_map_stk, loop_deep, stmt_list):
        top_ccc_use_deep = self.ccc_use_deep
        while True:
            if self.token_list.peek().is_sym("}"):
                assert self.ccc_use_deep == top_ccc_use_deep
                break

            t = self.token_list.pop()

            def ccc_jmp():
                #跳过ccc块，返回跳过的块的结束ccc token
                nested_ccc_stk = []
                while True:
                    t = self.token_list.pop()
                    if t.is_ccc("use"):
                        nested_ccc_stk.append("use")
                    elif t.is_ccc("if"):
                        nested_ccc_stk.append("if")
                    elif any([t.is_ccc(ccc) for ccc in ("oruse", "else_of_use", "enduse", "elif", "else_of_if", "endif")]):
                        if not nested_ccc_stk:
                            return t
                        if any([t.is_ccc(ccc) for ccc in ("oruse", "else_of_use", "enduse")]):
                            assert nested_ccc_stk[-1] == "use"
                        if any([t.is_ccc(ccc) for ccc in ("elif", "else_of_if", "endif")]):
                            assert nested_ccc_stk[-1] == "if"
                        if any([t.is_ccc(ccc) for ccc in ("enduse", "endif")]):
                            nested_ccc_stk.pop()

            if t.is_ccc("use"):
                self.ccc_use_deep += 1
                while True:
                    result = larc_common.fork()
                    if result is None:
                        #子进程
                        work_ccc_use_deep = self.ccc_use_deep #记录子进程工作的deep
                        break
                    #父进程，根据子进程的编译结果，若失败则继续下一个use block
                    if result == "1":
                        #成功，父进程在这个point继续编译
                        break
                    #失败了，跳过这个use block继续尝试下一个
                    assert result == ""
                    t = ccc_jmp()
                    if t.is_ccc("else_of_use"):
                        #已经是最后一个了，以这个为准
                        break
                    assert t.is_ccc("oruse")
                continue
            if any([t.is_ccc(ccc) for ccc in ("oruse", "else_of_use", "enduse")]):
                assert self.ccc_use_deep > top_ccc_use_deep
                if larc_common.is_child() and self.ccc_use_deep == work_ccc_use_deep:
                    #子进程尝试成功，汇报给父进程
                    larc_common.child_exit_succ("1")
                #当前进程为一个父进程，成功选择了一个use block，跳到enduse继续编译
                self.token_list.revert()
                while not ccc_jmp().is_ccc("enduse"):
                    pass
                self.ccc_use_deep -= 1
                continue

            if t.is_ccc("if"):
                while True:
                    ccc_if_arg_t = self.token_list.pop()
                    assert ccc_if_arg_t.is_sub_token_list
                    ccc_if_token_list = ccc_if_arg_t.value
                    ccc_if_result = self._eval_ccc_if(var_map_stk, ccc_if_arg_t.value)
                    assert ccc_if_token_list
                    end_tag_t = ccc_if_token_list.pop()
                    if not end_tag_t.is_end_tag:
                        end_tag_t.syntax_err()
                    if ccc_if_result:
                        #选择这个block
                        break
                    t = ccc_jmp()
                    if t.is_ccc("else_of_if"):
                        #已经是最后一个了，以这个为准
                        break
                    assert t.is_ccc("elif")
                continue
            if any([t.is_ccc(ccc) for ccc in ("elif", "else_of_if", "endif")]):
                #跳到endif继续编译
                self.token_list.revert()
                while not ccc_jmp().is_ccc("endif"):
                    pass
                continue

            if t.is_ccc("error"):
                ccc_err_msg_t = self.token_list.pop()
                assert ccc_err_msg_t.is_literal("str")
                ccc_err_msg = ccc_err_msg_t.value
                t.syntax_err(ccc_err_msg)

            if t.is_sym(";"):
                t.warning("空语句")
                continue
            if t.is_sym("{"):
                #新代码块
                stmt_list.append(_Stmt("block", stmt_list = self.parse(var_map_stk + (larc_common.OrderedDict(),), loop_deep)))
                self.token_list.pop_sym("}")
                continue
            if t.is_reserved and t.value in ("break", "continue"):
                if loop_deep == 0:
                    t.syntax_err("循环外的%s" % t.value)
                stmt_list.append(_Stmt(t.value))
                self.token_list.pop_sym(";")
                continue
            if t.is_reserved("return"):
                stmt_list.append(_Stmt("return", expr = self._parse_return(var_map_stk)))
                continue
            if t.is_reserved("for"):
                for_var_map, init_expr_list, judge_expr, loop_expr_list, closure_def_map = self._parse_for_prefix(var_map_stk)
                self.token_list.pop_sym("{")
                for_stmt_list = self.parse(var_map_stk + (for_var_map.copy(),), loop_deep + 1)
                self.token_list.pop_sym("}")
                stmt_list.append(_Stmt("for", for_var_map = for_var_map, init_expr_list = init_expr_list, judge_expr = judge_expr,
                                       loop_expr_list = loop_expr_list, closure_def_map = closure_def_map, stmt_list = for_stmt_list))
                continue
            if t.is_reserved("foreach"):
                var_tp, var_name, iter_expr = self._parse_foreach_prefix(var_map_stk)
                foreach_var_map = larc_common.OrderedDict()
                foreach_var_map[var_name] = var_tp
                self.token_list.pop_sym("{")
                foreach_stmt_list = self.parse(var_map_stk + (foreach_var_map,), loop_deep + 1)
                self.token_list.pop_sym("}")
                stmt_list.append(_Stmt("foreach", var_tp = var_tp, var_name = var_name, iter_expr = iter_expr, stmt_list = foreach_stmt_list))
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
            if t.is_reserved("var"):
                while True:
                    tp, name, expr, end_sym = self._parse_var(None, var_map_stk)
                    stmt_list.append(_Stmt("var", name = name, expr = expr))
                    if end_sym == ";":
                        break
                    assert end_sym == ","
                continue
            if t.is_reserved("defer"):
                expr = self.expr_parser.parse(var_map_stk, None)
                if expr.op not in ("call_method", "call_func"):
                    t.syntax_err("defer表达式必须是一个函数或方法调用")
                stmt_list.append(_Stmt("defer_expr", expr = expr))
                self.token_list.pop_sym(";")
                continue
            if t.is_native_code:
                stmt_list.append(_Stmt("native_code", native_code = larc_module.NativeCode(self.module, self.file_name, self.gtp_map, t),
                                       fom = self.fom))
                continue
            if t.is_reserved("else"):
                t.syntax_err("未匹配if的else")

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

    def _parse_var(self, var_tp, var_map_stk):
        t, name = self.token_list.pop_name()
        self._check_var_redefine(t, name, var_map_stk)
        var_map_stk[-1][name] = None #先将其设置到var_map，因为下面解析初始化的表达式流程可能需要用到
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
                #需要考虑表达式为ref参数的问题
                tp = copy.deepcopy(expr.type)
                tp.is_ref = False
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
        if t.is_sym(",") and self.token_list.peek().is_sym(";"):
            #允许最后一个变量定义也以逗号结尾
            t = self.token_list.pop()
        return tp, name, expr, t.value

    def _is_valid_expr_stmt(self, expr):
        if expr.op == "if-else":
            e_cond, ea, eb = expr.arg
            return self._is_valid_expr_stmt(ea) and self._is_valid_expr_stmt(eb)
        return isinstance(expr, _SeExpr) or expr.op in ("new", "call_array.method", "call_method", "call_func")

    def _check_valid_expr_stmt(self, t, expr):
        if not self._is_valid_expr_stmt(expr):
            t.syntax_err("表达式求值后未使用")

    def _check_var_redefine(self, t, name, var_map_stk):
        check_var_redefine(t, name, var_map_stk, self.module, self.dep_module_map, self.gtp_map)

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
        closure_def_pos = 0
        closure_def_map = {} #记录解析过程中遇到的closure的定义，{pos: [closure, ...]}
        def new_closure_hook(closure):
            if closure_def_pos not in closure_def_map:
                closure_def_map[closure_def_pos] = []
            closure_def_map[closure_def_pos].append(closure)
        self.expr_parser.push_new_closure_hook(new_closure_hook)
        if self.token_list.peek().is_reserved("var"):
            #第一部分为var变量定义
            self.token_list.pop()
            while True:
                _, _, expr, end_sym = self._parse_var(None, var_map_stk + (for_var_map,))
                init_expr_list.append(expr)
                closure_def_pos += 1
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
                    closure_def_pos += 1
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

        self.expr_parser.pop_new_closure_hook()

        return for_var_map, init_expr_list, judge_expr, loop_expr_list, closure_def_map

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
            if not lvalue.type.is_integer_type:
                t.syntax_err("类型'%s'无法做运算'%s'" % (lvalue.type, op))
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

    def _eval_ccc_if(self, var_map_stk, ccc_if_token_list):
        def parse_type():
            t = ccc_if_token_list.peek()
            tp = larc_type.try_parse_type(ccc_if_token_list, self.module, self.dep_module_map, self.gtp_map, var_map_stk)
            if tp is None:
                t.syntax_err("需要类型")
            return t, tp
        t = ccc_if_token_list.pop()
        if t.is_ccc_func_name:
            ccc_func_name = t.value
            if ccc_func_name in ("typein", "typeimplements", "typeisprimitive", "typeisarray"):
                ccc_if_token_list.pop_sym("(")
                t, tp_arg = parse_type()
                if ccc_func_name == "typein":
                    ccc_if_token_list.pop_sym(",")
                    ccc_if_token_list.pop_sym("{")
                    result = False
                    while True:
                        if ccc_if_token_list.peek().is_sym("}"):
                            ccc_if_token_list.pop_sym("}")
                            break
                        _, tp = parse_type()
                        if tp_arg == tp:
                            result = True
                        t = ccc_if_token_list.peek()
                        if not (t.is_sym("}") or t.is_sym(",")):
                            t.syntax_err("需要‘}’或‘,’")
                        if t.is_sym(","):
                            ccc_if_token_list.pop_sym(",")
                elif ccc_func_name == "typeimplements":
                    ccc_if_token_list.pop_sym(",")
                    t, intf_tp = parse_type()
                    is_intf = False
                    if intf_tp.is_coi_type:
                        intf_coi = intf_tp.get_coi()
                        if intf_coi.is_intf or intf_coi.is_gintf_inst:
                            is_intf = True
                    if not is_intf:
                        t.syntax_err("需要接口类型")
                    result = intf_tp.can_convert_from(tp_arg)
                elif ccc_func_name == "typeisprimitive":
                    result = tp_arg.is_primitive
                elif ccc_func_name == "typeisarray":
                    result = tp_arg.is_array
                else:
                    raise Exception("Bug")
                ccc_if_token_list.pop_sym(")")
                return result
            t.syntax_err("非法的#if函数名")
        t.syntax_err("需要#if函数名")

def check_var_redefine(t, name, var_map_stk, module, dep_module_map, gtp_map, is_arg = False):
    if name in dep_module_map:
        t.syntax_err("变量名和导入模块重名")
    if name in var_map_stk[-1]:
        t.syntax_err("变量名重定义")
    for var_map in var_map_stk[: -1]:
        if name in var_map:
            t.syntax_err("与上层的变量名冲突")
    if gtp_map is not None and name in gtp_map:
        t.syntax_err("变量名与泛型参数名冲突")
    for m in module, larc_module.builtins_module:
        elem = m.get_elem(name, public_only = m is not module and m is larc_module.builtins_module)
        if elem is not None:
            t.syntax_err("%s名与'%s'名字冲突" % ("参数" if is_arg else "变量", elem))
