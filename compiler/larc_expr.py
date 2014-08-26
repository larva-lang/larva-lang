#coding=utf8

"""
编译larva表达式
"""

import larc_builtin

_UNARY_OP_SET = set(["~", "not", "neg", "pos"])
_BINOCULAR_OP_SET = set(["%", "^", "&", "*", "-", "+", "|", "<", ">", "/",
                         "!=", "and", "==", "or", "<<", "<=", ">>", ">>>",
                         ">=", "in", "not in"])
"""
运算优先级相关的若干说明：

没有实现**运算，原因有几点：
1 **是唯一一个右结合的二元运算符，且不常用，容易产生歧义
2 **和单目运算的优先级关系较为复杂，跟单目运算符的左右位置有关
  即如-a**b相当于-(a**b)，而a**-b相当于a**(-b)，一来容易搞混，二来编译实现麻烦
3 整数的幂运算一般来说都是比较大的数字，因此定义为一个输入可以是int或long，
  输出统一为long的pow函数可能更合适些

not、位运算的优先级和py一致，但是和java、C都有区别，编译时not需做特殊处理

[]（下标），()（调用），.（属性），list（构造list），dict（构造dict）等运算的
优先级最高，解析时做特殊处理，不进入这个表
"""
_OP_PRIORITY_LIST = [["or"],
                     ["and"],
                     ["not"],
                     ["==", "!=", "<", "<=", ">", ">=", "in", "not in"],
                     ["|"],
                     ["^"],
                     ["&"],
                     ["<<", ">>", ">>>"],
                     ["+", "-"],
                     ["*", "/", "%"],
                     ["~", "neg", "pos"]]
_OP_PRIORITY_MAP = {}
for _i in xrange(len(_OP_PRIORITY_LIST)):
    for _op in _OP_PRIORITY_LIST[_i]:
        _OP_PRIORITY_MAP[_op] = _i
del _i
del _op

def _is_expr_end(t):
    if t.is_indent:
        return True
    if t.is_sym:
        if t.value in "=)]}:,":
            return True
        if t.value in ("%=", "^=", "&=", "*=", "-=", "+=", "|=", "/=",
                       "<<=", ">>=", ">>>="):
            return True
    if t.is_for or t.is_if:
        return True
    return False

