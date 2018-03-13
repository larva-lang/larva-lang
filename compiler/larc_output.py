#coding=utf8

"""
输出为go代码
"""

import os
import shutil
import sys
import platform
import subprocess

import larc_common
import larc_module
import larc_token
import larc_expr
import larc_type

_POS_INFO_IGNORE = object()

main_module_name = None
out_dir = None
runtime_dir = None

out_prog_dir = None
prog_module_name = None

prog_name = None

_tb_map = {}

class _Code:
    class _CodeBlk:
        def __init__(self, code, end_line):
            self.code = code
            self.end_line = end_line

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                return
            assert len(self.code.indent) >= 4
            self.code.indent = self.code.indent[: -4]
            self.code += self.end_line

    def __init__(self, file_path_name, pkg_name = None):
        self.file_path_name = file_path_name
        self.indent = ""
        self.line_list = []
        self += "package %s" % (prog_module_name if pkg_name is None else pkg_name)

    def __iadd__(self, line):
        self.line_list.append(self.indent + line)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return
        f = open(self.file_path_name, "w")
        for line in self.line_list:
            print >> f, line

    def new_blk(self, title, start_with_blank_line = True):
        if start_with_blank_line:
            self += ""
        end_line = "}"
        if title == "import":
            self += title + " ("
            end_line = ")"
        elif title == "else" or title.startswith("else if "):
            if start_with_blank_line:
                del self.line_list[-1]
            assert self.line_list[-1] == self.indent + "}"
            del self.line_list[-1]
            self += "} " + title + " {"
        elif title:
            self += title + " {"
        else:
            self += "{"
        self.indent += " " * 4
        return self._CodeBlk(self, end_line)

    #记录tb映射的信息，本code当前位置到输入的pos信息，在输出代码之前使用，adjust为代码行数修正值
    def record_tb_info(self, pos_info, adjust = 0):
        if pos_info is _POS_INFO_IGNORE:
            tb_info = None
        else:
            t, fom = pos_info
            if fom is None:
                fom = "<module>"
            tb_info = t.src_file, t.line_no, str(fom)
        _tb_map[(self.file_path_name, len(self.line_list) + 1 + adjust)] = tb_info

def _gen_module_name_code(module):
    if "/" not in module.name:
        return "%d_%s" % (len(module.name), module.name)
    pl = module.name.split("/")
    return "%d_%s" % (len(pl), "_".join(["%d_%s" % (len(p), p) for p in pl]))

def _gen_coi_name(coi):
    for i in "cls", "gcls_inst", "intf", "gintf_inst":
        if eval("coi.is_" + i):
            coi_name = "lar_" + i
            break
    else:
        raise Exception("Bug")
    coi_name += "_%s_%d_%s" % (_gen_module_name_code(coi.module), len(coi.name), coi.name)
    if coi.is_gcls_inst or coi.is_gintf_inst:
        #泛型实例还需增加泛型参数信息
        coi_name += "_%d" % len(coi.gtp_map)
        for tp in coi.gtp_map.itervalues():
            coi_name += "_%s" % _gen_non_array_type_name(tp)
    return coi_name

def _gen_non_array_type_name(tp):
    assert not (tp.is_array or tp.is_nil or tp.is_void or tp.is_literal_int)
    if tp.is_obj_type:
        return _gen_coi_name(tp.get_coi())
    assert tp.token.is_reserved
    return {"bool" : "bool",
            "schar" : "int8", "char" : "uint8",
            "short" : "int16", "ushort" : "uint16",
            "int" : "int32", "uint" : "uint32",
            "long" : "int64", "ulong" : "uint64",
            "float" : "float32", "double" : "float64"}[tp.name]

def _gen_type_name_code(tp):
    if tp.is_void:
        return ""
    array_dim_count = tp.array_dim_count
    while tp.is_array:
        tp = tp.to_elem_type()
    _reg_new_arr_func_info(tp, array_dim_count)
    type_name_code = _gen_non_array_type_name(tp)
    if type_name_code.startswith("lar_cls") or type_name_code.startswith("lar_gcls"):
        type_name_code = "*" + type_name_code
    return "*[]" * array_dim_count + type_name_code

