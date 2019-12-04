#coding=utf8

"""
输出为go代码
"""

import os, shutil, sys, platform, subprocess, re, hashlib, time

import larc_common
import larc_module
import larc_token
import larc_expr
import larc_type

_POS_INFO_IGNORE = object()

main_module_name = None
out_dir = None

_out_prog_dir = None
_prog_module_name = None

_exe_file = None

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

    class _NativeCode:
        def __init__(self, code):
            self.code = code

        def __enter__(self):
            self.code += "//native_code start"
            self.save_indent = self.code.indent
            self.code.indent = ""
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                return
            self.code.indent = self.save_indent
            self.code += "//native_code end"

    def __init__(self, file_path_name, pkg_name = None):
        assert file_path_name.endswith(".go")
        self.file_path_name_base = file_path_name[: -3]
        self.line_list_map = {}
        self.pkg_name = _prog_module_name if pkg_name is None else pkg_name
        self.indent = ""

        self.file_path_name = None
        self.line_list = None
        self.switch_file("")

    def switch_file(self, file_name):
        assert self.indent == ""
        if file_name != "":
            file_name = "." + file_name
        self.file_path_name = self.file_path_name_base + file_name + ".go"
        if file_name in self.line_list_map:
            self.line_list = self.line_list_map[file_name]
        else:
            self.line_list = self.line_list_map[file_name] = []
            self += "package %s" % self.pkg_name

    def __iadd__(self, line):
        self.line_list.append(self.indent + line)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return
        for file_name, line_list in self.line_list_map.iteritems():
            f = open(self.file_path_name_base + file_name + ".go", "w")
            for line in line_list:
                print >> f, line
            f.close()

    def new_blk(self, title, start_with_blank_line = True, tail = ""):
        if start_with_blank_line:
            self += ""
        end_line = "}" + tail
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

    def new_native_code(self):
        return self._NativeCode(self)

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

#gen funcs -----------------------------------------------------------------------------------------------

#对所有模块按照hash来做输出的code
_module_name_code_map = {}

def _gen_all_module_name_code_map():
    for hash_prefix_len in xrange(4, 33):
        hm = {}
        for name in larc_module.module_map:
            hm[name] = hashlib.md5(name).hexdigest().upper()[: hash_prefix_len]
        if len(hm) == len(set(hm.itervalues())):
            break
    else:
        rhm = {}
        for name, h in hm.iteritems():
            if h in rhm:
                larc_common.exit("恭喜你找到了两个md5一样的字符串：'%s'和'%s'" % (rhm[h], name))
        raise Exception("Bug")

    for name in larc_module.module_map:
        last_name = name.split("/")[-1]
        assert larc_token.is_valid_name(last_name)
        _module_name_code_map[name] = "mod%s_%d_%s" % (hm[name], len(last_name), last_name)

def _gen_module_name_code(module):
    return _module_name_code_map[module.name]

def _gen_coi_name(coi):
    if coi.is_closure:
        return "lar_%s" % coi.name

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
            coi_name += "_%s" % _gen_type_name_code_without_star(tp)
    return coi_name

_BASE_TYPE_NAME_MAP = {"bool": "bool",
                       "schar": "int8", "char": "uint8",
                       "short": "int16", "ushort": "uint16",
                       "int": "int32", "uint": "uint32",
                       "long": "int64", "ulong": "uint64",
                       "float": "float32", "double": "float64"}

def _gen_non_array_type_name(tp):
    assert not (tp.is_array or tp.is_nil or tp.is_void or tp.is_literal_int)
    if tp.is_obj_type:
        return _gen_coi_name(tp.get_coi())
    assert tp.token.is_reserved
    return _BASE_TYPE_NAME_MAP[tp.name]

def _gen_arr_tp_name(elem_tp_name, dim_count):
    return "lar_arr_%s_%d" % (elem_tp_name, dim_count)

def _gen_arr_tp_name_code(elem_tp_name, dim_count):
    return "*" + _gen_arr_tp_name(elem_tp_name, dim_count)

def _gen_type_name_code(tp):
    if tp.is_void:
        return ""
    array_dim_count = tp.array_dim_count
    while tp.is_array:
        tp = tp.to_elem_type()
    tp_name = _gen_non_array_type_name(tp)
    if array_dim_count > 0:
        return _gen_arr_tp_name_code(tp_name, array_dim_count)
    return _gen_tp_name_code_from_tp_name(tp_name)

def _gen_type_name_code_without_star(tp):
    c = _gen_type_name_code(tp)
    if c[0] == "*":
        c = c[1 :]
    assert c and re.match("^\w*$", c) is not None
    return c

def _gen_tp_name_code_from_tp_name(tp_name):
    if tp_name.startswith("lar_cls") or tp_name.startswith("lar_gcls") or tp_name.startswith("lar_closure"):
        return "*" + tp_name
    return tp_name

def _gen_new_arr_func_name_by_tp_name(tp_name, dim_count, new_dim_count):
    assert dim_count >= new_dim_count > 0
    return "lar_util_new_arr_%s_%d_%d" % (tp_name, dim_count, new_dim_count)

def _gen_new_arr_func_name(tp, dim_count, new_dim_count):
    assert not tp.is_array and dim_count >= new_dim_count > 0
    return _gen_new_arr_func_name_by_tp_name(_gen_non_array_type_name(tp), dim_count, new_dim_count)

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
            func_name += "_%s" % _gen_type_name_code_without_star(tp)
    return func_name

