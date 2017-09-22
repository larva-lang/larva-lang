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

curr_module = None

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

def _gen_tp_name(tp):
    assert not tp.is_array
    raise "todo"

_new_arr_func_name_set = set()
def _gen_new_arr_func_name(tp, dim, new_dim):
    assert not tp.is_array and dim >= new_dim > 0
    func_name = "new_arr_%s_%d_%d" % (_gen_tp_name(tp), dim, new_dim)
    _new_arr_func_name_set.add(func_name)
    if new_dim > 1:
        #递归记录需要生成的内层的new_arr_func_name
        _gen_new_arr_func(tp, dim - 1, new_dim - 1)
    return func_name

def _output_main_pkg():
    with _Code(os.path.join(out_prog_dir, "lar_prog.%s.go" % main_module_name), "main") as code:
        with code.new_blk("import"):
            code += '"os"'
            code += '"%s"' % prog_module_name
        with code.new_blk("func main()"):
            code += "os.Exit(%s.Start_prog())" % prog_module_name
    with _Code(os.path.join(out_prog_dir, "%s.booter.go" % prog_module_name)) as code:
        with code.new_blk("import"):
            code += '"os"'
        with code.new_blk("func Start_prog() int"):
            code += "argv := %s(lar_ulong_t(len(os.Args)))" % _gen_new_arr_func_name(larc_type.STR_TYPE, 1, 1)
            with code.new_blk("for i := 0; i < len(os.Args); i ++"):
                code += "argv[i] = create_lar_str_from_go_str(os.Args[i])"

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
    mod_dir = os.path.join(out_dir, "src", "lar_mod_" + module.name)
    os.makedirs(mod_dir)
    with _Code(os.path.join(mod_dir, "lar_mod.%s.go" % module.name)) as code:
        code += "package lar_mod_" + module.name

        with code.new_blk("import"):
            code += '"larva_obj"'
            code += '"larva_exc"'
            if module.name != "__builtins":
                code += '"lar_mod___builtins"'
            for dep_module_name in module.dep_module_set:
                if dep_module_name != "__builtins":
                    code += '"lar_mod_%s"' % dep_module_name

        code += ""
        for t in module.literal_set:
            assert t.is_literal
            if t.is_literal("nil") or t.is_literal("bool"):
                continue
            if t.is_literal("int"):
                code += "var literal_%d larva_obj.LarPtr = larva_obj.LarPtr{M_int : %s}" % (id(t), t.value)
            elif t.is_literal("float"):
                code += "var literal_%d larva_obj.LarPtr = lar_mod___builtins.NewLarObj_float_from_literal(%s)" % (id(t), t.value)
            else:
                assert t.is_literal("str")
                code += ("var literal_%d larva_obj.LarPtr = lar_mod___builtins.NewLarObj_str_from_literal(%s)" %
                         (id(t), _gen_str_literal(t.value)))

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

def _copy_runtime():
    out_runtime_dir = os.path.join(out_dir, "src")
    for pkg_dir in os.listdir(os.path.join(runtime_dir)):
        dst_dir = os.path.join(out_dir, "src", pkg_dir)
        pkg_dir = os.path.join(runtime_dir, pkg_dir)
        if os.path.isdir(pkg_dir):
            shutil.copytree(pkg_dir, dst_dir)

