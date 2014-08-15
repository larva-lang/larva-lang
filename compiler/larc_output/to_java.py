#coding=utf8

"""
输出为java代码
"""

import os
import shutil

_UNARY_OP_NAME_MAP = {"~" : "invert",
                      "neg" : "neg",
                      "pos" : "pos"}
_BINOCULAR_OP_NAME_MAP = {"[]" : "get_item",
                          "%" : "mod",
                          "^" : "xor",
                          "&" : "and",
                          "*" : "mul",
                          "-" : "sub",
                          "+" : "add",
                          "|" : "or",
                          "/" : "div",
                          "<<" : "shl",
                          ">>" : "shr",
                          ">>>" : "ushr"}

class _Code:
    def __init__(self, out_dir, prog_name, lib_path):
        self.indent = ""
        self.line_list = []

        self.tmp_iter_number = 0

        self.out_dir = os.path.join(out_dir, prog_name)
        self.prog_name = prog_name
        self.lib_path = os.path.join(lib_path, "java")

        self.lar_obj_op_call_set = set()
        self.lar_obj_op_attr_set = set()
        self.lar_obj_method_set = set()

    def __iadd__(self, line):
        self.line_list.append(self.indent + line)
        return self

    def blk_start(self, title):
        self += title
        self += "{"
        self.indent += " " * 4

    def blk_end(self):
        assert len(self.indent) >= 4
        self.indent = self.indent[: -4]
        self += "}"

    def output(self):
        self._add_lar_obj()

        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)
        out_file_name = (
            os.path.join(self.out_dir, "Prog_%s.java" % self.prog_name))
        f = open(out_file_name, "w")
        for line in self.line_list:
            print >> f, line

        self._copy_lib()

    def _add_lar_obj(self):
        self.blk_start("class LarObj extends LarBaseObj")

        for arg_count in self.lar_obj_op_call_set:
            self.blk_start("public LarObj op_call(%s) throws Exception" %
                           ",".join(["LarObj arg_%d" % (i + 1)
                                     for i in xrange(arg_count)]))
            self += ("""throw new Exception("未实现类型'" + """
                     """get_type_name() + "'的'()'运算，%d个参数");""" %
                     arg_count)
            self.blk_end()

        for attr_name in self.lar_obj_op_attr_set:
            self.blk_start("public LarObj op_get_attr_%s() throws Exception" %
                           attr_name)
            self += ("""throw new Exception("找不到类型'" + get_type_name() """
                     """+ "'的属性：%s");""" % attr_name)
            self.blk_end()
            self.blk_start("public void op_set_attr_%s(LarObj obj) "
                           "throws Exception" % attr_name)
            self += ("""throw new Exception("找不到类型'" + get_type_name() """
                     """+ "'的属性：%s");""" % attr_name)
            self.blk_end()

        for method_name, arg_count in self.lar_obj_method_set:
            self.blk_start("public LarObj f_%s(%s) throws Exception" %
                           (method_name,
                            ",".join(["LarObj arg_%d" % (i + 1)
                                      for i in xrange(arg_count)])))
            self += ("""throw new Exception("找不到类型'" + get_type_name() """
                     """+ "'的方法：%s，%d个参数");""" % (method_name, arg_count))
            self.blk_end()

        self.blk_end()

    def _copy_lib(self):
        type_name_list = ["Nil", "Bool", "Int", "Long", "Float", "Str",
                          "Tuple", "List", "Dict", "Range"]
        module_name_list = ["time"]
        lib_name_list = (
            ["LarUtil", "LarBuiltin", "LarBaseObj"] +
            ["LarObj" + type_name for type_name in type_name_list] +
            ["Mod_" + module_name for module_name in module_name_list])
        for lib_name in lib_name_list:
            shutil.copy(os.path.join(self.lib_path, lib_name + ".java"),
                        self.out_dir)

    def new_tmp_iter_number(self):
        self.tmp_iter_number += 1
        return self.tmp_iter_number

    def add_lar_obj_op_call(self, arg_count):
        self.lar_obj_op_call_set.add(arg_count)

    def add_lar_obj_op_attr(self, attr_name):
        self.lar_obj_op_attr_set.add(attr_name)

    def add_lar_obj_method(self, method_name, arg_count):
        self.lar_obj_method_set.add((method_name, arg_count))