def _gen_init_mod_func_name(module):
    return "lar_env_init_mod_" + _gen_module_name_code(module)

def _gen_str_literal_name(t):
    return "lar_literal_str_%s_%d" % (_gen_module_name_code(_curr_module), t.id)

def _gen_number_literal_name(t):
    return "lar_literal_number_%s_%d" % (_gen_module_name_code(_curr_module), t.id)

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

def _gen_method_name_code(method):
    #public的用同样的名字模板，非public的要加上module名，限定在模块内部使用
    if "public" in method.decr_set:
        return "lar_method_" + method.name
    return "lar_method_%s_%d_%s" % (_gen_module_name_code(method.module), len(method.name), method.name)

def _gen_se_expr_code(expr):
    if expr.expr is None:
        assert expr.op in ("++", "--")
        return "%s %s" % (_gen_expr_code(expr.lvalue), expr.op)
    return "%s %s %s" % (_gen_expr_code(expr.lvalue), expr.op, _gen_expr_code(expr.expr))

def _gen_expr_list_code(expr_list, with_lar_fiber = True):
    ecl = ["lar_fiber"] if with_lar_fiber else []
    ecl += [_gen_expr_code(e) for e in expr_list]
    return ", ".join(ecl)

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
        return "(%s)(%s)" % (tp_name_code, e_code)

    if expr.op in ("~", "!", "neg", "pos"):
        e = expr.arg
        return "%s(%s)" % ({"~" : "^", "!" : "!", "neg" : "-", "pos" : "+"}[expr.op], _gen_expr_code(e))

    if expr.op in larc_token.BINOCULAR_OP_SYM_SET:
        ea, eb = expr.arg
        ea_code = _gen_expr_code(ea)
        eb_code = _gen_expr_code(eb)
        if expr.op == "%" and ea.type.is_float_type:
            assert eb.type.is_float_type
            return "lar_util_fmod_%s((%s), (%s))" % (ea.type.name, ea_code, eb_code)
        op = expr.op
        if op in ("===", "!=="):
            op = op[: -1]
        return "(%s) %s (%s)" % (ea_code, op, eb_code)

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

    if expr.op == "new_obj_init_by_attr":
        attr_init_map = expr.arg
        tp = expr.type
        init_code_list = []
        for name, e in attr_init_map.iteritems():
            init_code_list.append("m_%s: (%s)" % (name, _gen_expr_code(e)))
        return "&%s{%s}" % (_gen_non_array_type_name(tp), ", ".join(init_code_list))

    if expr.op == "default_value":
        tp = expr.arg
        assert tp == expr.type
        return "(%s)(%s)" % (_gen_type_name_code(tp), _gen_default_value_code(tp))

    if expr.op == "new_array":
        tp, size_list = expr.arg
        try:
            new_dim_count = size_list.index(None)
        except ValueError:
            new_dim_count = len(size_list)
        assert new_dim_count > 0
        new_arr_method = larc_type.gen_arr_type(tp.to_array_type(len(size_list))).get_coi().method_map["new_arr"]
        return ("((%s)(nil)).%s(lar_fiber, []int64{%s})" %
                (_gen_arr_tp_name_code(_gen_non_array_type_name(tp), len(size_list)), _gen_method_name_code(new_arr_method),
                 ", ".join(["int64(%s)" % _gen_expr_code(e) for e in size_list[: new_dim_count]])))

    if expr.op == "new_array_by_init_list":
        expr_list = expr.arg
        expr_code_list = []
        for e in expr_list:
            if isinstance(e, tuple):
                first_e, second_e = e
                expr_code = "{(%s), (%s)}" % (_gen_expr_code(first_e), _gen_expr_code(second_e))
            else:
                expr_code = "(%s)" % _gen_expr_code(e)
            expr_code_list.append(expr_code)
        array_type = expr.type
        assert array_type.is_array
        elem_type = array_type.to_elem_type()
        return "&%s{arr: []%s{%s}}" % (_gen_type_name_code(array_type)[1 :], _gen_type_name_code(elem_type), ", ".join(expr_code_list))

    if expr.op == "this":
        return "this"

    if expr.op == "[]":
        arr_e, e = expr.arg
        return "(%s).arr[%s]" % (_gen_expr_code(arr_e), _gen_expr_code(e))

    if expr.op == "[:]":
        arr_e, ea, eb = expr.arg
        arr_tp_name_code = _gen_type_name_code(arr_e.type)
        assert arr_tp_name_code.startswith("*lar_arr_")
        return ("&%s{arr: (%s).arr[%s:%s]}" %
                (arr_tp_name_code[1 :], _gen_expr_code(arr_e), "" if ea is None else _gen_expr_code(ea),
                 "" if eb is None else _gen_expr_code(eb)))

    if expr.op == "call_array.method":
        e, method, expr_list = expr.arg
        assert e.type.is_array
        return "(%s).%s(%s)" % (_gen_expr_code(e), _gen_method_name_code(method), _gen_expr_list_code(expr_list))

    if expr.op == "str_format":
        fmt, expr_list = expr.arg
        return ("lar_str_fmt(%s%s%s)" %
                (_gen_str_literal(fmt), ", " if expr_list else "", _gen_expr_list_code(expr_list, with_lar_fiber = False)))

    if expr.op == "to_go_str":
        e = expr.arg
        if e.type == larc_type.STR_TYPE:
            #针对String小优化一下
            return "lar_str_to_go_str(%s)" % _gen_expr_code(e)
        return "lar_go_func_any_to_go_str(lar_fiber, %s)" % _gen_expr_code(e)

    if expr.op == "repr_to_go_str":
        e = expr.arg
        return "lar_go_func_any_repr_to_go_str(lar_fiber, %s)" % _gen_expr_code(e)

    if expr.op == "type_name_to_go_str":
        e = expr.arg
        return "lar_go_func_any_type_name_to_go_str(lar_fiber, %s)" % _gen_expr_code(e)

    if expr.op == "call_method":
        e, method, expr_list = expr.arg
        return "(%s).%s(%s)" % (_gen_expr_code(e), _gen_method_name_code(method), _gen_expr_list_code(expr_list))

    if expr.op == ".":
        e, attr = expr.arg
        return "(%s).m_%s" % (_gen_expr_code(e), attr.name)

    if expr.op == "global_var":
        gv = expr.arg
        return _gen_gv_name(gv)

    if expr.op == "call_func":
        func, expr_list = expr.arg
        if func.module.name == "__builtins" and func.name in ("_catch_throwable", "catch"):
            assert not expr_list
            expr_list_code = "lar_fiber, recover()"
        else:
            expr_list_code = _gen_expr_list_code(expr_list)
        return "%s(%s)" % (_gen_func_name(func), expr_list_code)

    if expr.op == "closure":
        closure = expr.arg
        coi_name = _gen_coi_name(closure)
        return "&%s{%s}" % (coi_name, ", ".join(["cm_%s: %s_method_%s" % (method.name, coi_name, method.name)
                                                 for method in closure.method_map.itervalues()]))

    if expr.op == "if-else":
        e_cond, ea, eb = expr.arg
        ret_stmt_prefix = "" if expr.type.is_void else "return"
        return ("func () %s {if (%s) {%s (%s)} else {%s (%s)}}()" %
                (_gen_type_name_code(expr.type), _gen_expr_code(e_cond), ret_stmt_prefix, _gen_expr_code(ea), ret_stmt_prefix,
                 _gen_expr_code(eb)))

    if expr.op == "matched_nil_ref":
        return "new(%s)" % (_gen_type_name_code(expr.type))

    raise Exception("Bug")

