#coding=utf8

"""
输出为java代码
"""

import os
import shutil
import larc_module

_UNARY_OP_NAME_MAP = {"~" : "invert",
                      "neg" : "neg",
                      "pos" : "pos"}
_UNARY_OP_NAME_MAP_FOR_INT = {"~" : "~",
                              "neg" : "-",
                              "pos" : "+"}
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

_TYPE_NAME_MAP = {"object" : "LarObj",
                  "int" : "long"}
_TYPE_INIT_VALUE_MAP = {"object" : "LarBuiltin.NIL",
                        "int" : "0L"}

class _Code:
    def __init__(self, out_dir, prog_name, lib_dir):
        self.indent = ""
        self.line_list = []

        self.tmp_iter_number = 0

        self.out_dir = os.path.join(out_dir, prog_name)
        self.prog_name = prog_name
        self.lib_dir = os.path.join(lib_dir, "java")

        self.extern_module_list = []

        self.lar_obj_op_call_set = set()
        self.lar_obj_op_attr_set = set()
        self.lar_obj_method_set = set()

        self.compr_number = 0
        self.list_compr_map = {}
        self.dict_compr_map = {}

        self.lambda_number = 0
        self.lambda_map = {}

        self.unpack_number = 0

        self.lambda_outter_class_name = None

        self.int_const_map = {}

    def add_extern_module(self, module):
        self.extern_module_list.append(module)

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
            self.blk_start("public LarObj meth_%s(%s) throws Exception" %
                           (method_name,
                            ",".join(["LarObj arg_%d" % (i + 1)
                                      for i in xrange(arg_count)])))
            self += ("""throw new Exception("找不到类型'" + get_type_name() """
                     """+ "'的方法：%s，%d个参数");""" % (method_name, arg_count))
            self.blk_end()

        self.blk_end()

    def _copy_lib(self):
        lar_lib_name_list = ["LarUtil", "LarBuiltin", "LarBaseObj",
                             "LarSeqObj"]
        type_name_list = ["Nil", "Bool", "Int", "Long", "Float", "Str",
                          "Tuple", "List", "Dict", "Set", "Range", "Bitmap",
                          "File"]
        lib_file_path_name_list = []
        for name in (lar_lib_name_list +
                     ["LarObj%s" % type_name for type_name in type_name_list]):
            lib_file_path_name_list.append(
                os.path.join(self.lib_dir, name + ".java"))
        for module in self.extern_module_list:
            lib_file_path_name_list.append(
                os.path.join(module.dir, "java", "Mod_%s.java" % module.name))
        for file_path_name in lib_file_path_name_list:
            shutil.copy(file_path_name, self.out_dir)

    def new_tmp_iter_number(self):
        self.tmp_iter_number += 1
        return self.tmp_iter_number

    def add_lar_obj_op_call(self, arg_count):
        self.lar_obj_op_call_set.add(arg_count)

    def add_lar_obj_op_attr(self, attr_name):
        self.lar_obj_op_attr_set.add(attr_name)

    def add_lar_obj_method(self, method_name, arg_count):
        self.lar_obj_method_set.add((method_name, arg_count))

    def add_list_compr(self, compr_arg_list, e, lvalue, name_set, if_expr):
        self.compr_number += 1
        self.list_compr_map[self.compr_number] = (
            compr_arg_list, e, lvalue, name_set, if_expr)
        return self.compr_number

    def add_dict_compr(self, compr_arg_list, ek, ev, lvalue, name_set,
                       if_expr):
        self.compr_number += 1
        self.dict_compr_map[self.compr_number] = (
            compr_arg_list, ek, ev, lvalue, name_set, if_expr)
        return self.compr_number

    def add_lambda(self, lambda_stat_arg_list, arg_list, e):
        self.lambda_number += 1
        self.lambda_map[self.lambda_number] = (
            lambda_stat_arg_list, arg_list, e)
        return self.lambda_number

    def new_unpack_number(self):
        self.unpack_number += 1
        return self.unpack_number

def _output_booter(code, prog):
    code.blk_start("public final class Prog_%s" % prog.main_module_name)
    code.blk_start("public static void main(String[] argv) throws Exception")
    code += "Mod_sys.set_argv(argv);"
    code += ""
    code += "LarBuiltin.init();"
    code += ""
    for module_name in prog.module_map:
        code += "Mod_%s.init();" % module_name
    code += ""
    code += "Mod_%s.f_main();" % prog.main_module_name
    code.blk_end()
    code.blk_end()
    code += ""

def _output_const(code, const_map):
    #输出常量表
    for (type, value), idx in const_map.iteritems():
        if type == "float":
            type = "LarObjFloat"
            value = "%e" % value
        elif type == "int":
            type = "LarObjInt"
            value = "%dL" % value
            code.int_const_map[idx] = value
        elif type == "long":
            type = "LarObjLong"
            value = '"%d"' % value
        elif type == "str":
            type = "LarObjStr"
            repr_char_list = list(value)
            for i, ch in enumerate(repr_char_list):
                esc_map = {"\\" : "\\\\",
                           '"' : '\\"',
                           "\n" : "\\n",
                           "\r" : "\\r",
                           "\t" : "\\t"}
                if ch in esc_map:
                    ch = esc_map[ch]
                elif ch in "\a\b\f\v":
                    ch = "\u%04x" % ord(ch)
                repr_char_list[i] = ch
            value = '"%s"' % "".join(repr_char_list).encode("utf8")
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

