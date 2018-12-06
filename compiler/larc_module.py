#coding=utf8

"""
编译larva模块
"""

import copy
import os
import larc_common
import larc_token
import larc_type
import larc_stmt
import larc_expr

find_module_file = None

builtins_module = None
module_map = larc_common.OrderedDict()

ginst_being_processed = [None] #用栈记录正在处理的ginst，放一个None在栈底可以简化代码

def _parse_decr_set(token_list):
    decr_set = set()
    while True:
        t = token_list.peek()
        for decr in "public", "native", "final":
            if t.is_reserved(decr):
                if decr in decr_set:
                    t.syntax_err("重复的修饰'%s'" % decr)
                decr_set.add(decr)
                token_list.pop()
                break
        else:
            return decr_set

def _parse_gtp_name_list(token_list, dep_module_map):
    gtp_name_t_list = []
    gtp_name_list = []
    while True:
        t = token_list.peek()
        if t.is_sym(">"):
            token_list.pop_sym()
            break

        t, name = token_list.pop_name()
        if name in dep_module_map:
            t.syntax_err("泛型参数名与导入模块重名")
        if name in gtp_name_list:
            t.syntax_err("泛型参数名重复定义")
        gtp_name_t_list.append(t)
        gtp_name_list.append(name)

        t = token_list.peek()
        if not (t.is_sym and t.value in (">", ",")):
            t.syntax_err("需要','或'>'")
        if t.value == ",":
            token_list.pop_sym()

    if not gtp_name_list:
        t.syntax_err("泛型参数列表不能为空")
    return gtp_name_t_list, gtp_name_list

def _parse_arg_map(token_list, dep_module_map, gtp_name_list):
    arg_name_t_list = []
    arg_map = larc_common.OrderedDict()
    while True:
        t = token_list.peek()
        if t.is_sym(")"):
            return arg_name_t_list, arg_map

        if token_list.peek().is_reserved("ref"):
            token_list.pop()
            is_ref = True
        else:
            is_ref = False
        type = larc_type.parse_type(token_list, dep_module_map, is_ref = is_ref)
        if type.name == "void":
            type.token.syntax_err("参数类型不可为void")
        t, name = token_list.pop_name()
        if name in dep_module_map:
            t.syntax_err("参数名和导入模块名冲突")
        if name in gtp_name_list:
            t.syntax_err("参数名和泛型参数名冲突")
        if name in arg_map:
            t.syntax_err("参数名重定义")
        arg_name_t_list.append(t)
        arg_map[name] = type

        t = token_list.peek()
        if not (t.is_sym and t.value in (")", ",")):
            t.syntax_err("需要','或')'")
        if t.value == ",":
            token_list.pop_sym()

def _parse_usemethod_list(token_list):
    usemethod_list = None
    if token_list.peek().is_sym("("):
        token_list.pop()
        usemethod_list = []
        while True:
            t = token_list.peek()
            if t.is_sym(")"):
                token_list.pop_sym()
                break

            usemethod_name_token, usemethod_name = token_list.pop_name()
            usemethod_list.append((usemethod_name_token, usemethod_name))

            t = token_list.peek()
            if not (t.is_sym and t.value in (")", ",")):
                t.syntax_err("需要','或')'")
            if t.value == ",":
                token_list.pop_sym()

        if not usemethod_list:
            t.syntax_err("usemethod方法列表不能为空")

    return usemethod_list

#下面_ClsBase和_IntfBase的基类，用于定义一些接口和类共有的通用属性和方法
class _CoiBase:
    def __init__(self):
        self.id = larc_common.new_id()
        self.is_cls = isinstance(self, _Cls)
        self.is_gcls_inst = isinstance(self, _GclsInst)
        self.is_intf = isinstance(self, _Intf)
        self.is_gintf_inst = isinstance(self, _GintfInst)
        assert [self.is_cls, self.is_gcls_inst, self.is_intf, self.is_gintf_inst].count(True) == 1

    def is_intf_any(self):
        return (self.is_intf or self.is_gintf_inst) and not self.method_map

    def can_convert_from_array(self, tp):
        if self.is_cls or self.is_gcls_inst:
            #只能是到接口的转换
            return False
        #检查self接口的每个方法是否都符合此数组的内建方法格式
        for method in self.method_map.itervalues():
            if not larc_type.array_has_method(tp, method):
                return False
        return True

    def can_convert_from(self, other):
        assert isinstance(other, _CoiBase) and self is not other
        if self.is_cls or self.is_gcls_inst:
            #只能是到接口的转换
            return False
        #检查self接口的每个方法是否都在other实现了
        for name, method in self.method_map.iteritems():
            if name not in other.method_map:
                #没有对应方法
                return False
            other_method = other.method_map[name]
            if (list(method.decr_set) + list(other_method.decr_set)).count("public") not in (0, 2):
                #权限签名不同
                return False
            if "public" not in method.decr_set and self.module is not other.module:
                #权限私有且两个coi不在同一模块，这个接口无权访问
                return False
            #检查返回类型和参数类型是否一致，参数类型比较必须考虑ref
            if method.type != other_method.type:
                return False
            arg_map = method.arg_map
            other_arg_map = other_method.arg_map
            if len(arg_map) != len(other_arg_map):
                return False
            for i in xrange(len(arg_map)):
                arg_tp = arg_map.value_at(i)
                other_arg_tp = other_arg_map.value_at(i)
                if arg_tp != other_arg_tp or arg_tp.is_ref != other_arg_tp.is_ref:
                    return False
        return True

    def has_method(self, name):
        return name in self.method_map

    def get_method(self, name, t):
        if name in self.method_map:
            return self.method_map[name]
        t.syntax_err("'%s'没有方法'%s'" % (self, name))

#下面_Cls和_GclsInst的基类，只用于定义一些通用属性和方法
class _ClsBase(_CoiBase):
    def __init__(self):
        _CoiBase.__init__(self)
        self.is_construct_method_auto_gened = False

    def expand_usemethod(self, expand_chain):
        if self.is_cls:
            assert not self.gtp_name_list
        else:
            assert self.type_checked

        #检查扩展状态
        assert self.usemethod_stat
        if self.usemethod_stat == "expanded":
            return
        if self.usemethod_stat == "expanding":
            larc_common.exit("检测到环形usemethod：'%s'" % expand_chain)

        self.usemethod_stat = "expanding"

        #统计usemethod属性的类型并确保其中的类都扩展完毕
        usemethod_array_list = []
        usemethod_coi_list = []
        for attr in self.attr_map.itervalues():
            if "usemethod" in attr.decr_set:
                if attr.type.is_array:
                    usemethod_array_list.append(attr)
                else:
                    coi = attr.type.get_coi()
                    if coi.is_cls or coi.is_gcls_inst:
                        coi.expand_usemethod(expand_chain + "." + attr.name)
                    usemethod_coi_list.append((attr, coi))

        #若默认指定，则列表中的类或接口的可见方法都use过来，否则use所有指定方法
        usemethod_map = larc_common.OrderedDict()
        def check_usemethod_name(name):
            if name in usemethod_map:
                larc_common.exit("类'%s'对方法'%s'存在多个可能的usemethod来源" % (self, name))
            if name in self.attr_map:
                larc_common.exit("类'%s'中的属性'%s'和通过usemethod引入的方法同名" % (self, name))
        for attr in usemethod_array_list:
            assert attr.type.is_array
            if attr.usemethod_list is None:
                usemethod_list = list(larc_type.iter_array_method_list(attr.type))
            else:
                usemethod_list = []
                for usemethod_name_token, usemethod_name in attr.usemethod_list:
                    method = larc_type.get_array_method(attr.type, usemethod_name)
                    if method is None:
                        usemethod_name_token.syntax_err("数组没有方法'%s'" % usemethod_name)
                    usemethod_list.append(method)
            for method in usemethod_list:
                if method.name in self.method_map:
                    #在本类已经重新实现的忽略
                    continue
                check_usemethod_name(method.name)
                usemethod_map[method.name] = _UseMethod(self, attr, method)
        for attr, coi in usemethod_coi_list:
            if attr.usemethod_list is None:
                usemethod_list = []
                for method in coi.method_map.itervalues():
                    if coi.module is not self.module and "public" not in method.decr_set:
                        #无访问权限的忽略
                        continue
                    usemethod_list.append(method)
            else:
                usemethod_list = []
                for usemethod_name_token, usemethod_name in attr.usemethod_list:
                    try:
                        method = coi.method_map[usemethod_name]
                    except KeyError:
                        usemethod_name_token.syntax_err("'%s'没有方法'%s'" % (coi, usemethod_name))
                    if coi.module is not self.module and "public" not in method.decr_set:
                        usemethod_name_token.syntax_err("对'%s'的方法'%s'没有访问权限" % (coi, usemethod_name))
                    usemethod_list.append(method)
            for method in usemethod_list:
                if method.name in self.method_map:
                    #在本类已经重新实现的忽略
                    continue
                check_usemethod_name(method.name)
                usemethod_map[method.name] = _UseMethod(self, attr, method)
        for method in usemethod_map.itervalues():
            assert method.name not in self.method_map
            self.method_map[method.name] = method

        self.usemethod_stat = "expanded"

    def has_method_or_attr(self, name):
        return name in self.attr_map or name in self.method_map

    def get_method_or_attr(self, name, token):
        if name in self.method_map:
            return self.method_map[name], None
        if name in self.attr_map:
            return None, self.attr_map[name]
        token.syntax_err("类'%s'没有方法或属性'%s'" % (self, name))

    def get_initable_attr_map(self, t):
        if "native" in self.decr_set:
            t.syntax_err("类'%s'不能按属性初始化：是native类" % self)
        attr_map = larc_common.OrderedDict()
        for attr in self.attr_map.itervalues():
            if "public" not in attr.decr_set:
                t.syntax_err("类'%s'不能按属性初始化：属性'%s'不是public" % (self, attr.name))
            attr_map[attr.name] = attr.type
        return attr_map

