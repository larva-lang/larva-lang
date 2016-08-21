#coding=utf8

"""
编译larva语句
"""

import larc_common
import larc_token
import larc_expr

def _parse_var_init_expr_token_list(token_list):
    return larc_token.parse_token_list_until_sym(token_list, (";", ","))

def parse_var_name(token_list):
    t = token_list.pop()
    if t.is_sym("("):
        vn_list = []
        while True:
            vn = parse_var_name(token_list)
            vn_list.append(vn)
            t, sym = token_list.pop_sym()
            if len(vn_list) > 1 and sym == ")":
                return tuple(vn_list)
            if sym != ",":
                t.syntax_err("需要','")
            if token_list.peek().is_sym(")"):
                token_list.pop_sym(")")
                return tuple(vn_list)
    if t.is_name:
        return t.value
    syntax_err("需要变量名定义")

def iter_var_name(var_name):
    if isinstance(var_name, str):
        yield var_name
        return

    assert isinstance(var_name, tuple)
    for each_vn in var_name:
        for vn in iter_var_name(each_vn):
            yield vn

def parse_var_define(token_list, module, cls, var_set_list, non_local_var_used_map, ret_expr_token_list = False):
    while True:
        start_t = token_list.peek()
        var_name = parse_var_name(token_list)
        t, sym = token_list.pop_sym()
        if not isinstance(var_name, str) or sym == "=":
            if ret_expr_token_list:
                expr, sym = _parse_var_init_expr_token_list(token_list)
            else:
                expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True)
                t, sym = token_list.pop_sym()
        else:
            expr = None
        yield start_t, var_name, expr
        if sym == ";":
            return
        if sym != ",":
            t.syntax_err("需要','或';'")

class _Stmt:
    def __init__(self, type, **kw_arg):
        self.type = type
        for k, v in kw_arg.iteritems():
            setattr(self, k, v)

class _StmtList(list):
    def __init__(self, var_set):
        list.__init__(self)
        self.var_set = var_set

def _parse_for_prefix(token_list, module, cls, var_set_list, non_local_var_used_map):
    token_list.pop_sym("(")
    for_var_set = larc_common.OrderedSet()
    if token_list.peek().is_reserved("var"):
        token_list.pop()
        t = token_list.peek()
        var_name = parse_var_name(token_list)
        for vn in iter_var_name(var_name):
            if vn in module.dep_module_set:
                t.syntax_err("变量名'%s'与导入模块重名" % vn)
            for var_set in var_set_list + (for_var_set,):
                if vn in var_set:
                    t.syntax_err("变量名'%s'重定义" % vn)
            for_var_set.add(vn)
        lvalue = var_name
    else:
        lvalue = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
    token_list.pop_sym(":")
    iter_obj = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
    token_list.pop_sym(")")
    return for_var_set, lvalue, iter_obj