_BUILTIN_METHOD_NAME_MAP = {"__init__" : "init"}
def _get_method_name(name):
    if name.startswith("__") and name.endswith("__"):
        return _BUILTIN_METHOD_NAME_MAP[name]
    return "meth_%s" % name

def _build_expr_code(code, expr, expect_type):
    assert expect_type in ("bool", "object", "int", None)
    def _build_expr_code_original(expr):
        """按expr原样编码：
           逻辑和比较表达式编码为结果为boolean类型
           若为int相关运算则编译为int类型
           其余编译成结果为LarObj类型
           返回编码后的code和类型信息"""
        if expr.op == "const":
            #nil,true,false
            if expr.arg.is_nil:
                return "LarBuiltin.NIL", "object"
            if expr.arg.is_true:
                return "LarBuiltin.TRUE", "object"
            if expr.arg.is_false:
                return "LarBuiltin.FALSE", "object"
            raise Exception("unreachable")
        if expr.op == "const_idx":
            if expr.arg in code.int_const_map:
                #int常量
                return "CONST_%d" % expr.arg, "const_int"
            else:
                return "CONST_%d" % expr.arg, "object"
        if expr.op == "local_name":
            return ("l_%s" % expr.arg.value,
                    code.curr_func.local_var_type_info[expr.arg.value])
        if expr.op == "global_name":
            return ("g_%s" % expr.arg.value,
                    code.curr_module.global_var_type_info[expr.arg.value])
        if expr.op == "module.global":
            return ("Mod_%s.g_%s" % (expr.arg[0].value, expr.arg[1].value),
                    "object")
        if expr.op == "dict":
            code_str = "(new LarObjDict())"
            for ek, ev in expr.arg:
                code_str += (".init_item(%s,%s)" %
                             (_build_expr_code(code, ek, None)[0],
                              _build_expr_code(code, ev, None)[0]))
            return code_str, "object"
        if expr.op == "()":
            ec, el = expr.arg
            code.add_lar_obj_op_call(len(el))
            return ((_build_expr_code(code, ec, "object") +
                     ".op_call(%s)" %
                     ",".join([_build_expr_code(code, e, "object")
                               for e in el])), "object")
        if expr.op == "call_func":
            t, el = expr.arg
            func_key = t.value, len(el)
            func = code.curr_module.func_map[func_key]
            arg_code_list = []
            assert len(el) == len(func.arg_list)
            for i, e in enumerate(el):
                if func.local_var_type_info[func.arg_list[i]] == "object":
                    arg_code_list.append(_build_expr_code(code, e, "object"))
                else:
                    arg_code_list.append(_build_expr_code(code, e, None)[0])
            return ("f_%s(%s)" % (t.value, ",".join(arg_code_list)),
                    func.ret_type)
        if expr.op == "call_method":
            eo, t, el = expr.arg
            code.add_lar_obj_method(t.value, len(el))
            return (_build_expr_code(code, eo, "object") + ".%s(%s)" %
                    (_get_method_name(t.value),
                     ",".join([_build_expr_code(code, e, "object")
                               for e in el])), "object")
        if expr.op == "call_module_func":
            tm, t, el = expr.arg
            return ("Mod_%s.f_%s(%s)" %
                    (tm.value, t.value,
                     ",".join([_build_expr_code(code, e, "object")
                               for e in el])), "object")
        if expr.op == "call_builtin_if":
            t, el = expr.arg
            if t.value == "str":
                assert len(el) == 1
                return ("new LarObjStr(%s)" %
                        _build_expr_code(code, el[0], None)[0]), "object"
            if t.value in ("tuple", "list", "set", "file"):
                return ("new LarObj%s(%s)" %
                        (t.value.capitalize(),
                         ",".join([_build_expr_code(code, e, "object")
                                   for e in el])), "object")
            if t.value == "range":
                return ("new LarObjRange(%s)" %
                        ",".join([_build_expr_code(code, e, "int")
                                  for e in el]), "object")
            if t.value == "bitmap":
                assert len(el) == 1
                return ("new LarObjBitmap(%s)" %
                        _build_expr_code(code, el[0], "int")), "object"
            if t.value == "len":
                assert len(el) == 1
                return ("%s.op_len()" %
                        _build_expr_code(code, el[0], "object")), "int"
            #默认接口
            return ("LarBuiltin.f_%s(%s)" %
                    (t.value, ",".join([_build_expr_code(code, e, "object")
                                        for e in el])), "object")
        if expr.op == ".":
            e, t = expr.arg
            code.add_lar_obj_op_attr(t.value)
            return (_build_expr_code(code, e, "object") +
                    ".op_get_attr_%s()" % t.value), "object"
        if expr.op == "tuple":
            return ("LarObjTuple.from_var_arg(%s)" %
                    ",".join([_build_expr_code(code, e, "object")
                              for e in expr.arg])), "object"
        if expr.op == "list":
            code_str = "(new LarObjList())"
            for e in expr.arg:
                code_str += (".meth_add(%s)" %
                             _build_expr_code(code, e, None)[0])
            return code_str, "object"
        if expr.op in _UNARY_OP_NAME_MAP:
            expr_code, is_int = _build_expr_code(code, expr.arg[0], None)
            if is_int:
                return _UNARY_OP_NAME_MAP_FOR_INT[expr.op] + expr_code, "int"
            else:
                return (expr_code + ".op_%s()" % _UNARY_OP_NAME_MAP[expr.op],
                        "object")
        if expr.op == "not":
            return "!" + _build_expr_code(code, expr.arg[0], "bool"), "bool"
        if expr.op in _BINOCULAR_OP_NAME_MAP:
            ea, eb = expr.arg
            if expr.op == "[]":
                #下标运算左运算分量需要是object
                return ("%s.op_get_item(%s)" %
                        (_build_expr_code(code, ea, "object"),
                         _build_expr_code(code, eb, None)[0])), "object"
            #其他二元运算需分情况
            ea_code, ea_is_int = _build_expr_code(code, ea, None)
            eb_code, eb_is_int = _build_expr_code(code, eb, None)
            if ea_is_int:
                if eb_is_int:
                    return ea_code + expr.op + eb_code, "int"
                else:
                    return ("%s.op_reverse_%s(%s)" %
                            (eb_code, _BINOCULAR_OP_NAME_MAP[expr.op],
                             ea_code)), "object"
            else:
                return ("%s.op_%s(%s)" %
                        (ea_code, _BINOCULAR_OP_NAME_MAP[expr.op], eb_code),
                        "object")
        if expr.op in ("and", "or"):
            return (_build_expr_code(code, expr.arg[0], "bool") +
                    {"and" : "&&", "or" : "||"}[expr.op] +
                    _build_expr_code(code, expr.arg[1], "bool"), "bool")
        if expr.op in ("in", "not in"):
            code_str = (_build_expr_code(code, expr.arg[1], "object") +
                        ".op_contain(%s)" %
                        _build_expr_code(code, expr.arg[0], None)[0])
            if expr.op == "not in":
                code_str = "!" + code_str
            return code_str, "bool"
        if expr.op in ("==", "!="):
            ea, eb = expr.arg
            ea_code, ea_is_int = _build_expr_code(code, ea, None)
            eb_code, eb_is_int = _build_expr_code(code, eb, None)
            if ea_is_int:
                if eb_is_int:
                    return ea_code + expr.op + eb_code, "bool"
                else:
                    code_str = "%s.op_reverse_eq(%s)" % (eb_code, ea_code)
            else:
                code_str = "%s.op_eq(%s)" % (ea_code, eb_code)
            if expr.op == "!=":
                code_str = "!" + code_str
            return code_str, "bool"
        if expr.op in ("<", "<=", ">", ">="):
            ea, eb = expr.arg
            ea_code, ea_is_int = _build_expr_code(code, ea, None)
            eb_code, eb_is_int = _build_expr_code(code, eb, None)
            if ea_is_int:
                if eb_is_int:
                    return ea_code + expr.op + eb_code, "bool"
                else:
                    return ("%s.op_reverse_cmp(%s)%s0" %
                            (eb_code, ea_code, expr.op), "bool")
            else:
                return ("%s.op_cmp(%s)%s0" %
                        (ea_code, eb_code, expr.op), "bool")
        if expr.op == "[:]":
            eo, el = expr.arg
            assert len(el) == 3
            arg_code_str = (
                ",".join(["null" if e is None
                          else _build_expr_code(code, e, "object")
                          for e in el]))
            return ("%s.op_get_slice(%s)" %
                    (_build_expr_code(code, eo, "object"), arg_code_str),
                    "object")
        if expr.op == "list_compr":
            (iter_expr, compr_local_var_set, e, lvalue, name_set,
             if_expr) = expr.arg
            iter_expr_code = _build_expr_code(code, iter_expr, "object")
            compr_arg_list = sorted(compr_local_var_set - name_set)
            arg_code_str = (
                ",".join(["l_" + name for name in compr_arg_list] +
                         [iter_expr_code]))
            compr_number = (
                code.add_list_compr(compr_arg_list, e, lvalue, name_set,
                                    if_expr))
            return "compr_list_%d(%s)" % (compr_number, arg_code_str), "object"
        if expr.op == "dict_compr":
            (iter_expr, compr_local_var_set, ek, ev, lvalue, name_set,
             if_expr) = expr.arg
            iter_expr_code = _build_expr_code(code, iter_expr, "object")
            compr_arg_list = sorted(compr_local_var_set - name_set)
            arg_code_str = (
                ",".join(["l_" + name for name in compr_arg_list] +
                         [iter_expr_code]))
            compr_number = (
                code.add_dict_compr(compr_arg_list, ek, ev, lvalue, name_set,
                                    if_expr))
            return "compr_dict_%d(%s)" % (compr_number, arg_code_str), "object"
        if expr.op == "lambda":
            lambda_local_var_set, arg_list, e = expr.arg
            lambda_stat_arg_list = (
                sorted(lambda_local_var_set - set(arg_list)))
            stat_arg_code_str = (
                ",".join(["l_" + name for name in lambda_stat_arg_list]))
            lambda_number = (
                code.add_lambda(lambda_stat_arg_list, arg_list, e))
            return ("new Lambda_%d(%s)" % (lambda_number, stat_arg_code_str),
                    "object")
        if expr.op == "call_class":
            t, el = expr.arg
            return ("(new Cls_%s()).construct(%s)" %
                    (t.value,
                     ",".join([_build_expr_code(code, e, "object")
                               for e in el])),
                    "object")
        if expr.op == "this.attr":
            if code.lambda_outter_class_name is None:
                return "this.m_%s" % expr.arg.value, "object"
            else:
                return ("Cls_%s.this.m_%s" %
                        (code.lambda_outter_class_name, expr.arg.value),
                        "object")
        if expr.op in ("this", "super"):
            if code.lambda_outter_class_name is None:
                return expr.op, "object"
            else:
                return ("Cls_%s.%s" % (code.lambda_outter_class_name, expr.op),
                        "object")
        if expr.op == "int()":
            return ("LarUtil.convert_to_int(%s)" %
                    ",".join([_build_expr_code(code, e, None)[0]
                              for e in expr.arg]),
                    "int")
        if expr.op == ".int":
            expr_code, is_int = _build_expr_code(code, expr.arg, None)
            if is_int:
                return expr_code, "int"
            else:
                return expr_code + ".as_int()", "int"
        if expr.op == "[].int":
            ea, eb = expr.arg
            #下标运算左运算分量需要是object
            return ("%s.op_get_item_int(%s)" %
                    (_build_expr_code(code, ea, "object"),
                     _build_expr_code(code, eb, None)[0])), "int"

        raise Exception("unreachable expr.op[%s]" % expr.op)

    expr_code, type = _build_expr_code_original(expr)
    if expr_code not in ("this", "super"):
        expr_code = "(%s)" % expr_code

    if type == "object":
        if expect_type == "bool":
            return "(%s.op_bool())" % expr_code
        elif expect_type == "int":
            return "(%s.as_int())" % expr_code
        elif expect_type == "object":
            return expr_code
        else:
            return expr_code, False
    if type == "int":
        if expect_type == "bool":
            return "(%s != 0)" % expr_code
        elif expect_type == "object":
            return "(new LarObjInt(%s))" % expr_code
        elif expect_type == "int":
            return expr_code
        else:
            return expr_code, True
    if type == "bool":
        if expect_type == "bool":
            return expr_code
        else:
            expr_code = "(%s?LarBuiltin.TRUE:LarBuiltin.FALSE)" % expr_code
            if expect_type == "int":
                return "(%s.as_int())" % expr_code
            if expect_type == "object":
                return expr_code
            else:
                return expr_code, False
    if type == "const_int":
        assert expr_code.startswith("(CONST_") and expr_code.endswith(")")
        value = code.int_const_map[int(expr_code[7 : -1])]
        if expect_type == "bool":
            return "((%s) != 0)" % value
        elif expect_type == "object":
            return expr_code
        elif expect_type == "int":
            return "(%s)" % value
        else:
            return "(%s)" % value, True

    raise Exception("unreachable[%s]" % type)