class _MethodBase:
    def __init__(self):
        self.is_method = isinstance(self, _Method) or isinstance(self, _GclsInstMethod)
        self.is_usemethod = isinstance(self, _UseMethod)
        assert [self.is_method, self.is_usemethod].count(True) == 1

class _Method(_MethodBase):
    def __init__(self, cls, decr_set, type, name, arg_name_t_list, arg_map, block_token_list):
        _MethodBase.__init__(self)

        self.cls = cls
        self.module = cls.module
        self.decr_set = decr_set
        self.type = type
        self.name = name
        self.arg_name_t_list = arg_name_t_list
        self.arg_map = arg_map
        self.block_token_list = block_token_list

    __repr__ = __str__ = lambda self : "%s.%s" % (self.cls, self.name)

    def check_name_conflict(self):
        for name_t, name in zip(self.arg_name_t_list, self.arg_map):
            for m in self.module, builtins_module:
                if m is not None:
                    elem = m.get_elem(name, public_only = m is builtins_module)
                    if elem is not None:
                        name_t.syntax_err("参数'%s'和'%s'名字冲突" % (name, elem))

    def check_type(self):
        self.type.check(self.cls.module)
        for tp in self.arg_map.itervalues():
            tp.check(self.cls.module)

    def check_type_ignore_gtp(self, gtp_name_set):
        self.type.check_ignore_gtp(self.cls.module, gtp_name_set)
        for tp in self.arg_map.itervalues():
            tp.check_ignore_gtp(self.cls.module, gtp_name_set)

    def compile(self):
        if self.block_token_list is None:
            self.stmt_list = None
        else:
            self.stmt_list = larc_stmt.Parser(self.block_token_list, self.cls.module, self.cls.module.get_dep_module_map(self.cls.file_name),
                                              self.cls, None, self).parse((self.arg_map.copy(),), 0, 0)
            self.block_token_list.pop_sym("}")
            assert not self.block_token_list
        del self.block_token_list

class _Attr:
    def __init__(self, cls, decr_set, type, name, usemethod_list):
        self.cls = cls
        self.module = cls.module
        self.decr_set = decr_set
        self.type = type
        self.name = name
        self.usemethod_list = usemethod_list

    __repr__ = __str__ = lambda self : "%s.%s" % (self.cls, self.name)

    def check_type(self):
        self.type.check(self.cls.module)

    def check_type_ignore_gtp(self, gtp_name_set):
        self.type.check_ignore_gtp(self.cls.module, gtp_name_set)

class _UseMethod(_MethodBase):
    def __init__(self, cls, attr, method):
        _MethodBase.__init__(self)

        self.attr = attr
        self.used_method = method

        self.cls = cls
        self.module = cls.module
        self.decr_set = method.decr_set
        self.type = method.type
        self.name = method.name
        self.arg_map = method.arg_map

    __repr__ = __str__ = lambda self : "%s.usemethod[%s.%s]" % (self.cls, self.attr.name, self.used_method)

class _Cls(_ClsBase):
    def __init__(self, module, file_name, decr_set, name_t, name, gtp_name_t_list, gtp_name_list):
        _ClsBase.__init__(self)

        if gtp_name_list:
            assert "native" not in decr_set

        self.module = module
        self.file_name = file_name
        self.decr_set = decr_set
        self.name_t = name_t
        self.name = name
        self.gtp_name_t_list = gtp_name_t_list
        self.gtp_name_list = gtp_name_list
        self.construct_method = None
        self.attr_map = larc_common.OrderedDict()
        self.method_map = larc_common.OrderedDict()
        self.usemethod_stat = None

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def parse(self, token_list):
        while True:
            t = token_list.peek()
            if t.is_sym("}"):
                break

            #解析修饰
            decr_set = _parse_decr_set(token_list)
            if set(["native", "final"]) & decr_set:
                t.syntax_err("方法或属性不能用native或final修饰")

            t = token_list.peek()
            if t.is_name and t.value == self.name:
                t, name = token_list.pop_name()
                if token_list.peek().is_sym("("):
                    #构造方法
                    token_list.pop_sym("(")
                    self._parse_method(decr_set, larc_type.VOID_TYPE, name, token_list)
                    continue
                token_list.revert()

            #解析属性或方法
            type = larc_type.parse_type(token_list, self.module.get_dep_module_map(self.file_name))
            t, name = token_list.pop_name()
            if name == self.name:
                t.syntax_err("属性或方法不可与类同名")
            self._check_redefine(t, name)
            next_t = token_list.pop()
            if next_t.is_sym("("):
                #方法
                self._parse_method(decr_set, type, name, token_list)
                continue
            if next_t.is_sym and next_t.value in (";", ",") or next_t.is_reserved("usemethod"):
                #属性
                if type.name == "void":
                    t.syntax_err("属性类型不可为void")
                while True:
                    usemethod_list = None
                    if next_t.is_reserved("usemethod"):
                        if type.is_nil or not type.is_obj_type:
                            t.syntax_err("usemethod不可用于类型'%s'" % type)
                        decr_set.add("usemethod")
                        usemethod_list = _parse_usemethod_list(token_list)

                        next_t = token_list.pop()
                        if not (next_t.is_sym and next_t.value in (",", ";")):
                            next_t.syntax_err("需要','或';'")
                    self.attr_map[name] = _Attr(self, decr_set, type, name, usemethod_list)
                    if next_t.is_sym(";"):
                        break
                    #多属性定义
                    assert next_t.is_sym(",")
                    t, name = token_list.pop_name()
                    self._check_redefine(t, name)
                    next_t = token_list.pop()
                    if not (next_t.is_sym and next_t.value in (",", ";") or next_t.is_reserved("usemethod")):
                        next_t.syntax_err()
                continue
            next_t.syntax_err()
        if self.construct_method is None:
            #生成默认构造方法，非public，无参数，无指令
            if "native" in self.decr_set:
                block_token_list = None
            else:
                block_token_list = larc_token.gen_empty_token_list("}")
            self.construct_method = _Method(self, set(), larc_type.VOID_TYPE, self.name, [], larc_common.OrderedDict(), block_token_list)
            self.is_construct_method_auto_gened = True
        self.usemethod_stat = "to_expand"

    def _check_redefine(self, t, name):
        for i in self.attr_map, self.method_map:
            if name in i:
                t.syntax_err("属性或方法名重定义")

    def _parse_method(self, decr_set, type, name, token_list):
        arg_name_t_list, arg_map = _parse_arg_map(token_list, self.module.get_dep_module_map(self.file_name), self.gtp_name_list)
        token_list.pop_sym(")")

        if "native" in self.decr_set:
            token_list.pop_sym(";")
            block_token_list = None
        else:
            token_list.pop_sym("{")
            block_token_list, sym = larc_token.parse_token_list_until_sym(token_list, ("}",))
            assert sym == "}"

        if name == self.name:
            #构造方法
            assert type is larc_type.VOID_TYPE
            self.construct_method = _Method(self, decr_set, larc_type.VOID_TYPE, name, arg_name_t_list, arg_map, block_token_list)
        else:
            self.method_map[name] = _Method(self, decr_set, type, name, arg_name_t_list, arg_map, block_token_list)

    def check_name_conflict(self):
        for name_t, name in zip(self.gtp_name_t_list, self.gtp_name_list):
            for m in self.module, builtins_module:
                if m is not None:
                    elem = self.module.get_elem(name, public_only = m is builtins_module)
                    if elem is not None:
                        name_t.syntax_err("泛型参数'%s'和'%s'名字冲突" % (name, elem))
        self.construct_method.check_name_conflict()
        for method in self.method_map.itervalues():
            method.check_name_conflict()

    def check_type(self):
        assert not self.gtp_name_list
        for attr in self.attr_map.itervalues():
            attr.check_type()
        self.construct_method.check_type()
        for method in self.method_map.itervalues():
            method.check_type()

    def check_type_ignore_gtp(self):
        assert self.gtp_name_list
        gtp_name_set = set(self.gtp_name_list)
        for attr in self.attr_map.itervalues():
            attr.check_type_ignore_gtp(gtp_name_set)
        self.construct_method.check_type_ignore_gtp(gtp_name_set)
        for method in self.method_map.itervalues():
            method.check_type_ignore_gtp(gtp_name_set)

    def compile(self):
        assert not self.gtp_name_list
        self.construct_method.compile()
        for method in self.method_map.itervalues():
            if method.is_usemethod:
                continue
            method.compile()

