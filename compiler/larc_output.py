#coding=utf8

"""
输出为go代码
"""

import os
import shutil
import sys

import larc_common
import larc_module
import larc_token
import larc_expr
import larc_type

main_module_name = None
out_dir = None
runtime_dir = None

out_prog_dir = None
prog_module_name = None

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

def _gen_coi_name(coi):
    for i in "cls", "gcls_inst", "intf", "gintf_inst":
        if eval("coi.is_" + i):
            coi_name = "lar_" + i
            break
    else:
        raise Exception("Bug")
    coi_name += "_%d_%s_%d_%s" % (len(coi.module.name), coi.module.name, len(coi.name), coi.name)
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
    return "lar_type_%s" % tp.name

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
    func_name += "_%d_%s_%d_%s" % (len(func.module.name), func.module.name, len(func.name), func.name)
    if func.is_gfunc_inst:
        #泛型实例还需增加泛型参数信息
        func_name += "_%d" % len(func.gtp_map)
        for tp in func.gtp_map.itervalues():
            func_name += "_%s" % _gen_non_array_type_name(tp)
    return func_name

def _output_main_pkg():
    with _Code(os.path.join(out_dir, "src", "lar_prog.%s.go" % main_module_name), "main") as code:
        with code.new_blk("import"):
            code += '"os"'
            code += '"%s"' % prog_module_name
        with code.new_blk("func main()"):
            code += "os.Exit(%s.Lar_booter_start_prog())" % prog_module_name

def _output_booter():
    with _Code(os.path.join(out_prog_dir, "%s.booter.go" % prog_module_name)) as code:
        with code.new_blk("import"):
            code += '"os"'
        with code.new_blk("func Lar_booter_start_prog() int"):
            code += "argv := %s((lar_type_long)(len(os.Args)))" % (_gen_new_arr_func_name(larc_type.STR_TYPE, 1, 1))
            with code.new_blk("for i := 0; i < len(os.Args); i ++"):
                code += "(*argv)[i] = lar_util_create_lar_str_from_go_str(os.Args[i])"
            code += "lar_env_init_mod___builtins()"
            code += "lar_env_init_mod_%s()" % main_module_name
            code += "return int(%s(argv))" % _gen_func_name(larc_module.module_map[main_module_name].get_main_func())

def _gen_str_literal_name(t):
    return "lar_literal_str_%s_%d" % (curr_module.name, id(t))

def _gen_str_literal(s):
    code_list = []
    for c in s:
        asc = ord(c)
        assert 0 <= asc <= 0xFF
        if asc < 32 or asc > 126 or asc in ('"', "\\"):
            code_list.append("\\%03o" % asc)
        else:
            code_list.append(c)
    return '"%s"' % "".join(code_list)

def _gen_gv_name(gv):
    return "lar_gv_%d_%s_%d_%s" % (len(gv.module.name), gv.module.name, len(gv.name), gv.name)

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
        return "(%s)(%s)" % (_gen_type_name_code(tp), _gen_expr_code(e))

    if expr.op in ("~", "!", "neg", "pos"):
        e = expr.arg
        return "%s(%s)" % ({"~" : "^", "!" : "!", "neg" : "-", "pos" : "+"}[expr.op], _gen_expr_code(e))

    if expr.op in larc_token.BINOCULAR_OP_SYM_SET:
        ea, eb = expr.arg
        return "(%s) %s (%s)" % (_gen_expr_code(ea), expr.op, _gen_expr_code(eb))

    if expr.op == "?:":
        ea, eb, ec = expr.arg
        return """func () %s {
if (%s) {
return (%s)
}
return (%s)
}()""" % (_gen_type_name_code(expr.type), _gen_expr_code(ea), _gen_expr_code(eb), _gen_expr_code(ec))

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
        if literal_type == "int":
            assert tp == larc_type.LITERAL_INT_TYPE
            return "%d" % t.value
        if literal_type == "str":
            return _gen_str_literal_name(t)
        return "%s(%s)" % (_gen_type_name_code(tp), t.value)

    if expr.op == "new":
        expr_list = expr.arg
        tp = expr.type
        return "lar_new_obj_%s(%s)" % (_gen_non_array_type_name(tp), _gen_expr_list_code(expr_list))

    if expr.op == "new_array":
        tp, size_list = expr.arg
        _reg_new_arr_func_info(tp, len(size_list))
        try:
            new_dim_count = size_list.index(None)
        except ValueError:
            new_dim_count = len(size_list)
        assert new_dim_count > 0
        return "%s(%s)" % (_gen_new_arr_func_name(tp, len(size_list), new_dim_count),
                           ", ".join(["(lar_type_long)(%s)" % _gen_expr_code(e) for e in size_list[: new_dim_count]]))

    if expr.op == "this":
        return "this"

    if expr.op == "[]":
        arr_e, e = expr.arg
        return "(*(%s))[%s]" % (_gen_expr_code(arr_e), _gen_expr_code(e))

    if expr.op == "array.size":
        arr_e = expr.arg
        return "(lar_type_long)(len(*(%s)))" % _gen_expr_code(arr_e)

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
        return "%s(%s)" % (_gen_func_name(func), _gen_expr_list_code(expr_list))

    if expr.op == "this.attr":
        attr = expr.arg
        return "this.m_%s" % attr.name

    if expr.op == "call_this.method":
        method, expr_list = expr.arg
        return "this.method_%s(%s)" % (method.name, _gen_expr_list_code(expr_list))

    raise Exception("Bug")