def _output_booter(code, prog):
    code.blk_start("public final class Prog_%s" % prog.main_module_name)
    code.blk_start("public static void main(String[] argv) throws Exception")
    code += "LarBuiltin.init();"
    code += ""
    for module_name in prog.module_map:
        code += "Mod_%s.init();" % module_name
    code += ""
    code += "Mod_%s.f_main();" % prog.main_module_name
    code.blk_end()
    code.blk_end()

def _output_const(code, const_map):
    #输出常量表
    for (type, value), idx in const_map.iteritems():
        if type == "float":
            type = "LarObjFloat"
            value = "%e" % value
        elif type == "int":
            type = "LarObjInt"
            value = "%d" % value
        elif type == "long":
            type = "LarObjLong"
            value = '"%d"' % value
        elif type == "str":
            type = "LarObjStr"
            value = '"%s"' % value.encode("utf8")
        elif type == "byte":
            type = "LarObjByte"
            byte_list = []
            for c in value:
                c = ord(c)
                if c > 127:
                    c -= 256
                byte_list.append("%d" % c)
            value = "new byte[]{" + ",".join(byte_list) + "}"
        else:
            raise Exception("unreachable")
        code += ("private static final %s CONST_%d = new %s(%s);" %
                 (type, idx, type, value))
    code += ""

def _build_expr_code(code, expr, expect_bool = False):
    assert isinstance(expect_bool, bool)
    def _build_expr_code_original(expr):
        #按expr原样编码，即逻辑和比较表达式编码为结果为boolean类型
        #其余编译成结果为LarObj类型
        if expr.op == "const":
            #nil,true,false
            if expr.arg.is_nil:
                return "LarBuiltin.NIL"
            if expr.arg.is_true:
                return "LarBuiltin.TRUE"
            if expr.arg.is_false:
                return "LarBuiltin.FALSE"
            raise Exception("unreachable")
        if expr.op == "const_idx":
            return "CONST_%d" % expr.arg
        if expr.op == "local_name":
            return "l_%s" % expr.arg.value
        if expr.op == "global_name":
            return "g_%s" % expr.arg.value
        if expr.op == "module.global":
            return "Mod_%s.g_%s" % (expr.arg[0].value, expr.arg[1].value)
        if expr.op == "dict":
            code_str = "(new LarObjDict())"
            for ek, ev in expr.arg:
                code_str += (".op_set_item(%s,%s)" %
                             (_build_expr_code(code, ek),
                              _build_expr_code(code, ev)))
            return code_str
        if expr.op == "()":
            ec, el = expr.arg
            code.add_lar_obj_op_call(len(el))
            return (_build_expr_code(code, ec) +
                    ".op_call(%s)" %
                    ",".join([_build_expr_code(code, e) for e in el]))
        if expr.op == "call_func":
            t, el = expr.arg
            return ("f_%s" % t.value +
                    "(%s)" % ",".join([_build_expr_code(code, e) for e in el]))
        if expr.op == "call_method":
            eo, t, el = expr.arg
            code.add_lar_obj_method(t.value, len(el))
            return (_build_expr_code(code, eo) + ".f_%s" % t.value +
                    "(%s)" % ",".join([_build_expr_code(code, e) for e in el]))
        if expr.op == "call_module_func":
            tm, t, el = expr.arg
            return ("Mod_%s" % tm.value + ".f_%s" % t.value +
                    "(%s)" % ",".join([_build_expr_code(code, e) for e in el]))
        if expr.op == "call_builtin_if":
            t, el = expr.arg
            return ("LarBuiltin.f_%s" % t.value +
                    "(%s)" % ",".join([_build_expr_code(code, e) for e in el]))
        if expr.op == ".":
            e, t = expr.arg
            code.add_lar_obj_op_attr(t.value)
            return _build_expr_code(code, e) + ".op_get_attr_%s()" % t.value
        if expr.op == "tuple":
            return ("new LarObjTuple(%s)" %
                    ",".join([_build_expr_code(code, e) for e in expr.arg]))
        if expr.op == "list":
            code_str = "(new LarObjList())"
            for e in expr.arg:
                code_str += ".f_add(%s)" % _build_expr_code(code, e)
            return code_str
        if expr.op in _UNARY_OP_NAME_MAP:
            return (_build_expr_code(code, expr.arg[0]) +
                    ".op_%s()" % _UNARY_OP_NAME_MAP[expr.op])
        if expr.op == "not":
            return "!" + _build_expr_code(code, expr.arg[0], True)
        if expr.op in _BINOCULAR_OP_NAME_MAP:
            return (_build_expr_code(code, expr.arg[0]) +
                    ".op_%s(%s)" % (_BINOCULAR_OP_NAME_MAP[expr.op],
                                    _build_expr_code(code, expr.arg[1])))
        if expr.op in ("and", "or"):
            return (_build_expr_code(code, expr.arg[0], True) +
                    {"and" : "&&", "or" : "||"}[expr.op] +
                    _build_expr_code(code, expr.arg[1], True))
        if expr.op in ("in", "not in"):
            code_str = (_build_expr_code(code, expr.arg[1]) +
                        ".op_contain(%s)" %
                        _build_expr_code(code, expr.arg[1]))
            if expr.op == "not in":
                code_str = "!" + code_str
            return code_str
        if expr.op in ("==", "!="):
            code_str = (_build_expr_code(code, expr.arg[0]) +
                        ".op_eq(%s)" % _build_expr_code(code, expr.arg[1]))
            if expr.op == "!=":
                code_str = "!" + code_str
            return code_str
        if expr.op in ("<", "<=", ">", ">="):
            return (_build_expr_code(code, expr.arg[0]) +
                    ".op_cmp(%s)" % _build_expr_code(code, expr.arg[1]) +
                    "%s0" % expr.op)

        raise Exception("unreachable")

    code = _build_expr_code_original(expr)

    if expr.op in ("and", "or", "not", "==", "!=", "<", "<=", ">", ">=",
                   "in", "not in"):
        if not expect_bool:
            #打包成返回true和false对象
            code = "(%s)?LarBuiltin.TRUE:LarBuiltin.FALSE" % code
    else:
        if expect_bool:
            #需要boolean类型
            code = "(%s).op_bool()" % code

    return "(%s)" % code