class _GclsInstMethod(_MethodBase):
    def __init__(self, gcls_inst, method):
        _MethodBase.__init__(self)

        self.cls = gcls_inst
        self.method = method

        self.module = gcls_inst.module
        self.decr_set = method.decr_set
        self.type = copy.deepcopy(method.type)
        self.name = method.name
        self.arg_map = copy.deepcopy(method.arg_map)
        self.block_token_list = method.block_token_list.copy()

    __repr__ = __str__ = lambda self : "%s.%s" % (self.cls, self.method.name)

    def check_type(self):
        self.type.check(self.cls.gcls.module, self.cls.gtp_map)
        for tp in self.arg_map.itervalues():
            tp.check(self.cls.gcls.module, self.cls.gtp_map)

    def compile(self):
        self.stmt_list = larc_stmt.Parser(self.block_token_list, self.module, self.module.get_dep_module_map(self.cls.file_name), self.cls,
                                          self.cls.gtp_map, self).parse((self.arg_map.copy(),), 0, 0)
        self.block_token_list.pop_sym("}")
        assert not self.block_token_list
        del self.block_token_list

class _GclsInstAttr:
    def __init__(self, gcls_inst, attr):
        self.cls = gcls_inst
        self.attr = attr

        self.module = gcls_inst.module
        self.decr_set = attr.decr_set
        self.type = copy.deepcopy(attr.type)
        self.name = attr.name
        self.usemethod_list = attr.usemethod_list

    __repr__ = __str__ = lambda self : "%s.%s" % (self.cls, self.attr.name)

    def check_type(self):
        self.type.check(self.cls.gcls.module, self.cls.gtp_map)

class _GclsInst(_ClsBase):
    def __init__(self, gcls, gtp_list, creator_token):
        _ClsBase.__init__(self)

        self.gcls = gcls

        self.gtp_map = larc_common.OrderedDict()
        assert len(gcls.gtp_name_list) == len(gtp_list)
        for i in xrange(len(gtp_list)):
            self.gtp_map[gcls.gtp_name_list[i]] = gtp_list[i]

        self.ginst_creator = ginst_being_processed[-1]
        self.creator_token = creator_token

        self.module = gcls.module
        self.decr_set = gcls.decr_set
        self.name = gcls.name
        self.file_name = gcls.file_name
        self._init_attr_and_method()
        self.type_checked = False
        self.usemethod_stat = "to_expand"
        self.compiled = False

    __repr__ = __str__ = lambda self : "%s<%s>" % (self.gcls, ", ".join([str(tp) for tp in self.gtp_map.itervalues()]))

    def _init_attr_and_method(self):
        assert self.gcls.construct_method is not None
        self.construct_method = _GclsInstMethod(self, self.gcls.construct_method)
        self.attr_map = larc_common.OrderedDict()
        for name, attr in self.gcls.attr_map.iteritems():
            self.attr_map[name] = _GclsInstAttr(self, attr)
        self.method_map = larc_common.OrderedDict()
        for name, method in self.gcls.method_map.iteritems():
            self.method_map[name] = _GclsInstMethod(self, method)

    def check_type(self):
        if self.type_checked:
            return False
        for attr in self.attr_map.itervalues():
            attr.check_type()
        self.construct_method.check_type()
        for method in self.method_map.itervalues():
            method.check_type()
        self.type_checked = True
        return True

    def compile(self):
        if self.compiled:
            return False
        self.construct_method.compile()
        for method in self.method_map.itervalues():
            if method.is_usemethod:
                continue
            method.compile()
        self.compiled = True
        return True

#下面_Intf和_GintfInst的基类，只用于定义一些通用属性和方法
class _IntfBase(_CoiBase):
    def get_method_or_attr(self, name, token):
        if name in self.method_map:
            return self.method_map[name], None
        token.syntax_err("接口'%s'没有方法'%s'" % (self, name))

    def expand_usemethod(self, expand_chain):
        if self.is_intf:
            assert not self.gtp_name_list
        else:
            assert self.type_checked

        #检查扩展状态
        assert self.usemethod_stat
        if self.usemethod_stat == "expanded":
            return
        if self.usemethod_stat == "expanding":
            larc_common.exit("检测到环形usemethod：'%s'" % expand_chain)

        self.usemethod_stat = "expanding"

        #确保所有usemethod的类型是接口，并确保对其扩展完毕
        for tp, _ in self.usemethod_intf_list:
            assert not tp.is_nil
            if tp.is_coi_type:
                coi = tp.get_coi()
                if coi.is_intf or coi.is_gintf_inst:
                    coi.expand_usemethod("%s.(%s)" % (expand_chain, coi))
                    continue
            tp.token.syntax_err("需要接口类型")

        #根据usemethod的指定列表将method复制到当前接口，如未指定列表则复制所有method
        usemethod_map = larc_common.OrderedDict()
        for tp, usemethod_list in self.usemethod_intf_list:
            assert tp.is_coi_type
            coi = tp.get_coi()
            assert coi.is_intf or coi.is_gintf_inst
            assert coi.usemethod_stat == "expanded"
            if usemethod_list is None:
                usemethod_list = []
                for method in coi.method_map.itervalues():
                    if coi.module is not self.module and "public" not in method.decr_set:
                        #无访问权限的忽略
                        continue
                    usemethod_list.append(method)
            else:
                it = iter(usemethod_list)
                usemethod_list = []
                for usemethod_name_token, usemethod_name in it:
                    try:
                        method = coi.method_map[usemethod_name]
                    except KeyError:
                        usemethod_name_token.syntax_err("'%s'没有方法'%s'" % (coi, usemethod_name))
                    if coi.module is not self.module and "public" not in method.decr_set:
                        usemethod_name_token.syntax_err("对'%s'的方法'%s'没有访问权限" % (coi, usemethod_name))
                    usemethod_list.append(method)
            for method in usemethod_list:
                if method.name in self.method_map:
                    #在本接口已经重新定义的忽略
                    continue
                if method.name in usemethod_map:
                    #有多个来源，检查是否一致，一致的话忽略，不一致则报错
                    used_method = usemethod_map[method.name]
                    assert used_method.name == method.name
                    class MethodNotMatch(Exception):
                        pass
                    try:
                        if (used_method.decr_set != method.decr_set or used_method.type != method.type or
                            len(used_method.arg_map) != len(method.arg_map)):
                            raise MethodNotMatch()
                        for used_method_arg_tp, arg_tp in zip(used_method.arg_map.itervalues(), method.arg_map.itervalues()):
                            if ((used_method_arg_tp.is_ref and not arg_tp.is_ref) or (not used_method_arg_tp.is_ref and arg_tp.is_ref) or
                                used_method_arg_tp != arg_tp):
                                raise MethodNotMatch()
                    except MethodNotMatch:
                        larc_common.exit("接口'%s'对方法'%s'存在签名不一致的usemethod来源" % (self, method.name))
                    continue
                usemethod_map[method.name] = _IntfUseMethod(self, method)
        for method in usemethod_map.itervalues():
            assert method.name not in self.method_map
            self.method_map[method.name] = method

        self.usemethod_stat = "expanded"