def _gen_arg_def(arg_map):
    return ", ".join(["l_%s %s%s" % (name, "*" if tp.is_ref else "", _gen_type_name_code(tp)) for name, tp in arg_map.iteritems()])

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
            if stmt.expr is None:
                code += "return"
            else:
                code += "return (%s)" % _gen_expr_code(stmt.expr)
            continue
        if stmt.type == "for":
            with code.new_blk(""):
                if len(stmt.for_var_map) == 0:
                    for expr in stmt.init_expr_list:
                        code += _gen_expr_code(expr)
                else:
                    assert len(stmt.for_var_map) == len(stmt.init_expr_list)
                    for (name, tp), expr in zip(stmt.for_var_map.iteritems(), stmt.init_expr_list):
                        code += "var l_%s %s = (%s)" % (name, _gen_type_name_code(tp), _gen_expr_code(expr))
                if stmt.judge_expr is None:
                    judge_expr_code = ""
                else:
                    judge_expr_code = _gen_expr_code(stmt.judge_expr)
                if len(stmt.loop_expr_list) == 0:
                    loop_expr_code = ""
                elif len(stmt.loop_expr_list) == 1:
                    loop_expr_code = _gen_expr_code(stmt.loop_expr_list[0])
                else:
                    loop_expr_code = "func () {%s}()" % "; ".join([_gen_expr_code(e) for e in stmt.loop_expr_list])
                with code.new_blk("for ; %s; %s" % (judge_expr_code, loop_expr_code)):
                    _output_stmt_list(code, stmt.stmt_list)
            continue
        if stmt.type == "while":
            with code.new_blk("for (%s)" % _gen_expr_code(stmt.expr)):
                _output_stmt_list(code, stmt.stmt_list)
            continue
        if stmt.type == "if":
            assert len(stmt.if_expr_list) == len(stmt.if_stmt_list_list)
            for i, (if_expr, if_stmt_list) in enumerate(zip(stmt.if_expr_list, stmt.if_stmt_list_list)):
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
            code += ("var l_%s %s = (%s)" % (stmt.name, _gen_type_name_code(stmt_list.var_map[stmt.name]), expr_code))
            continue
        if stmt.type == "expr":
            code += _gen_expr_code(stmt.expr)
            continue
        raise Exception("Bug")