def _gen_arg_def(arg_map, with_lar_fiber = True):
    acl = ["lar_fiber *lar_go_stru_fiber"] if with_lar_fiber else []
    acl += ["l_%s %s%s" % (name, "*" if tp.is_ref else "", _gen_type_name_code(tp)) for name, tp in arg_map.iteritems()]
    return ", ".join(acl)

#gen funcs end -----------------------------------------------------------------------------------------------

_main_pkg_file = None

_BOOTER_START_PROC_FUNC_NAME = "Lar_booter_start_prog"

def _output_main_pkg():
    with _Code(_main_pkg_file, "main") as code:
        with code.new_blk("import"):
            code += '"%s"' % _prog_module_name
        with code.new_blk("func main()"):
            code += "%s.%s()" % (_prog_module_name, _BOOTER_START_PROC_FUNC_NAME)

def _output_booter():
    with _Code("%s/%s.booter.go" % (_out_prog_dir, _prog_module_name)) as code:
        init_std_lib_internal_modules_func_name = "init_std_lib_internal_modules"
        with code.new_blk("func %s(lar_fiber *lar_go_stru_fiber)" % init_std_lib_internal_modules_func_name):
            code += "%s(lar_fiber)" % _gen_init_mod_func_name(larc_module.builtins_module) #保证内建模块先初始化
            for mn in larc_common.STD_LIB_INTERNAL_MODULES:
                code += "%s(lar_fiber)" % _gen_init_mod_func_name(larc_module.module_map[mn])
        with code.new_blk("func %s()" % _BOOTER_START_PROC_FUNC_NAME):
            code += ("lar_booter_start_prog(%s, %s, %s)" %
                     (init_std_lib_internal_modules_func_name,
                      _gen_init_mod_func_name(larc_module.module_map[main_module_name]),
                      _gen_func_name(larc_module.module_map[main_module_name].get_main_func())))

def _output_native_code(code, native_code, fom):
    class FakeToken:
        def __init__(self, line_no):
            self.src_file = native_code.module.dir + "/" + native_code.file_name
            self.line_no = native_code.t.line_no + line_no

    with code.new_native_code():
        for line_idx, line in enumerate(native_code.line_list):
            s = ""
            for i in line:
                if isinstance(i, str):
                    s += i
                elif larc_type.is_type(i):
                    s += _gen_type_name_code(i)
                else:
                    assert isinstance(i, tuple)
                    module_name, name = i
                    s += "%s_%d_%s" % (_gen_module_name_code(larc_module.module_map[module_name]), len(name), name)
            code.record_tb_info((FakeToken(line_idx + 1), fom))
            if s.endswith(";"):
                larc_common.warning("文件[%s]行[%d] native代码存在分号结尾" %
                                    (native_code.module.dir + "/" + native_code.file_name, native_code.t.line_no + line_idx + 1))
            code += s

def _output_closure_method(code, closure):
    coi_name = _gen_coi_name(closure)
    for method in closure.method_map.itervalues():
        with code.new_blk("var %s_method_%s = func (%s) %s" %
                          (coi_name, method.name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))):
            _output_stmt_list(code, method.stmt_list)
            code += "return %s" % _gen_default_value_code(method.type)