class _IntfUseMethod:
    def __init__(self, intf, method):
        self.intf = intf
        self.used_method = method

        self.module = intf.module
        self.decr_set = method.decr_set
        self.type = method.type
        self.name = method.name
        self.arg_map = method.arg_map

    __repr__ = __str__ = lambda self : "%s.usemethod[%s]" % (self.intf, self.used_method)

class _IntfMethod:
    def __init__(self, intf, decr_set, type, name, arg_name_t_list, arg_map):
        self.intf = intf

        self.module = intf.module
        self.decr_set = decr_set
        self.type = type
        self.name = name
        self.arg_name_t_list = arg_name_t_list
        self.arg_map = arg_map

    __repr__ = __str__ = lambda self : "%s.%s" % (self.intf, self.name)

    def check_name_conflict(self):
        for name_t, name in zip(self.arg_name_t_list, self.arg_map):
            for m in self.module, builtins_module:
                if m is not None:
                    elem = m.get_elem(name, public_only = m is builtins_module)
                    if elem is not None:
                        name_t.syntax_err("参数'%s'和'%s'名字冲突" % (name, elem))

    def check_type(self):
        self.type.check(self.intf.module)
        for tp in self.arg_map.itervalues():
            tp.check(self.intf.module)

    def check_type_ignore_gtp(self, gtp_name_set):
        self.type.check_ignore_gtp(self.intf.module, gtp_name_set)
        for tp in self.arg_map.itervalues():
            tp.check_ignore_gtp(self.intf.module, gtp_name_set)

class _Intf(_IntfBase):
    def __init__(self, module, file_name, decr_set, name_t, name, gtp_name_t_list, gtp_name_list):
        _IntfBase.__init__(self)

        self.module = module
        self.file_name = file_name
        self.decr_set = decr_set
        self.name_t = name_t
        self.name = name
        self.gtp_name_t_list = gtp_name_t_list
        self.gtp_name_list = gtp_name_list
        self.method_map = larc_common.OrderedDict()
        self.usemethod_intf_list = []
        self.usemethod_stat = None

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def parse(self, token_list):
        while True:
            t = token_list.peek()
            if t.is_sym("}"):
                break

            decr_set = _parse_decr_set(token_list)
            if decr_set - set(["public"]):
                t.syntax_err("接口方法只能用public修饰")

            type = larc_type.parse_type(token_list, self.module.get_dep_module_map(self.file_name))
            if token_list.peek().is_reserved("usemethod"):
                #接口usemethod
                token_list.pop()
                usemethod_list = _parse_usemethod_list(token_list)

                token_list.pop_sym(";")
                self.usemethod_intf_list.append((type, usemethod_list))
                continue
            t, name = token_list.pop_name()
            self._check_redefine(t, name)
            token_list.pop_sym("(")
            self._parse_method(decr_set, type, name, token_list)
        self.usemethod_stat = "to_expand"

    def _check_redefine(self, t, name):
        if name in self.method_map:
            t.syntax_err("接口方法名重定义")

    def _parse_method(self, decr_set, type, name, token_list):
        arg_name_t_list, arg_map = _parse_arg_map(token_list, self.module.get_dep_module_map(self.file_name), self.gtp_name_list)
        token_list.pop_sym(")")
        token_list.pop_sym(";")
        self.method_map[name] = _IntfMethod(self, decr_set, type, name, arg_name_t_list, arg_map)

    def check_name_conflict(self):
        for name_t, name in zip(self.gtp_name_t_list, self.gtp_name_list):
            for m in self.module, builtins_module:
                if m is not None:
                    elem = self.module.get_elem(name, public_only = m is builtins_module)
                    if elem is not None:
                        name_t.syntax_err("泛型参数'%s'和'%s'名字冲突" % (name, elem))
        for method in self.method_map.itervalues():
            method.check_name_conflict()

    def check_type(self):
        assert not self.gtp_name_list
        for tp, _ in self.usemethod_intf_list:
            tp.check(self.module)
        for method in self.method_map.itervalues():
            method.check_type()

    def check_type_ignore_gtp(self):
        assert self.gtp_name_list
        gtp_name_set = set(self.gtp_name_list)
        for tp, _ in self.usemethod_intf_list:
            tp.check_ignore_gtp(self.module, gtp_name_set)
        for method in self.method_map.itervalues():
            method.check_type_ignore_gtp(gtp_name_set)

class _GintfInstMethod:
    def __init__(self, gintf_inst, method):
        self.intf = gintf_inst
        self.method = method

        self.module = gintf_inst.module
        self.decr_set = method.decr_set
        self.type = copy.deepcopy(method.type)
        self.name = method.name
        self.arg_map = copy.deepcopy(method.arg_map)

    __repr__ = __str__ = lambda self : "%s.%s" % (self.intf, self.method.name)

    def check_type(self):
        self.type.check(self.intf.gintf.module, self.intf.gtp_map)
        for tp in self.arg_map.itervalues():
            tp.check(self.intf.gintf.module, self.intf.gtp_map)

class _GintfInst(_IntfBase):
    def __init__(self, gintf, gtp_list, creator_token):
        _IntfBase.__init__(self)

        self.gintf = gintf

        self.gtp_map = larc_common.OrderedDict()
        assert len(gintf.gtp_name_list) == len(gtp_list)
        for i in xrange(len(gtp_list)):
            self.gtp_map[gintf.gtp_name_list[i]] = gtp_list[i]

        self.ginst_creator = ginst_being_processed[-1]
        self.creator_token = creator_token

        self.module = gintf.module
        self.decr_set = gintf.decr_set
        self.name = gintf.name
        self.file_name = gintf.file_name
        self._init_method()
        self.usemethod_intf_list = copy.deepcopy(gintf.usemethod_intf_list)
        self.usemethod_stat = "to_expand"
        self.type_checked = False

    __repr__ = __str__ = lambda self : "%s<%s>" % (self.gintf, ", ".join([str(tp) for tp in self.gtp_map.itervalues()]))

    def _init_method(self):
        self.method_map = larc_common.OrderedDict()
        for name, method in self.gintf.method_map.iteritems():
            self.method_map[name] = _GintfInstMethod(self, method)

    def check_type(self):
        if self.type_checked:
            return False
        for tp, _ in self.usemethod_intf_list:
            tp.check(self.module, self.gtp_map)
        for method in self.method_map.itervalues():
            method.check_type()
        self.type_checked = True
        return True

class _FuncBase:
    def __init__(self):
        self.id = larc_common.new_id()
        self.is_func = isinstance(self, _Func)
        self.is_gfunc_inst = isinstance(self, _GfuncInst)
        assert [self.is_func, self.is_gfunc_inst].count(True) == 1