class _Expr:
    def __init__(self, op, arg):
        self.op = op
        self.arg = arg
        if op in ("name", ".", "[]", "[:]"):
            self.is_lvalue = True
        elif op in ("tuple", "list"):
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

    def link(self, curr_module, module_map, local_var_set = None):
        self._link(curr_module, module_map, local_var_set)
        self._check()

    def _link(self, curr_module, module_map, local_var_set):
        """链接表达式，主要做：
           1 所有name转成对应名字空间
           2 对于函数调用运算，改变expr形式
           3 对于方法调用运算，改变expr形式
           4 对于外部模块的"."运算，视情况改变形式
           5 常量表"""
        if self.op == "const":
            for const_type in "float", "long", "int", "str", "byte":
                if getattr(self.arg, "is_" + const_type):
                    const_key = const_type, self.arg.value
                    if const_key in curr_module.const_map:
                        const_idx = curr_module.const_map[const_key]
                    else:
                        const_idx = len(curr_module.const_map)
                        curr_module.const_map[const_key] = const_idx
                    self.op = "const_idx"
                    self.arg = const_idx
                    return
            assert self.arg.is_true or self.arg.is_false or self.arg.is_nil
            return
        if self.op == "name":
            name = self.arg.value
            #由内而外找名字空间
            if local_var_set is not None and name in local_var_set:
                self.op = "local_name"
                return
            if name in curr_module.global_var_map:
                self.op = "global_name"
                return
            if name in curr_module.func_name_set:
                self.op = "func_name"
                return
            if name in curr_module.dep_module_set:
                self.op = "module_name"
                return
            if name in larc_builtin.builtin_if_name_set:
                self.op = "builtin_if_name"
                return
            self.arg.syntax_err("找不到名字'%s'" % name)
        if self.op == "dict":
            for ek, ev in self.arg:
                ek._link(curr_module, module_map, local_var_set)
                ev._link(curr_module, module_map, local_var_set)
            return
        if self.op == "()":
            ec, el = self.arg
            ec._link(curr_module, module_map, local_var_set)
            for e in el:
                e._link(curr_module, module_map, local_var_set)
            if ec.op == "func_name":
                #模块内函数调用，需检查参数匹配情况
                func_key = ec.arg.value, len(el)
                if func_key not in curr_module.func_map:
                    ec.arg.syntax_err("找不到匹配的函数：%d个参数的'%s'" %
                                      (len(el), ec.arg.value))
                self.op = "call_func"
                self.arg = [ec.arg, el]
                return
            if ec.op == "builtin_if_name":
                #内置函数（或类）调用，检查参数匹配情况
                builtin_if_key = ec.arg.value, len(el)
                if builtin_if_key not in larc_builtin.builtin_if_set:
                    ec.arg.syntax_err("找不到匹配的内置接口：%d个参数的'%s'" %
                                      (len(el), ec.arg.value))
                self.op = "call_builtin_if"
                self.arg = [ec.arg, el]
                return
            if ec.op == ".":
                #方法调用，或属性的()运算，不做区分
                self.op = "call_method"
                self.arg = ec.arg + [el]
                return
            if ec.op == "module.func":
                #外部函数调用，检查参数匹配情况
                module = module_map[ec.arg[0].value]
                func_key = ec.arg[1].value, len(el)
                if func_key not in module.func_map:
                    ec.arg[1].syntax_err(
                        "模块'%s'中找不到匹配的函数：%d个参数的'%s'" %
                        (module.name, len(el), ec.arg[1].value))
                self.op = "call_module_func"
                self.arg = ec.arg + [el]
                return
            #其余情况，属于对象的()运算
            return
        if self.op == ".":
            e, attr = self.arg
            e._link(curr_module, module_map, local_var_set)
            if e.op == "module_name":
                #引用其他模块的内容
                module = module_map[e.arg.value]
                if attr.value in module.global_var_map:
                    self.op = "module.global"
                elif attr.value in module.func_name_set:
                    self.op = "module.func"
                else:
                    attr.syntax_err("模块'%s'没有'%s'" %
                                    (e.arg.value, attr.value))
                self.arg = [e.arg, attr]
                return
            #其余情况，属于对象的"."运算
            return
        if self.op == "[:]":
            eo, el = self.arg
            eo._link(curr_module, module_map, local_var_set)
            for e in el:
                if e is not None:
                    e._link(curr_module, module_map, local_var_set)
            return
        if self.op == "list_compr":
            e, lvalue, name_set, expr, if_expr = self.arg
            expr._link(curr_module, module_map, local_var_set)
            assert lvalue.op in ("name", "tuple", "list")
            if local_var_set is None:
                compr_local_var_set = name_set
            else:
                compr_local_var_set = local_var_set | name_set
            e._link(curr_module, module_map, compr_local_var_set)
            lvalue._link(curr_module, module_map, compr_local_var_set)
            if if_expr is not None:
                if_expr._link(curr_module, module_map, compr_local_var_set)
            self.arg = [expr, compr_local_var_set, e, lvalue, name_set,
                        if_expr]
            return
        if self.op == "dict_compr":
            ek, ev, lvalue, name_set, expr, if_expr = self.arg
            expr._link(curr_module, module_map, local_var_set)
            assert lvalue.op in ("name", "tuple", "list")
            if local_var_set is None:
                compr_local_var_set = name_set
            else:
                compr_local_var_set = local_var_set | name_set
            ek._link(curr_module, module_map, compr_local_var_set)
            ev._link(curr_module, module_map, compr_local_var_set)
            lvalue._link(curr_module, module_map, compr_local_var_set)
            if if_expr is not None:
                if_expr._link(curr_module, module_map, compr_local_var_set)
            self.arg = [expr, compr_local_var_set, ek, ev, lvalue, name_set,
                        if_expr]
            return
        if self.op == "lambda":
            arg_list, e = self.arg
            if local_var_set is None:
                lambda_local_var_set = set(arg_list)
            else:
                lambda_local_var_set = local_var_set | set(arg_list)
            e._link(curr_module, module_map, lambda_local_var_set)
            self.arg = [lambda_local_var_set, arg_list, e]
            return

        #其余类型，包括单目、双目运算、下标、tuple和list构造等
        assert (self.op in _UNARY_OP_SET or self.op in _BINOCULAR_OP_SET or
                self.op in ("[]", "tuple", "list")), self.op
        for e in self.arg:
            e._link(curr_module, module_map, local_var_set)

    def _check(self):
        #检查表达式
        if self.op in ("const", "const_idx", "local_name", "global_name",
                       "module.global"):
            return
        if self.op == "module_name":
            self.arg.syntax_err("模块名不能作为值")
        if self.op == "func_name":
            self.arg.syntax_err("函数名不能作为值")
        if self.op == "module.func":
            self.arg.syntax_err("外部函数不能作为值")
        if self.op == "builtin_if_name":
            self.arg.syntax_err("内置接口不能作为值")
        if self.op == "dict":
            for ek, ev in self.arg:
                ek._check()
                ev._check()
            return
        if self.op == "()":
            ec, el = self.arg
            ec._check()
            for e in el:
                e._check()
            return
        if self.op in ("call_func", "call_method", "call_module_func",
                       "call_builtin_if"):
            for e in self.arg[-1]:
                e._check()
            if self.op == "call_method":
                self.arg[0]._check()
            return
        if self.op == ".":
            self.arg[0]._check()
            return
        if self.op == "[:]":
            eo, el = self.arg
            eo._check()
            for e in el:
                if e is not None:
                    e._check()
            return
        if self.op == "list_compr":
            expr, compr_local_var_set, e, lvalue, name_set, if_expr = self.arg
            expr._check()
            e._check()
            lvalue._check()
            if if_expr is not None:
                if_expr._check()
            return
        if self.op == "dict_compr":
            expr, compr_local_var_set, ek, ev, lvalue, name_set, if_expr = (
                self.arg)
            expr._check()
            ek._check()
            ev._check()
            lvalue._check()
            if if_expr is not None:
                if_expr._check()
            return
        if self.op == "lambda":
            lambda_local_var_set, arg_list, e = self.arg
            e._check()
            return

        #其余类型，包括单目、双目运算、下标、tuple和list构造等
        assert (self.op in _UNARY_OP_SET or self.op in _BINOCULAR_OP_SET or
                self.op in ("[]", "tuple", "list")), self.op
        for e in self.arg:
            e._check()