def _output_stmt_list(code, stmt_list):
    for stmt in stmt_list:
        if stmt.type == "block":
            with code.new_blk(""):
                _output_stmt_list(code, stmt.stmt_list)
            continue

        if stmt.type in ("break", "continue"):
            code += stmt.type
            continue

        if stmt.type == "return":
            #顶层，普通return
            if stmt.expr is not None:
                code.record_tb_info(stmt.expr.pos_info)
            code += "return %s" % ("" if stmt.expr is None else "(%s)" % _gen_expr_code(stmt.expr))
            continue

        if stmt.type == "for":
            with code.new_blk(""):
                if len(stmt.for_var_map) == 0:
                    for expr in stmt.init_expr_list:
                        code.record_tb_info(expr.pos_info)
                        code += _gen_expr_code(expr)
                else:
                    assert len(stmt.for_var_map) == len(stmt.init_expr_list)
                    pos = 0
                    for (name, tp), expr in zip(stmt.for_var_map.iteritems(), stmt.init_expr_list):
                        if pos in stmt.closure_def_map:
                            for closure in stmt.closure_def_map[pos]:
                                _output_closure_method(code, closure)
                        if expr is not None:
                            code.record_tb_info(expr.pos_info)
                        code += "var l_%s %s = (%s)" % (name, _gen_type_name_code(tp),
                                                        _gen_default_value_code(tp) if expr is None else _gen_expr_code(expr))
                        code += "_ = l_%s" % name
                        pos += 1
                    else:
                        if pos in stmt.closure_def_map:
                            for closure in stmt.closure_def_map[pos]:
                                _output_closure_method(code, closure)
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
                    _output_stmt_list(code, stmt.stmt_list)
            continue

        if stmt.type == "foreach":
            with code.new_blk(""):
                code += "var l_%s %s = (%s)" % (stmt.var_name, _gen_type_name_code(stmt.var_tp), _gen_default_value_code(stmt.var_tp))
                code += "_ = l_%s" % (stmt.var_name)
                code.record_tb_info(stmt.iter_expr.pos_info)
                with code.new_blk("for foreach_iter := (%s); !foreach_iter.lar_method_after_end(lar_fiber); "
                                  "foreach_iter.lar_method_inc(lar_fiber)" %
                                  _gen_expr_code(stmt.iter_expr), start_with_blank_line = False):
                    code += "l_%s = foreach_iter.lar_method_get(lar_fiber)" % (stmt.var_name)
                    _output_stmt_list(code, stmt.stmt_list)
            continue

        if stmt.type == "while":
            code.record_tb_info(stmt.expr.pos_info, adjust = 1)
            with code.new_blk("for (%s)" % _gen_expr_code(stmt.expr)):
                _output_stmt_list(code, stmt.stmt_list)
            continue

        if stmt.type == "if":
            assert len(stmt.if_expr_list) == len(stmt.if_stmt_list_list)
            for i, (if_expr, if_stmt_list) in enumerate(zip(stmt.if_expr_list, stmt.if_stmt_list_list)):
                code.record_tb_info(if_expr.pos_info, adjust = 1 if i == 0 else -1)
                with code.new_blk("%sif (%s)" % ("" if i == 0 else "else ", _gen_expr_code(if_expr))):
                    _output_stmt_list(code, if_stmt_list)
            if stmt.else_stmt_list is not None:
                with code.new_blk("else"):
                    _output_stmt_list(code, stmt.else_stmt_list)
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
            with code.new_blk("defer func ()", tail = "()"):
                _output_stmt_list(code, stmt.stmt_list)
            continue

        if stmt.type == "defer_expr":
            code.record_tb_info(stmt.expr.pos_info)
            code += "defer " + _gen_expr_code(stmt.expr)
            continue

        if stmt.type == "native_code":
            _output_native_code(code, stmt.native_code, stmt.fom)
            continue

        if stmt.type == "def_closure_method":
            _output_closure_method(code, stmt.closure)
            continue

        raise Exception("Bug")

_literal_token_id_set = set()
_reflect_zvs = ["false"] + ["%s(0)" % _tp_name_code for _tp_name_code in _BASE_TYPE_NAME_MAP.itervalues() if _tp_name_code != "bool"]
del _tp_name_code

