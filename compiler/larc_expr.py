#coding=utf8

"""
编译larva表达式
"""

import larc_common
import larc_token
import larc_module
import larc_stmt

_UNARY_OP_SET = set(["~", "!", "neg", "pos"])
_BINOCULAR_OP_SET = larc_token.BINOCULAR_OP_SYM_SET
_OP_PRIORITY_LIST = [["?", ":", "?:"],
                     ["||"],
                     ["&&"],
                     ["==", "!=", "<", "<=", ">", ">="],
                     ["|"],
                     ["^"],
                     ["&"],
                     ["<<", ">>"],
                     ["+", "-"],
                     ["*", "/", "%"],
                     ["~", "!", "neg", "pos"]]
_OP_PRIORITY_MAP = {}
for _i in xrange(len(_OP_PRIORITY_LIST)):
    for _op in _OP_PRIORITY_LIST[_i]:
        _OP_PRIORITY_MAP[_op] = _i
del _i
del _op

def _is_expr_end(t):
    if t.is_sym:
        if t.value in set([")", "]", "}", ":", ",", ";"]) | larc_token.ASSIGN_SYM_SET:
            return True
    if t.is_reserved and t.value in ("for", "if"):
        return True
    return False

class _Expr:
    def __init__(self, op, arg):
        self.op = op
        self.arg = arg
        if op in ("this.attr", "global_var", "local_var", "[]", "[:]", "."):
            self.is_lvalue = True
        elif op == "tuple":
            if self.arg:
                self.is_lvalue = True
                for e in self.arg:
                    if not e.is_lvalue:
                        self.is_lvalue = False
                        break
            else:
                self.is_lvalue = False
        else:
            self.is_lvalue = False

class _ParseStk:
    #解析表达式时使用的栈
    def __init__(self, start_token, module, cls):
        self.start_token = start_token
        self.module = module
        self.cls = cls
        self.stk = []
        self.op_stk = []

    def push_op(self, op):
        #弹出所有优先级高的运算
        while self.op_stk:
            if _OP_PRIORITY_MAP[self.op_stk[-1]] > _OP_PRIORITY_MAP[op]:
                self._pop_top_op()
            elif _OP_PRIORITY_MAP[self.op_stk[-1]] < _OP_PRIORITY_MAP[op]:
                break
            else:
                #同优先级看结合性
                if op in _UNARY_OP_SET or op in ("?", ":"):
                    #单目、三目运算符右结合
                    break
                self._pop_top_op()
        if op == ":":
            if not self.op_stk or self.op_stk[-1] != "?":
                self.start_token.syntax_err("非法的表达式，存在未匹配'?'的':'")
            self.op_stk[-1] = "?:"
            return
        self.op_stk.append(op)

    def _pop_top_op(self):
        op = self.op_stk.pop()
        if op in _UNARY_OP_SET:
            #单目运算符
            if len(self.stk) < 1:
                self.start_token.syntax_err("非法的表达式")
            e = self.stk.pop()
            self.stk.append(_Expr(op, [e]))
        elif op in _BINOCULAR_OP_SET:
            #双目运算符
            if len(self.stk) < 2:
                self.start_token.syntax_err("非法的表达式")
            eb = self.stk.pop()
            ea = self.stk.pop()
            self.stk.append(_Expr(op, [ea, eb]))
        elif op == "?":
            self.start_token.syntax_err("非法的表达式，存在未匹配':'的'?'")
        elif op == "?:":
            #三目运算符
            if len(self.stk) < 3:
                self.start_token.syntax_err("非法的表达式")
            ec = self.stk.pop()
            eb = self.stk.pop()
            ea = self.stk.pop()
            self.stk.append(_Expr(op, [ea, eb, ec]))
        else:
            raise Exception("Bug")

    def push_expr(self, e):
        self.stk.append(e)

    def finish(self):
        while self.op_stk:
            self._pop_top_op()
        if len(self.stk) != 1:
            self.start_token.syntax_err("非法的表达式")
        return self.stk.pop()

def _parse_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map, end_sym):
    if token_list.peek().is_sym(end_sym):
        #空列表
        token_list.pop_sym(end_sym)
        return []
    expr_list = []
    while True:
        expr_list.append(parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True))
        t = token_list.pop()
        if t.is_sym(end_sym):
            return expr_list
        if t.is_sym(","):
            continue
        t.syntax_err("需要','或'%s'" % end_sym)

def _parse_dict_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map):
    if token_list.peek().is_sym("}"):
        #空字典
        token_list.pop_sym("}")
        return []
    expr_list = []
    while True:
        ek = parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True)
        token_list.pop_sym(":")
        ev = parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True)
        expr_list.append((ek, ev))
        t = token_list.pop()
        if t.is_sym("}"):
            return expr_list
        if t.is_sym(","):
            continue
        t.syntax_err("需要','或'}'")