class _ParseStk:
    #解析表达式时使用的栈
    def __init__(self, start_token):
        self.start_token = start_token
        self.stk = []
        self.op_stk = []

    def push_op(self, op):
        #弹出所有优先级高的运算
        while self.op_stk:
            if _OP_PRIORITY_MAP[self.op_stk[-1]] > _OP_PRIORITY_MAP[op]:
                #特殊处理单目运算符not
                if op == "not":
                    self.start_token.syntax_err("运算符'not'位置错误")
                self._pop_top_op()
            elif _OP_PRIORITY_MAP[self.op_stk[-1]] < _OP_PRIORITY_MAP[op]:
                break
            else:
                #同优先级看结合性
                if op in _UNARY_OP_SET:
                    #单目运算符右结合
                    break
                self._pop_top_op()
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
        else:
            raise Exception("unreachable")

    def push_expr(self, e):
        self.stk.append(e)

    def finish(self):
        while self.op_stk:
            self._pop_top_op()
        if len(self.stk) != 1:
            self.start_token.syntax_err("非法的表达式")
        return self.stk.pop()

def _parse_expr_list(token_list, end_sym):
    if token_list.peek().is_sym(end_sym):
        #空列表
        token_list.pop_sym(end_sym)
        return []
    expr_list = []
    while True:
        expr_list.append(parse_expr(token_list, True))
        t = token_list.pop()
        if t.is_sym(end_sym):
            return expr_list
        if t.is_sym(","):
            continue
        t.syntax_err("需要','或'%s'" % end_sym)

def _parse_compr(token_list, end_sym):
    assert token_list.pop().is_for
    t = token_list.peek()
    in_expr = parse_expr(token_list, True)
    if in_expr.op != "in":
        t.syntax_err("for语句中的非'in'表达式")
    lvalue, expr = in_expr.arg

    name_set = set()
    def _valid_lvalue(lvalue):
        #判断是否变量名或仅含变量名的unpack左值
        #同时收集变量名到name_set
        if lvalue.op == "name":
            name_set.add(lvalue.arg.value)
            return True
        if lvalue.op in ("tuple", "list"):
            for unpack_lvalue in lvalue.arg:
                if not _valid_lvalue(unpack_lvalue):
                    return False
            return True
        return False

    if not _valid_lvalue(lvalue):
        t.syntax_err("迭代元素必须是变量名或仅含变量名的unpack左值")

    t = token_list.pop()
    if t.is_if:
        if_expr = parse_expr(token_list, True)
        t = token_list.pop()
    else:
        if_expr = None
    if t.is_sym(end_sym):
        return [lvalue, name_set, expr, if_expr]
    t.syntax_err("需要'%s'" % end_sym)

def _parse_dict_expr_list(token_list):
    if token_list.peek().is_sym("}"):
        #空字典
        token_list.pop_sym("}")
        return []
    expr_list = []
    while True:
        ek = parse_expr(token_list, True)
        token_list.pop_sym(":")
        ev = parse_expr(token_list, True)
        expr_list.append((ek, ev))
        t = token_list.pop()
        if t.is_sym("}"):
            return expr_list
        if t.is_sym(","):
            continue
        t.syntax_err("需要','或'}'")