_curr_module = None
def _output_module():
    module = _curr_module
    '''
    因为go编译器一个坑爹的type alias的bug：https://github.com/golang/go/issues/25838
    这个bug简单说就是，如果代码有type alias，那么对应的type定义应该出现在go代码中使用alias的位置（例如函数定义等）之前，否则编译时无法解析
    go在编译代码的时候，对于每个package的目录，是按照文件名字典序排序的顺序进行，因此通过PROG_NAME.-.XXX的命名来强制一些文件被优先编译
    这里用到type alias的只有数组，所以数组相关代码会被这样特殊处理
    '''
    is_array_mod = module is larc_module.array_module
    module_file_name = "%s/%s.%smod.%s.mod.go" % (_out_prog_dir, _prog_module_name, "-." if is_array_mod else "", _gen_module_name_code(module))
    with _Code(module_file_name) as code:
        code += ""
        for t in module.literal_str_list:
            assert t.is_literal("str") and t.id not in _literal_token_id_set
            _literal_token_id_set.add(t.id)
            code += ("var %s %s = lar_str_from_go_str(%s)" % (_gen_str_literal_name(t), _STR_TYPE_NAME_CODE, _gen_str_literal(t.value)))
        for t in module.literal_number_list:
            assert (t.is_literal and t.type[8 :] in ("char", "int", "uint", "long", "ulong", "double") and
                    t.id not in _literal_token_id_set)
            _literal_token_id_set.add(t.id)
            if t.is_literal("double"):
                v = t.value.hex()
            else:
                v = "%s" % t.value
            code += ("var %s %s = (%s)" %
                     (_gen_number_literal_name(t), _gen_type_name_code(eval("larc_type.%s_TYPE" % t.type[8 :].upper())), v))

        code += ""
        for gv in module.global_var_map.itervalues():
            code += "var %s %s = %s" % (_gen_gv_name(gv), _gen_type_name_code(gv.type), _gen_default_value_code(gv.type))

        code += ""
        mod_inited_flag_name = "lar_env_inited_flag_of_mod_%s" % _gen_module_name_code(module)
        code += "var %s bool = false" % mod_inited_flag_name
        with code.new_blk("func %s(lar_fiber *lar_go_stru_fiber)" % _gen_init_mod_func_name(module), False):
            with code.new_blk("if !%s" % mod_inited_flag_name):
                code += "%s = true" % mod_inited_flag_name
                for dep_module_name in module.get_dep_module_set():
                    code += "%s(lar_fiber)" % _gen_init_mod_func_name(larc_module.module_map[dep_module_name])
                for gv in module.global_var_map.itervalues():
                    if gv.expr is not None:
                        code.record_tb_info(gv.expr.pos_info)
                        code += "%s = %s" % (_gen_gv_name(gv), _gen_expr_code(gv.expr))
                init_func = module.get_init_func()
                if init_func is not None:
                    code += "%s(lar_fiber)" % _gen_func_name(init_func)

        for intf in [i for i in module.intf_map.itervalues() if not i.gtp_name_list] + list(module.gintf_inst_map.itervalues()):
            with code.new_blk("type %s interface" % (_gen_coi_name(intf))):
                for method in intf.method_map.itervalues():
                    code += "%s(%s) %s" % (_gen_method_name_code(method), _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))

        def output_reflect_method(code, coi, type_name):
            coi_name = _gen_coi_name(coi)
            _reflect_zvs.append("(*%s)(nil)" % coi_name)
            #1 类型名
            code += "var lar_reflect_type_name_%s = lar_str_from_go_str(%s)" % (coi_name, _gen_str_literal(type_name))
            with code.new_blk("func (this *%s) lar_reflect_type_name() %s" % (coi_name, _STR_TYPE_NAME_CODE)):
                code += "return lar_reflect_type_name_%s" % coi_name
            #2 new_empty，仅包含public属性的类（所有属性public并且无native代码）
            can_new_empty = ((coi.is_cls or coi.is_gcls_inst) and all(["public" in attr.decr_set for attr in coi.attr_map.itervalues()]) and
                             not coi.native_code_list)
            with code.new_blk("func (this *%s) lar_reflect_can_new_empty() bool" % coi_name):
                code += "return %s" % ("true" if can_new_empty else "false")
            with code.new_blk("func (this *%s) lar_reflect_new_empty() interface{}" % coi_name):
                code += "return %s" % ("&%s{}" % coi_name if can_new_empty else "nil")
            #3 属性信息（仅对public属性）
            public_attrs = [attr for attr in coi.attr_map.itervalues() if "public" in attr.decr_set] if coi.is_cls or coi.is_gcls_inst else []
            with code.new_blk("var lar_reflect_attr_infos_%s = []*lar_reflect_attr_info_type" % coi_name):
                for attr in public_attrs:
                    with code.new_blk("&lar_reflect_attr_info_type", tail = ","):
                        code += "tn: %s," % _gen_str_literal(attr.type.to_str(ignore_builtins_module_prefix = True))
                        code += "zv: (%s)(%s)," % (_gen_type_name_code(attr.type), _gen_default_value_code(attr.type))
                        code += "name: %s," % _gen_str_literal(attr.name)
                        with code.new_blk("tags: []*lar_reflect_attr_tag_type", tail = ","):
                            for tag_name, tag_value in attr.tags:
                                code += ("&lar_reflect_attr_tag_type{%s, %s}," % (_gen_str_literal(tag_name), _gen_str_literal(tag_value)))
            with code.new_blk("func (this *%s) lar_reflect_attr_infos() []*lar_reflect_attr_info_type" % coi_name):
                code += "return lar_reflect_attr_infos_%s" % coi_name
            #4 属性左值（仅对public属性）
            with code.new_blk("func (this *%s) lar_reflect_attr_refs() []*lar_reflect_attr_ref_type" % coi_name):
                with code.new_blk("return []*lar_reflect_attr_ref_type"):
                    for i, attr in enumerate(public_attrs):
                        with code.new_blk("&lar_reflect_attr_ref_type", tail = ","):
                            code += "ptr: &this.m_%s," % attr.name
                            code += "tn: lar_reflect_attr_infos_%s[%d].tn," % (coi_name, i)
                            code += "get: func () interface{} {return this.m_%s}," % attr.name
                            if attr.type.is_coi_type:
                                attr_type_coi = attr.type.get_coi()
                                attr_is_intf = attr_type_coi.is_intf or attr_type_coi.is_gintf_inst
                            else:
                                attr_is_intf = False
                            with code.new_blk("can_set: func (i interface{}) bool", tail = ","):
                                if attr_is_intf:
                                    with code.new_blk("if i == nil"):
                                        code += "return true"
                                code += "_, ok := i.(%s)" % _gen_type_name_code(attr.type)
                                code += "return ok"
                            with code.new_blk("set: func (i interface{}) bool", tail = ","):
                                if attr_is_intf:
                                    with code.new_blk("if i == nil"):
                                        code += "this.m_%s = nil" % attr.name
                                        code += "return true"
                                with code.new_blk("if v, ok := i.(%s); ok" % _gen_type_name_code(attr.type)):
                                    code += "this.m_%s = v" % attr.name
                                    code += "return true"
                                code += "return false"
            #5 方法信息（构造方法和public方法，构造方法按是否public决定信息是否为nil）
            constructor = coi.construct_method if (coi.is_cls or coi.is_gcls_inst) and "public" in coi.construct_method.decr_set else None
            public_methods = [method for method in coi.method_map.itervalues() if "public" in method.decr_set]
            with code.new_blk("var lar_reflect_method_infos_%s = []*lar_reflect_method_info_type" % coi_name):
                for i, method in enumerate([constructor] + public_methods):
                    if i == 0 and method is None:
                        code += "nil,"
                        continue
                    with code.new_blk("&lar_reflect_method_info_type", tail = ","):
                        code += "ret_tn: %s," % _gen_str_literal(method.type.to_str(ignore_builtins_module_prefix = True))
                        if method.type.is_void:
                            code += "ret_zv: nil,"
                        else:
                            code += "ret_zv: (%s)(%s)," % (_gen_type_name_code(method.type), _gen_default_value_code(method.type))
                        code += "name: %s," % _gen_str_literal(method.name)
                        with code.new_blk("arg_infos: []*lar_reflect_method_arg_info_type", tail = ","):
                            for arg_tp in method.arg_map.itervalues():
                                with code.new_blk("&lar_reflect_method_arg_info_type", tail = ","):
                                    code += "is_ref: %s," % ("true" if arg_tp.is_ref else "false")
                                    code += "tn: %s," % _gen_str_literal(arg_tp.to_str(ignore_builtins_module_prefix = True))
                                    code += "zv: (%s)(%s)," % (_gen_type_name_code(arg_tp), _gen_default_value_code(arg_tp))
            with code.new_blk("func (this *%s) lar_reflect_method_infos() []*lar_reflect_method_info_type" % coi_name):
                code += "return lar_reflect_method_infos_%s" % coi_name
            #6 方法（仅对public方法）
            def output_code_of_preparing_args(code, method): #这个函数下面构造方法的地方还需要用到
                with code.new_blk("if len(args) != %d" % len(method.arg_map)):
                    code += "err_arg_seq = -1"
                    code += "return"

                code += ""
                code += "var ok bool"
                code += "_ = ok"
                code += ""
                for i, arg_tp in enumerate(method.arg_map.itervalues()):
                    if arg_tp.is_coi_type and not arg_tp.is_ref:
                        arg_tp_coi = arg_tp.get_coi()
                        arg_tp_is_intf = arg_tp_coi.is_intf or arg_tp_coi.is_gintf_inst
                    else:
                        arg_tp_is_intf = False
                    arg_tp_code = "%s%s" % ("*" if arg_tp.is_ref else "", _gen_type_name_code(arg_tp))

                    code += "var arg_%d %s" % (i, arg_tp_code)
                    with code.new_blk("", start_with_blank_line = False):
                        code += "var arg = args[%d]" % i
                        #先判断ref修饰的一致性
                        with code.new_blk("if %sarg.is_ref" % ("!" if arg_tp.is_ref else "")):
                            code += "err_arg_seq = %d" % (i + 1)
                            code += "return"
                        #逻辑：当参数类型是非ref的接口类型，且输入为nil，则不作下面的block（即保留接口初始化的nil值）
                        with code.new_blk(("if arg.v != nil") if arg_tp_is_intf else "", start_with_blank_line = False):
                            with code.new_blk("if arg_%d, ok = arg.v.(%s); !ok" % (i, arg_tp_code)):
                                code += "err_arg_seq = %d" % (i + 1)
                                code += "return"
                        code += "_ = arg_%d" % i
            with code.new_blk("func (this *%s) lar_reflect_methods() []*lar_reflect_method_type" % coi_name):
                with code.new_blk("return []*lar_reflect_method_type"):
                    for method in public_methods:
                        with code.new_blk("&lar_reflect_method_type", tail = ","):
                            with code.new_blk("can_call: func (args []*lar_reflect_method_arg_type) (err_arg_seq int32)", tail = ","):
                                output_code_of_preparing_args(code, method)
                                code += "return"
                            with code.new_blk("call: func (lar_fiber *lar_go_stru_fiber, args []*lar_reflect_method_arg_type) "
                                              "(err_arg_seq int32, ret interface{}, has_ret bool)", tail = ","):
                                output_code_of_preparing_args(code, method)
                                code_of_calling_method = (
                                    "this.%s(lar_fiber, %s)" %
                                    (_gen_method_name_code(method), ", ".join(["arg_%d" % i for i in xrange(len(method.arg_map))])))
                                if method.type.is_void:
                                    code += code_of_calling_method
                                else:
                                    code += "ret = %s" % code_of_calling_method
                                    code += "has_ret = true"
                                code += "return"
            #7 构造方法
            with code.new_blk("func (this *%s) lar_reflect_method_of_new() *lar_reflect_method_type" % coi_name):
                if constructor is None:
                    code += "return nil"
                else:
                    with code.new_blk("return &lar_reflect_method_type"):
                        with code.new_blk("can_call: func (args []*lar_reflect_method_arg_type) (err_arg_seq int32)", tail = ","):
                            output_code_of_preparing_args(code, constructor)
                            code += "return"
                        with code.new_blk("call: func (lar_fiber *lar_go_stru_fiber, args []*lar_reflect_method_arg_type) "
                                          "(err_arg_seq int32, ret interface{}, has_ret bool)", tail = ","):
                            output_code_of_preparing_args(code, constructor)
                            code += ("ret = lar_new_obj_%s(lar_fiber, %s)" %
                                     (coi_name, ", ".join(["arg_%d" % i for i in xrange(len(constructor.arg_map))])))
                            code += "has_ret = true"
                            code += "return"

        for closure in module.closure_map.itervalues():
            coi_name = _gen_coi_name(closure)
            with code.new_blk("type %s struct" % coi_name):
                for method in closure.method_map.itervalues():
                    code += "cm_%s func (%s) %s" % (method.name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))
            for method in closure.method_map.itervalues():
                with code.new_blk("func (this *%s) %s(%s) %s" %
                                  (coi_name, _gen_method_name_code(method), _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))):
                    code.record_tb_info(_POS_INFO_IGNORE)
                    code += ("%sthis.cm_%s(%s)" %
                             ("" if method.type.is_void else "return ", method.name,
                              ", ".join(["lar_fiber"] + ["l_%s" % name for name in method.arg_map])))
            output_reflect_method(code, closure, "<%s>" % closure)

        for file_name, native_code_list in module.global_native_code_map.iteritems():
            code.switch_file(file_name)
            for native_code in native_code_list:
                _output_native_code(code, native_code, "")

        def output_cls_reflect_method(code):
            if cls.module is larc_module.array_module and cls.name == "Arr":
                #数组对象的类型名要处理一下
                assert len(cls.gtp_map) == 1
                cls_type_name = cls.gtp_map.value_at(0).to_str(ignore_builtins_module_prefix = True) + "[]"
            else:
                cls_type_name = larc_type.gen_type_from_cls(cls).to_str(ignore_builtins_module_prefix = True)
            output_reflect_method(code, cls, cls_type_name)
        for cls in [i for i in module.cls_map.itervalues() if not i.gtp_name_list] + list(module.gcls_inst_map.itervalues()):
            code.switch_file(cls.file_name)
            lar_cls_name = _gen_coi_name(cls)
            output_cls_reflect_method(code)
            with code.new_blk("type %s struct" % (lar_cls_name)):
                for native_code in cls.native_code_list:
                    _output_native_code(code, native_code, "")
                for attr in cls.attr_map.itervalues():
                    code += "m_%s %s" % (attr.name, _gen_type_name_code(attr.type))
            with code.new_blk("func lar_new_obj_%s(%s) *%s" % (lar_cls_name, _gen_arg_def(cls.construct_method.arg_map), lar_cls_name)):
                code += "o := new(%s)" % lar_cls_name
                code.record_tb_info(_POS_INFO_IGNORE)
                code += ("o.lar_construct_method_%s(%s)" %
                         (cls.name, ", ".join(["lar_fiber"] + ["l_%s" % name for name in cls.construct_method.arg_map])))
                code += "return o"
            for method in [cls.construct_method] + list(cls.method_map.itervalues()):
                if method is cls.construct_method:
                    assert method.name == cls.name
                    method_name = "lar_construct_method_" + method.name
                else:
                    method_name = _gen_method_name_code(method)
                with code.new_blk("func (this *%s) %s(%s) %s" %
                                  (lar_cls_name, method_name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))):
                    if method.is_method:
                        _output_stmt_list(code, method.stmt_list)
                        code += "return %s" % _gen_default_value_code(method.type)
                    else:
                        assert method.is_usemethod
                        code.record_tb_info((method.attr.type.token, "<usemethod>"))
                        code += ("%sthis.m_%s.%s(%s)" %
                                 ("" if method.type.is_void else "return ", method.attr.name, method_name,
                                  ", ".join(["lar_fiber"] + ["l_%s" % name for name in method.arg_map])))

        for func in [i for i in module.func_map.itervalues() if not i.gtp_name_list] + list(module.gfunc_inst_map.itervalues()):
            code.switch_file(func.file_name)
            if module.name == "__builtins" and func.name in ("_catch_throwable", "catch"):
                assert not func.arg_map
                arg_def = "lar_fiber *lar_go_stru_fiber, _go_recovered interface{}"
            else:
                arg_def = _gen_arg_def(func.arg_map)
            with code.new_blk("func %s(%s) %s" % (_gen_func_name(func), arg_def, _gen_type_name_code(func.type))):
                _output_stmt_list(code, func.stmt_list)
                code += "return %s" % _gen_default_value_code(func.type)