def _output_global_init(code, global_var_map, export_global_var_set,
                        global_var_type_info):
    for var_name in global_var_map:
        var_type = global_var_type_info[var_name]
        code += (
            "%s static %s g_%s = %s;" %
            ("public" if var_name in export_global_var_set else "private",
             _TYPE_NAME_MAP[var_type], var_name,
             _TYPE_INIT_VALUE_MAP[var_type]))
    code += ""
    code.blk_start("public static void init() throws Exception")
    for var_name, expr in global_var_map.iteritems():
        var_type = global_var_type_info[var_name]
        if var_type == "object":
            code += ("g_%s = %s;" %
                     (var_name, _build_expr_code(code, expr, "object")))
        else:
            code += ("g_%s = %s;" %
                     (var_name, _build_expr_code(code, expr, None)[0]))
    code.blk_end()
    code += ""

def _output_assign(code, lvalue, expr_code, is_int = False):
    if lvalue.op == "local_name":
        if (is_int and
            code.curr_func.local_var_type_info[lvalue.arg.value] == "object"):
            code += ("l_%s = new LarObjInt(%s);" %
                     (lvalue.arg.value, expr_code))
        else:
            code += "l_%s = %s;" % (lvalue.arg.value, expr_code)
        return
    if lvalue.op == "global_name":
        if (is_int and
            code.curr_module.global_var_type_info[lvalue.arg.value] ==
            "object"):
            code += ("g_%s = new LarObjInt(%s);" %
                     (lvalue.arg.value, expr_code))
        else:
            code += "g_%s = %s;" % (lvalue.arg.value, expr_code)
        return
    if lvalue.op == "module.global":
        if is_int:
            expr_code = "new LarObjInt(%s)" % expr_code
        code += ("Mod_%s.g_%s = %s;" %
                 (lvalue.arg[0].value, lvalue.arg[1].value, expr_code))
        return
    if lvalue.op == ".":
        if is_int:
            expr_code = "new LarObjInt(%s)" % expr_code
        e, attr = lvalue.arg
        code.add_lar_obj_op_attr(attr.value)
        code += ("%s.op_set_attr_%s(%s);" %
                 (_build_expr_code(code, e, "object"), attr.value, expr_code))
        return
    if lvalue.op == "[]":
        ea, eb = lvalue.arg
        code += ("%s.op_set_item(%s, %s);" %
                 (_build_expr_code(code, ea, "object"),
                  _build_expr_code(code, eb, None)[0], expr_code))
        return
    if lvalue.op == "[:]":
        if is_int:
            expr_code = "new LarObjInt(%s)" % expr_code
        eo, el = lvalue.arg
        code += ("%s.op_set_slice(%s,%s);" %
                 (_build_expr_code(code, eo, "object"),
                  ",".join(["null" if e is None
                            else _build_expr_code(code, e, "object")
                            for e in el]), expr_code))
        return
    if lvalue.op in ("tuple", "list"):
        if is_int:
            expr_code = "new LarObjInt(%s)" % expr_code
        unpack_number = code.new_unpack_number()
        unpack_tmp_array = "unpack_tmp_array_%d" % unpack_number
        code += ("LarObj[] %s = LarUtil.unpack_seq(%s, %d);" %
                 (unpack_tmp_array, expr_code, len(lvalue.arg)))
        for i, unpack_lvalue in enumerate(lvalue.arg):
            _output_assign(
                code, unpack_lvalue, "%s[%d]" % (unpack_tmp_array, i))
        return
    if lvalue.op == "this.attr":
        if is_int:
            expr_code = "new LarObjInt(%s)" % expr_code
        if code.lambda_outter_class_name is None:
            code += "this.m_%s = %s;" % (lvalue.arg.value, expr_code)
        else:
            code += ("Cls_%s.this.m_%s = %s;" %
                     (code.lambda_outter_class_name, lvalue.arg.value,
                      expr_code))
        return
    raise Exception("unreachable lvalue.op[%s]" % lvalue.op)