def _gen_new_arr_func_name_by_tp_name(tp_name, dim_count, new_dim_count):
    assert dim_count >= new_dim_count > 0
    return "lar_util_new_arr_%s_%d_%d" % (tp_name, dim_count, new_dim_count)

def _gen_new_arr_func_name(tp, dim_count, new_dim_count):
    assert not tp.is_array and dim_count >= new_dim_count > 0
    _reg_new_arr_func_info(tp, dim_count)
    return _gen_new_arr_func_name_by_tp_name(_gen_non_array_type_name(tp), dim_count, new_dim_count)

_new_arr_func_info_set = set()
def _reg_new_arr_func_info(tp, dim_count):
    if tp.is_void:
        return
    while tp.is_array:
        dim_count += 1
        tp = tp.to_elem_type()
    tp_name = _gen_non_array_type_name(tp)
    while dim_count > 0:
        _new_arr_func_info_set.add((tp_name, dim_count))
        dim_count -= 1

def _gen_func_name(func):
    for i in "func", "gfunc_inst":
        if eval("func.is_" + i):
            func_name = "lar_" + i
            break
    else:
        raise Exception("Bug")
    func_name += "_%s_%d_%s" % (_gen_module_name_code(func.module), len(func.name), func.name)
    if func.is_gfunc_inst:
        #泛型实例还需增加泛型参数信息
        func_name += "_%d" % len(func.gtp_map)
        for tp in func.gtp_map.itervalues():
            func_name += "_%s" % _gen_non_array_type_name(tp)
    return func_name

def _output_main_pkg():
    with _Code(os.path.join(out_dir, "src", "lar_prog.%s.P.go" % prog_name), "main") as code:
        with code.new_blk("import"):
            code += '"os"'
            code += '"%s"' % prog_module_name
        with code.new_blk("func main()"):
            code += "os.Exit(%s.Lar_booter_start_prog())" % prog_module_name

def _output_booter():
    booter_fix_file_path_name = os.path.join(runtime_dir, "lar_booter.go")
    if not os.path.exists(booter_fix_file_path_name):
        larc_common.exit("runtime文件缺失，请检查编译器环境：[%s]" % booter_fix_file_path_name)
    f = open(os.path.join(out_prog_dir, "%s.booter_fix.go" % prog_module_name), "w")
    print >> f, "package %s" % prog_module_name
    print >> f
    f.write(open(booter_fix_file_path_name).read())
    f.close()

    with _Code(os.path.join(out_prog_dir, "%s.booter.go" % prog_module_name)) as code:
        with code.new_blk("import"):
            code += '"os"'
        with code.new_blk("func Lar_booter_start_prog() int"):
            code += "argv := %s(int64(len(os.Args)))" % (_gen_new_arr_func_name(larc_type.STR_TYPE, 1, 1))
            with code.new_blk("for i := 0; i < len(os.Args); i ++"):
                code += "(*argv)[i] = lar_util_create_lar_str_from_go_str(os.Args[i])"
            code += ("return lar_booter_start_prog(lar_env_init_mod_%s, %s, argv)" %
                     (_gen_module_name_code(larc_module.module_map[main_module_name]),
                      _gen_func_name(larc_module.module_map[main_module_name].get_main_func())))

def _gen_str_literal_name(t):
    return "lar_literal_str_%s_%d" % (_gen_module_name_code(curr_module), t.id)

def _gen_number_literal_name(t):
    return "lar_literal_number_%s_%d" % (_gen_module_name_code(curr_module), t.id)

def _gen_str_literal(s):
    code_list = []
    for c in s:
        asc = ord(c)
        assert 0 <= asc <= 0xFF
        if asc < 32 or asc > 126 or c in ('"', "\\"):
            code_list.append("\\%03o" % asc)
        else:
            code_list.append(c)
    return '"%s"' % "".join(code_list)

def _gen_gv_name(gv):
    return "lar_gv_%s_%d_%s" % (_gen_module_name_code(gv.module), len(gv.name), gv.name)

def _gen_default_value_code(tp):
    if tp.is_void:
        return ""
    if tp.is_bool_type:
        return "false"
    if tp.is_number_type:
        return "0"
    assert tp.is_obj_type
    return "nil"