def _output_util():
    #生成普通util代码
    with _Code("%s/%s.util.go" % (_out_prog_dir, _prog_module_name)) as code:
        #生成数组alias代码
        for tp in larc_type.array_type_set:
            assert tp.is_array
            arr_type = larc_type.gen_arr_type(tp)
            dim_count = tp.array_dim_count
            while tp.is_array:
                tp = tp.to_elem_type()
            tp_name = _gen_non_array_type_name(tp)
            #数组结构体名和元素类型的code
            arr_tp_name = _gen_arr_tp_name(tp_name, dim_count)
            code += "type %s = %s" % (arr_tp_name, _gen_type_name_code_without_star(arr_type))

        #traceback信息
        with code.new_blk("var lar_util_tb_map = map[lar_util_go_tb]*lar_util_lar_tb"):
            for (go_file_name, go_line_no), tb_info in _tb_map.iteritems():
                if tb_info is None:
                    code += "lar_util_go_tb{file: %s, line: %d}: nil," % (_gen_str_literal(go_file_name), go_line_no)
                else:
                    lar_file_name, lar_line_no, lar_fom_name = tb_info
                    code += ("lar_util_go_tb{file: %s, line: %d}: &lar_util_lar_tb{file: %s, line: %d, fom_name: %s}," %
                             (_gen_str_literal(go_file_name), go_line_no, _gen_str_literal(lar_file_name), lar_line_no,
                              _gen_str_literal(lar_fom_name)))

        #模块输出名和实际名字的映射信息
        assert len(_module_name_code_map) == len(set(_module_name_code_map.itervalues()))
        with code.new_blk("var lar_util_module_name_map = map[string]string"):
            for name, name_code in _module_name_code_map.iteritems():
                code += "`%s`: `%s`," % (name_code, name)

        #反射需要的所有类型的零值
        with code.new_blk("var lar_reflect_all_zvs = []interface{}"):
            for zv_code in _reflect_zvs:
                code += "%s," % zv_code