def _output_global_init(code, global_var_list, global_var_map):
    for var_name in global_var_list:
        code += "public static LarObj g_%s = LarBuiltin.NIL;" % var_name
    code += ""
    code.blk_start("public static void init() throws Exception")
    for var_name in global_var_list:
        expr = global_var_map[var_name]
        code += "g_%s = %s;" % (var_name, _build_expr_code(code, expr))
    code.blk_end()
    code += ""

def _output_stmt_list(code, stmt_list):
    for stmt in stmt_list:
        if stmt.type in ("break", "continue"):
            code += stmt.type + ";"
            continue
        if stmt.type == "print":
            for e in stmt.expr_list:
                code += ("System.out.print(%s.op_str());" %
                         _build_expr_code(code, e))
                code += 'System.out.print(" ");'
            if stmt.print_new_line:
                code += "System.out.println();"
            continue
        if stmt.type == "return":
            if stmt.expr is None:
                code += "return LarBuiltin.NIL;"
            else:
                code += "return %s;" % _build_expr_code(code, stmt.expr)
            continue
        if stmt.type == "expr":
            expr_code = _build_expr_code(code, stmt.expr)
            #java不允许带外层括号的表达式
            while expr_code and expr_code[0] == "(" and expr_code[-1] == ")":
                #去掉括号后需要检查，避免出现类似(a).b()情况
                expr_code = expr_code[1 : -1]
                deep = 0
                for c in expr_code:
                    if c == "(":
                        deep += 1
                    elif c == ")":
                        deep -= 1
                        if deep < 0:
                            break
                else:
                    continue
                expr_code = "(%s)" % expr_code
                break
            code += "%s;" % expr_code
            continue
        if stmt.type == "while":
            code.blk_start("while (%s)" %
                           _build_expr_code(code, stmt.expr, True))
            _output_stmt_list(code, stmt.stmt_list)
            code.blk_end()
            continue
        if stmt.type == "if":
            in_else_if = False
            for e, if_stmt_list in stmt.if_list:
                if in_else_if:
                    code.blk_start("else if (%s)" %
                                   _build_expr_code(code, e, True))
                else:
                    code.blk_start("if (%s)" % _build_expr_code(code, e, True))
                    in_else_if = True
                _output_stmt_list(code, if_stmt_list)
                code.blk_end()
            if stmt.else_stmt_list is not None:
                code.blk_start("else")
                _output_stmt_list(code, stmt.else_stmt_list)
                code.blk_end()
            continue

        def _output_assign(code, lvalue, expr_code):
            if lvalue.op in ("local_name", "global_name"):
                code += ("%s_%s = %s;" %
                         (lvalue.op[0], lvalue.arg.value, expr_code))
                return
            if lvalue.op == "module.global":
                code += ("Mod_%s.g_%s = %s;" %
                         (lvalue.arg[0].value, lvalue.arg[1].value) )
                return
            if lvalue.op == ".":
                e, attr = lvalue.arg
                code.add_lar_obj_op_attr(attr.value)
                code += ("%s.op_set_attr_%s(%s);" %
                         (_build_expr_code(code, e), attr.value, expr_code))
                return
            if lvalue.op == "[]":
                ea, eb = lvalue.arg
                code += ("%s.op_set_item(%s, %s);" %
                         (_build_expr_code(code, ea),
                          _build_expr_code(code, eb), expr_code))
                return
            raise Exception("unreachable")

        if stmt.type == "=":
            _output_assign(code, stmt.lvalue, _build_expr_code(code, stmt.expr))
            continue
        if stmt.type == "for":
            tmp_iter = "tmp_iter_%d" % code.new_tmp_iter_number()
            if (stmt.expr.op == "call_builtin_if" and
                stmt.expr.arg[0].value == "range"):
                #针对range的特殊处理
                code.blk_start(
                    "for (LarObjRange %s = %s; %s.has_next();)" %
                    (tmp_iter, _build_expr_code(code, stmt.expr), tmp_iter))
                _output_assign(code, stmt.lvalue,
                               "new LarObjInt(%s.next())" % tmp_iter)
            elif stmt.expr.op == "tuple":
                #针对tuple的特殊处理
                tmp_iter_index = tmp_iter + "_index"
                code += "int %s = 0;" % tmp_iter_index
                code.blk_start(
                    "for (LarObj[] %s = LarUtil.make_array(%s); "
                    "%s < %s.length; ++ %s)" %
                    (tmp_iter, ",".join([_build_expr_code(code, e)
                                         for e in stmt.expr.arg]),
                     tmp_iter_index, tmp_iter, tmp_iter_index))
                _output_assign(code, stmt.lvalue,
                               "%s[%s]" % (tmp_iter, tmp_iter_index))
            else:
                code.blk_start(
                    "for (LarObj %s = %s.f_iterator(); "
                    "%s.f_has_next().op_bool();)" %
                    (tmp_iter, _build_expr_code(code, stmt.expr), tmp_iter))
                _output_assign(code, stmt.lvalue, "%s.f_next()" % tmp_iter)
            _output_stmt_list(code, stmt.stmt_list)
            code.blk_end()
            continue

        raise Exception("unreachable")

def _output_func(code, func):
    code.blk_start(
        "public static LarObj f_%s(%s) throws Exception" %
        (func.name, ",".join(["LarObj l_%s" % arg_name
                              for arg_name in func.arg_list])))
    for var_name in func.local_var_set - set(func.arg_list):
        code += "LarObj l_%s = LarBuiltin.NIL;" % var_name
    code += ""
    _output_stmt_list(code, func.stmt_list)
    code.blk_end()
    code += ""

def _output_module(code, module):
    code += ""
    code.blk_start("final class Mod_%s" % module.name)
    _output_const(code, module.const_map)
    _output_global_init(code, module.global_var_list, module.global_var_map)
    for func in module.func_map.itervalues():
        _output_func(code, func)
    code.blk_end()
    code += ""

def output(out_dir, prog, lib_path):
    code = _Code(out_dir, prog.main_module_name, lib_path)

    _output_booter(code, prog)
    for module in prog.module_map.itervalues():
        if module.is_extern:
            continue
        _output_module(code, module)

    code.output()
