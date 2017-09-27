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
    if tp.is_obj_type:
        type_name_code = "*" + type_name_code
    return "*[]" * array_dim_count + type_name_code

def _gen_new_arr_func_name(tp, dim_count, new_dim_count):
    assert not tp.is_array and dim_count >= new_dim_count > 0
    _reg_new_arr_func_info(tp, dim_count)
    return "lar_util_new_arr_%s_%d_%d" % (_gen_non_array_type_name(tp), dim_count, new_dim_count)

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
    with _Code(os.path.join(out_prog_dir, "lar_prog.%s.go" % main_module_name), "main") as code:
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
            code += ("argv := %s((%s)(len(os.Args)))" %
                     (_gen_new_arr_func_name(larc_type.STR_TYPE, 1, 1), _gen_type_name_code(larc_type.ULONG_TYPE)))
            with code.new_blk("for i := 0; i < len(os.Args); i ++"):
                code += "argv[i] = lar_util_create_lar_str_from_go_str(os.Args[i])"
            code += "lar_env_init_mod___builtins()"
            code += "lar_env_init_mod_%s()" % main_module_name
            code += "return %s(argv)" % _gen_func_name(larc_module.module_map[main_module_name].get_main_func())

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
    return "todo"

def _gen_expr_code(expr):
    if expr.is_se_expr:
        return _gen_se_expr_code(expr)
    assert expr.is_expr

    if expr.op == "force_convert":
        return "todo"

    if expr.op in ("~", "!", "neg", "pos"):
        return "todo"

    if expr.op in larc_token.BINOCULAR_OP_SYM_SET:
        return "todo"

    if expr.op == "?:":
        return "todo"

    if expr.op == "local_var":
        return "todo"

    if expr.op == "literal":
        return "todo"

    if expr.op == "new":
        return "todo"

    if expr.op == "new_array":
        return "todo"

    if expr.op == "this":
        return "todo"

    if expr.op == "[]":
        return "todo"

    if expr.op == "array.size":
        return "todo"

    if expr.op == "str_format":
        return "todo"

    if expr.op == "call_method":
        return "todo"

    if expr.op == ".":
        return "todo"

    if expr.op == "global_var":
        return "todo"

    if expr.op == "call_func":
        return "todo"

    if expr.op == "this.attr":
        return "todo"

    if expr.op == "call_this.method":
        return "todo"

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
                    loop_expr_code = "func () {%s}()" % "; ".join([_gen_expr_code(e) for e in loop_expr_list])
                with code.new_blk("for ; %s; %s" % (judge_expr_code, loop_expr_code)):
                    _output_stmt_list(code, stmt.stmt_list)
            continue
        if stmt.type == "while":
            with code.new_blk("for (%s)" % stmt.expr):
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
            code += ("var l_%s %s = (%s)" %
                     (stmt.name, _gen_type_name_code(stmt_list.var_map[stmt.name]), _gen_expr_code(stmt.expr)))
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
            code += ("var lar_literal_str_%s_%d %s = lar_util_create_lar_str_from_go_str(%s)" %
                     (module.name, id(t), _gen_type_name_code(larc_type.STR_TYPE), _gen_str_literal(t.value)))

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
                    assert gv.expr is not None
                    code += "%s = %s" % (_gen_gv_name(gv), _gen_expr_code(gv.expr))

        for cls in list(module.cls_map.itervalues()) + list(module.gcls_inst_map.itervalues()):
            if "native" in cls.decr_set:
                #todo reg arrs
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
                    _output_stmt_list(code, method.stmt_list)
                    code += "return %s" % _gen_default_value_code(method.type)

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
        native_code_file_path_name = os.path.join(module.dir, "native_go", "lar_native.%s.go" % module.name)
        if not os.path.exists(native_code_file_path_name):
            larc_common.exit("找不到模块'%s'的go语言的native部分实现：[%s]" % (module.name, native_code_file_path_name))
        f = open(os.path.join(out_prog_dir, "%s.mod.%s.native.go" % (prog_module_name, module.name)), "w")
        print >> f, "package %s" % prog_module_name
        print >> f
        f.write(open(native_code_file_path_name).read())
        f.close()

def _output_util():
    raise "todo"

def _output_makefile():
    if sys.platform.lower().startswith("win"):
        f = open(os.path.join(out_dir, "make.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src/lar_prog_%s/lar_prog.%s.go" % (main_module_name, main_module_name, main_module_name)
        print >> f, "@if %ERRORLEVEL% == 0 goto success"
        print >> f, "@pause"
        print >> f, ":success"
        f = open(os.path.join(out_dir, "make_and_run.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src/lar_prog_%s/lar_prog.%s.go" % (main_module_name, main_module_name, main_module_name)
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

    runtime_dir = os.path.join(runtime_dir, "go")
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