def _parse_method_or_attr_of_this_cls((t, name), token_list, module, cls, var_set_list, non_local_var_used_map):
    if cls.has_attr(name):
        return _Expr("this.attr", name)

    if not cls.has_method(name):
        t.syntax_err("类'%s'没有属性或方法'%s'" % (cls, name))

    token_list.pop_sym("(")
    expr_list = _parse_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map, ")")
    if not cls.has_method(name, len(expr_list)):
        t.syntax_err("类'%s'没有方法'%s(...%d args)'" % (cls, name, len(expr_list)))
    return _Expr("call_this.method", (cls.get_method(name, len(expr_list)), expr_list))

def _parse_global_elem(m, (t, name), token_list, module, cls, var_set_list, non_local_var_used_map):
    if m.has_global_var(name):
        return _Expr("global_var", m.get_global_var(name))

    if not m.has_cls(name) and not m.has_func(name):
        t.syntax_err("模块'%s'没有名为'%s'的类、函数或全局变量" % (m, name))

    token_list.pop_sym("(")
    expr_list = _parse_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map, ")")
    if m.has_func(name):
        if not m.has_func(name, len(expr_list)):
            t.syntax_err("模块'%s'没有方法'%s(...%d args)'" % (m, name, len(expr_list)))
        return _Expr("call_func", (m.get_func(name, len(expr_list)), expr_list))

    callee_cls = m.get_cls(name)
    if not callee_cls.has_method("__init", len(expr_list)):
        t.syntax_err("类'%s'没有构造方法'__init(...%d args)'" % (callee_cls, len(expr_list)))
    return _Expr("new", (callee_cls, expr_list))

def _parse_compr(token_list, module, cls, var_set_list, non_local_var_used_map, end_sym):
    assert token_list.pop().is_reserved("for")
    for_var_set, lvalue, iter_obj = larc_stmt.parse_for_prefix(token_list, module, cls, var_set_list, non_local_var_used_map)
    token_list.pop_sym(end_sym)
    return [for_var_set, lvalue, iter_obj]

def parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = False):
    parse_stk = _ParseStk(token_list.peek(), module, cls)
    while True:
        #状态：等待表达式的开始
        #包括单目运算、名字、常量、tuple、list、dict、圆括号开头的子表达式等
        t = token_list.pop()
        if t.is_sym and t.value in ("~", "!", "+", "-"):
            #单目运算
            parse_stk.push_op({"+" : "pos", "-" : "neg"}.get(t.value, t.value))
            continue

        if t.is_sym("("):
            if token_list.peek().is_sym(")"):
                #空元组
                token_list.pop_sym(")")
                parse_stk.push_expr(_Expr("tuple", []))
            else:
                #子表达式开始，使用递归解析
                parse_stk.push_expr(parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map))
                token_list.pop_sym(")")
        elif t.is_sym("["):
            #列表
            if token_list.peek().is_sym("]"):
                token_list.pop_sym("]")
                parse_stk.push_expr(_Expr("list", []))
            else:
                #先解析一个表达式
                idx = token_list.i
                e = parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True)
                t = token_list.peek()
                if t.is_sym(",") or t.is_sym("]"):
                    #正常列表
                    token_list.revert(idx)
                    parse_stk.push_expr(_Expr("list", _parse_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map, "]")))
                elif t.is_reserved("for"):
                    #列表解析式
                    parse_stk.push_expr(_Expr("list_compr",
                                              [e] + _parse_compr(token_list, module, cls, var_set_list, non_local_var_used_map, "]")))
                else:
                    t.syntax_err("需要','、']'或'for'")
        elif t.is_sym("{"):
            #字典
            if token_list.peek().is_sym("}"):
                token_list.pop()
                parse_stk.push_expr(_Expr("dict", []))
            else:
                #先解析一对键值
                idx = token_list.i
                ek = parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True)
                token_list.pop_sym(":")
                ev = parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True)
                t = token_list.peek()
                if t.is_sym(",") or t.is_sym("}"):
                    #正常字典
                    token_list.revert(idx)
                    parse_stk.push_expr(_Expr("dict", _parse_dict_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map)))
                elif t.is_for:
                    #字典解析式
                    parse_stk.push_expr(_Expr("dict_compr",
                                              [ek, ev] + _parse_compr(token_list, module, cls, var_set_list, non_local_var_used_map, "}")))
                else:
                    t.syntax_err("需要','、'}'或'for'")
        elif t.is_name:
            if t.value in module.dep_module_set:
                m = larc_module.module_map[t.value]
                token_list.pop_sym(".")
                t, name = token_list.pop_name()
                expr = _parse_global_elem(m, (t, name), token_list, module, cls, var_set_list, non_local_var_used_map)
                parse_stk.push_expr(expr)
            else:
                for var_set in var_set_list:
                    if t.value in var_set:
                        #局部变量
                        parse_stk.push_expr(_Expr("local_var", t.value))
                        break
                else:
                    if t.value not in non_local_var_used_map:
                        non_local_var_used_map[t.value] = t #记录一下使用过的非局部变量的名字使用
                    if cls is not None and (cls.has_attr(t.value) or cls.has_method(t.value)):
                        #类方法或属性
                        expr = _parse_method_or_attr_of_this_cls((t, t.value), token_list, module, cls, var_set_list, non_local_var_used_map)
                        parse_stk.push_expr(expr)
                    else:
                        #当前模块或内建模块的全局元素
                        for m in (module, larc_module.module_map["__builtins"]):
                            if m.has_cls(t.value) or m.has_func(t.value) or m.has_global_var(t.value):
                                expr = _parse_global_elem(m, (t, t.value), token_list, module, cls, var_set_list, non_local_var_used_map)
                                parse_stk.push_expr(expr)
                                break
                        else:
                            t.syntax_err("未定义的标识符'%s'" % t.value)
        elif t.is_literal:
            assert t.type.startswith("literal_")
            module.literal_set.add(t)
            parse_stk.push_expr(_Expr("literal", t))
        elif t.is_reserved("this"):
            if cls is None:
                t.syntax_err("'this'只能用于成员函数中")
            if token_list.peek().is_sym("."):
                token_list.pop_sym(".")
                t, name = token_list.pop_name()
                expr = _parse_method_or_attr_of_this_cls((t, name), token_list, module, cls, var_set_list, non_local_var_used_map)
                parse_stk.push_expr(expr)
            else:
                #单独的this
                parse_stk.push_expr(_Expr(t.value, t))
        else:
            t.syntax_err("非法的表达式")

        assert parse_stk.stk

        #状态：解析后缀运算
        while True:
            t = token_list.pop()
            if t.is_sym("["):
                #下标或分片操作
                el = []
                while True:
                    t = token_list.peek()
                    if t.is_sym("]"):
                        el.append(None)
                        break
                    if t.is_sym(":"):
                        el.append(None)
                        token_list.pop_sym(":")
                        continue
                    el.append(parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True))
                    t = token_list.peek()
                    if t.is_sym("]"):
                        break
                    if t.is_sym(":"):
                        token_list.pop_sym(":")
                        continue
                    t.syntax_err("需要']'或':'")
                token_list.pop_sym("]")
                assert len(el) > 0
                if len(el) == 1:
                    #下标操作
                    if el[0] is None:
                        t.syntax_err("空下标")
                    parse_stk.stk[-1] = _Expr("[]", [parse_stk.stk[-1], el[0]])
                else:
                    #分片操作
                    if len(el) == 2:
                        el.append(None)
                    if len(el) > 3:
                        t.syntax_err("分片最多只能三个参数")
                    parse_stk.stk[-1] = _Expr("[:]", [parse_stk.stk[-1], el])
            elif t.is_sym("."):
                t, name = token_list.pop_name()
                if token_list.peek().is_sym("("):
                    token_list.pop_sym("(")
                    expr_list = _parse_expr_list(token_list, module, cls, var_set_list, non_local_var_used_map, ")")
                    parse_stk.stk[-1] = _Expr("call_method", [parse_stk.stk[-1], t, expr_list])
                else:
                    parse_stk.stk[-1] = _Expr(".", [parse_stk.stk[-1], t])
            else:
                token_list.revert()
                break

        if token_list.peek().is_sym(","):
            if end_at_comma:
                #没有在解析元组
                break
            #解析元组
            token_list.pop()
            arg_list = [parse_stk.finish()]
            while True:
                #循环解析元组各项
                t = token_list.peek()
                if t.is_sym(","):
                    #出现连续两个逗号
                    t.syntax_err("需要表达式")
                if _is_expr_end(t):
                    #元组解析结束
                    break
                arg_list.append(parse_expr(token_list, module, cls, var_set_list, non_local_var_used_map, end_at_comma = True))
                #接下来应该是逗号或表达式结束
                t = token_list.peek()
                if t.is_sym(","):
                    #后续可能还有
                    token_list.pop()
                    continue
                if _is_expr_end(t):
                    #元组结束
                    break
                t.syntax_err("非法的元组")
            parse_stk.push_expr(_Expr("tuple", arg_list))

        t = token_list.peek()
        if _is_expr_end(t) and (not t.is_sym(":") or "?" not in parse_stk.op_stk):
            #表达式结束
            break

        #状态：解析普通二元/三元运算符
        t = token_list.pop()
        if t.is_sym and t.value in _BINOCULAR_OP_SET | set(["?", ":"]):
            #二元运算
            parse_stk.push_op(t.value)
        else:
            t.syntax_err("需要二元或三元运算符")

    return parse_stk.finish()

def var_name_to_expr(var_name):
    if isinstance(var_name, str):
        return _Expr("local_var", var_name)

    assert isinstance(var_name, tuple)
    return _Expr("tuple", [var_name_to_expr(vn) for vn in var_name])