curr_module = None
def _output_module():
    module = curr_module
    has_native_item = module.has_native_item()
    module_file_name = os.path.join(out_prog_dir, "%s.mod.%s.go" % (prog_module_name, module.name))
    with _Code(module_file_name) as code:
        code += ""
        for t in module.literal_str_list:
            assert t.is_literal("str")
            code += ("var %s %s = lar_util_create_lar_str_from_go_str(%s)" %
                     (_gen_str_literal_name(t), _gen_type_name_code(larc_type.STR_TYPE), _gen_str_literal(t.value)))

        code += ""
        for gv in module.global_var_map.itervalues():
            code += "var %s %s = %s" % (_gen_gv_name(gv), _gen_type_name_code(gv.type), _gen_default_value_code(gv.type))

        code += ""
        mod_inited_flag_name = "lar_env_inited_flag_of_mod_%s" % module.name
        code += "var %s bool = false" % mod_inited_flag_name
        with code.new_blk("func lar_env_init_mod_%s()" % module.name, False):
            with code.new_blk("if !%s" % mod_inited_flag_name):
                code += "%s = true" % mod_inited_flag_name
                for dep_module_name in module.dep_module_set:
                    code += "lar_env_init_mod_%s()" % dep_module_name
                for gv in module.global_var_map.itervalues():
                    if gv.expr is not None:
                        code += "%s = %s" % (_gen_gv_name(gv), _gen_expr_code(gv.expr))

        for cls in list(module.cls_map.itervalues()) + list(module.gcls_inst_map.itervalues()):
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
                code += "o.method_%s(%s)" % (cls.name, ", ".join(["l_%s" % name for name in cls.construct_method.arg_map]))
                code += "return o"
            for method in [cls.construct_method] + list(cls.method_map.itervalues()):
                with code.new_blk("func (this *%s) method_%s(%s) %s" %
                                  (lar_cls_name, method.name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))):
                    if method.is_method:
                        _output_stmt_list(code, method.stmt_list)
                        code += "return %s" % _gen_default_value_code(method.type)
                    else:
                        assert method.is_usemethod
                        code += ("%sthis.m_%s.method_%s(%s)" %
                                 ("" if method.type.is_void else "return ", method.attr.name, method.name,
                                  ", ".join(["l_%s" % name for name in method.arg_map])))

        for intf in list(module.intf_map.itervalues()) + list(module.gintf_inst_map.itervalues()):
            with code.new_blk("type %s interface" % (_gen_coi_name(intf))):
                for method in intf.method_map.itervalues():
                    code += "method_%s(%s) %s" % (method.name, _gen_arg_def(method.arg_map), _gen_type_name_code(method.type))

        for func in list(module.func_map.itervalues()) + list(module.gfunc_inst_map.itervalues()):
            if "native" in func.decr_set:
                _reg_new_arr_func_info(func.type, 0)
                for tp in func.arg_map.itervalues():
                    _reg_new_arr_func_info(tp, 0)
                continue
            with code.new_blk("func %s(%s) %s" % (_gen_func_name(func), _gen_arg_def(func.arg_map), _gen_type_name_code(func.type))):
                _output_stmt_list(code, func.stmt_list)
                code += "return %s" % _gen_default_value_code(func.type)

    if has_native_item:
        native_code_file_path_name = os.path.join(module.dir, "%s.lar_native.go" % module.name)
        if not os.path.exists(native_code_file_path_name):
            larc_common.exit("找不到模块'%s'的go语言的native部分实现：[%s]" % (module.name, native_code_file_path_name))
        f = open(os.path.join(out_prog_dir, "%s.mod.%s.native.go" % (prog_module_name, module.name)), "w")
        print >> f, "package %s" % prog_module_name
        print >> f
        f.write(open(native_code_file_path_name).read())
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
                arg_code = ", ".join(["d%d_size" % i for i in xrange(new_dim_count)]) + " lar_type_long"
                arr_tp_name_code = "*[]" * dim_count + tp_name_code
                if new_dim_count == 1:
                    elem_type_name_code = arr_tp_name_code[3 :]
                    if (elem_type_name_code[0] == "*" or elem_type_name_code.startswith("lar_intf") or
                        elem_type_name_code.startswith("lar_gintf")):
                        elem_code = "nil"
                    elif elem_type_name_code.startswith("lar_type_bool"):
                        elem_code = "false"
                    else:
                        assert elem_type_name_code.startswith("lar_type")
                        elem_code = "0"
                else:
                    assert new_dim_count > 1
                    elem_code = "%s(%s)" % (_gen_new_arr_func_name_by_tp_name(tp_name, dim_count - 1, new_dim_count - 1), 
                                            ", ".join(["d%d_size" % i for i in xrange(1, new_dim_count)]))
                with code.new_blk("func %s(%s) %s" % (new_arr_func_name, arg_code, arr_tp_name_code)):
                    code += "arr := make(%s, d0_size)" % arr_tp_name_code[1 :]
                    with code.new_blk("for i := lar_type_long(0); i < d0_size; i ++"):
                        code += "arr[i] = %s" % elem_code
                    code += "return &arr"

def _output_makefile():
    if sys.platform.lower().startswith("win"):
        f = open(os.path.join(out_dir, "make.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src/lar_prog.%s.go" % (main_module_name, main_module_name)
        print >> f, "@if %ERRORLEVEL% == 0 goto success"
        print >> f, "@pause"
        print >> f, ":success"
        f = open(os.path.join(out_dir, "make_and_run.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src/lar_prog.%s.go" % (main_module_name, main_module_name)
        print >> f, "@if %ERRORLEVEL% == 0 goto success"
        print >> f, "@pause"
        print >> f, "@exit"
        print >> f, ":success"
        print >> f, "%s.exe" % main_module_name
        print >> f, "@pause"
        print >> f, "@exit"
    else:
        larc_common.exit("不支持在平台'%s'生成make脚本" % sys.platform)

def output():
    global runtime_dir, out_prog_dir, prog_module_name, curr_module

    out_prog_dir = os.path.join(out_dir, "src", "lar_prog_" + main_module_name)

    shutil.rmtree(out_dir, True)
    os.makedirs(out_prog_dir)

    prog_module_name = "lar_prog_" + main_module_name

    _output_main_pkg()
    _output_booter()
    for curr_module in larc_module.module_map.itervalues():
        _output_module()
    _output_util()
    _output_makefile()
