#coding=utf8

"""
编译larva表达式
"""

import re

import larc_common
import larc_token
import larc_module
import larc_stmt
import larc_type

_UNARY_OP_SET = set(["~", "!", "neg", "pos", "force_convert"])
_BINOCULAR_OP_SET = larc_token.BINOCULAR_OP_SYM_SET
_OP_PRIORITY_LIST = [["?", ":", "?:"],
                     ["||"],
                     ["&&"],
                     ["|"],
                     ["^"],
                     ["&"],
                     ["==", "!="],
                     ["<", "<=", ">", ">="],
                     ["<<", ">>"],
                     ["+", "-"],
                     ["*", "/", "%"],
                     ["~", "!", "neg", "pos", "force_convert"]]
_OP_PRIORITY_MAP = {}
for _i in xrange(len(_OP_PRIORITY_LIST)):
    for _op in _OP_PRIORITY_LIST[_i]:
        _OP_PRIORITY_MAP[_op] = _i
del _i
del _op

#将literal_int expr转换成对应type，type一定是一个number
def _convert_literal_int_expr(e, tp):
    assert e.op in ("literal", "?:") and e.type == larc_type.LITERAL_INT_TYPE and tp.is_number_type and not tp.is_literal_int
    if e.op == "?:":
        #若两个结果分量都可转为tp，则可转换
        ea, eb, ec = e.arg
        eb = _convert_literal_int_expr(eb, tp)
        ec = _convert_literal_int_expr(ec, tp)
        if eb is None or ec is None:
            return None
        assert eb.type == tp and ec.type == tp
        return _Expr("?:", (ea, eb, ec), tp)
    else:
        #literal int
        v = e.arg.value
        bit_num_table = {"schar" : 7, "char" : 8, "short" : 15, "ushort" : 16}
        if tp.name in bit_num_table and v >= 2 ** bit_num_table[tp.name]:
            #e的字面量值大于tp支持的范围了
            return None
        #将e字面量转为tp类型
        return _Expr("force_convert", (tp, e), tp)

class _CantMakeNumberTypeSame(Exception):
    pass

#处理ea、eb类型不同，但是存在literal_int的情况
def _make_number_type_same(ea, eb):
    assert ea.type != eb.type and ea.type.is_number_type and eb.type.is_number_type

    if ea.type.is_literal_int:
        ea = _convert_literal_int_expr(ea, eb.type)
        if ea is None:
            raise _CantMakeNumberTypeSame()
        return ea, eb
    if eb.type.is_literal_int:
        eb = _convert_literal_int_expr(eb, ea.type)
        if eb is None:
            raise _CantMakeNumberTypeSame()
        return ea, eb

    raise _CantMakeNumberTypeSame()

class ExprBase:
    def __init__(self, expr_name):
        self.is_expr = self.is_se_expr = False
        setattr(self, "is_" + expr_name, True)

class _Expr(ExprBase):
    def __init__(self, op, arg, type):
        ExprBase.__init__(self, "expr")

        if op not in ("literal", "?:") and type.is_literal_int:
            type = larc_type.INT_TYPE
        if op not in ("literal", "?:"):
            assert not type.name.startswith("literal_")
        else:
            assert type.is_literal_int or not type.name.startswith("literal_")
        self.op = op
        self.arg = arg
        self.type = type
        self.is_lvalue = op in ("this.attr", "global_var", "local_var", "[]", ".")
        self.is_ref = False #仅用于标识函数或方法的参数ref传递的表达式修饰，由外部修改和使用
        self.pos_info = None #位置信息，只有在解析栈finish时候才会被赋值为解析栈的开始位置，参考相关代码，主要用于output时候的代码位置映射构建