def _gen_se_expr_code(expr):
    if expr.expr is None:
        assert expr.op in ("++", "--")
        return "%s %s" % (_gen_expr_code(expr.lvalue), expr.op)
    return "%s %s %s" % (_gen_expr_code(expr.lvalue), expr.op, _gen_expr_code(expr.expr))

def _gen_expr_list_code(expr_list):
    return ", ".join([_gen_expr_code(e) for e in expr_list])

def _gen_expr_code(expr):
    if expr.is_se_expr:
        return _gen_se_expr_code(expr)
    assert expr.is_expr
    expr_code = _gen_expr_code_ex(expr)
    if expr.is_ref:
        expr_code = "&(%s)" % expr_code
    return expr_code

def _gen_expr_code_ex(expr):
    if expr.op == "force_convert":
        tp, e = expr.arg
        tp_name_code = _gen_type_name_code(tp)
        e_code = _gen_expr_code(e)
        if tp.can_convert_from(e.type) or not tp.is_obj_type:
            return "(%s)(%s)" % (tp_name_code, e_code)
        assert e.type.is_obj_type and not (e.type.is_array or e.type.is_nil)
        e_coi = e.type.get_coi()
        assert e_coi.is_intf or e_coi.is_gintf_inst
        return "func () %s {r, ok := (%s).(%s); if ok {return r} else {return nil}}()" % (tp_name_code, e_code, tp_name_code)

    if expr.op in ("~", "!", "neg", "pos"):
        e = expr.arg
        return "%s(%s)" % ({"~" : "^", "!" : "!", "neg" : "-", "pos" : "+"}[expr.op], _gen_expr_code(e))

    if expr.op in larc_token.BINOCULAR_OP_SYM_SET:
        ea, eb = expr.arg
        ea_code = _gen_expr_code(ea)
        eb_code = _gen_expr_code(eb)
        if expr.op in ("==", "!=") and ea.type.is_obj_type and eb.type.is_obj_type:
            ea_coi = ea.type.get_coi()
            eb_coi = eb.type.get_coi()
            if ea_coi.is_intf or ea_coi.is_gintf_inst:
                assert eb_coi.is_intf or eb_coi.is_gintf_inst
                return "%slar_util_is_same_intf((%s), (%s))" % ("!" if expr.op == "!=" else "", ea_code, eb_code)
        if expr.op == "%" and ea.type.is_float_type:
            assert eb.type.is_float_type
            return "lar_util_fmod_%s((%s), (%s))" % (ea.type.name, ea_code, eb_code)
        return "(%s) %s (%s)" % (ea_code, expr.op, eb_code)

    if expr.op == "?:":
        ea, eb, ec = expr.arg
        tp = expr.type
        if tp == larc_type.LITERAL_INT_TYPE:
            tp = larc_type.INT_TYPE
        return ("func () %s {if (%s) {return (%s)} else {return (%s)}}()" %
                (_gen_type_name_code(tp), _gen_expr_code(ea), _gen_expr_code(eb), _gen_expr_code(ec)))

    if expr.op == "local_var":
        name = expr.arg
        return "%sl_%s" % ("*" if expr.type.is_ref else "", name)

    if expr.op == "literal":
        t = expr.arg
        assert t.type.startswith("literal_")
        literal_type = t.type[8 :]
        tp = expr.type
        if literal_type in ("nil", "bool"):
            return t.value
        assert t.id in _literal_token_id_set
        if literal_type == "str":
            return _gen_str_literal_name(t)
        return _gen_number_literal_name(t)

    if expr.op == "new":
        expr_list = expr.arg
        tp = expr.type
        return "lar_new_obj_%s(%s)" % (_gen_non_array_type_name(tp), _gen_expr_list_code(expr_list))

    if expr.op == "default_value":
        tp = expr.arg
        assert tp == expr.type
        return "(%s)(%s)" % (_gen_type_name_code(tp), _gen_default_value_code(tp))

    if expr.op == "new_array":
        tp, size_list = expr.arg
        _reg_new_arr_func_info(tp, len(size_list))
        try:
            new_dim_count = size_list.index(None)
        except ValueError:
            new_dim_count = len(size_list)
        assert new_dim_count > 0
        return "%s(%s)" % (_gen_new_arr_func_name(tp, len(size_list), new_dim_count),
                           ", ".join(["int64(%s)" % _gen_expr_code(e) for e in size_list[: new_dim_count]]))

    if expr.op == "this":
        return "this"

    if expr.op == "[]":
        arr_e, e = expr.arg
        return "(*(%s))[%s]" % (_gen_expr_code(arr_e), _gen_expr_code(e))

    if expr.op == "array.size":
        arr_e = expr.arg
        return "int64(len(*(%s)))" % _gen_expr_code(arr_e)

    if expr.op == "str_format":
        fmt, expr_list = expr.arg
        return "lar_str_fmt(%s%s%s)" % (_gen_str_literal(fmt), ", " if expr_list else "", _gen_expr_list_code(expr_list))

    if expr.op == "call_method":
        e, method, expr_list = expr.arg
        return "(%s).method_%s(%s)" % (_gen_expr_code(e), method.name, _gen_expr_list_code(expr_list))

    if expr.op == ".":
        e, attr = expr.arg
        return "(%s).m_%s" % (_gen_expr_code(e), attr.name)

    if expr.op == "global_var":
        gv = expr.arg
        return _gen_gv_name(gv)

    if expr.op == "call_func":
        func, expr_list = expr.arg
        if func.module.name == "__builtins" and func.name in ("catch_base", "catch"):
            assert not expr_list
            expr_list_code = "recover()"
        else:
            expr_list_code = _gen_expr_list_code(expr_list)
        return "%s(%s)" % (_gen_func_name(func), expr_list_code)

    if expr.op == "this.attr":
        attr = expr.arg
        return "this.m_%s" % attr.name

    if expr.op == "call_this.method":
        method, expr_list = expr.arg
        return "this.method_%s(%s)" % (method.name, _gen_expr_list_code(expr_list))

    raise Exception("Bug")