def _output_stmt_list(code, stmt_list):
    for stmt in stmt_list:
        if stmt.type in ("break", "continue"):
            code += stmt.type + ";"
            continue
        if stmt.type == "print":
            for e in stmt.expr_list:
                code += ("System.out.print(%s.op_str());" %
                         _build_expr_code(code, e, "object"))
                code += 'System.out.print(" ");'
            if stmt.print_new_line:
                code += "System.out.println();"
            continue
        if stmt.type == "return":
            if stmt.expr is None:
                code += "return LarBuiltin.NIL;"
            else:
                if code.curr_func.ret_type == "object":
                    code += ("return %s;" %
                             _build_expr_code(code, stmt.expr, "object"))
                else:
                    code += ("return %s;" %
                             _build_expr_code(code, stmt.expr, None)[0])
            continue
        if stmt.type == "expr":
            expr_code = _build_expr_code(code, stmt.expr, None)[0]
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
                           _build_expr_code(code, stmt.expr, "bool"))
            _output_stmt_list(code, stmt.stmt_list)
            code.blk_end()
            continue
        if stmt.type == "if":
            in_else_if = False
            for e, if_stmt_list in stmt.if_list:
                if in_else_if:
                    code.blk_start("else if (%s)" %
                                   _build_expr_code(code, e, "bool"))
                else:
                    code.blk_start("if (%s)" %
                                   _build_expr_code(code, e, "bool"))
                    in_else_if = True
                _output_stmt_list(code, if_stmt_list)
                code.blk_end()
            if stmt.else_stmt_list is not None:
                code.blk_start("else")
                _output_stmt_list(code, stmt.else_stmt_list)
                code.blk_end()
            continue
        if stmt.type == "=":
            _output_assign(code, stmt.lvalue,
                           *_build_expr_code(code, stmt.expr, None))
            continue
        if stmt.type == "for":
            tmp_iter_number = code.new_tmp_iter_number()
            tmp_iter = "tmp_iter_%d" % tmp_iter_number
            if (stmt.expr.op == "call_builtin_if" and
                stmt.expr.arg[0].value == "range"):
                #针对range的特殊处理
                range_arg_list = stmt.expr.arg[1]
                if len(range_arg_list) == 3:
                    #附带step的，慢速处理
                    code.blk_start(
                        "for (LarObjRange %s = %s; %s.has_next();)" %
                        (tmp_iter, _build_expr_code(code, stmt.expr, "object"),
                         tmp_iter))
                    _output_assign(code, stmt.lvalue, "%s.next()" % tmp_iter,
                                   True)
                else:
                    #顺序递增的range可进一步优化
                    tmp_iter_start = "tmp_iter_start_%d" % tmp_iter_number
                    tmp_iter_end = "tmp_iter_end_%d" % tmp_iter_number
                    if len(range_arg_list) == 2:
                        start_e, end_e = range_arg_list
                        code += ("long %s = %s;" %
                                 (tmp_iter_start,
                                  _build_expr_code(code, start_e, "int")))
                        code += ("long %s = %s;" %
                                 (tmp_iter_end,
                                  _build_expr_code(code, end_e, "int")))
                    elif len(range_arg_list) == 1:
                        end_e = range_arg_list[0]
                        code += "long %s = 0;" % tmp_iter_start
                        code += ("long %s = %s;" %
                                 (tmp_iter_end,
                                  _build_expr_code(code, end_e, "int")))
                    else:
                        raise Exception("unreachable")
                    code.blk_start(
                        "for (long %s = %s; %s < %s;)" %
                        (tmp_iter, tmp_iter_start, tmp_iter, tmp_iter_end))
                    _output_assign(code, stmt.lvalue, "(%s ++)" % tmp_iter,
                                   True)
            elif stmt.expr.op == "tuple":
                #针对tuple的特殊处理
                tmp_iter_index = tmp_iter + "_index"
                code += "int %s = 0;" % tmp_iter_index
                code.blk_start(
                    "for (LarObj[] %s = LarUtil.make_array(%s); "
                    "%s < %s.length; ++ %s)" %
                    (tmp_iter, ",".join([_build_expr_code(code, e, "object")
                                         for e in stmt.expr.arg]),
                     tmp_iter_index, tmp_iter, tmp_iter_index))
                _output_assign(code, stmt.lvalue,
                               "%s[%s]" % (tmp_iter, tmp_iter_index))
            else:
                code.blk_start(
                    "for (LarObj %s = %s.meth_iterator(); "
                    "%s.meth_has_next().op_bool();)" %
                    (tmp_iter, _build_expr_code(code, stmt.expr, "object"),
                     tmp_iter))
                _output_assign(code, stmt.lvalue, "%s.meth_next()" % tmp_iter)
            _output_stmt_list(code, stmt.stmt_list)
            code.blk_end()
            continue
        if stmt.type in ("%=", "^=", "&=", "*=", "-=", "+=", "|=", "/=",
                         "<<=", ">>=", ">>>="):
            #增量赋值，需保证左值只计算一次
            lvalue = stmt.lvalue
            expr_code, expr_is_int = _build_expr_code(code, stmt.expr, None)
            inplace_op_name = ("op_inplace_" +
                               _BINOCULAR_OP_NAME_MAP[stmt.type[: -1]])
            #对于变量类的直接调用对应inplace操作函数
            if lvalue.op == "local_name":
                if (code.curr_func.local_var_type_info[lvalue.arg.value] ==
                    "object"):
                    code += ("l_%s = l_%s.%s(%s);" %
                             (lvalue.arg.value, lvalue.arg.value,
                              inplace_op_name, expr_code))
                else:
                    assert expr_is_int
                    code += "l_%s += %s;" % (lvalue.arg.value, expr_code)
                continue
            if lvalue.op == "global_name":
                if (code.curr_module.global_var_type_info[lvalue.arg.value] ==
                    "object"):
                    code += ("g_%s = g_%s.%s(%s);" %
                             (lvalue.arg.value, lvalue.arg.value,
                              inplace_op_name, expr_code))
                else:
                    assert expr_is_int
                    code += "g_%s += %s;" % (lvalue.arg.value, expr_code)
                continue
            if lvalue.op == "module.global":
                var_name = ("Mod_%s.g_%s" %
                            (lvalue.arg[0].value, lvalue.arg[1].value))
                code += ("%s = %s.%s(%s);" %
                         (var_name, var_name, inplace_op_name, expr_code))
                continue
            #对于左值为属性和下标的，需要借助临时变量
            if lvalue.op == ".":
                e, attr = lvalue.arg
                code.add_lar_obj_op_attr(attr.value)
                code += ("tmp_augmented_assign_object = %s;" %
                         _build_expr_code(code, e, "object"))
                code += ("tmp_augmented_assign_object.op_set_attr_%s("
                         "tmp_augmented_assign_object.op_get_attr_%s()."
                         "%s(%s));" %
                         (attr.value, attr.value, inplace_op_name, expr_code))
                continue
            if lvalue.op == "[]":
                ea, eb = lvalue.arg
                code += ("tmp_augmented_assign_object = %s;" %
                         _build_expr_code(code, ea, "object"))
                subscr_code, subscr_is_int = _build_expr_code(code, eb, None)
                if subscr_is_int:
                    code += ("tmp_augmented_assign_subscript_int = %s;" %
                             subscr_code)
                    code += ("tmp_augmented_assign_object.op_set_item("
                             "tmp_augmented_assign_subscript_int, "
                             "tmp_augmented_assign_object.op_get_item("
                             "tmp_augmented_assign_subscript_int).%s(%s));" %
                             (inplace_op_name, expr_code))
                else:
                    code += ("tmp_augmented_assign_subscript = %s;" %
                             subscr_code)
                    code += ("tmp_augmented_assign_object.op_set_item("
                             "tmp_augmented_assign_subscript, "
                             "tmp_augmented_assign_object.op_get_item("
                             "tmp_augmented_assign_subscript).%s(%s));" %
                             (inplace_op_name, expr_code))
                continue
            raise Exception("unreachable")

        raise Exception("unreachable")