class _Func(_FuncBase):
    def __init__(self, module, file_name, decr_set, type, name_t, name, gtp_name_t_list, gtp_name_list, arg_name_t_list, arg_map,
                 block_token_list):
        _FuncBase.__init__(self)

        self.module = module
        self.file_name = file_name
        self.decr_set = decr_set
        self.type = type
        self.name_t = name_t
        self.name = name
        self.gtp_name_t_list = gtp_name_t_list
        self.gtp_name_list = gtp_name_list
        self.arg_name_t_list = arg_name_t_list
        self.arg_map = arg_map
        self.block_token_list = block_token_list

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def check_name_conflict(self):
        for name_t, name in zip(self.gtp_name_t_list, self.gtp_name_list):
            for m in self.module, builtins_module:
                if m is not None:
                    elem = self.module.get_elem(name, public_only = m is builtins_module)
                    if elem is not None:
                        name_t.syntax_err("泛型参数'%s'和'%s'名字冲突" % (name, elem))
        for name_t, name in zip(self.arg_name_t_list, self.arg_map):
            for m in self.module, builtins_module:
                if m is not None:
                    elem = m.get_elem(name, public_only = m is builtins_module)
                    if elem is not None:
                        name_t.syntax_err("参数'%s'和'%s'名字冲突" % (name, elem))

    def check_type(self):
        assert not self.gtp_name_list
        self.type.check(self.module)
        for tp in self.arg_map.itervalues():
            tp.check(self.module)

    def check_type_ignore_gtp(self):
        assert self.gtp_name_list
        gtp_name_set = set(self.gtp_name_list)
        self.type.check_ignore_gtp(self.module, gtp_name_set)
        for tp in self.arg_map.itervalues():
            tp.check_ignore_gtp(self.module, gtp_name_set)

    def compile(self):
        if self.block_token_list is None:
            self.stmt_list = None
        else:
            self.stmt_list = larc_stmt.Parser(self.block_token_list, self.module, self.module.get_dep_module_map(self.file_name), None, None,
                                              self).parse((self.arg_map.copy(),), 0, 0)
            self.block_token_list.pop_sym("}")
            assert not self.block_token_list
        del self.block_token_list

class _GfuncInst(_FuncBase):
    def __init__(self, gfunc, gtp_list, creator_token):
        _FuncBase.__init__(self)

        self.gfunc = gfunc

        self.module = gfunc.module
        self.decr_set = gfunc.decr_set
        self.name = gfunc.name
        self.file_name = gfunc.file_name

        self.gtp_map = larc_common.OrderedDict()
        assert len(gfunc.gtp_name_list) == len(gtp_list)
        for i in xrange(len(gtp_list)):
            self.gtp_map[gfunc.gtp_name_list[i]] = gtp_list[i]

        self.ginst_creator = ginst_being_processed[-1]
        self.creator_token = creator_token

        self.type = copy.deepcopy(gfunc.type)
        self.arg_map = copy.deepcopy(gfunc.arg_map)
        self.block_token_list = gfunc.block_token_list.copy()

        self.type_checked = False
        self.compiled = False

    __repr__ = __str__ = lambda self : "%s<%s>" % (self.gfunc, ", ".join([str(tp) for tp in self.gtp_map.itervalues()]))

    def check_type(self):
        if self.type_checked:
            return False
        self.type.check(self.gfunc.module, self.gtp_map)
        for tp in self.arg_map.itervalues():
            tp.check(self.gfunc.module, self.gtp_map)
        self.type_checked = True
        return True

    def compile(self):
        if self.compiled:
            return False
        self.stmt_list = larc_stmt.Parser(self.block_token_list, self.module, self.module.get_dep_module_map(self.file_name), None,
                                          self.gtp_map, self).parse((self.arg_map.copy(),), 0, 0)
        self.block_token_list.pop_sym("}")
        assert not self.block_token_list
        del self.block_token_list
        self.compiled = True
        return True

class _GlobalVar:
    def __init__(self, module, file_name, decr_set, type, name_t, name, expr_token_list):
        self.module = module
        self.file_name = file_name
        self.decr_set = decr_set
        self.type = type
        self.name_t = name_t
        self.name = name
        self.expr_token_list = expr_token_list
        self.used_dep_module_set = set()

    __repr__ = __str__ = lambda self : "%s.%s" % (self.module, self.name)

    def check_type(self):
        self.type.check(self.module)

    def compile(self):
        if self.expr_token_list is None:
            self.expr = None
        else:
            self.expr = larc_expr.Parser(self.expr_token_list, self.module, self.module.get_dep_module_map(self.file_name), None,
                                         None, None, self.used_dep_module_set).parse((), self.type)
            t, sym = self.expr_token_list.pop_sym()
            assert not self.expr_token_list and sym in (";", ",")
        del self.expr_token_list

        if self.module.name in self.used_dep_module_set:
            self.used_dep_module_set.remove(self.module.name)
        for used_dep_module in self.used_dep_module_set:
            module_map[used_dep_module].check_cycle_import_for_gv_init(self, [used_dep_module])

class _NativeFile:
    def __init__(self, module, sub_module_name, file_path_name):
        assert os.path.isfile(file_path_name) and file_path_name.endswith(sub_module_name + ".lar_native")
        self.module = module
        self.sub_module_name = sub_module_name
        self.file_path_name = file_path_name
        self.line_list = [line.rstrip() for line in larc_common.open_src_file(file_path_name)]
        self.dep_module_set = set()
        self._parse()

    def _parse(self):
        #先检查文件头
        if not self.line_list or self.line_list[0].split() != ["package", "LARVA_NATIVE"]:
            larc_common.exit("native实现[%s]格式错误：第一行必须为'package LARVA_NATIVE'" % self.file_path_name)

        #逐行扫描，分析标识符的宏替换
        for i, line in enumerate(self.line_list):
            self.line_list[i] = self._analyze_name_macro(i + 1, line)

    def _analyze_name_macro(self, line_no, line):
        #native文件的token类，只用于报告错误
        class NativeFileToken:
            def __init__(token_self, pos):
                token_self.pos_desc = "文件[%s]行[%d]列[%d]" % (self.file_path_name, line_no, pos + 1)
            def syntax_err(self, msg):
                larc_common.exit("%s %s" % (self.pos_desc, msg))

        #line转换为一个列表，列表元素为字符串或元组，字符串为单行的子串，元组为解析后的标识符宏(module_name, name)
        result = []
        idx = 0
        while True:
            pos = line.find("@<<", idx)
            if pos < 0:
                result.append(line[idx :])
                return result
            result.append(line[idx : pos])
            token = NativeFileToken(pos)
            end_pos = line.find(">>", pos + 3)
            if end_pos < 0:
                token.syntax_err("非法的标识符宏：找不到结束标记'>>'")
            macro = line[pos + 3 : end_pos]
            idx = end_pos + 2
            #开始分析macro
            if "." in macro:
                #带模块的macro
                relative_deep = None
                if macro.startswith("./"):
                    relative_deep = 0
                    macro = macro[2 :]
                elif macro.startswith("../"):
                    relative_deep = 0
                    while macro.startswith("../"):
                        macro = macro[3 :]
                        relative_deep += 1
                try:
                    module_name, name = macro.split(".")
                except ValueError:
                    token.syntax_err("非法的标识符宏")
                if not all([larc_token.is_valid_name(p) for p in module_name.split("/")]):
                    token.syntax_err("非法的标识符宏")
                #module_name相当于匿名导入了一个模块，按import流程处理：修正module_name后加入dep_module_set
                module_name = self.module.fix_module_name(relative_deep, token, module_name)
                self.dep_module_set.add(module_name)
            elif macro.startswith(":"):
                #__builtin模块name简写形式
                module_name = "__builtins"
                name = macro[1 :]
            else:
                #单个name
                module_name = self.module.name
                name = macro
            if not larc_token.is_valid_name(name):
                token.syntax_err("非法的标识符宏")
            result.append((module_name, name))

