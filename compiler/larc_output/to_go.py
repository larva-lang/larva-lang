#coding=utf8

"""
输出为go代码
"""

import os
import shutil
import sys

import larc_module

main_module_name = None
out_dir = None
runtime_dir = None
out_prog_dir = None

class _Code:
    class _CodeBlk:
        def __init__(self, code, end_line):
            self.code = code
            self.end_line = end_line

        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                return
            assert len(self.code.indent) >= 4
            self.code.indent = self.code.indent[: -4]
            self.code += self.end_line

    def __init__(self, file_path_name):
        self.file_path_name = file_path_name
        self.indent = ""
        self.line_list = []

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
            assert self.line_list[-1] == self.indent + "}"
            del self.line_list[-1]
            self += "} " + title + " {"
        elif title:
            self += title + " {"
        else:
            self += "{"
        self.indent += " " * 4
        return self._CodeBlk(self, end_line)

def _output_main_pkg():
    main_lar_mod_name = "lar_mod_" + main_module_name
    with _Code(os.path.join(out_prog_dir, "lar_prog.%s.go" % main_module_name)) as code:
        code += "package main"
        with code.new_blk("import"):
            code += '"os"'
            code += '"larva_booter"'
            code += '"%s"' % main_lar_mod_name
        with code.new_blk("func main()"):
            code += "os.Exit(larva_booter.Start_prog(%s.Func_main))" % main_lar_mod_name

def _output_module(module):
    has_native_item = module.has_native_item()
    mod_dir = os.path.join(out_dir, "src", "lar_mod_" + module.name)
    os.makedirs(mod_dir)
    with _Code(os.path.join(mod_dir, "lar_mod.%s.go" % module.name)) as code:
        code += "package lar_mod_" + module.name
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
    method_def_set = set()
    for m in larc_module.module_map.itervalues():
        for cls in m.class_map.itervalues():
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

    bops = ["add", "sub", "mul", "div", "mod", "and", "or", "xor", "shl", "shr"]
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
                        code += "tmp := self.This.Method___get_item(k)"
                        code += 'return self.This.Method___set_item(k, tmp.Method___%s(obj))' % op[1 :]
                elif op in ("get_slice", "set_slice"):
                    code += ('Lar_panic_string(fmt.Sprintf("(%%v instance)[x:y:z]%s not implemented", self.Type_name))' %
                             (" = obj" if op == "set_slice" else ""))
                elif op in ("inc", "dec"):
                    code += ('Lar_panic_string(fmt.Sprintf("%s(%%v instance) not implemented", self.Type_name))' %
                             {"inc" : "++", "dec" : "--"}[op])
                elif op == "eq":
                    code += "tmp := self.This.Method___cmp(obj)"
                    with code.new_blk("if tmp.As_int() == 0"):
                        code += "return TRUE"
                    code += "return FALSE"
                elif op == "cmp":
                    code += 'Lar_panic_string(fmt.Sprintf("(%v instance).__cmp(obj) not implemented", self.Type_name))'
                else:
                    if op[0] == "i" and op[1 :] in bops:
                        code += "return self.This.Method___%s(obj)" % op[1 :]
                    elif op[0] == "r" and op[1 :] in bops:
                        code += ('Lar_panic_string(fmt.Sprintf("(%%v instance) %s (%%v instance) not implemented", '
                                 'obj.Get_type_name(), self.Type_name))' % bops_to_go_op[op[1 :]])
                    else:
                        assert op in bops
                        code += "return obj.Method___r%s(self.To_lar_ptr())" % op
                if code.line_list[-1].lstrip().startswith("Lar_panic_string"):
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
            with code.new_blk("func (ptr *LarPtr) %s" % op_def):
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
                    code += 'return NewLarObj_str_from_literal(fmt.Sprintf("%d", ptr.M_int))'
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
                        code += "return (*obj.M_obj_ptr).Method___eq(*ptr)"
                    with code.new_blk("if ptr.M_int == obj.M_int"):
                        code += "return TRUE"
                    code += "return FALSE"
                elif op == "cmp":
                    with code.new_blk("if obj.M_obj_ptr != nil"):
                        code += "return LarPtr{M_int : -(*obj.M_obj_ptr).Method___cmp(*ptr).M_int}"
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
                            code += "return obj.Method___r%s(*ptr)" % op
                        if op in ("shl", "shr"):
                            code += "return LarPtr{M_int : ptr.M_int %s int_to_shift_count(obj.M_int)}" % bops_to_go_op[op]
                        else:
                            code += "return LarPtr{M_int : ptr.M_int %s obj.M_int}" % bops_to_go_op[op]
                if code.line_list[-1].lstrip().startswith("Lar_panic_string"):
                    code += "return NIL"

def _gen_makefile():
    if sys.platform.lower().startswith("win"):
        f = open(os.path.join(out_dir, "make.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src/lar_prog_%s/lar_prog.%s.go" % (main_module_name, main_module_name, main_module_name)
        print >> f, "@if %ERRORLEVEL% == 0 goto success"
        print >> f, "@pause"
        print >> f, ":success"
    else:
        raise Exception("Not implemented on '%s'" % sys.platform)

def output():
    global runtime_dir, out_prog_dir
    runtime_dir = os.path.join(runtime_dir, "go")
    out_prog_dir = os.path.join(out_dir, "src", "lar_prog_" + main_module_name)

    shutil.rmtree(out_dir, True)
    os.makedirs(out_prog_dir)

    _output_main_pkg()
    for m in larc_module.module_map.itervalues():
        _output_module(m)

    _copy_runtime()
    _complete_runtime_code()

    _gen_makefile()