def _make_prog():
    if platform.system() in ("Darwin", "Linux"):
        try:
            p = subprocess.Popen(["go", "env", "GOPATH"], stdout = subprocess.PIPE)
        except OSError:
            larc_common.exit("无法执行go命令")
        rc = p.wait()
        if rc != 0:
            larc_common.exit("通过go env获取GOPATH失败")
        go_path = p.stdout.read().strip()
        os.environ["GOPATH"] = out_dir + ":" + go_path
        rc = os.system("go build -o %s %s" % (_exe_file, _main_pkg_file))
        if rc != 0:
            larc_common.exit("go build失败")
    else:
        larc_common.exit("不支持在平台'%s'生成可执行程序" % platform.system())

def _make_out_bin(out_bin):
    global _exe_file
    if platform.system() in ("Darwin", "Linux"):
        pass
    else:
        raise Exception("Bug")
    if os.path.exists(_exe_file):
        shutil.copy(_exe_file, out_bin)
        _exe_file = out_bin #用于后面可能的run过程
    else:
        larc_common.exit("找不到可执行文件[%s]" % _exe_file)

def _run_prog(args_for_run):
    if platform.system() in ("Darwin", "Linux"):
        pass
    else:
        raise Exception("Bug")
    if os.path.exists(_exe_file):
        os.execv(_exe_file, [_exe_file] + args_for_run)
    else:
        larc_common.exit("找不到可执行文件[%s]" % _exe_file)

