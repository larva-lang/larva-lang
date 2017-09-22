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
        _gen_new_arr_func(tp, dim - 1, new_dim - 1)
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
            code += "return %s(argv)" % _gen_func_name(larc_module.module_map[main_module_name].get_main_func())

def _gen_expr_code(expr):
    if expr.op in ("~", "!", "neg", "pos"):
        e, = expr.arg
        expr_code = _gen_expr_code(e)
        if expr.op == "!":
            return "(%s).Method___bool().Bool_not()" % expr_code
        return "(%s).Method__%s()" % (expr_code, {"~" : "inv"}.get(expr.op, expr.op))

    if expr.op in larc_token.BINOCULAR_OP_SYM_SET:
        ea, eb = expr.arg
        ea_code = _gen_expr_code(ea)
        eb_code = _gen_expr_code(eb)
        if expr.op in ("&&", "||"):
            return ("larva_obj.Lar_bool_from_bool((%s).Method___bool().As_bool() %s (%s).Method___bool().As_bool())" %
                    (ea_code, expr.op, eb_code))
        if expr.op in ("==", "!="):
            return "(%s).Method___eq(%s)%s" % (ea_code, eb_code, "" if expr.op == "==" else ".Bool_not()")
        if expr.op in ("<", "<=", ">", ">="):
            return "larva_obj.Lar_bool_from_bool((%s).Method___cmp(%s).As_int() %s 0)" % (ea_code, eb_code, expr.op)
        return ("(%s).Method___%s(%s)" %
                (ea_code,
                 {"+" : "add", "-" : "sub", "*" : "mul", "/" : "div", "%" : "mod", "&" : "and", "|" : "or", "^" : "xor", "<<" : "shl",
                  ">>" : "shr"}[expr.op], eb_code))

    if expr.op == "?:":
        ea, eb, ec = expr.arg
        ea_code = _gen_expr_code(ea)
        eb_code = _gen_expr_code(eb)
        ec_code = _gen_expr_code(ec)
        return """func () larva_obj.LarPtr {
if (%s).Method___bool().As_bool() {
return (%s)
}
return (%s)
}()""" % (ea_code, eb_code, ec_code)

    if expr.op == "this.attr":
        name = expr.arg
        return "self.M_%s" % name

    if expr.op == "call_this.method":
        method, el = expr.arg
        return "self.This.Method_%s_%d(%s)" % (method.name, len(el), ", ".join([_gen_expr_code(e) for e in el]))

    if expr.op == "global_var":
        gv = expr.arg
        return "%sG_%s" % ("" if gv.module is curr_module else "lar_mod_%s." % gv.module.name, gv.name)

    if expr.op == "call_func":
        func, el = expr.arg
        return ("%sFunc_%s_%d(%s)" %
                ("" if func.module is curr_module else "lar_mod_%s." % func.module.name, func.name, len(el),
                 ", ".join([_gen_expr_code(e) for e in el])))
        
    if expr.op == "new":
        cls, el = expr.arg
        return ("%sNewLarObj_%s_%d(%s)" %
                ("" if cls.module is curr_module else "lar_mod_%s." % cls.module.name, cls.name, len(el),
                 ", ".join([_gen_expr_code(e) for e in el])))
        
    if expr.op == "tuple":
        el = expr.arg
        return "lar_mod___builtins.NewLarObj_tuple_from_var_arg(%s)" % ", ".join([_gen_expr_code(e) for e in el])
        
    if expr.op == "list":
        el = expr.arg
        return "lar_mod___builtins.NewLarObj_list_from_var_arg(%s)" % ", ".join([_gen_expr_code(e) for e in el])
        
    if expr.op == "list_compr":
        e, for_var_set, lvalue, iter_obj = expr.arg
        return """func () larva_obj.LarPtr {
var tmp_list larva_obj.LarPtr = lar_mod___builtins.NewLarObj_list_0()
%s
for iter := (%s).Method_iter_new_0(); !iter.Method_iter_end_0().As_bool(); iter.Method_iter_next_0() {
%s
%s
tmp_list.Method_add_1(%s)
}
return tmp_list
}()""" % ("\n".join(["var l_%s larva_obj.LarPtr" % name for name in for_var_set]), _gen_expr_code(iter_obj),
          "\n".join(["l_%s.Touch()" % name for name in for_var_set]), _gen_assign_code(lvalue, "iter.Method_iter_get_item_0()"),
          _gen_expr_code(e))
        
    if expr.op == "dict":
        ekv_list = expr.arg
        raise Exception("not implemented")
        return #todo
        
    if expr.op == "dict_compr":
        ek, ev, for_var_set, lvalue, iter_obj = expr.arg
        raise Exception("not implemented")
        return #todo
        
    if expr.op == "local_var":
        name = expr.arg
        return "l_%s" % name

    if expr.op == "literal":
        t = expr.arg
        assert t.is_literal
        if t.is_literal("nil"):
            return "larva_obj.NIL"
        if t.is_literal("bool"):
            return "larva_obj.%s" % t.value.upper()
        return "literal_%d" % id(t)

    if expr.op == "this":
        return "self.To_lar_ptr()"

    if expr.op == "[]":
        e_obj, e_idx = expr.arg
        return "(%s).Method___get_item(%s)" % (_gen_expr_code(e_obj), _gen_expr_code(e_idx))

    if expr.op == "[:]":
        e_obj, el = expr.arg
        raise Exception("not implemented")
        return #todo

    if expr.op == "call_method":
        callee, t, el = expr.arg
        return "(%s).Method_%s_%d(%s)" % (_gen_expr_code(callee), t.value, len(el), ", ".join([_gen_expr_code(e) for e in el]))

    if expr.op == ".":
        e, t = expr.arg
        return "(%s).Attr_get_%s()" % (_gen_expr_code(e), t.value)
        
    raise Exception("Bug")