class _ParseStk:
    #解析表达式时使用的栈
    def __init__(self, start_token, curr_module, cls, fom):
        self.start_token = start_token
        self.fom = fom
        self.cls = cls
        self.curr_module = curr_module
        self.stk = []
        self.op_stk = []

    def push_op(self, op, force_convert_type = None):
        if op == "force_convert":
            assert force_convert_type is not None
        else:
            assert force_convert_type is None
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
        if op == "force_convert":
            #类型强转额外压入一个类型对象
            self.op_stk.append(force_convert_type)
            self.op_stk.append(op)
            return
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
            if op == "force_convert":
                tp = self.op_stk.pop()
                if not tp.can_force_convert_from(e.type):
                    self.start_token.syntax_err("非法的表达式，存在无效的强制类型转换：'%s'到'%s'" % (e.type, tp))
                self.stk.append(_Expr(op, (tp, e), tp))
            else:
                if op in ("neg", "pos"):
                    if not e.type.is_number_type:
                        self.start_token.syntax_err("非法的表达式：类型'%s'不可做正负运算" % e.type)
                elif op == "!":
                    if not e.type.is_bool_type:
                        self.start_token.syntax_err("非法的表达式：类型'%s'不可做'!'运算" % e.type)
                elif op == "~":
                    if not e.type.is_integer_type:
                        self.start_token.syntax_err("非法的表达式：类型'%s'不可做'~'运算" % e.type)
                else:
                    raise Exception("Bug")
                self.stk.append(_Expr(op, e, e.type))

        elif op in _BINOCULAR_OP_SET:
            #双目运算符
            if len(self.stk) < 2:
                self.start_token.syntax_err("非法的表达式")
            eb = self.stk.pop()
            ea = self.stk.pop()

            class _InvalidBinocularOp(Exception):
                pass

            try:
                normal_binocular_op = False

                if op in ("&&", "||"):
                    if not ea.type.is_bool_type or not eb.type.is_bool_type:
                        self.start_token.syntax_err("非法的表达式：运算'%s'的左右分量必须是bool型" % op)
                    tp = larc_type.BOOL_TYPE
                elif op in ("==", "!="):
                    if ea.type.is_obj_type and eb.type.is_obj_type:
                        #是否为同一个对象
                        if ea.type != eb.type:
                            if ea.type.can_convert_from(eb.type):
                                eb = _Expr("force_convert", (ea.type, eb), ea.type)
                            elif eb.type.can_convert_from(ea.type):
                                ea = _Expr("force_convert", (eb.type, ea), eb.type)
                            else:
                                raise _InvalidBinocularOp()
                    elif ea.type.is_obj_type and ea.type.can_convert_from(eb.type):
                        eb = _Expr("force_convert", (ea.type, eb), ea.type)
                    elif eb.type.is_obj_type and eb.type.can_convert_from(ea.type):
                        ea = _Expr("force_convert", (eb.type, ea), eb.type)
                    elif ea.type.is_bool_type and eb.type.is_bool_type:
                        pass #bool类型也可直接比较
                    elif ea.type.is_number_type and eb.type.is_number_type:
                        normal_binocular_op = True
                    else:
                        raise _InvalidBinocularOp()
                    tp = larc_type.BOOL_TYPE
                elif op in ("+", "-", "*", "/", "%", "<", ">", "<=", ">="):
                    if ea.type.is_number_type and eb.type.is_number_type:
                        normal_binocular_op = True
                    else:
                        raise _InvalidBinocularOp()
                    if op in ("<", ">", "<=", ">="):
                        tp = larc_type.BOOL_TYPE
                    else:
                        tp = None
                elif op in ("&", "|", "^"):
                    if ea.type.is_integer_type and eb.type.is_integer_type:
                        normal_binocular_op = True
                    else:
                        raise _InvalidBinocularOp()
                    tp = None
                elif op in ("<<", ">>"):
                    if not (ea.type.is_integer_type and eb.type.is_unsigned_integer_type):
                        raise _InvalidBinocularOp()
                    tp = ea.type
                else:
                    raise Exception("Bug")

                if normal_binocular_op:
                    if ea.type != eb.type:
                        try:
                            ea, eb = _make_number_type_same(ea, eb)
                        except _CantMakeNumberTypeSame:
                            raise _InvalidBinocularOp()
                    if tp is None:
                        tp = ea.type
                assert tp is not None
                if op not in ("<<", ">>"):
                    assert ea.type == eb.type
                self.stk.append(_Expr(op, (ea, eb), tp))

            except _InvalidBinocularOp:
                self.start_token.syntax_err("非法的表达式：类型'%s'和'%s'无法做'%s'运算" % (ea.type, eb.type, op))

        elif op == "?":
            self.start_token.syntax_err("非法的表达式，存在未匹配':'的'?'")

        elif op == "?:":
            #三目运算符
            if len(self.stk) < 3:
                self.start_token.syntax_err("非法的表达式")
            ec = self.stk.pop()
            eb = self.stk.pop()
            ea = self.stk.pop()
            if not ea.type.is_bool_type:
                self.start_token.syntax_err("非法的表达式：'?:'运算的第一运算分量类型不能是'%s'" % ea.type)
            if eb.type == ec.type:
                #完全一样，则使用此类型，但不允许都是nil
                if eb.type.is_nil:
                    assert ec.type.is_nil
                    self.start_token.syntax_err("非法的表达式：'?:'运算的第二、三运算分量都是nil字面量")
                tp = eb.type
            else:
                #类型不相同，对number类型归一化，对存在nil字面量的情况，根据另一分量确定nil的类型，其他情况要求代码显式强转
                try:
                    if eb.type.is_number_type and ec.type.is_number_type:
                        eb, ec = _make_number_type_same(eb, ec)
                    elif eb.type.is_obj_type and ec.type.is_obj_type:
                        if eb.type.is_nil:
                            assert not ec.type.is_nil
                            eb = _Expr("force_convert", (ec.type, eb), ec.type)
                        elif ec.type.is_nil:
                            ec = _Expr("force_convert", (eb.type, ec), eb.type)
                        else:
                            raise _CantMakeNumberTypeSame()
                    else:
                        raise _CantMakeNumberTypeSame()
                except _CantMakeNumberTypeSame:
                    self.start_token.syntax_err("非法的表达式：'?:'运算的第二、三运算分量类型'%s'和'%s'不同" % (eb.type, ec.type))
                tp = eb.type
            self.stk.append(_Expr(op, (ea, eb, ec), tp))

        else:
            raise Exception("Bug")

    def push_expr(self, e):
        self.stk.append(e)

    def finish(self):
        while self.op_stk:
            self._pop_top_op()
        if len(self.stk) != 1:
            self.start_token.syntax_err("非法的表达式")
        e = self.stk.pop()
        e.pos_info = self.start_token, self.fom
        return e