_GO_ANY_INTF_TYPE_NAME_CODE = None
_ANY_INTF_TYPE_NAME_CODE = None
_STR_TYPE_NAME_CODE = None

def output(out_bin, need_run_prog, args_for_run):
    output_start_time = time.time()
    larc_common.verbose_log("开始输出go代码")

    _gen_all_module_name_code_map()

    global _GO_ANY_INTF_TYPE_NAME_CODE, _ANY_INTF_TYPE_NAME_CODE, _STR_TYPE_NAME_CODE
    _GO_ANY_INTF_TYPE_NAME_CODE = _gen_type_name_code(larc_type.GO_ANY_INTF_TYPE)
    _ANY_INTF_TYPE_NAME_CODE = _gen_type_name_code(larc_type.ANY_INTF_TYPE)
    _STR_TYPE_NAME_CODE = _gen_type_name_code(larc_type.STR_TYPE)

    global _out_prog_dir, _prog_module_name, _exe_file, _main_pkg_file, _curr_module

    main_module = larc_module.module_map[main_module_name]
    main_module_name_code = _gen_module_name_code(main_module)

    _out_prog_dir = "%s/src/lar_prog_%s" % (out_dir, main_module_name_code)

    shutil.rmtree(out_dir, True)
    os.makedirs(_out_prog_dir)

    _prog_module_name = "lar_prog_" + main_module_name_code

    _exe_file = "%s/%s" % (out_dir, main_module_name_code)

    _main_pkg_file = "%s/src/lar_prog.%s.P.go" % (out_dir, main_module_name_code)

    _output_main_pkg()
    _output_booter()
    for _curr_module in larc_module.module_map.itervalues():
        _output_module()
    _output_util()

    larc_common.verbose_log("go代码输出完毕，耗时%.2f秒" % (time.time() - output_start_time))

    go_build_start_time = time.time()
    larc_common.verbose_log("开始执行go build")
    _make_prog()
    if out_bin is not None:
        _make_out_bin(out_bin)
    larc_common.verbose_log("go build完毕，耗时%.2f秒" % (time.time() - go_build_start_time))

    larc_common.output_all_warning()

    if need_run_prog:
        _run_prog(args_for_run)