def _gen_arg_def(arg_map):
    return ", ".join(["l_%s %s%s" % (name, "*" if tp.is_ref else "", _gen_type_name_code(tp)) for name, tp in arg_map.iteritems()])

#fom:func or method; boc:break or continue
_NEST_LOOP_INVALID = -(10 ** 10) #无效值采用一个很小的负数，这样递归过程中逐步+1也保证不会>=0
def _output_stmt_list(code, stmt_list, fom, long_ret_nest_deep, long_boc_nest_deep, need_check_defer = True):
    if need_check_defer:
        #需要检查当前block是否有defer，若有则转为输出一个嵌套函数调用
        if stmt_list.has_defer():
            if long_ret_nest_deep >= 0:
                if not fom.type.is_void:
                    code += "var ret_%d %s" % (long_ret_nest_deep, _gen_type_name_code(fom.type))
                code += "rbc_%d := RBC_NONE" % long_ret_nest_deep

            with code.new_blk("func ()"):
                _output_stmt_list(code, stmt_list, fom, long_ret_nest_deep + 1, long_boc_nest_deep + 1, need_check_defer = False)
            assert code.line_list[-1].strip() == "}"
            code.line_list[-1] += "()"
            code.record_tb_info(_POS_INFO_IGNORE, adjust = -1)

            if long_ret_nest_deep == 0:
                with code.new_blk("if rbc_%d == RBC_RET" % long_ret_nest_deep):
                    code += "return %s" % ("" if fom.type.is_void else "ret_%d" % long_ret_nest_deep)
            elif long_ret_nest_deep > 0:
                with code.new_blk("if rbc_%d == RBC_RET" % long_ret_nest_deep):
                    if not fom.type.is_void:
                        code += "ret_%d = ret_%d" % (long_ret_nest_deep - 1, long_ret_nest_deep)
                    code += "rbc_%d = RBC_RET" % (long_ret_nest_deep - 1)
                    code += "return"

            for rbc in "break", "continue":
                if long_boc_nest_deep == 0:
                    code += "if rbc_%d == RBC_%s {%s}" % (long_ret_nest_deep, rbc.upper(), rbc)
                elif long_boc_nest_deep > 0:
                    with code.new_blk("if rbc_%d == RBC_%s" % (long_ret_nest_deep, rbc.upper())):
                        code += "rbc_%d = RBC_%s" % (long_ret_nest_deep - 1, rbc.upper())
                        code += "return"

            return

    for stmt in stmt_list:
        if stmt.type == "block":
            with code.new_blk(""):
                _output_stmt_list(code, stmt.stmt_list, fom, long_ret_nest_deep, long_boc_nest_deep)
            continue
        if stmt.type in ("break", "continue"):
            assert long_boc_nest_deep >= 0 #出现boc的代码一定在循环内部
            if long_boc_nest_deep == 0:
                code += stmt.type
            else:
                code += "rbc_%d = RBC_%s" % (long_ret_nest_deep - 1, stmt.type.upper())
                code += "return"
            continue
        if stmt.type == "return":
            assert long_ret_nest_deep >= 0 #defer代码块中不会有return stmt，校验下
            if long_ret_nest_deep == 0:
                #顶层，普通return
                if stmt.expr is not None:
                    code.record_tb_info(stmt.expr.pos_info)
                code += "return %s" % ("" if stmt.expr is None else "(%s)" % _gen_expr_code(stmt.expr))
            else:
                #内层，设置上一层的ret并return上去
                if stmt.expr is not None:
                    code.record_tb_info(stmt.expr.pos_info)
                    code += "ret_%d = (%s)" % (long_ret_nest_deep - 1, _gen_expr_code(stmt.expr))
                code += "rbc_%d = RBC_RET" % (long_ret_nest_deep - 1)
                code += "return"
            continue
        if stmt.type == "for":
            with code.new_blk(""):
                if len(stmt.for_var_map) == 0:
                    for expr in stmt.init_expr_list:
                        code.record_tb_info(expr.pos_info)
                        code += _gen_expr_code(expr)
                else:
                    assert len(stmt.for_var_map) == len(stmt.init_expr_list)
                    for (name, tp), expr in zip(stmt.for_var_map.iteritems(), stmt.init_expr_list):
                        if expr is not None:
                            code.record_tb_info(expr.pos_info)
                        code += "var l_%s %s = (%s)" % (name, _gen_type_name_code(tp),
                                                        _gen_default_value_code(tp) if expr is None else _gen_expr_code(expr))
                        code += "_ = l_%s" % name
                if stmt.judge_expr is None:
                    code += "for ; ;"
                else:
                    code.record_tb_info(stmt.judge_expr.pos_info)
                    code += "for ; %s;" % _gen_expr_code(stmt.judge_expr)
                if len(stmt.loop_expr_list) == 0:
                    blk_title = ""
                elif len(stmt.loop_expr_list) == 1:
                    code.record_tb_info(stmt.loop_expr_list[0].pos_info)
                    blk_title = _gen_expr_code(stmt.loop_expr_list[0])
                else:
                    with code.new_blk("func ()"):
                        for e in stmt.loop_expr_list:
                            code.record_tb_info(e.pos_info)
                            code += _gen_expr_code(e)
                    assert code.line_list[-1].strip() == "}"
                    del code.line_list[-1]
                    blk_title = "}()"
                    code.record_tb_info(_POS_INFO_IGNORE)

                with code.new_blk(blk_title, start_with_blank_line = False):
                    _output_stmt_list(code, stmt.stmt_list, fom, long_ret_nest_deep, 0)
            continue
        if stmt.type == "while":
            code.record_tb_info(stmt.expr.pos_info, adjust = 1)
            with code.new_blk("for (%s)" % _gen_expr_code(stmt.expr)):
                _output_stmt_list(code, stmt.stmt_list, fom, long_ret_nest_deep, 0)
            continue
        if stmt.type == "if":
            assert len(stmt.if_expr_list) == len(stmt.if_stmt_list_list)
            for i, (if_expr, if_stmt_list) in enumerate(zip(stmt.if_expr_list, stmt.if_stmt_list_list)):
                code.record_tb_info(if_expr.pos_info, adjust = 1 if i == 0 else -1)
                with code.new_blk("%sif (%s)" % ("" if i == 0 else "else ", _gen_expr_code(if_expr))):
                    _output_stmt_list(code, if_stmt_list, fom, long_ret_nest_deep, long_boc_nest_deep)
            if stmt.else_stmt_list is not None:
                with code.new_blk("else"):
                    _output_stmt_list(code, stmt.else_stmt_list, fom, long_ret_nest_deep, long_boc_nest_deep)
            continue
        if stmt.type == "var":
            if stmt.expr is None:
                expr_code = _gen_default_value_code(stmt_list.var_map[stmt.name])
            else:
                expr_code = _gen_expr_code(stmt.expr)
                code.record_tb_info(stmt.expr.pos_info)
            code += "var l_%s %s = (%s)" % (stmt.name, _gen_type_name_code(stmt_list.var_map[stmt.name]), expr_code)
            code += "_ = l_%s" % stmt.name
            continue
        if stmt.type == "expr":
            code.record_tb_info(stmt.expr.pos_info)
            code += _gen_expr_code(stmt.expr)
            continue
        if stmt.type == "defer_block":
            with code.new_blk("defer func ()"):
                _output_stmt_list(code, stmt.stmt_list, fom, _NEST_LOOP_INVALID, _NEST_LOOP_INVALID, need_check_defer = False)
            assert code.line_list[-1].strip() == "}"
            code.line_list[-1] += "()"
            continue
        if stmt.type == "defer_expr":
            code.record_tb_info(stmt.expr.pos_info)
            code += "defer " + _gen_expr_code(stmt.expr)
            continue
        raise Exception("Bug")