class NativeCode:
    def __init__(self, module, file_name, gtp_map, t, is_global = False):
        self.module = module
        self.file_name = os.path.join(module.dir, file_name)
        self.gtp_map = gtp_map
        self.t = t
        self.is_global = is_global
        self.line_list = t.value[:]
        self._parse()

    def _parse(self):
        #逐行扫描，分析标识符的宏替换
        for i, line in enumerate(self.line_list):
            self.line_list[i] = self._analyze_name_macro(i + 1, line)

    def _analyze_name_macro(self, line_no, line):
        #native code的token类，只用于报告错误
        class NativeCodeToken:
            def __init__(token_self, pos):
                token_self.pos_desc = "文件[%s]行[%d]列[%d]" % (self.t.src_file, self.t.line_no + line_no, pos + 1)
            def syntax_err(self, msg):
                larc_common.exit("%s %s" % (self.pos_desc, msg))

        #line转换为一个列表，列表元素为字符串、类型或元组，字符串为单行的子串，类型为替换后的泛型类型，元组为解析后的标识符宏(module_name, name)
        result = []
        idx = 0
        while True:
            pos = line.find("@<<", idx)
            if pos < 0:
                result.append(line[idx :])
                return result
            result.append(line[idx : pos])
            token = NativeCodeToken(pos)
            end_pos = line.find(">>", pos + 3)
            if end_pos < 0:
                token.syntax_err("非法的标识符宏：找不到结束标记'>>'")
            macro = line[pos + 3 : end_pos]
            idx = end_pos + 2
            #开始分析macro
            if macro.startswith("{") and macro.endswith("}"):
                #泛型类型
                gtp_name = macro[1 : -1]
                if not larc_token.is_valid_name(gtp_name):
                    token.syntax_err("非法的标识符宏：非法的泛型类型名")
                if self.gtp_map is None:
                    token.syntax_err("非法的标识符宏：无效的泛型，不在泛型类或泛型函数的代码块中")
                if gtp_name not in self.gtp_map:
                    token.syntax_err("非法的标识符宏：找不到泛型类型")
                gtp = self.gtp_map[gtp_name]
                result.append(gtp)
                continue
            if "." in macro:
                #带模块的macro
                relative_deep = None
                if macro.startswith("./"):
                    relative_deep = 0
                    macro = macro[2 :]
                elif macro.startswith("../"):
                    relative_deep = 0
                    while macro.startswith("../"):
                        macro = macro[3 :]
                        relative_deep += 1
                try:
                    module_name, name = macro.split(".")
                except ValueError:
                    token.syntax_err("非法的标识符宏")
                if not all([larc_token.is_valid_name(p) for p in module_name.split("/")]):
                    token.syntax_err("非法的标识符宏")
                #module_name相当于匿名导入了一个模块，若是global域的native_code则按import流程处理：修正module_name后加入dep_module_set
                module_name = self.module.fix_module_name(relative_deep, token, module_name)
                if self.is_global:
                    self.module.dep_module_set_of_global_native_code.add(module_name)
                else:
                    if module_name not in module_map:
                        #处于代码块中的native_code引用了一个没有被预处理导入的模块，报错
                        token.syntax_err("模块'%s'需要显式导入" % module_name)
            elif macro.startswith(":"):
                #__builtin模块name简写形式
                module_name = "__builtins"
                name = macro[1 :]
            else:
                #单个name
                module_name = self.module.name
                name = macro
            if not larc_token.is_valid_name(name):
                token.syntax_err("非法的标识符宏")
            result.append((module_name, name))