def _output_func(code, func, export):
    arg_code_list = []
    for arg_name in func.arg_list:
        arg_code_list.append(
            "%s l_%s" %
            (_TYPE_NAME_MAP[func.local_var_type_info[arg_name]], arg_name))
    code.blk_start(
        "%s static %s f_%s(%s) throws Exception" %
        ("public" if export else "private", _TYPE_NAME_MAP[func.ret_type],
         func.name, ",".join(arg_code_list)))
    #增量赋值使用的临时变量
    code += "LarObj tmp_augmented_assign_object = LarBuiltin.NIL;"
    code += "LarObj tmp_augmented_assign_subscript = LarBuiltin.NIL;"
    code += "long tmp_augmented_assign_subscript_int = 0;"
    for var_name in func.local_var_set - set(func.arg_list):
        if func.local_var_type_info[var_name] == "object":
            code += "LarObj l_%s = LarBuiltin.NIL;" % var_name
        else:
            code += "long l_%s = 0;" % var_name
    code += ""
    code.curr_func = func
    _output_stmt_list(code, func.stmt_list)
    del code.curr_func
    code.blk_end()
    code += ""

def _output_list_compr(code, idx,
                       (compr_arg_list, e, lvalue, name_set, if_expr)):
    code.blk_start(
        "private static LarObjList compr_list_%d(%s) throws Exception" %
        (idx, ",".join(["LarObj l_%s" % name for name in compr_arg_list] +
                       ["LarObj iterable"])))
    for name in name_set:
        code += "LarObj l_%s;" % name
    code += "LarObjList list = new LarObjList();"
    code.blk_start("for (LarObj iter = iterable.meth_iterator(); "
                   "iter.meth_has_next().op_bool();)")
    _output_assign(code, lvalue, "iter.meth_next()")
    if if_expr is not None:
        code.blk_start("if (%s.op_bool())" %
                       _build_expr_code(code, if_expr, "object"))
    code += "list.meth_add(%s);" % _build_expr_code(code, e, None)[0]
    if if_expr is not None:
        code.blk_end()
    code.blk_end()
    code += "return list;"
    code.blk_end()
    code += ""