_literal_token_id_set = set()

curr_module = None
def _output_module():
    module = curr_module
    module_file_name = os.path.join(out_prog_dir, "%s.mod.%s.mod.go" % (prog_module_name, _gen_module_name_code(module)))
    with _Code(module_file_name) as code:
        code += ""
        for t in module.literal_str_list:
            assert t.is_literal("str") and t.id not in _literal_token_id_set
            _literal_token_id_set.add(t.id)
            code += ("var %s %s = lar_util_create_lar_str_from_go_str(%s)" %
                     (_gen_str_literal_name(t), _gen_type_name_code(larc_type.STR_TYPE), _gen_str_literal(t.value)))
        for t in module.literal_number_list:
            assert (t.is_literal and t.type[8 :] in ("char", "int", "uint", "long", "ulong", "float", "double") and
                    t.id not in _literal_token_id_set)
            _literal_token_id_set.add(t.id)
            code += ("var %s %s = (%s)" %
                     (_gen_number_literal_name(t), _gen_type_name_code(eval("larc_type.%s_TYPE" % t.type[8 :].upper())), t.value))

        code += ""
        for gv in module.global_var_map.itervalues():
            code += "var %s %s = %s" % (_gen_gv_name(gv), _gen_type_name_code(gv.type), _gen_default_value_code(gv.type))

        code += ""
        mod_inited_flag_name = "lar_env_inited_flag_of_mod_%s" % _gen_module_name_code(module)
        code += "var %s bool = false" % mod_inited_flag_name
        with code.new_blk("func lar_env_init_mod_%s()" % _gen_module_name_code(module), False):
            with code.new_blk("if !%s" % mod_inited_flag_name):
                code += "%s = true" % mod_inited_flag_name
                for dep_module_name in module.get_dep_module_set():
                    code += "lar_env_init_mod_%s()" % _gen_module_name_code(larc_module.module_map[dep_module_name])
                for gv in module.global_var_map.itervalues():
                    if gv.expr is not None:
                        code.record_tb_info(gv.expr.pos_info)
                        code += "%s = %s" % (_gen_gv_name(gv), _gen_expr_code(gv.expr))

        for cls in [i for i in module.cls_map.itervalues() if not i.gtp_name_list] + list(module.gcls_inst_map.itervalues()):
            if "native" in cls.decr_set:
                for attr in cls.attr_map.itervalues():
                    _reg_new_arr_func_info(attr.type, 0)
                for method in [cls.construct_method] + list(cls.method_map.itervalues()):
                    _reg_new_arr_func_info(method.type, 0)
                    for tp in method.arg_map.itervalues():
                        _reg_new_arr_func_info(tp, 0)
                continue
            lar_cls_name = _gen_coi_name(cls)
            with code.new_blk("type %s struct" % (lar_cls_name)):
                for attr in cls.attr_map.itervalues():
                    code += "m_%s %s" % (attr.name, _gen_type_name_code(attr.type))
            with code.new_blk("func lar_new_obj_%s(%s) *%s" % (lar_cls_name, _gen_arg_def(cls.construct_method.arg_map), lar_cls_name)):
                code += "o := new(%s)" % lar_cls_name
                code.record_tb_info(_POS_INFO_IGNORE)
                code += "o.method_%s(%s)" % (cls.name, ", ".join(["l_%s" % name for name in cls.construct_method.arg_map]))
                code += "return o"
            for method in [cls.construct_method] + list(cls.method_map.itervalues()):
                with code.new_blk("func (this *%s) method_%s(%s) %s" %
                                  (lar_cls_name, method.name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))):
                    if method.is_method:
                        _output_stmt_list(code, method.stmt_list, method, 0, _NEST_LOOP_INVALID, need_check_defer = False)
                        code += "return %s" % _gen_default_value_code(method.type)
                    else:
                        assert method.is_usemethod
                        code.record_tb_info((method.attr.type.token, "<usemethod>"))
                        code += ("%sthis.m_%s.method_%s(%s)" %
                                 ("" if method.type.is_void else "return ", method.attr.name, method.name,
                                  ", ".join(["l_%s" % name for name in method.arg_map])))

        for intf in [i for i in module.intf_map.itervalues() if not i.gtp_name_list] + list(module.gintf_inst_map.itervalues()):
            with code.new_blk("type %s interface" % (_gen_coi_name(intf))):
                for method in intf.method_map.itervalues():
                    code += "method_%s(%s) %s" % (method.name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))

        for func in [i for i in module.func_map.itervalues() if not i.gtp_name_list] + list(module.gfunc_inst_map.itervalues()):
            if "native" in func.decr_set:
                _reg_new_arr_func_info(func.type, 0)
                for tp in func.arg_map.itervalues():
                    _reg_new_arr_func_info(tp, 0)
                continue
            if module.name == "__builtins" and func.name in ("catch_base", "catch"):
                assert not func.arg_map
                arg_def = "%s interface{}" % _gen_gv_name(module.global_var_map["_go_recovered"])
            else:
                arg_def = _gen_arg_def(func.arg_map)
            with code.new_blk("func %s(%s) %s" % (_gen_func_name(func), arg_def, _gen_type_name_code(func.type))):
                _output_stmt_list(code, func.stmt_list, func, 0, _NEST_LOOP_INVALID, need_check_defer = False)
                code += "return %s" % _gen_default_value_code(func.type)

    #输出native实现
    for sub_mod_name, nf in module.native_file_map.iteritems():
        nf.line_list[0] = ["package %s" % prog_module_name]
        f = open(os.path.join(out_prog_dir, "%s.mod.%s.native.%s.N.go" % (prog_module_name, _gen_module_name_code(module), sub_mod_name)), "w")
        for line in nf.line_list:
            s = ""
            for i in line:
                if isinstance(i, str):
                    s += i
                else:
                    assert isinstance(i, tuple)
                    module_name, name = i
                    s += "%s_%d_%s" % (_gen_module_name_code(larc_module.module_map[module_name]), len(name), name)
            print >> f, s.rstrip()
        f.close()