dep_module_token_map = {}
class Module:
    def __init__(self, name):
        file_path_name = find_module_file(name)
        assert os.path.isdir(file_path_name)
        assert file_path_name.endswith(os.path.join(*name.split("/")))
        self.dir = file_path_name
        self.name = name
        file_name_list = [fn for fn in os.listdir(self.dir) if fn.endswith(".lar")]
        native_file_name_list = [fn for fn in os.listdir(self.dir) if fn.endswith(".lar_native")]

        self.file_dep_module_map_map = {}
        self.cls_map = larc_common.OrderedDict()
        self.gcls_inst_map = larc_common.OrderedDict()
        self.intf_map = larc_common.OrderedDict()
        self.gintf_inst_map = larc_common.OrderedDict()
        self.func_map = larc_common.OrderedDict()
        self.gfunc_inst_map = larc_common.OrderedDict()
        self.global_var_map = larc_common.OrderedDict()
        self.literal_str_list = []
        self.literal_number_list = []
        self.native_file_map = {}
        self.global_native_code_map = {}
        self.dep_module_set_of_global_native_code = set()
        for file_name in file_name_list:
            self._precompile(file_name)
        for file_name in native_file_name_list:
            self._parse_native_file(file_name)
        self._check_name_conflict()

    __repr__ = __str__ = lambda self : self.name

    def _check_name_conflict(self):
        #如果不是内建模块，则检查本模块name和内建模块导出name是否冲突
        if builtins_module is not None:
            for map in self.cls_map, self.intf_map, self.func_map, self.global_var_map:
                for i in map.itervalues():
                    elem = builtins_module.get_elem(i.name, public_only = True)
                    if elem is not None:
                        i.name_t.syntax_err("'%s'与'%s'名字冲突" % (i, elem))
        #依次检查类、接口和函数的定义名字中是否有冲突的
        for map in self.cls_map, self.intf_map, self.func_map:
            for i in map.itervalues():
                i.check_name_conflict()

    def get_elem(self, name, public_only = False):
        for map in self.cls_map, self.intf_map, self.func_map, self.global_var_map:
            if name in map:
                elem = map[name]
                if public_only and "public" not in elem.decr_set:
                    return None
                return elem
        return None

    def _parse_native_file(self, file_name):
        assert file_name.endswith(".lar_native")
        sub_module_name = file_name[: -11]
        file_path_name = os.path.join(self.dir, file_name)
        if not os.path.isfile(file_path_name):
            larc_common.exit("[%s]需要是一个文件" % file_path_name)
        self.native_file_map[sub_module_name] = _NativeFile(self, sub_module_name, file_path_name)

    def _precompile(self, file_name):
        #解析token列表，解析正文
        file_path_name = os.path.join(self.dir, file_name)
        if not os.path.isfile(file_path_name):
            larc_common.exit("[%s]需要是一个文件" % file_path_name)
        token_list = larc_token.parse_token_list(file_path_name)
        self._parse_text(file_name, token_list)

    def _parse_text(self, file_name, token_list):
        self.file_dep_module_map_map[file_name] = dep_module_map = larc_common.OrderedDict()
        import_end = False
        self.global_native_code_map[file_name] = native_code_list = []
        self.literal_str_list += [t for t in token_list if t.type == "literal_str"]
        self.literal_number_list += [
            t for t in token_list
            if t.type.startswith("literal_") and t.type[8 :] in ("char", "int", "uint", "long", "ulong", "float", "double")]
        while token_list:
            #解析import
            t = token_list.peek()
            if t.is_reserved("import"):
                #import
                if import_end:
                    t.syntax_err("import必须在模块代码最前面")
                self._parse_import(token_list, dep_module_map)
                continue
            import_end = True

            #解析global域的native_code
            if t.is_native_code:
                token_list.pop()
                native_code_list.append(NativeCode(self, file_name, None, t, is_global = True))
                continue

            #解析修饰
            decr_set = _parse_decr_set(token_list)

            #解析各种定义
            t = token_list.peek()
            if t.is_reserved("class"):
                #解析类
                if decr_set - set(["public", "native"]):
                    t.syntax_err("类只能用public和native修饰")
                self._parse_cls(file_name, dep_module_map, decr_set, token_list)
                continue

            if t.is_reserved("interface"):
                #解析interface
                if decr_set - set(["public"]):
                    t.syntax_err("interface只能用public修饰")
                self._parse_intf(file_name, dep_module_map, decr_set, token_list)
                continue

            #可能是函数或全局变量
            type = larc_type.parse_type(token_list, dep_module_map)
            name_t, name = token_list.pop_name()
            self._check_redefine(name_t, name, dep_module_map)
            t, sym = token_list.pop_sym()
            if sym in ("(", "<"):
                #函数
                if decr_set - set(["public", "native"]):
                    t.syntax_err("函数只能用public和native修饰")
                if sym == "<" and "native" in decr_set:
                    t.syntax_err("不可定义native泛型函数")
                self._parse_func(file_name, dep_module_map, decr_set, type, name_t, sym == "<", token_list)
                continue
            if sym in (";", "=", ","):
                #全局变量
                if decr_set - set(["public", "final"]):
                    t.syntax_err("全局变量只能用public和final修饰")
                if type.name == "void":
                    t.syntax_err("变量类型不可为void")
                while True:
                    if sym == "=":
                        expr_token_list, sym = larc_token.parse_token_list_until_sym(token_list, (";", ","))
                    else:
                        expr_token_list = None
                    self.global_var_map[name] = _GlobalVar(self, file_name, decr_set, type, name_t, name, expr_token_list)
                    if sym == ";":
                        break
                    #定义了多个变量，继续解析
                    assert sym == ","
                    t, name = token_list.pop_name()
                    self._check_redefine(t, name, dep_module_map)
                    t, sym = token_list.pop_sym()
                    if sym not in (";", "=", ","):
                        t.syntax_err()
                continue

            t.syntax_err()

    def _check_redefine(self, t, name, dep_module_map):
        if name in dep_module_map:
            t.syntax_err("定义的名字和导入模块名重名")
        for i in self.cls_map, self.intf_map, self.global_var_map, self.func_map:
            if name in i:
                t.syntax_err("名字重定义")

    def fix_module_name(self, relative_deep, module_name_token, module_name):
        #若为相对路径导入，则修正为普通module_name并做路径一致性检查
        if relative_deep is not None:
            pl = self.name.split("/")
            if relative_deep > len(pl):
                #相对路径超过了当前模块层级
                module_name_token.syntax_err("非法的相对路径模块[%s/%s%s]" % (self.name, "../" * relative_deep, module_name))
            expect_module_dir = (
                os.path.abspath(os.path.join(self.dir, *([".."] * relative_deep + module_name.split("/"))))) #期望目录是相对当前模块路径的位置
            module_name = "/".join(pl[: len(pl) - relative_deep] + [module_name]) #修正module_name
            dep_module_token_map[module_name] = module_name_token #修正后立即记录token，下面find时候马上可能用到
            module_dir = find_module_file(module_name) #试着找一下模块目录
            if module_dir != expect_module_dir:
                #找到了但是和期望不符，也报错
                module_name_token.syntax_err("模块[%s]存在于其他module_path[%s]" % (module_name, module_dir))
        else:
            dep_module_token_map[module_name] = module_name_token
        return module_name

    def _parse_import(self, token_list, dep_module_map):
        t = token_list.pop()
        assert t.is_reserved("import")
        while True:
            #获取module_name全名
            module_name_token = token_list.peek()
            relative_deep = None
            if token_list.peek().is_sym("."):
                relative_deep = 0
                token_list.pop_sym(".")
                token_list.pop_sym("/")
            elif token_list.peek().is_sym(".."):
                relative_deep = 0
                while token_list.peek().is_sym(".."):
                    token_list.pop_sym("..")
                    token_list.pop_sym("/")
                    relative_deep += 1
            module_name = ""
            while True:
                t, name = token_list.pop_name()
                module_name += name
                if not token_list.peek().is_sym("/"):
                    break
                token_list.pop_sym("/")
                module_name += "/"

            module_name = self.fix_module_name(relative_deep, module_name_token, module_name)

            #检查是否设置别名，没设置则采用module name最后一个域作为名字
            if token_list.peek().is_reserved("as"):
                token_list.pop()
                t, module_name_alias = token_list.pop_name()
            else:
                module_name_alias = module_name.split("/")[-1]
            if module_name_alias in dep_module_map:
                t.syntax_err("存在重名的模块")
            dep_module_map[module_name_alias] = module_name
            t = token_list.peek()
            if not t.is_sym:
                t.syntax_err("需要';'或','")
            t, sym = token_list.pop_sym()
            if sym == ";":
                return
            if sym != ",":
                t.syntax_err("需要';'或','")

    def _parse_cls(self, file_name, dep_module_map, decr_set, token_list):
        t = token_list.pop()
        assert t.is_reserved("class")
        name_t, name = token_list.pop_name()
        self._check_redefine(name_t, name, dep_module_map)
        t = token_list.peek()
        if t.is_sym("<"):
            if "native" in decr_set:
                t.syntax_err("不可定义native泛型类")
            token_list.pop_sym("<")
            gtp_name_t_list, gtp_name_list = _parse_gtp_name_list(token_list, dep_module_map)
            if name in gtp_name_list:
                t.syntax_err("存在与类名相同的泛型参数名")
        else:
            gtp_name_t_list = []
            gtp_name_list = []
        token_list.pop_sym("{")
        cls = _Cls(self, file_name, decr_set, name_t, name, gtp_name_t_list, gtp_name_list)
        cls.parse(token_list)
        token_list.pop_sym("}")
        self.cls_map[name] = cls

    def _parse_intf(self, file_name, dep_module_map, decr_set, token_list):
        t = token_list.pop()
        assert t.is_reserved("interface")
        name_t, name = token_list.pop_name()
        self._check_redefine(name_t, name, dep_module_map)
        t = token_list.peek()
        if t.is_sym("<"):
            token_list.pop_sym("<")
            gtp_name_t_list, gtp_name_list = _parse_gtp_name_list(token_list, dep_module_map)
        else:
            gtp_name_t_list = []
            gtp_name_list = []
        token_list.pop_sym("{")
        intf = _Intf(self, file_name, decr_set, name_t, name, gtp_name_t_list, gtp_name_list)
        intf.parse(token_list)
        token_list.pop_sym("}")
        self.intf_map[name] = intf

    def _parse_func(self, file_name, dep_module_map, decr_set, type, name_t, is_gfunc, token_list):
        name = name_t.value

        if is_gfunc:
            gtp_name_t_list, gtp_name_list = _parse_gtp_name_list(token_list, dep_module_map)
            token_list.pop_sym("(")
        else:
            gtp_name_t_list = []
            gtp_name_list = []
        arg_name_t_list, arg_map = _parse_arg_map(token_list, dep_module_map, gtp_name_list)
        token_list.pop_sym(")")

        if "native" in decr_set:
            assert not is_gfunc
            token_list.pop_sym(";")
            block_token_list = None
        else:
            token_list.pop_sym("{")
            block_token_list, sym = larc_token.parse_token_list_until_sym(token_list, ("}",))
            assert sym == "}"

        self.func_map[name] = _Func(self, file_name, decr_set, type, name_t, name, gtp_name_t_list, gtp_name_list, arg_name_t_list, arg_map,
                                    block_token_list)

    def check_type_for_non_ginst(self):
        for map in self.cls_map, self.intf_map, self.func_map:
            for i in map.itervalues():
                if i.gtp_name_list:
                    #泛型元素做check type ignore gtp
                    i.check_type_ignore_gtp()
                else:
                    #普通check type
                    i.check_type()
        for i in self.global_var_map.itervalues():
            i.check_type()

    def check_type_for_ginst(self):
        for map in self.gcls_inst_map, self.gintf_inst_map, self.gfunc_inst_map:
            #反向遍历，优先处理新ginst
            for i in xrange(len(map) - 1, -1, -1):
                ginst_being_processed.append(map.value_at(i))
                result = ginst_being_processed[-1].check_type()
                ginst_being_processed.pop()
                if result:
                    #成功处理了一个新的，立即返回
                    return True
        #全部都无需处理
        return False

    def expand_intf_usemethod(self):
        for intf in self.intf_map.itervalues():
            if intf.gtp_name_list:
                continue
            intf.expand_usemethod(str(intf))
        for gintf_inst in self.gintf_inst_map.itervalues():
            gintf_inst.expand_usemethod(str(gintf_inst))

    def expand_cls_usemethod(self):
        for cls in self.cls_map.itervalues():
            if cls.gtp_name_list:
                continue
            cls.expand_usemethod(str(cls))
        for gcls_inst in self.gcls_inst_map.itervalues():
            gcls_inst.expand_usemethod(str(gcls_inst))

    def check_main_func(self):
        if "main" not in self.func_map:
            larc_common.exit("主模块[%s]没有main函数" % self)
        main_func = self.func_map["main"]
        if main_func.gtp_name_list:
            larc_common.exit("主模块[%s]的main函数不能是泛型函数" % self)
        if main_func.type != larc_type.INT_TYPE:
            larc_common.exit("主模块[%s]的main函数返回类型必须为int" % self)
        if len(main_func.arg_map) != 1:
            larc_common.exit("主模块[%s]的main函数只能有一个类型为'__builtins.String[]'的参数" % self)
        tp = main_func.arg_map.value_at(0)
        if tp.array_dim_count != 1 or tp.is_ref or tp.to_elem_type() != larc_type.STR_TYPE:
            larc_common.exit("主模块[%s]的main函数的参数类型必须为'__builtins.String[]'" % self)
        if "public" not in main_func.decr_set:
            larc_common.exit("主模块[%s]的main函数必须是public的" % self)

    def compile_non_ginst(self):
        for map in self.cls_map, self.func_map:
            for i in map.itervalues():
                if i.gtp_name_list:
                    continue
                i.compile()
        for i in self.global_var_map.itervalues():
            i.compile()

    def compile_ginst(self):
        for map in self.gcls_inst_map, self.gfunc_inst_map:
            #反向遍历，优先处理新ginst
            for i in xrange(len(map) - 1, -1, -1):
                assert ginst_being_processed[-1] is None
                ginst_being_processed.append(map.value_at(i))
                result = ginst_being_processed[-1].compile()
                ginst_being_processed.pop()
                if result:
                    #成功处理了一个新的，立即返回
                    return True
        #全部都无需处理
        return False

    def check_cycle_import_for_gv_init(self, gv, stk):
        assert stk and stk[-1] == self.name
        for dep_module in self.get_dep_module_set():
            if dep_module == gv.module.name:
                larc_common.exit("全局变量'%s'的初始化依赖于模块'%s'，且存在从其依赖关系开始并包含模块'%s'的循环模块依赖：%s" %
                                 (gv, stk[0], gv.module.name, "->".join([gv.module.name] + stk + [dep_module])))
            if dep_module in stk:
                #进入循环依赖但不包含gv模块，继续探测
                continue
            stk.append(dep_module)
            module_map[dep_module].check_cycle_import_for_gv_init(gv, stk)
            stk.pop()

    def get_coi_original(self, name):
        assert self.has_coi(name)
        if name in self.cls_map:
            return self.cls_map[name]
        return self.intf_map[name]

    def get_coi(self, type):
        is_cls = is_intf = False
        if type.name in self.cls_map:
            is_cls = True
            coi = self.cls_map[type.name]
            tp_desc = "类"
        elif type.name in self.intf_map:
            is_intf = True
            coi = self.intf_map[type.name]
            tp_desc = "接口"
        else:
            return None

        if coi.gtp_name_list:
            if type.gtp_list:
                if len(coi.gtp_name_list) != len(type.gtp_list):
                    type.token.syntax_err("泛型参数数量错误：需要%d个，传入了%d个" % (len(coi.gtp_name_list), len(type.gtp_list)))
            else:
                type.token.syntax_err("泛型%s'%s'无法单独使用" % (tp_desc, coi))
        else:
            if type.gtp_list:
                type.token.syntax_err("'%s'不是泛型%s" % (coi, tp_desc))

        assert len(coi.gtp_name_list) == len(type.gtp_list)
        if not coi.gtp_name_list:
            return coi

        #泛型类或接口，生成gXXX实例后再返回，ginst_key是这个泛型实例的唯一key标识
        ginst_key = coi.id,
        for tp in type.gtp_list:
            array_dim_count = tp.array_dim_count
            while tp.is_array:
                tp = tp.to_elem_type()
            if tp.token.is_reserved:
                ginst_key += tp.name, array_dim_count
            else:
                ginst_key += tp.get_coi().id, array_dim_count

        if is_cls:
            ginst_map = self.gcls_inst_map
            ginst_class = _GclsInst
        else:
            assert is_intf
            ginst_map = self.gintf_inst_map
            ginst_class = _GintfInst
        if ginst_key in ginst_map:
            return ginst_map[ginst_key]
        ginst_map[ginst_key] = ginst = ginst_class(coi, type.gtp_list, type.token)

        s = str(ginst)
        if len(s) > 1000:
            larc_common.exit("存在名字过长的泛型实例，请检查是否存在泛型实例的无限递归构建：%s" % s)

        return ginst

    def get_func_original(self, name):
        assert self.has_func(name)
        return self.func_map[name]

    def get_func(self, t, gtp_list):
        name = t.value
        if name not in self.func_map:
            return None
        func = self.func_map[name]
        if func.gtp_name_list:
            if gtp_list:
                if len(func.gtp_name_list) != len(gtp_list):
                    t.syntax_err("泛型参数数量错误：需要%d个，传入了%d个" % (len(func.gtp_name_list), len(gtp_list)))
            else:
                t.syntax_err("泛型函数'%s'无法单独使用" % func)
        else:
            if gtp_list:
                t.syntax_err("'%s'不是泛型函数" % func)

        assert len(func.gtp_name_list) == len(gtp_list)
        if not func.gtp_name_list:
            return func

        #泛型函数，生成gfunc实例后再返回，gfunc_key是这个泛型实例的唯一key标识
        gfunc_key = func.id,
        for tp in gtp_list:
            array_dim_count = tp.array_dim_count
            while tp.is_array:
                tp = tp.to_elem_type()
            if tp.token.is_reserved:
                gfunc_key += tp.name, array_dim_count
            else:
                gfunc_key += tp.get_coi().id, array_dim_count

        if gfunc_key in self.gfunc_inst_map:
            return self.gfunc_inst_map[gfunc_key]
        self.gfunc_inst_map[gfunc_key] = gfunc_inst = _GfuncInst(func, gtp_list, t)

        s = str(gfunc_inst)
        if len(s) > 1000:
            larc_common.exit("存在名字过长的泛型实例，请检查是否存在泛型实例的无限递归构建：%s" % s)

        return gfunc_inst

    def get_global_var(self, name):
        return self.global_var_map[name] if name in self.global_var_map else None

    def has_type(self, name):
        return name in self.cls_map or name in self.intf_map

    has_coi = has_type

    def has_func(self, name):
        return name in self.func_map

    def has_global_var(self, name):
        return name in self.global_var_map

    def get_main_func(self):
        assert "main" in self.func_map
        return self.func_map["main"]

    def has_native_item(self):
        for cls in self.cls_map.itervalues():
            if "native" in cls.decr_set:
                return True
        for func in self.func_map.itervalues():
            if "native" in func.decr_set:
                return True
        return False

    def get_dep_module_set(self):
        dep_module_set = set()
        for m in self.file_dep_module_map_map.itervalues():
            dep_module_set |= set(m.itervalues())
        for nf in self.native_file_map.itervalues():
            dep_module_set |= nf.dep_module_set
        dep_module_set |= self.dep_module_set_of_global_native_code
        return dep_module_set

    def get_dep_module_map(self, file_name):
        return self.file_dep_module_map_map[file_name]