def parse_stmt_list(token_list, module, cls, var_set_list, loop_deep):
    assert var_set_list
    stmt_list = _StmtList(var_set_list[-1])
    non_local_var_used_map = larc_common.OrderedDict()
    while token_list:
        if token_list.peek().is_sym("}"):
            break

        #解析语句
        t = token_list.pop()
        if t.is_sym(";"):
            t.warning("空语句")
            continue
        if t.is_sym("{"):
            stmt = _Stmt("block", stmt_list = parse_stmt_list(token_list, module, cls, var_set_list + (larc_common.OrderedSet(),), loop_deep))
            token_list.pop_sym("}")
            stmt_list.append(stmt)
            continue
        if t.is_reserved("var"):
            def add_to_curr_var_set(t, vn):
                if vn in module.dep_module_set:
                    t.syntax_err("变量名'%s'与导入模块重名" % vn)
                for var_set in var_set_list:
                    if vn in var_set:
                        t.syntax_err("变量名'%s'重定义" % vn)
                if vn in non_local_var_used_map:
                    non_local_var_used_map[vn].syntax_err("局部变量在定义之前使用")
                var_set_list[-1].add(vn)
            for t, var_name, expr in parse_var_define(token_list, module, cls, var_set_list, non_local_var_used_map):
                for vn in iter_var_name(var_name):
                    add_to_curr_var_set(t, vn)
                stmt_list.append(_Stmt("var", name = var_name, expr = expr))
            continue
        if t.is_reserved and t.value in ("break", "continue"):
            if loop_deep == 0:
                t.syntax_err("循环外的'%s'" % t.value)
            token_list.pop_sym(";")
            stmt_list.append(_Stmt(t.value))
            continue
        if t.is_reserved("return"):
            expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
            token_list.pop_sym(";")
            stmt_list.append(_Stmt("return", expr = expr))
            continue
        if t.is_reserved("for"):
            for_var_set, lvalue, iter_obj = _parse_for_prefix(token_list, module, cls, var_set_list, non_local_var_used_map)
            token_list.pop_sym("{")
            for_stmt_list = parse_stmt_list(token_list, module, cls, var_set_list + (for_var_set.copy(),), loop_deep + 1)
            token_list.pop_sym("}")
            stmt_list.append(_Stmt("for", var_set = for_var_set, lvalue = lvalue, iter_obj = iter_obj, stmt_list = for_stmt_list))
            continue
        if t.is_reserved("while"):
            token_list.pop_sym("(")
            expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
            token_list.pop_sym(")")
            token_list.pop_sym("{")
            while_stmt_list = parse_stmt_list(token_list, module, cls, var_set_list + (larc_common.OrderedDict(),), loop_deep + 1)
            token_list.pop_sym("}")
            stmt_list.append(_Stmt("while", expr = expr, stmt_list = while_stmt_list))
            continue
        if t.is_reserved("do"):
            token_list.pop_sym("{")
            do_stmt_list = parse_stmt_list(token_list, module, cls, var_set_list + (larc_common.OrderedDict(),), loop_deep + 1)
            token_list.pop_sym("}")
            t = token_list.pop()
            if not t.is_reserved("while"):
                t.syntax_err("需要'while'")
            token_list.pop_sym("(")
            expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
            token_list.pop_sym(")")
            token_list.pop_sym(";")
            stmt_list.append(_Stmt("do", expr = expr, stmt_list = do_stmt_list))
            continue
        if t.is_reserved("if"):
            if_expr_list = []
            if_stmt_list_list = []
            else_stmt_list = None
            while True:
                token_list.pop_sym("(")
                expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
                token_list.pop_sym(")")
                token_list.pop_sym("{")
                if_stmt_list = parse_stmt_list(token_list, module, cls, var_set_list + (larc_common.OrderedDict(),), loop_deep)
                token_list.pop_sym("}")
                if_expr_list.append(expr)
                if_stmt_list_list.append(if_stmt_list)
                if not token_list.peek().is_reserved("else"):
                    break
                token_list.pop()
                t = token_list.pop()
                if t.is_reserved("if"):
                    continue
                if not t.is_sym("{"):
                    t.syntax_err("需要'{'")
                else_stmt_list = parse_stmt_list(token_list, module, cls, var_set_list + (larc_common.OrderedDict(),), loop_deep)
                token_list.pop_sym("}")
                break
            stmt_list.append(_Stmt("if", if_expr_list = if_expr_list, if_stmt_list_list = if_stmt_list_list, else_stmt_list = else_stmt_list))
            continue
        if t.is_sym and t.value in larc_token.INC_DEC_SYM_SET:
            inc_dec_op = t.value
            t = token_list.peek()
            lvalue = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
            if not lvalue.is_lvalue:
                t.syntax_err("非左值表达式不能做'%s'操作" % inc_dec_op)
            if lvalue.op in ("[:]", "tuple", "list"):
                t.syntax_err("分片和解包左值表达式不能做'%s'操作" % inc_dec_op)
            stmt_list.append(_Stmt(inc_dec_op, lvalue = lvalue))
            continue
        #todo: try catch finally throw assert

        #剩下的就是表达式和赋值了
        token_list.revert()
        expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
        if token_list.peek().is_sym(";"):
            #表达式
            token_list.pop_sym(";")
            stmt_list.append(_Stmt("expr", expr = expr))
            continue

        t = token_list.peek()
        if t.is_sym and t.value in larc_token.ASSIGN_SYM_SET:
            #赋值
            assign_sym = t.value
            lvalue = expr
            if not lvalue.is_lvalue:
                t.syntax_err("赋值操作'%s'左边非左值表达式" % assign_sym)
            if assign_sym != "=":
                #增量赋值
                if lvalue.op in ("[:]", "tuple", "list"):
                    t.syntax_err("分片和解包左值表达式无法增量赋值")
            token_list.pop_sym(assign_sym)
            expr = larc_expr.parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map)
            token_list.pop_sym(";")
            stmt_list.append(_Stmt(assign_sym, lvalue = lvalue, expr = expr))
            continue

        t.syntax_err()

    return stmt_list