def _output_assign(code, lvalue, expr_code, assign_sym = "="):
    assert lvalue.is_lvalue
    if assign_sym == "=":
        if lvalue.op == "this.attr":
            name = lvalue.arg
            code += "self.M_%s = (%s)" % (name, expr_code)
            return
        if lvalue.op == "global_var":
            gv = lvalue.arg
            code += "%sG_%s = (%s)" % ("" if gv.module is curr_module else "lar_mod_%s." % gv.module.name, gv.name, expr_code)
            return
        if lvalue.op == "local_var":
            name = lvalue.arg
            code += "l_%s = (%s)" % (name, expr_code)
            return
        if lvalue.op == "[]":
            e_obj, e_idx = lvalue.arg
            code += "(%s).Method___set_item(%s, %s)" % (_gen_expr_code(e_obj), _gen_expr_code(e_idx), expr_code)
            return
        if lvalue.op == "[:]":
            e_obj, el = lvalue.arg
            raise Exception("not implemented")
            return #todo
        if lvalue.op == ".":
            e, t = lvalue.arg
            code += "(%s).Attr_set_%s(%s)" % (_gen_expr_code(e), t.value, expr_code)
            return
        print lvalue.op
        raise Exception("Bug")
    else:
        assert assign_sym[-1] == "="
        op = {"+" : "add", "-" : "sub", "*" : "mul", "/" : "div", "%" : "mod", "&" : "and", "|" : "or", "^" : "xor", "<<" : "shl",
              ">>" : "shr"}[assign_sym[: -1]]
        if lvalue.op == "this.attr":
            name = lvalue.arg
            code += "self.M_%s.Method___i%s(%s)" % (name, op, expr_code)
            return
        if lvalue.op == "global_var":
            gv = lvalue.arg
            code += "%sG_%s.Method___i%s(%s)" % ("" if gv.module is curr_module else "lar_mod_%s." % gv.module.name, gv.name, op, expr_code)
            return
        if lvalue.op == "local_var":
            name = lvalue.arg
            code += "l_%s.Method___i%s(%s)" % (name, op, expr_code)
            return
        if lvalue.op == "[]":
            e_obj, e_idx = lvalue.arg
            code += "(%s).Method___item_i%s(%s, %s)" % (_gen_expr_code(e_obj), op, _gen_expr_code(e_idx), expr_code)
            return
        if lvalue.op == "[:]":
            e_obj, el = lvalue.arg
            raise Exception("not implemented")
            return #todo
        if lvalue.op == ".":
            e, t = lvalue.arg
            code += "(%s).Attr_i%s_%s(%s)" % (_gen_expr_code(e), op, t.value, expr_code)
            return
        raise Exception("Bug")

def _gen_assign_code(lvalue, expr_code):
    class Code:
        def __init__(self):
            self.l = []
        def __iadd__(self, line):
            self.l.append(line)
            return self
    code = Code()
    _output_assign(code, lvalue, expr_code)
    return "\n".join(code.l)