def _is_expr_end(t):
    if t.is_sym:
        if t.value in (set([")", "]", ",", ";"]) | larc_token.ASSIGN_SYM_SET | larc_token.INC_DEC_SYM_SET):
            return True
    return False

class Parser:
    def __init__(self, token_list, curr_module, dep_module_map, cls, gtp_map, fom, used_dep_module_set = None):
        self.token_list = token_list
        self.curr_module = curr_module
        self.dep_module_map = dep_module_map
        self.cls = cls
        self.gtp_map = gtp_map
        self.fom = fom
        self.used_dep_module_set = used_dep_module_set

    def parse(self, var_map_stk, need_type):
        start_token = self.token_list.peek()
        parse_stk = _ParseStk(start_token, self.curr_module, self.cls, self.fom)
        while True:
            t = self.token_list.pop()

            if t.is_sym and t.value in ("~", "!", "+", "-"):
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
                tp = larc_type.try_parse_type(self.token_list, self.curr_module, self.dep_module_map, self.gtp_map,
                                              used_dep_module_set = self.used_dep_module_set)
                if tp is not None:
                    #类型强转
                    if tp == larc_type.VOID_TYPE:
                        t.syntax_err("无效的类型强转：不能转为void类型")
                    self.token_list.pop_sym(")")
                    parse_stk.push_op("force_convert", tp)
                    continue
                #子表达式
                parse_stk.push_expr(self.parse(var_map_stk, None))
                self.token_list.pop_sym(")")
            elif t.is_name:
                if t.value in self.dep_module_map:
                    m = larc_module.module_map[self.dep_module_map[t.value]]
                    self.token_list.pop_sym(".")
                    t, name = self.token_list.pop_name()
                    expr = self._parse_func_or_global_var(m, (t, name), var_map_stk)
                    parse_stk.push_expr(expr)
                else:
                    for var_map in reversed(var_map_stk):
                        if t.value in var_map:
                            #局部变量
                            parse_stk.push_expr(_Expr("local_var", t.value, var_map[t.value]))
                            break
                    else:
                        if self.cls is not None and self.cls.has_method_or_attr(t.value):
                            #类方法或属性
                            expr = self._parse_method_or_attr_of_this_cls((t, t.value), var_map_stk)
                            parse_stk.push_expr(expr)
                        else:
                            #当前模块或builtin模块
                            for m in self.curr_module, larc_module.builtins_module:
                                if m.has_func(t.value) or m.has_global_var(t.value):
                                    expr = self._parse_func_or_global_var(m, (t, t.value), var_map_stk)
                                    parse_stk.push_expr(expr)
                                    break
                            else:
                                t.syntax_err("未定义的标识符'%s'" % t.value)
            elif t.is_literal:
                assert t.type.startswith("literal_")
                if t.type == "literal_int":
                    #int字面量需要特殊处理
                    tp = larc_type.LITERAL_INT_TYPE
                else:
                    tp = eval("larc_type.%s_TYPE" % t.type[8 :].upper())
                e = _Expr("literal", t, tp)
                if t.type == "literal_str" and self.token_list.peek().is_sym(".") and self.token_list.peek(1).is_sym("("):
                    #字符串常量的format语法
                    fmt, expr_list = self._parse_str_format(var_map_stk, t)
                    e = _Expr("str_format", (fmt, expr_list), larc_type.STR_TYPE)
                parse_stk.push_expr(e)
            elif t.is_reserved("new"):
                base_type = larc_type.parse_type(self.token_list, self.dep_module_map, non_array = True)
                base_type.check(self.curr_module, self.gtp_map, self.used_dep_module_set)
                larc_module.check_new_ginst_during_compile()
                new_token = t
                t = self.token_list.pop()
                if t.is_sym("("):
                    t = self.token_list.peek()
                    expr_list = self._parse_expr_list(var_map_stk)
                    if base_type.is_array:
                        arg_map = larc_type.get_array_construct_arg_map()
                        self._make_expr_list_match_arg_map(t, expr_list, arg_map)
                        size_list = [expr_list[0]]
                        array_base_type = base_type.to_elem_type()
                        while array_base_type.is_array:
                            size_list.append(None)
                            array_base_type = array_base_type.to_elem_type()
                        parse_stk.push_expr(_Expr("new_array", (array_base_type, size_list), base_type))
                    else:
                        is_new_cls = False
                        if not base_type.token.is_reserved:
                            new_coi = base_type.get_coi()
                            if new_coi.is_cls or new_coi.is_gcls_inst:
                                if "native" in new_coi.decr_set and new_coi.is_construct_method_auto_gened:
                                    assert new_coi.is_cls and "public" not in new_coi.construct_method.decr_set
                                    base_type.token.syntax_err("无法创建'%s'的实例：native类未显式定义构造方法" % new_coi)
                                if new_coi.module is not self.curr_module and "public" not in new_coi.construct_method.decr_set:
                                    base_type.token.syntax_err("无法创建'%s'的实例：对构造方法无访问权限" % new_coi)
                                self._make_expr_list_match_arg_map(t, expr_list, new_coi.construct_method.arg_map)
                                parse_stk.push_expr(_Expr("new", expr_list, base_type))
                                is_new_cls = True
                        if not is_new_cls:
                            #对基础类型或接口使用new语法
                            if base_type.is_void:
                                new_token.syntax_err("不能创建void实例")
                            if len(expr_list) == 0:
                                #构建默认值的语法
                                parse_stk.push_expr(_Expr("default_value", base_type, base_type))
                            elif len(expr_list) == 1:
                                if not base_type.can_force_convert_from(expr_list[0].type):
                                    new_token.syntax_err("无法从类型'%s'转换到'%s'" % (expr_list[0].type, base_type))
                                parse_stk.push_expr(_Expr("force_convert", (base_type, expr_list[0]), base_type))
                            else:
                                t.syntax_err("基础类型或接口的new只能输入0或1个参数")
                else:
                    if not t.is_sym("["):
                        t.syntax_err("需要'('或'['")
                    if base_type.is_void:
                        t.syntax_err("无法创建void数组")
                    size_list = [self.parse(var_map_stk, larc_type.VALID_ARRAY_IDX_TYPES)]
                    init_dim_count = 1
                    self.token_list.pop_sym("]")
                    while self.token_list.peek().is_sym("["):
                        self.token_list.pop_sym("[")
                        t = self.token_list.peek()
                        if t.is_sym("]"):
                            size_list.append(None)
                            self.token_list.pop_sym("]")
                            continue
                        if size_list[-1] is None:
                            t.syntax_err("需要']'")
                        size_list.append(self.parse(var_map_stk, larc_type.VALID_ARRAY_IDX_TYPES))
                        init_dim_count += 1
                        self.token_list.pop_sym("]")
                    array_base_type = base_type
                    while array_base_type.is_array:
                        array_base_type = array_base_type.to_elem_type()
                        size_list.append(None)
                    parse_stk.push_expr(_Expr("new_array", (array_base_type, size_list), array_base_type.to_array_type(len(size_list))))
            elif t.is_reserved("this"):
                if self.cls is None:
                    t.syntax_err("'this'只能用于方法中")
                if self.token_list.peek().is_sym("."):
                    self.token_list.pop_sym(".")
                    t, name = self.token_list.pop_name()
                    expr = self._parse_method_or_attr_of_this_cls((t, name), var_map_stk)
                    parse_stk.push_expr(expr)
                else:
                    #单独的this
                    parse_stk.push_expr(_Expr("this", t, larc_type.gen_type_from_cls(self.cls)))
            else:
                t.syntax_err("非法的表达式")

            assert parse_stk.stk

            #解析后缀运算符
            while self.token_list:
                t = self.token_list.pop()
                if t.is_sym("["):
                    expr = self.parse(var_map_stk, larc_type.VALID_ARRAY_IDX_TYPES)
                    self.token_list.pop_sym("]")
                    array_expr = parse_stk.stk[-1]
                    if not array_expr.type.is_array:
                        t.syntax_err("'%s'非数组，不能进行下标运算" % array_expr.type)
                    parse_stk.stk[-1] = _Expr("[]", [array_expr, expr], array_expr.type.to_elem_type())
                elif t.is_sym("."):
                    obj = parse_stk.stk[-1]
                    if obj.type.is_array:
                        #数组
                        t, name = self.token_list.pop_name()
                        method = larc_type.get_array_method(obj.type, name)
                        if method is None:
                            t.syntax_err("数组没有方法'%s'" % name)
                        self.token_list.pop_sym("(")
                        t = self.token_list.peek()
                        expr_list = self._parse_expr_list(var_map_stk)
                        self._make_expr_list_match_arg_map(t, expr_list, method.arg_map)
                        parse_stk.stk[-1] = _Expr("call_array.method", (parse_stk.stk[-1], method, expr_list), method.type)
                    else:
                        t, name = self.token_list.pop_name()
                        if obj.type.token.is_reserved:
                            t.syntax_err("不能对基础类型取属性或调用方法")
                        else:
                            obj_coi = obj.type.get_coi()
                            method, attr = obj_coi.get_method_or_attr(name, t)
                            if method is not None:
                                assert attr is None
                                self.token_list.pop_sym("(")
                                if method.module is not self.curr_module and "public" not in method.decr_set:
                                    t.syntax_err("无法使用方法'%s'：没有权限" % method)
                                t = self.token_list.peek()
                                expr_list = self._parse_expr_list(var_map_stk)
                                self._make_expr_list_match_arg_map(t, expr_list, method.arg_map)
                                parse_stk.stk[-1] = _Expr("call_method", (parse_stk.stk[-1], method, expr_list), method.type)
                            else:
                                assert attr is not None and method is None
                                if attr.module is not self.curr_module and "public" not in attr.decr_set:
                                    t.syntax_err("无法访问属性'%s'：没有权限" % attr)
                                parse_stk.stk[-1] = _Expr(".", (parse_stk.stk[-1], attr), attr.type)
                else:
                    self.token_list.revert()
                    break

            if _is_expr_end(self.token_list.peek()):
                #表达式结束
                break

            #状态：解析普通二元/三元运算符
            t = self.token_list.pop()
            if t.is_sym and (t.value in _BINOCULAR_OP_SET or t.value in ("?", ":")):
                #二元运算
                parse_stk.push_op(t.value)
            else:
                t.syntax_err("需要二元或三元运算符")

        expr = parse_stk.finish()
        expr_pos_info = expr.pos_info #保存一下pos info
        if need_type is not None:
            if isinstance(need_type, (tuple, list)):
                need_type_list = list(need_type)
            else:
                need_type_list = [need_type]
            for need_type in need_type_list:
                if need_type == expr.type:
                    break
                if expr.op in ("literal", "?:") and expr.type == larc_type.LITERAL_INT_TYPE and need_type.is_number_type:
                    e = _convert_literal_int_expr(expr, need_type)
                    if e is None:
                        continue
                    expr = e
                if expr is not None and need_type.can_convert_from(expr.type):
                    if need_type != expr.type:
                        expr = _Expr("force_convert", (need_type, expr), need_type)
                    break
            else:
                if len(need_type_list) == 1:
                    start_token.syntax_err("表达式（类型'%s'）无法隐式转换为类型'%s'" % (expr.type, need_type_list[0]))
                else:
                    start_token.syntax_err("表达式（类型'%s'）无法隐式转换为类型%s其中任意一个" % (expr.type, str(need_type_list)))
        expr.pos_info = expr_pos_info #expr可能根据need_tyep修改了，恢复一下pos info
        return expr

    def _parse_func_or_global_var(self, module, (t, name), var_map_stk):
        if self.used_dep_module_set is not None:
            self.used_dep_module_set.add(module.name)
        global_var = module.get_global_var(name)
        if global_var is not None:
            if module is not self.curr_module and "public" not in global_var.decr_set:
                t.syntax_err("无法使用全局变量'%s'：没有权限" % global_var)
            return _Expr("global_var", global_var, global_var.type)

        if not module.has_func(name):
            t.syntax_err("未定义的全局变量或函数'%s.%s'" % (module, name))

        if self.token_list.peek().is_sym("<"):
            self.token_list.pop_sym("<")
            gtp_list = larc_type.parse_gtp_list(self.token_list, self.dep_module_map)
            for tp in gtp_list:
                tp.check(self.curr_module, self.gtp_map, self.used_dep_module_set)
        else:
            gtp_list = []
        func = module.get_func(t, gtp_list)
        larc_module.check_new_ginst_during_compile() #这个check必须在get_func之后，因为get_func同时负责创建gfunc_inst
        if func.module is not self.curr_module and "public" not in func.decr_set:
            t.syntax_err("无法使用函数'%s'：没有权限" % func)
        self.token_list.pop_sym("(")
        t = self.token_list.peek()
        expr_list = self._parse_expr_list(var_map_stk)
        self._make_expr_list_match_arg_map(t, expr_list, func.arg_map)
        return _Expr("call_func", (func, expr_list), func.type)

    def _parse_method_or_attr_of_this_cls(self, (t, name), var_map_stk):
        assert self.cls is not None
        method, attr = self.cls.get_method_or_attr(name, t)
        if attr is not None:
            return _Expr("this.attr", attr, attr.type)
        assert method is not None
        self.token_list.pop_sym("(")
        t = self.token_list.peek()
        expr_list = self._parse_expr_list(var_map_stk)
        self._make_expr_list_match_arg_map(t, expr_list, method.arg_map)
        return _Expr("call_this.method", (method, expr_list), method.type)

    def _parse_expr_list(self, var_map_stk, allow_ref = True):
        expr_list = []
        if self.token_list.peek().is_sym(")"):
            self.token_list.pop_sym(")")
            return expr_list
        while True:
            t = self.token_list.peek()
            if t.is_reserved("ref"):
                if not allow_ref:
                    t.syntax_err("无效的ref修饰")
                self.token_list.pop()
                is_ref = True
            else:
                is_ref = False
            expr = self.parse(var_map_stk, None)
            if is_ref:
                if not expr.is_lvalue:
                    t.syntax_err("ref修饰的实参不是左值表达式")
                if expr.op == "global_var":
                    global_var = expr.arg
                    if "final" in global_var.decr_set:
                        t.syntax_err("ref修饰了带final属性的全局变量")
            expr.is_ref = is_ref
            expr_list.append(expr)
            if self.token_list.peek().is_sym(")"):
                self.token_list.pop_sym(")")
                return expr_list
            self.token_list.pop_sym(",")

    def _make_expr_list_match_arg_map(self, t, expr_list, arg_map):
        if len(expr_list) != len(arg_map):
            t.syntax_err("传入参数数量错误：需要%d个，传入了%d个" % (len(arg_map), len(expr_list)))
        for i in xrange(len(expr_list)):
            e = expr_list[i]
            e_type = e.type
            tp = arg_map.value_at(i)
            assert not tp.is_literal_int
            if e.is_ref and not tp.is_ref:
                t.syntax_err("参数#%d：形参不是ref，无效的实参ref修饰" % (i + 1))
            if not e.is_ref and tp.is_ref:
                t.syntax_err("参数#%d：形参是ref，实参缺少ref修饰" % (i + 1))
            if e.op in ("literal", "?:") and e.type == larc_type.LITERAL_INT_TYPE and tp.is_number_type:
                e = _convert_literal_int_expr(e, tp)
            if e is None or not tp.can_convert_from(e.type):
                t.syntax_err("参数#%d：无法从类型'%s'转为'%s'" % (i + 1, e_type, tp))
            expr_list[i] = e #e可能被转化了

    def _parse_str_format(self, var_map_stk, t):
        assert t.type == "literal_str"
        self.token_list.pop_sym(".")
        self.token_list.pop_sym("(")
        expr_list = self._parse_expr_list(var_map_stk)
        fmt = ""
        pos = 0
        expr_idx = 0
        while pos < len(t.value):
            if t.value[pos] != "%":
                fmt += t.value[pos]
                pos += 1
                continue
            class ExprTypeError:
                def __init__(self, need_type_desc):
                    self.need_type_desc = need_type_desc
            try:
                pos += 1
                if t.value[pos] == "%":
                    fmt += "%%"
                    pos += 1
                    continue
                if expr_idx >= len(expr_list):
                    t.syntax_err("format格式化参数不足")
                expr = expr_list[expr_idx]
                if expr.is_ref:
                    t.syntax_err("format格式化参数不能有ref修饰")
                expr_idx += 1
                #先解析前缀
                conv_spec = "%"
                while t.value[pos] in "+-#0\x20":
                    d = t.value[pos]
                    pos += 1
                    if d in conv_spec:
                        t.syntax_err("format格式存在重复的前缀修饰：'%s...'" % `t.value[: pos]`[1 : -1])
                    conv_spec += d
                #解析宽度和精度字段
                wp, = re.match(r"""^(\d*\.?\d*)""", t.value[pos :]).groups()
                pos += len(wp)
                conv_spec += wp #wp暂时不需要做校验，所有格式都用统一的wp形式
                #解析格式字符
                verb = t.value[pos]
                pos += 1
                if verb == "t":
                    if not expr.type.is_bool_type:
                        raise ExprTypeError("'bool'")
                elif verb == "b":
                    if not expr.type.is_integer_type and not expr.type.is_float_type:
                        raise ExprTypeError("整数或浮点数")
                elif verb in "cdo":
                    if not expr.type.is_integer_type:
                        raise ExprTypeError("整数")
                elif verb in "xX":
                    if not expr.type.is_integer_type and expr.type != larc_type.STR_TYPE:
                        raise ExprTypeError("整数或字符串")
                elif verb in "eEfFgG":
                    if not expr.type.is_float_type:
                        raise ExprTypeError("浮点数")
                elif verb in "sr":
                    if expr.type.is_bool_type:
                        verb = "t"
                    elif expr.type.is_integer_type:
                        verb = "d"
                    elif expr.type.is_float_type:
                        verb = "f"
                    elif expr.type == larc_type.STR_TYPE:
                        if verb == "r":
                            expr_list[expr_idx - 1] = _Expr("str_repr", expr, larc_type.STR_TYPE)
                            verb = "s"
                    else:
                        raise ExprTypeError("bool、整数、浮点数或字符串")
                else:
                    t.syntax_err("非法的格式符：'%s...'" % `t.value[: pos]`[1 : -1])
                conv_spec += verb
                fmt += conv_spec
            except IndexError:
                t.syntax_err("format格式串非正常结束")
            except ExprTypeError, exc:
                t.syntax_err("format格式化参数#%d类型错误：格式符'%s'需要%s" % (expr_idx, verb, exc.need_type_desc))
        if expr_idx < len(expr_list):
            t.syntax_err("format格式化参数过多")
        return fmt, expr_list