def _output_util():
    #拷贝runtime中固定的util代码
    util_fix_file_path_name = os.path.join(runtime_dir, "lar_util.go")
    if not os.path.exists(util_fix_file_path_name):
        larc_common.exit("runtime文件缺失，请检查编译器环境：[%s]" % util_fix_file_path_name)
    f = open(os.path.join(out_prog_dir, "%s.util_fix.go" % prog_module_name), "w")
    print >> f, "package %s" % prog_module_name
    print >> f
    f.write(open(util_fix_file_path_name).read())
    f.close()

    #生成util代码
    with _Code(os.path.join(out_prog_dir, "%s.util.go" % prog_module_name)) as code:
        for tp_name, dim_count in _new_arr_func_info_set:
            assert dim_count > 0
            tp_name_code = tp_name
            if tp_name.startswith("lar_cls") or tp_name.startswith("lar_gcls"):
                tp_name_code = "*" + tp_name_code
            for new_dim_count in xrange(1, dim_count + 1):
                new_arr_func_name = _gen_new_arr_func_name_by_tp_name(tp_name, dim_count, new_dim_count)
                arg_code = ", ".join(["d%d_size" % i for i in xrange(new_dim_count)]) + " int64"
                arr_tp_name_code = "*[]" * dim_count + tp_name_code
                if new_dim_count == 1:
                    elem_type_name_code = arr_tp_name_code[3 :]
                    if (elem_type_name_code[0] == "*" or elem_type_name_code.startswith("lar_intf") or
                        elem_type_name_code.startswith("lar_gintf")):
                        elem_code = "nil"
                    elif elem_type_name_code.startswith("bool"):
                        elem_code = "false"
                    else:
                        elem_code = "0"
                else:
                    assert new_dim_count > 1
                    elem_code = "%s(%s)" % (_gen_new_arr_func_name_by_tp_name(tp_name, dim_count - 1, new_dim_count - 1), 
                                            ", ".join(["d%d_size" % i for i in xrange(1, new_dim_count)]))
                with code.new_blk("func %s(%s) %s" % (new_arr_func_name, arg_code, arr_tp_name_code)):
                    code += "arr := make(%s, d0_size)" % arr_tp_name_code[1 :]
                    with code.new_blk("for i := int64(0); i < d0_size; i ++"):
                        code += "arr[i] = %s" % elem_code
                    code += "return &arr"
        with code.new_blk("var lar_util_tb_map = map[lar_util_go_tb]*lar_util_lar_tb"):
            for (go_file_name, go_line_no), tb_info in _tb_map.iteritems():
                if tb_info is None:
                    code += "lar_util_go_tb{file: %s, line: %d}: nil," % (_gen_str_literal(go_file_name), go_line_no)
                else:
                    lar_file_name, lar_line_no, lar_fom_name = tb_info
                    code += ("lar_util_go_tb{file: %s, line: %d}: &lar_util_lar_tb{file: %s, line: %d, fom_name: %s}," %
                             (_gen_str_literal(go_file_name), go_line_no, _gen_str_literal(lar_file_name), lar_line_no,
                              _gen_str_literal(lar_fom_name)))