def _output_list_compr_in_class(code, idx,
                                (compr_arg_list, e, lvalue, name_set,
                                 if_expr)):
    code.blk_start(
        "private LarObjList compr_list_%d(%s) throws Exception" %
        (idx, ",".join(["LarObj l_%s" % name for name in compr_arg_list] +
                       ["LarObj iterable"])))
    for name in name_set:
        code += "LarObj l_%s;" % name
    code += "LarObjList list = new LarObjList();"
    code.blk_start("for (LarObj iter = iterable.meth_iterator(); "
                   "iter.meth_has_next().op_bool();)")
    _output_assign(code, lvalue, "iter.meth_next()")
    if if_expr is not None:
        code.blk_start("if (%s.op_bool())" %
                       _build_expr_code(code, if_expr, "object"))
    code += "list.meth_add(%s);" % _build_expr_code(code, e, None)[0]
    if if_expr is not None:
        code.blk_end()
    code.blk_end()
    code += "return list;"
    code.blk_end()
    code += ""

def _output_dict_compr(code, idx,
                       (compr_arg_list, ek, ev, lvalue, name_set, if_expr)):
    code.blk_start(
        "private static LarObjDict compr_dict_%d(%s) throws Exception" %
        (idx, ",".join(["LarObj l_%s" % name for name in compr_arg_list] +
                       ["LarObj iterable"])))
    for name in name_set:
        code += "LarObj l_%s;" % name
    code += "LarObjDict dict = new LarObjDict();"
    code.blk_start("for (LarObj iter = iterable.meth_iterator(); "
                   "iter.meth_has_next().op_bool();)")
    _output_assign(code, lvalue, "iter.meth_next()")
    if if_expr is not None:
        code.blk_start("if (%s.op_bool())" %
                       _build_expr_code(code, if_expr, "object"))
    code += ("dict.op_set_item(%s, %s);" %
             (_build_expr_code(code, ek, None)[0],
              _build_expr_code(code, ev, None)[0]))
    if if_expr is not None:
        code.blk_end()
    code.blk_end()
    code += "return dict;"
    code.blk_end()
    code += ""

