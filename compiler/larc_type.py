#coding=utf8

"""
类型相关
"""

import larc_common
import larc_module

_BASE_TYPE_LIST = ("void", "bool", "schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "float", "double")

class _Type:
    def __init__(self, (name_token, name), token_list, dep_module_set, module_name = None, non_array = False, is_ref = False):
        self.token = name_token
        self.name = name
        self.module_name = module_name
        self.array_dim_count = 0
        self.gtp_list = []
        if not self.token.is_reserved and token_list and token_list.peek().is_sym("<"):
            #解析泛型参数
            token_list.pop_sym("<")
            self.gtp_list = parse_gtp_list(token_list, dep_module_set)
        if not non_array:
            while token_list and token_list.peek().is_sym("["):
                if self.name == "void":
                    token_list.peek().syntax_err("无法定义void的数组")
                if self.name == "nil":
                    raise Exception("Bug")
                token_list.pop_sym("[")
                token_list.pop_sym("]")
                self.array_dim_count += 1
        self.is_ref = is_ref
        self._set_is_XXX()

    def _set_is_XXX(self):
        self.is_array = self.array_dim_count > 0
        self.is_nil = self.token.is_reserved("nil")
        self.is_obj_type = self.is_nil or self.is_array or self.token.is_name
        self.is_void = self.token.is_reserved("void")
        self.is_bool_type = self.token.is_reserved("bool") and self.array_dim_count == 0
        self.is_integer_type = (self.token.is_reserved and
                                self.name in ("schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "literal_int") and
                                self.array_dim_count == 0)
        self.is_unsigned_integer_type = self.is_integer_type and self.name in ("char", "ushort", "uint", "ulong", "literal_int")
        self.is_literal_int = self.is_integer_type and self.name == "literal_int"
        self.is_float_type = self.token.is_reserved and self.name in ("float", "double") and self.array_dim_count == 0
        self.is_number_type = self.is_integer_type or self.is_float_type
        self.can_inc_dec = self.is_integer_type

    def __repr__(self):
        s = self.name
        if self.module_name is not None:
            s = self.module_name + "." + s
        if self.gtp_list:
            s += "<%s>" % ", ".join([str(tp) for tp in self.gtp_list])
        s += "[]" * self.array_dim_count
        return s
    __str__ = __repr__

    def __eq__(self, other):
        return (self.name == other.name and self.module_name == other.module_name and self.gtp_list == other.gtp_list and
                self.array_dim_count == other.array_dim_count)

    def __ne__(self, other):
        return not self == other

    def to_array_type(self, array_dim_count):
        assert self.array_dim_count == 0
        tp = _Type((self.token, self.name), None, None, module_name = self.module_name)
        tp.gtp_list = self.gtp_list
        tp.array_dim_count = array_dim_count
        tp._set_is_XXX()
        return tp

    def to_elem_type(self):
        assert self.array_dim_count > 0
        tp = _Type((self.token, self.name), None, None, module_name = self.module_name)
        tp.gtp_list = self.gtp_list
        tp.array_dim_count = self.array_dim_count - 1
        tp._set_is_XXX()
        return tp

    def get_coi(self):
        assert self.token.is_name and self.module_name is not None and not self.is_array
        m = larc_module.module_map[self.module_name]
        coi = m.get_coi(self)
        assert coi is not None
        return coi

    def check(self, curr_module, gtp_map = None, used_dep_module_set = None):
        if self.token.is_reserved:
            #忽略基础类型
            assert not self.gtp_list
            return
        assert self.token.is_name
        #先check泛型参数
        for tp in self.gtp_list:
            tp.check(curr_module, gtp_map, used_dep_module_set)
        #构建find_path并查找类型，coi = cls_or_intf
        if self.module_name is None:
            if gtp_map is not None and self.name in gtp_map:
                #泛型类型，检查后替换内容
                if self.gtp_list:
                    self.token.syntax_err("泛型参数不可作为泛型类型使用")
                tp = gtp_map[self.name]
                self.token = tp.token.copy_on_pos(self.token) #在当前位置创建一个一样的假token
                self.name = tp.name
                self.module_name = tp.module_name
                self.gtp_list = tp.gtp_list
                self.array_dim_count += tp.array_dim_count #数组维度是累加的
                self._set_is_XXX()
                if used_dep_module_set is not None:
                    used_dep_module_set.add(self.module_name)
                return
            find_path = curr_module, larc_module.builtins_module
        else:
            find_path = larc_module.module_map[self.module_name],
        for m in find_path:
            coi = m.get_coi(self)
            if coi is not None:
                self.module_name = m.name #check的同时也将不带模块的类型标准化
                if m is not curr_module:
                    #非当前模块，检查权限
                    if "public" not in coi.decr_set:
                        self.token.syntax_err("无法使用类型'%s'：没有权限" % self)
                break
        else:
            self.token.syntax_err("无效的类型'%s'" % self)
        if used_dep_module_set is not None:
            used_dep_module_set.add(self.module_name)

    def can_convert_from(self, type):
        for tp in self, type:
            if tp.module_name is None:
                assert tp.token.is_reserved
            else:
                assert tp.token.is_name
        #nil和literal_int类型仅作为字面量的类型，转换的目标类型不可能是nil
        assert not self.is_nil
        if self.is_integer_type:
            assert not self.is_literal_int

        if self == type:
            #完全一样
            return True
        if self.is_obj_type and type.is_nil:
            #允许nil直接赋值给任何对象
            return True
        if self.is_obj_type and not self.is_array and type.is_obj_type and not type.is_array:
            coi = self.get_coi()
            from_coi = type.get_coi()
            #若self是接口，则检查其他对象或接口到接口的转换
            if coi.can_convert_from(from_coi):
                return True

        return False

    def can_force_convert_from(self, type):
        if self.can_convert_from(type):
            #能隐式转换，则也能强制转换
            return True

        #存在数组的情形
        if self.array_dim_count != type.array_dim_count:
            #不同维度的数组肯定不能转换
            return False
        if self.array_dim_count > 0:
            #不同类型的数组也不能互相转
            return False
        assert not (self.is_array or type.is_array) #已排除数组

        #存在基础类型的情形
        if self.module_name is None:
            if type.module_name is not None:
                return False #基础类型和对象无法互相转换
            #两个基础类型，只要都是number就可以
            return self.is_number_type and type.is_number_type
        if type.module_name is None:
            return False #基础类型和对象无法互相转换

        if self.is_obj_type and type.is_obj_type:
            coi = self.get_coi()
            from_coi = type.get_coi()
            #若type是接口，则检查它到其他对象或接口的反向转换（正向的上面隐式转换判断了）
            if from_coi.can_convert_from(coi):
                return True

        return False

class _FakeReservedToken:
    def __init__(self, tp):
        self._tp = tp
    def is_reserved(self, tp):
        return self._tp == tp
    is_name = False

class _FakeNonReservedToken:
    def __init__(self, tp):
        self._tp = tp

        class IsReserved:
            def __nonzero__(self):
                return False
            def __call__(self, word):
                return False

        self.is_reserved = IsReserved()

    is_name = True

for _tp in _BASE_TYPE_LIST + ("literal_int", "nil"):
    exec '%s_TYPE = _Type((_FakeReservedToken("%s"), "%s"), None, None)' % (_tp.upper(), _tp, _tp)
STR_TYPE = _Type((_FakeNonReservedToken("String"), "String"), None, None, module_name = "__builtins")
VALID_ARRAY_IDX_TYPES = [SCHAR_TYPE, CHAR_TYPE]
for _tp in "short", "int", "long":
    VALID_ARRAY_IDX_TYPES.append(eval("%s_TYPE" % _tp.upper()))
    VALID_ARRAY_IDX_TYPES.append(eval("U%s_TYPE" % _tp.upper()))
PTM_TYPE_LIST = [_tp for _tp in _BASE_TYPE_LIST if _tp != "void"]
del _tp

def parse_type(token_list, dep_module_set, is_ref = False, non_array = False):
    assert not (is_ref and non_array) #不可能既是ref又解析数组base
    t = token_list.pop()
    if t.is_reserved and t.value in _BASE_TYPE_LIST:
        return _Type((t, t.value), token_list, dep_module_set, is_ref = is_ref, non_array = non_array)
    if t.is_name:
        if t.value in dep_module_set:
            token_list.pop_sym(".")
            return _Type(token_list.pop_name(), token_list, dep_module_set, module_name = t.value, is_ref = is_ref, non_array = non_array)
        return _Type((t, t.value), token_list, dep_module_set, is_ref = is_ref, non_array = non_array)
    t.syntax_err()

def _try_parse_type(token_list, curr_module, dep_module_set, gtp_map, used_dep_module_set):
    t = token_list.pop()
    if t.is_reserved and t.value in _BASE_TYPE_LIST:
        return _Type((t, t.value), token_list, dep_module_set)
    if t.is_name:
        name = t.value
        if name in dep_module_set:
            module = larc_module.module_map[name]
            token_list.pop_sym(".")
            t, name = token_list.pop_name()
            if module.has_type(name):
                tp = _Type((t, name), token_list, dep_module_set, module_name = module.name)
                tp.check(curr_module, gtp_map, used_dep_module_set)
                larc_module.check_new_ginst_during_compile()
                return tp
        else:
            if gtp_map is not None and name in gtp_map:
                tp = _Type((t, name), token_list, dep_module_set)
                tp.check(curr_module, gtp_map, used_dep_module_set)
                larc_module.check_new_ginst_during_compile()
                return tp
            for module in curr_module, larc_module.builtins_module:
                if module.has_type(name):
                    tp = _Type((t, name), token_list, dep_module_set, module_name = module.name)
                    tp.check(curr_module, gtp_map, used_dep_module_set)
                    larc_module.check_new_ginst_during_compile()
                    return tp
    return None

#若解析类型成功，则统一做check_new_ginst_during_compile，即这个函数只用于编译过程
def try_parse_type(token_list, curr_module, dep_module_set, gtp_map, used_dep_module_set = None):
    revert_idx = token_list.i #用于解析失败时候回滚
    ret = _try_parse_type(token_list, curr_module, dep_module_set, gtp_map, used_dep_module_set)
    if ret is None:
        token_list.revert(revert_idx)
    return ret

def parse_gtp_list(token_list, dep_module_set):
    gtp_list = []
    while True:
        tp = parse_type(token_list, dep_module_set)
        if tp.is_void or tp.is_array:
            tp.token.syntax_err("void或数组不可作为泛型参数传入")
        gtp_list.append(tp)
        t = token_list.pop()
        if t.is_sym(","):
            continue
        if t.is_sym(">"):
            break
        if t.is_sym(">>"):
            token_list.split_shr_sym()
            break
        t.syntax_err("需要','或'>'")
    return gtp_list

def gen_type_from_cls(cls):
    tp = _Type((_FakeNonReservedToken(cls.name), cls.name), None, None, module_name = cls.module.name)
    if cls.is_gcls_inst:
        tp.gtp_list = list(cls.gtp_map.itervalues())
    #这个类型没必要check了，校验一下get_coi正常就直接返回
    assert tp.get_coi() is cls
    return tp