def _output_makefile():
    if platform.system() == "Windows":
        f = open(os.path.join(out_dir, "make.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src\\lar_prog.%s.P.go" % (prog_name, prog_name)
    elif platform.system() in ("Darwin", "Linux"):
        f = open(os.path.join(out_dir, "Makefile"), "w")
        print >> f, "all:"
        print >> f, "\t@export GOPATH=%s; go build -o %s src/lar_prog.%s.P.go" % (out_dir, prog_name, prog_name)
    else:
        larc_common.exit("不支持在平台'%s'生成make脚本" % platform.system())

def _run_prog(args_for_run):
    if platform.system() == "Windows":
        larc_common.exit("Windows下不支持--run，请手动执行make.bat和编译出的exe")
    elif platform.system() in ("Darwin", "Linux"):
        os.system("make -C %s" % out_dir)
        exe_file = os.path.join(out_dir, "%s" % prog_name)
    else:
        raise Exception("Bug")
    if os.path.exists(exe_file):
        os.execv(exe_file, [exe_file] + args_for_run)

def output(need_run_prog, args_for_run):
    global runtime_dir, out_prog_dir, prog_module_name, prog_name, curr_module

    out_prog_dir = os.path.join(out_dir, "src", "lar_prog_" + _gen_module_name_code(larc_module.module_map[main_module_name]))

    shutil.rmtree(out_dir, True)
    os.makedirs(out_prog_dir)

    prog_module_name = "lar_prog_" + _gen_module_name_code(larc_module.module_map[main_module_name])

    prog_name = main_module_name.split("/")[-1]

    _output_main_pkg()
    _output_booter()
    for curr_module in larc_module.module_map.itervalues():
        _output_module()
    _output_util()
    _output_makefile()
    if need_run_prog:
        _run_prog(args_for_run)
