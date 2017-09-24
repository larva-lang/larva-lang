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
            coi_name += "_%s" % _gen_tp_name(tp)
    return coi_name

def _gen_tp_name(tp):
    assert not (tp.is_array or tp.is_nil or tp.is_void or tp.is_literal_int)
    if tp.is_obj_type:
        return _gen_coi_name(tp.get_coi())
    assert tp.token.is_reserved
    return "lar_type_%s" % tp.name

_new_arr_func_name_set = set()
def _gen_new_arr_func_name(tp, dim, new_dim):
    assert not tp.is_array and dim >= new_dim > 0
    func_name = "lar_util_new_arr_%s_%d_%d" % (_gen_tp_name(tp), dim, new_dim)
    _new_arr_func_name_set.add(func_name)
    if new_dim > 1:
        #递归记录需要生成的内层的new_arr_func_name
        _gen_new_arr_func_name(tp, dim - 1, new_dim - 1)
    return func_name

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
            func_name += "_%s" % _gen_tp_name(tp)
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
            code += "argv := %s(%s(len(os.Args)))" % (_gen_new_arr_func_name(larc_type.STR_TYPE, 1, 1), _gen_tp_name(larc_type.ULONG_TYPE))
            with code.new_blk("for i := 0; i < len(os.Args); i ++"):
                code += "argv[i] = lar_util_create_lar_str_from_go_str(os.Args[i])"
            code += "lar_env_init_mod___builtins()"
            code += "lar_env_init_mod_%s" % main_module_name
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

curr_module = None
def _output_module():
    module = curr_module
    has_native_func = module.has_native_func()
    module_file_name = os.path.join(out_prog_dir, "%s.mod.%s.go" % (prog_module_name, module.name))
    with _Code(module_file_name) as code:
        code += ""
        for t in module.literal_str_list:
            assert t.is_literal("str")
            code += ("var lar_literal_str_%s_%d %s = lar_util_create_lar_str_from_go_str(%s)" %
                     (module.name, id(t), _gen_tp_name(larc_type.STR_TYPE), _gen_str_literal(t.value)))

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

        code += ""
        for gv in module.global_var_map.itervalues():
            if gv.type.is_bool_type:
                v = "false"
            elif gv.type.is_number_type:
                v = "0"
            else:
                assert gv.type.is_obj_type
                v = "nil"
            code += "var %s %s = %s" % (_gen_gv_name(gv), _gen_tp_name(gv.type), v)

        for cls in module.class_map.itervalues():
            if cls.is_native:
                continue
            with code.new_blk("type LarObj_%s struct" % cls.name):
                code += "larva_obj.LarObjBase"
                for attr_name in cls.attr_set:
                    code += "M_%s larva_obj.LarPtr" % attr_name
            with code.new_blk("func NewLarObj_%s() *LarObj_%s" % (cls.name, cls.name)):
                code += "o := new(LarObj_%s)" % cls.name
                code += "o.This = o"
                code += 'o.Type_name = "%s.%s"' % (cls.module.name, cls.name)
                code += "return o"
            for attr_name in cls.attr_set:
                with code.new_blk("func (self *LarObj_%s) Attr_get_%s() larva_obj.LarPtr" % (cls.name, attr_name)):
                    code += "return self.M_%s" % attr_name
                with code.new_blk("func (self *LarObj_%s) Attr_set_%s(v larva_obj.LarPtr)" % (cls.name, attr_name)):
                    code += "self.M_%s = v" % attr_name
                for op in "inc", "dec":
                    with code.new_blk("func (self *LarObj_%s) Attr_%s_%s()" % (cls.name, op, attr_name)):
                        code += "self.M_%s.Method___%s()" % (attr_name, op)
                for op in bops:
                    with code.new_blk("func (self *LarObj_%s) Attr_i%s_%s(v larva_obj.LarPtr)" % (cls.name, op, attr_name)):
                        code += "self.M_%s.Method___i%s(v)" % (attr_name, op)
            for method in cls.method_map.itervalues():
                args = ", ".join(["l_%s" % a for a in method.arg_set])
                args_def = args
                if method.arg_set:
                    args_def += " larva_obj.LarPtr"
                if method.name == "__init":
                    with code.new_blk("func NewLarObj_%s_%d(%s) larva_obj.LarPtr" % (cls.name, len(method.arg_set), args_def)):
                        code += "o := NewLarObj_%s()" % cls.name
                        code += "o.Method___init_%d(%s)" % (len(method.arg_set), args)
                        code += "return o.To_lar_ptr()"
                with code.new_blk("func (self *LarObj_%s) Method_%s_%d(%s) larva_obj.LarPtr" %
                                  (cls.name, method.name, len(method.arg_set), args_def)):
                    _output_stmt_list(code, method.stmt_list)
                    code += "return larva_obj.NIL"


        for func in module.func_map.itervalues():
            if func.is_native:
                continue
            args = ", ".join(["l_%s" % a for a in func.arg_set]) + " larva_obj.LarPtr" if func.arg_set else ""
            with code.new_blk("func Func_%s_%d(%s) larva_obj.LarPtr" % (func.name, len(func.arg_set), args)):
                _output_stmt_list(code, func.stmt_list)
                code += "return larva_obj.NIL"

    if has_native_func:
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