def _output_stmt_list(code, stmt_list):
    for stmt in stmt_list:
        if stmt.type == "block":
            with code.new_blk(""):
                _output_stmt_list(code, stmt.stmt_list)
        elif stmt.type == "var":
            code += "var l_%s larva_obj.LarPtr = (%s)" % (stmt.name, _gen_expr_code(stmt.expr))
        elif stmt.type in ("break", "continue"):
            code += stmt.type
        elif stmt.type == "return":
            code += "return (%s)" % _gen_expr_code(stmt.expr)
        elif stmt.type == "for":
            with code.new_blk(""):
                for vn in stmt.var_set:
                    code += "var l_%s larva_obj.LarPtr" % vn
                with code.new_blk("for iter := (%s).Method_iter_new_0(); !iter.Method_iter_end_0().As_bool(); iter.Method_iter_next_0()" %
                                  _gen_expr_code(stmt.iter_obj)):
                    for vn in stmt.var_set:
                        code += "l_%s.Touch()" % vn
                    _output_assign(code, stmt.lvalue, "iter.Method_iter_get_item_0()")
                    _output_stmt_list(code, stmt.stmt_list)
        elif stmt.type == "while":
            with code.new_blk("for (%s).Method___bool().As_bool()" % _gen_expr_code(stmt.expr)):
                _output_stmt_list(code, stmt.stmt_list)
        elif stmt.type == "do":
            with code.new_blk("for first := true; first || (%s).Method___bool().As_bool(); first = false" % _gen_expr_code(stmt.expr)):
                _output_stmt_list(code, stmt.stmt_list)
        elif stmt.type == "if":
            assert len(stmt.if_expr_list) == len(stmt.if_stmt_list_list)
            for i, if_expr in enumerate(stmt.if_expr_list):
                if_stmt_list = stmt.if_stmt_list_list[i]
                with code.new_blk("%sif (%s).Method___bool().As_bool()" % ("" if i == 0 else "else ", _gen_expr_code(if_expr))):
                    _output_stmt_list(code, if_stmt_list)
                if stmt.else_stmt_list is not None:
                    with code.new_blk("else"):
                        _output_stmt_list(code, stmt.else_stmt_list)
        elif stmt.type in larc_token.INC_DEC_SYM_SET:
            code += "(%s).Method___%s()" % (_gen_expr_code(stmt.lvalue), {"++" : "inc", "--" : "dec"}[stmt.type])
        elif stmt.type == "expr":
            code += _gen_expr_code(stmt.expr)
        elif stmt.type in larc_token.ASSIGN_SYM_SET:
            _output_assign(code, stmt.lvalue, _gen_expr_code(stmt.expr), stmt.type)
        else:
            raise Exception("Bug")

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

curr_module = None
def _output_module():
    module = curr_module
    has_native_item = module.has_native_item()
    module_file_name = os.path.join(out_dir, "src", "%s.mod.%s.go" % (prog_module_name, module.name))
    with _Code(module_file_name) as code:
        code += ""
        for t in module.literal_str_list:
            assert t.is_literal("str")
            code += ("var lar_literal_str_%d %s = lar_util_create_lar_str_from_go_str(%s)" %
                     (id(t), _gen_tp_name(larc_type.STR_TYPE), _gen_str_literal(t.value)))

        code += ""
        code += "var mod_inited bool = false"
        with code.new_blk("func Init()", False):
            with code.new_blk("if !mod_inited"):
                code += "larva_obj.Init()"
                code += "larva_exc.Init()"
                if module.name != "__builtins":
                    code += "lar_mod___builtins.Init()"
                for dep_module_name in module.dep_module_set:
                    if dep_module_name != "__builtins":
                        code += "lar_mod_%s.Init()" % dep_module_name
                if has_native_item:
                    code += "NativeInit()"
                for gv in module.global_var_map.itervalues():
                    if gv.is_native:
                        continue
                    code += "G_%s = larva_obj.NIL" % gv.name
                for var_name, expr in module.global_var_init_map.iteritems():
                    if expr is not None:
                        lvalue = larc_expr.var_name_to_expr(var_name, module = curr_module)
                        _output_assign(code, lvalue, _gen_expr_code(expr))
                code += "mod_inited = true"

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

        code += ""
        for gv in module.global_var_map.itervalues():
            if gv.is_native:
                continue
            code += "var G_%s larva_obj.LarPtr" % gv.name

        for func in module.func_map.itervalues():
            if func.is_native:
                continue
            args = ", ".join(["l_%s" % a for a in func.arg_set]) + " larva_obj.LarPtr" if func.arg_set else ""
            with code.new_blk("func Func_%s_%d(%s) larva_obj.LarPtr" % (func.name, len(func.arg_set), args)):
                _output_stmt_list(code, func.stmt_list)
                code += "return larva_obj.NIL"

    if has_native_item:
        shutil.copy(os.path.join(module.dir, "go", "lar_ext_mod.%s.go" % module.name), mod_dir)

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