def _complete_runtime_code():
    attr_set = set()
    method_def_set = set()
    for m in larc_module.module_map.itervalues():
        for cls in m.class_map.itervalues():
            for attr_name in cls.attr_set:
                attr_set.add(attr_name)
            for method_name, arg_count in cls.method_map:
                if method_name != "__init" and method_name.startswith("__"):
                    continue
                method_name = "Method_%s" % method_name
                if arg_count == 0:
                    arg_def = ""
                else:
                    arg_def = "%s LarPtr" % ", ".join(["arg_%s" % (i + 1) for i in xrange(arg_count)])
                method_def_set.add("%s_%s(%s) LarPtr" % (method_name, arg_count, arg_def))
    construct_method_def_list = sorted([method_def for method_def in method_def_set if method_def.startswith("Method___init")])
    method_def_list = sorted([method_def for method_def in method_def_set if not method_def.startswith("Method___init")])

    bops_to_go_op = {"add" : "+", "sub" : "-", "mul" : "*", "div" : "/", "mod" : "%", "and" : "&", "or" : "|", "xor" : "^", "shl" : "<<",
                     "shr" : ">>"}
    def op_defs():
        def _op_defs():
            for op in "bool", "str", "inv", "pos", "neg":
                yield "Method___%s()" % op
            yield "Method___get_item(k LarPtr)"
            yield "Method___set_item(k, v LarPtr)"
            for op in "inc", "dec":
                yield "Method___item_%s(k LarPtr)" % op
            for op in bops:
                yield "Method___item_i%s(k, obj LarPtr)" % op
            yield "Method___get_slice(start, stop, step LarPtr)"
            yield "Method___set_slice(start, stop, step, obj LarPtr)"
            for op in "inc", "dec":
                yield "Method___%s()" % op
            for op in "eq", "cmp":
                yield "Method___%s(obj LarPtr)" % op
            for op in bops:
                for prefix in "", "r", "i":
                    yield "Method___%s%s(obj LarPtr)" % (prefix, op)
        for i in _op_defs():
            assert i.startswith("Method___")
            pos = i.find("(")
            assert pos > 0
            op = i[len("Method___") : pos]
            assert op
            yield op, i + " LarPtr"

    larva_obj_dir = os.path.join(out_dir, "src", "larva_obj")

    #自动生成统一化的动态类型接口
    with _Code(os.path.join(larva_obj_dir, "larva_obj.auto_gen.go")) as code:
        code += "package larva_obj"
        with code.new_blk("type LarObjIntf interface"):
            code += "LarObjIntfBase"
            code += ""
            for op, op_def in op_defs():
                code += op_def
            code += ""
            for attr_name in attr_set:
                code += "Attr_get_%s() LarPtr" % attr_name
                code += "Attr_set_%s(v LarPtr)" % attr_name
                for op in "inc", "dec":
                    code += "Attr_%s_%s()" % (op, attr_name)
                for op in bops:
                    code += "Attr_i%s_%s(v LarPtr)" % (op, attr_name)
            code += ""
            for method_def in construct_method_def_list:
                code += method_def
            code += ""
            for method_def in method_def_list:
                code += method_def

    #自动生成所有接口的默认实现
    with _Code(os.path.join(larva_obj_dir, "larva_obj_base.auto_gen.go")) as code:
        code += "package larva_obj"
        with code.new_blk("import"):
            code += '"fmt"'
        for op, op_def in op_defs():
            with code.new_blk("func (self *LarObjBase) %s" % op_def):
                if op == "bool":
                    code += "return TRUE"
                elif op == "str":
                    code += 'return NewLarObj_str_from_literal(fmt.Sprintf("<%v object at %v>", self.Type_name, self))'
                elif op in ("inv", "pos", "neg"):
                    code += ('Lar_panic_string(fmt.Sprintf("%s(%%v instance) not implemented", self.Type_name))' %
                             {"inv" : "~", "pos" : "+", "neg" : "-"}[op])
                elif op in ("get_item", "set_item"):
                    code += ('Lar_panic_string(fmt.Sprintf("(%%v instance)[obj]%s not implemented", self.Type_name))' %
                             (" = obj" if op == "set_item" else ""))
                elif op.startswith("item_"):
                    op = op[len("item_") :]
                    if op in ("inc", "dec"):
                        code += ('Lar_panic_string(fmt.Sprintf("%s(%%v instance)[obj] not implemented", self.Type_name))' %
                                 {"inc" : "++", "dec" : "--"}[op])
                    else:
                        assert op[0] == "i"
                        code += 'return self.This.Method___set_item(k, self.This.Method___get_item(k).Method___%s(obj))' % op[1 :]
                elif op in ("get_slice", "set_slice"):
                    code += ('Lar_panic_string(fmt.Sprintf("(%%v instance)[x:y:z]%s not implemented", self.Type_name))' %
                             (" = obj" if op == "set_slice" else ""))
                elif op in ("inc", "dec"):
                    code += ('Lar_panic_string(fmt.Sprintf("%s(%%v instance) not implemented", self.Type_name))' %
                             {"inc" : "++", "dec" : "--"}[op])
                elif op == "eq":
                    code += "return Lar_bool_from_bool(&self.This == obj.M_obj_ptr)"
                elif op == "cmp":
                    code += 'Lar_panic_string(fmt.Sprintf("(%v instance).__cmp(obj) not implemented", self.Type_name))'
                else:
                    if op[0] == "i" and op[1 :] in bops:
                        code += "return self.This.Method___%s(obj)" % op[1 :]
                    elif op[0] == "r" and op[1 :] in bops:
                        go_op = bops_to_go_op[op[1 :]]
                        if go_op == "%":
                            go_op = "%%"
                        code += ('Lar_panic_string(fmt.Sprintf("(%%v instance) %s (%%v instance) not implemented", '
                                 'obj.Get_type_name(), self.Type_name))' % go_op)
                    else:
                        assert op in bops
                        code += "return obj.Method___r%s(self.To_lar_ptr())" % op
                if code.line_list[-1].lstrip().startswith("Lar_panic_string"):
                    code += "return NIL"

        for attr_name in attr_set:
            with code.new_blk("func (self *LarObjBase) Attr_get_%s() LarPtr" % attr_name):
                code += '''Lar_panic_string(fmt.Sprintf("(%%v instance) doesn't have attr '%s'", self.Type_name))''' % attr_name
                code += "return NIL"
            with code.new_blk("func (self *LarObjBase) Attr_set_%s(v LarPtr)" % attr_name):
                code += '''Lar_panic_string(fmt.Sprintf("(%%v instance) doesn't have attr '%s'", self.Type_name))''' % attr_name
            for op in "inc", "dec":
                with code.new_blk("func (self *LarObjBase) Attr_%s_%s()" % (op, attr_name)):
                    code += '''Lar_panic_string(fmt.Sprintf("(%%v instance) doesn't have attr '%s'", self.Type_name))''' % attr_name
            for op in bops:
                with code.new_blk("func (self *LarObjBase) Attr_i%s_%s(v LarPtr)" % (op, attr_name)):
                    code += '''Lar_panic_string(fmt.Sprintf("(%%v instance) doesn't have attr '%s'", self.Type_name))''' % attr_name

        for method_def in construct_method_def_list + method_def_list:
            assert method_def.startswith("Method_")
            pos = method_def.find("(")
            assert pos > 0
            method_name = method_def[len("Method_") : pos]
            method_name, arg_count = method_name.rsplit("_", 1)
            arg_count = int(arg_count)
            with code.new_blk("func (self *LarObjBase) %s" % method_def):
                code += ('Lar_panic_string(fmt.Sprintf("method (%%v instance).%s with %s args not implemented", self.Type_name))' %
                         (method_name, arg_count))
                code += "return NIL"

    #自动生成LarPtr的所有对应接口的方法
    with _Code(os.path.join(larva_obj_dir, "larva_ptr.auto_gen.go")) as code:
        code += "package larva_obj"
        with code.new_blk("import"):
            code += '"fmt"'
        for op, op_def in op_defs():
            assert op_def.endswith(" LarPtr")
            se_op = (op in ("inc", "dec")) or (op[0] == "i" and op[1 :] in bops)
            if se_op:
                op_def = op_def[: -len(" LarPtr")]
            assert op_def.count("(") == op_def.count(")") == 1
            start_pos = op_def.find("(")
            end_pos = op_def.find(")")
            assert start_pos < end_pos
            args = op_def[start_pos + 1 : end_pos]
            if args:
                assert args.endswith(" LarPtr")
                args = args[: -len(" LarPtr")]
            with code.new_blk("func (ptr %sLarPtr) %s" % ("*" if se_op else "", op_def)):
                with code.new_blk("if ptr.M_obj_ptr != nil"):
                    if se_op:
                        code += "*ptr = (*ptr.M_obj_ptr).Method___%s(%s)" % (op, args)
                        code += "return"
                    else:
                        code += "return (*ptr.M_obj_ptr).Method___%s(%s)" % (op, args)
                if op == "bool":
                    with code.new_blk("if ptr.M_int == 0"):
                        code += "return FALSE"
                    code += "return TRUE"
                elif op == "str":
                    code += 'return NewLarObj_str_from_literal(fmt.Sprint(ptr.M_int))'
                elif op in ("inv", "pos", "neg"):
                    code += "return LarPtr{M_int : (%sptr.M_int)}" % {"inv" : "^", "pos" : "+", "neg" : "-"}[op]
                elif op in ("get_item", "set_item"):
                    code += ('Lar_panic_string(fmt.Sprintf("(int instance)[obj]%s not implemented"))' %
                             (" = obj" if op == "set_item" else ""))
                elif op.startswith("item_"):
                    code += 'Lar_panic_string(fmt.Sprintf("(int instance)[obj] not implemented"))'
                elif op in ("get_slice", "set_slice"):
                    code += 'Lar_panic_string(fmt.Sprintf("(int instance)[x:y:z] not implemented"))'
                elif op in ("inc", "dec"):
                    code += 'ptr.M_int %s' % {"inc" : "++", "dec" : "--"}[op]
                elif op == "eq":
                    with code.new_blk("if obj.M_obj_ptr != nil"):
                        code += "return (*obj.M_obj_ptr).Method___eq(ptr)"
                    with code.new_blk("if ptr.M_int == obj.M_int"):
                        code += "return TRUE"
                    code += "return FALSE"
                elif op == "cmp":
                    with code.new_blk("if obj.M_obj_ptr != nil"):
                        code += "return LarPtr{M_int : -(*obj.M_obj_ptr).Method___cmp(ptr).M_int}"
                    with code.new_blk("if ptr.M_int < obj.M_int"):
                        code += "return LarPtr{M_int : -1}"
                    with code.new_blk("if ptr.M_int > obj.M_int"):
                        code += "return LarPtr{M_int : 1}"
                    code += "return LarPtr{M_int : 0}"
                else:
                    if op[0] == "i" and op[1 :] in bops:
                        with code.new_blk("if obj.M_obj_ptr != nil"):
                            code += "*ptr = (*obj.M_obj_ptr).Method___r%s(*ptr)" % op[1 :]
                            code += "return"
                        if op[1 :] in ("shl", "shr"):
                            code += "ptr.M_int %s= int_to_shift_count(obj.M_int)" % bops_to_go_op[op[1 :]]
                        else:
                            code += "ptr.M_int %s= obj.M_int" % bops_to_go_op[op[1 :]]
                    elif op[0] == "r" and op[1 :] in bops:
                        code += ('Lar_panic_string(fmt.Sprintf("(%%v instance) %s (int instance) not implemented", obj.Get_type_name()))' %
                                 bops_to_go_op[op[1 :]])
                    else:
                        assert op in bops
                        with code.new_blk("if obj.M_obj_ptr != nil"):
                            code += "return obj.Method___r%s(ptr)" % op
                        if op in ("shl", "shr"):
                            code += "return LarPtr{M_int : ptr.M_int %s int_to_shift_count(obj.M_int)}" % bops_to_go_op[op]
                        else:
                            code += "return LarPtr{M_int : ptr.M_int %s obj.M_int}" % bops_to_go_op[op]
                if code.line_list[-1].lstrip().startswith("Lar_panic_string"):
                    code += "return NIL"

        for attr_name in attr_set:
            with code.new_blk("func (ptr LarPtr) Attr_get_%s() LarPtr" % attr_name):
                with code.new_blk("if ptr.M_obj_ptr != nil"):
                    code += "return (*ptr.M_obj_ptr).Attr_get_%s()" % attr_name
                code += '''Lar_panic_string(fmt.Sprintf("(int instance) doesn't have attr '%s'"))''' % attr_name
                code += "return NIL"
            with code.new_blk("func (ptr LarPtr) Attr_set_%s(v LarPtr)" % attr_name):
                with code.new_blk("if ptr.M_obj_ptr != nil"):
                    code += "(*ptr.M_obj_ptr).Attr_set_%s(v)" % attr_name
                    code += "return"
                code += '''Lar_panic_string(fmt.Sprintf("(int instance) doesn't have attr '%s'"))''' % attr_name
            for op in "inc", "dec":
                with code.new_blk("func (ptr LarPtr) Attr_%s_%s()" % (op, attr_name)):
                    with code.new_blk("if ptr.M_obj_ptr != nil"):
                        code += "(*ptr.M_obj_ptr).Attr_%s_%s()" % (op, attr_name)
                        code += "return"
                    code += '''Lar_panic_string(fmt.Sprintf("(int instance) doesn't have attr '%s'"))''' % attr_name
            for op in bops:
                with code.new_blk("func (ptr LarPtr) Attr_i%s_%s(v LarPtr)" % (op, attr_name)):
                    with code.new_blk("if ptr.M_obj_ptr != nil"):
                        code += "(*ptr.M_obj_ptr).Attr_i%s_%s(v)" % (op, attr_name)
                        code += "return"
                    code += '''Lar_panic_string(fmt.Sprintf("(int instance) doesn't have attr '%s'"))''' % attr_name

        for method_def in construct_method_def_list + method_def_list:
            assert method_def.startswith("Method_")
            pos = method_def.find("(")
            assert pos > 0
            method_name = method_def[len("Method_") : pos]
            method_name, arg_count = method_name.rsplit("_", 1)
            arg_count = int(arg_count)
            args = method_def[pos + 1 :]
            assert args.count(")") == 1
            args = args[: args.find(")")]
            if args:
                assert args.endswith(" LarPtr")
                args = args[: -len(" LarPtr")]
            with code.new_blk("func (ptr LarPtr) %s" % method_def):
                with code.new_blk("if ptr.M_obj_ptr != nil"):
                    code += "return (*ptr.M_obj_ptr).Method_%s_%d(%s)" % (method_name, arg_count, args)
                code += ('Lar_panic_string(fmt.Sprintf("method (int instance).%s with %s args not implemented"))' % (method_name, arg_count))
                code += "return NIL"

def _gen_makefile():
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
    for curr_module in larc_module.module_map.itervalues():
        _output_module()

    _copy_runtime()
    _complete_runtime_code()

    _gen_makefile()