def _output_dict_compr_in_class(code, idx,
                                (compr_arg_list, ek, ev, lvalue, name_set,
                                 if_expr)):
    code.blk_start(
        "private LarObjDict compr_dict_%d(%s) throws Exception" %
        (idx, ",".join(["LarObj l_%s" % name for name in compr_arg_list] +
                       ["LarObj iterable"])))
    for name in name_set:
        code += "LarObj l_%s;" % name
    code += "LarObjDict dict = new LarObjDict();"
    code.blk_start("for (LarObj iter = iterable.meth_iterator(); "
                   "iter.meth_has_next().op_bool();)")
    _output_assign(code, lvalue, "iter.meth_next()")
    if if_expr is not None:
        code.blk_start("if (%s.op_bool())" %
                       _build_expr_code(code, if_expr, "object"))
    code += ("dict.op_set_item(%s, %s);" %
             (_build_expr_code(code, ek, None)[0],
              _build_expr_code(code, ev, None)[0]))
    if if_expr is not None:
        code.blk_end()
    code.blk_end()
    code += "return dict;"
    code.blk_end()
    code += ""

def _output_lambda(code, idx, (lambda_stat_arg_list, arg_list, e)):
    code.blk_start("private static final class Lambda_%d extends LarObj" %
                   idx)
    for name in lambda_stat_arg_list:
        code += "private final LarObj l_%s;" % name
    code += ""
    #构造函数
    code.blk_start("Lambda_%d(%s)" %
                   (idx, ",".join(["LarObj %s" % name
                                   for name in lambda_stat_arg_list])))
    for name in lambda_stat_arg_list:
        code += "l_%s = %s;" % (name, name)
    code.blk_end()
    code += ""
    #调用操作
    code.blk_start("public LarObj op_call(%s) throws Exception" %
                   ",".join(["LarObj l_%s" % name for name in arg_list]))
    code += "return %s;" % _build_expr_code(code, e, "object")
    code.blk_end()
    code += ""
    code.blk_end()
    code += ""

def _output_lambda_in_class(code, class_name, idx,
                            (lambda_stat_arg_list, arg_list, e)):
    code.blk_start("private final class Lambda_%d extends LarObj" % idx)
    for name in lambda_stat_arg_list:
        code += "private final LarObj l_%s;" % name
    code += ""
    #构造函数
    code.blk_start("Lambda_%d(%s)" %
                   (idx, ",".join(["LarObj %s" % name
                                   for name in lambda_stat_arg_list])))
    for name in lambda_stat_arg_list:
        code += "l_%s = %s;" % (name, name)
    code.blk_end()
    code += ""
    #调用操作
    code.blk_start("public LarObj op_call(%s) throws Exception" %
                   ",".join(["LarObj l_%s" % name for name in arg_list]))
    #用lambda_outter_class_name属性做状态标记
    code.lambda_outter_class_name = class_name
    code += "return %s;" % _build_expr_code(code, e, "object")
    code.lambda_outter_class_name = None
    code.blk_end()
    code += ""
    code.blk_end()
    code += ""