#反复对所有新增的ginst进行check type，直到完成
def check_type_for_ginst():
    while True:
        for m in module_map.itervalues():
            if m.check_type_for_ginst():
                #有一个模块刚check了新的ginst，有可能生成新ginst，重启check流程
                break
        else:
            #所有ginst都check完毕
            break

#在编译过程中如果可能新生成了泛型实例，则调用这个进行check type和usemethod的expand
def check_new_ginst_during_compile():
    check_type_for_ginst()
    for m in module_map.itervalues():
        m.expand_intf_usemethod()
    for m in module_map.itervalues():
        m.expand_cls_usemethod()

def decide_if_name_maybe_type_by_lcgb(name, var_map_stk, gtp_map, dep_module_map, module):
    for var_map in var_map_stk:
        if name in var_map:
            return False #局部变量
    if gtp_map is not None and name in gtp_map:
        return True #泛型类型
    if name in dep_module_map:
        return True #显式引用其他模块元素
    if module.has_type(name):
        return True #本模块的类型
    if module.has_func(name) or module.has_global_var(name):
        return False #本模块的函数或全局变量
    if builtins_module.has_type(name):
        #因为只是返回可能性，所以也没必要做是否私有判断了，后面try_parse_type的时候会做的
        return True #内建模块的类型
    if builtins_module.has_func(name) or builtins_module.has_global_var(name):
        return False #内建模块的函数或全局变量
    return True #其他可能