def parse_expr(token_list, end_at_comma = False):
    parse_stk = _ParseStk(token_list.peek())
    while True:
        #状态：等待表达式的开始
        #包括单目运算、名字、常量、tuple、list、dict、圆括号开头的子表达式等
        t = token_list.pop()
        if t.is_sym and t.value in "~+-" or t.is_not:
            #单目运算
            if t.value == "+":
                op = "pos"
            elif t.value == "-":
                op = "neg"
            else:
                op = t.value
            parse_stk.push_op(op)
            continue
        if t.is_sym("("):
            if token_list.peek().is_sym(")"):
                #空元组
                token_list.pop()
                parse_stk.push_expr(_Expr("tuple", []))
            else:
                #子表达式开始，使用递归解析
                parse_stk.push_expr(parse_expr(token_list))
                token_list.pop_sym(")")
        elif t.is_sym("["):
            #列表
            if token_list.peek().is_sym("]"):
                token_list.pop()
                parse_stk.push_expr(_Expr("list", []))
            else:
                #先解析一个表达式
                idx = token_list.i
                e = parse_expr(token_list, True)
                t = token_list.peek()
                if t.is_sym(",") or t.is_sym("]"):
                    #正常列表
                    token_list.revert(idx)
                    parse_stk.push_expr(
                        _Expr("list", _parse_expr_list(token_list, "]")))
                elif t.is_for:
                    #列表解析式
                    parse_stk.push_expr(
                        _Expr("list_compr",
                              [e] + _parse_compr(token_list, "]")))
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
                ek = parse_expr(token_list, True)
                token_list.pop_sym(":")
                ev = parse_expr(token_list, True)
                t = token_list.peek()
                if t.is_sym(",") or t.is_sym("}"):
                    #正常字典
                    token_list.revert(idx)
                    parse_stk.push_expr(
                        _Expr("dict", _parse_dict_expr_list(token_list)))
                elif t.is_for:
                    #字典解析式
                    parse_stk.push_expr(
                        _Expr("dict_compr",
                              [ek, ev] + _parse_compr(token_list, "}")))
                else:
                    t.syntax_err("需要','、'}'或'for'")
        elif t.is_name:
            #名字
            parse_stk.push_expr(_Expr("name", t))
        elif t.is_const:
            parse_stk.push_expr(_Expr("const", t))
        elif t.is_lambda:
            #lambda表达式，先解析参数列表
            arg_list = []
            """参数列表两边的括号可加可不加，这里若直接调用parse_expr
               然后判断是name或含有一堆name的tuple也可以，
               不过我认为这种形式可能导致误解为python的参数自动unpack：
               lambda ((x,y,z)) : ...
               因此特殊处理语法"""
            if token_list.peek().is_sym("("):
                arg_with_parenthesis = True
                token_list.pop_sym("(")
                if token_list.peek().is_sym(")"):
                    has_arg = False
                    token_list.pop_sym(")")
                    token_list.pop_sym(":")
                else:
                    has_arg = True
            else:
                arg_with_parenthesis = False
                if token_list.peek().is_sym(":"):
                    has_arg = False
                    token_list.pop_sym(":")
                else:
                    has_arg = True
            if has_arg:
                while True:
                    arg_list.append(token_list.pop_name())
                    if token_list.peek().is_sym(","):
                        token_list.pop_sym(",")
                        continue
                    if arg_with_parenthesis:
                        token_list.pop_sym(")")
                    token_list.pop_sym(":")
                    break
            e = parse_expr(token_list, True)
            parse_stk.push_expr(
                _Expr("lambda", [arg_list, e]))
        else:
            t.syntax_err("非法的表达式")

        assert parse_stk.stk

        #状态：解析()、[]、.三种运算
        while token_list:
            t = token_list.pop()
            if t.is_sym("("):
                #函数调用
                parse_stk.stk[-1] = (
                    _Expr("()", [parse_stk.stk[-1],
                                 _parse_expr_list(token_list, ")")]))
            elif t.is_sym("["):
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
                    el.append(parse_expr(token_list, True))
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
                #属性
                token_list.peek_name()
                parse_stk.stk[-1] = _Expr(".", [parse_stk.stk[-1],
                                                token_list.pop()])
            else:
                token_list.revert()
                break

        if token_list and token_list.peek().is_sym(","):
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
                arg_list.append(parse_expr(token_list, True))
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

        if not token_list or _is_expr_end(token_list.peek()):
            #表达式结束
            break

        #状态：解析普通二元运算符
        t = token_list.pop()
        if t.is_not:
            #not in是两个token，特殊处理
            t_next = token_list.pop()
            if t_next.is_in:
                parse_stk.push_op("not in")
            else:
                t.syntax_err("需要二元运算符")
        elif (t.is_sym and t.value in _BINOCULAR_OP_SET or
              t.is_and or t.is_or or t.is_in):
            #二元运算
            parse_stk.push_op(t.value)
        else:
            t.syntax_err("需要二元运算符")

    return parse_stk.finish()