def _output_method(code, method, cls):
    #先决定method_name等
    if method.name == "__init__":
        #对于构造函数，不直接生成java的构造函数，而是通过代理
        code.blk_start("public Cls_%s construct(%s) throws Exception" %
                       (cls.name,
                        ",".join(["LarObj l_%s" % arg_name
                                  for arg_name in method.arg_list])))
        code += "init(%s);" % ",".join(["l_%s" % arg_name
                                        for arg_name in method.arg_list])
        code += "return this;"
        code.blk_end()
        method_name = "init"
        ret_type = "LarObj"
    #todo：其它内置接口
    else:
        method_name = "meth_%s" % method.name
        ret_type = "LarObj"
    code.blk_start(
        "public %s %s(%s) throws Exception" %
        (ret_type, method_name, ",".join(["LarObj l_%s" % arg_name
                                          for arg_name in method.arg_list])))
    #增量赋值使用的临时变量
    code += "LarObj tmp_augmented_assign_object = LarBuiltin.NIL;"
    code += "LarObj tmp_augmented_assign_subscript = LarBuiltin.NIL;"
    code += "long tmp_augmented_assign_subscript_int = 0;"
    for var_name in method.local_var_set - set(method.arg_list):
        if method.local_var_type_info[var_name] == "object":
            code += "LarObj l_%s = LarBuiltin.NIL;" % var_name
        else:
            code += "long l_%s = 0;" % var_name
    code += ""
    code.curr_func = method
    _output_stmt_list(code, method.stmt_list)
    del code.curr_func
    code.blk_end()
    code += ""

def _output_class(code, cls, module_name, export):
    assert not (code.list_compr_map or code.dict_compr_map or code.lambda_map)
    if cls.base_class is None:
        base_class_code = "LarObj"
    else:
        if cls.base_class_module is None:
            base_class_code = "Cls_%s" % cls.base_class_name
        else:
            base_class_code = ("Mod_%s.Cls_%s" %
                               (cls.base_class_module, cls.base_class_name))
    code.blk_start("%s static class Cls_%s extends %s" %
                   ("public" if export else "private", cls.name,
                    base_class_code))
    #get_type_name
    code.blk_start("public String get_type_name()")
    code += 'return "%s.%s";' % (module_name, cls.name)
    code.blk_end()
    code += ""
    #attr，当前类的属性集合减去基类的
    base_attr_set = set()
    base_class = cls.base_class
    while base_class is not None:
        for attr in base_class.attr_set:
            base_attr_set.add(attr)
        base_class = base_class.base_class
    for attr in cls.attr_set:
        if attr in base_attr_set:
            continue
        code += "protected LarObj m_%s = LarBuiltin.NIL;" % attr
    code += ""
    #attr get/set
    for attr in cls.attr_set:
        if attr in base_attr_set:
            continue
        code.blk_start("public LarObj op_get_attr_%s() throws Exception" %
                       attr)
        code += "return this.m_%s;" % attr
        code.blk_end()
        code.blk_start("public void op_set_attr_%s(LarObj obj) "
                       "throws Exception" % attr)
        code += "this.m_%s = obj;" % attr
        code.blk_end()
    code += ""
    #method
    for method in cls.method_map.itervalues():
        _output_method(code, method, cls)
    #输出解析式、lambda等需要的代码
    while code.list_compr_map or code.dict_compr_map or code.lambda_map:
        while code.list_compr_map:
            _output_list_compr_in_class(code, *code.list_compr_map.popitem())
        while code.dict_compr_map:
            _output_dict_compr_in_class(code, *code.dict_compr_map.popitem())
        while code.lambda_map:
            _output_lambda_in_class(code, cls.name, *code.lambda_map.popitem())
    code.blk_end()
    code += ""

def _output_module(code, module):
    code.blk_start("final class Mod_%s" % module.name)
    code.curr_module = module
    _output_const(code, module.const_map)
    for cls in module.class_map.itervalues():
        _output_class(code, cls, module.name,
                      cls.name in module.export_class_set)
    _output_global_init(
        code, module.global_var_map, module.export_global_var_set,
        module.global_var_type_info)
    for func_key, func in module.func_map.iteritems():
        _output_func(code, func, func_key in module.export_func_set)
    #输出解析式、lambda等需要的代码
    while code.list_compr_map or code.dict_compr_map or code.lambda_map:
        while code.list_compr_map:
            _output_list_compr(code, *code.list_compr_map.popitem())
        while code.dict_compr_map:
            _output_dict_compr(code, *code.dict_compr_map.popitem())
        while code.lambda_map:
            _output_lambda(code, *code.lambda_map.popitem())
    del code.curr_module
    code.blk_end()
    code += ""

def output(out_dir, prog, lib_dir):
    code = _Code(out_dir, prog.main_module_name, lib_dir)

    _output_booter(code, prog)
    for module in prog.module_map.itervalues():
        if isinstance(module, larc_module.ExternModule):
            #外部模块加入code的拷贝列表
            code.add_extern_module(module)
        else:
            _output_module(code, module)

    code.output()
