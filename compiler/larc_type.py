#coding=utf8

"""
类型相关
"""

import larc_common
import larc_module
import larc_token

_BASE_TYPE_LIST = ("void", "bool", "schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "float", "double")

class _Type:
    def __init__(self, (name_token, name), token_list, dep_module_map, module_name = None, non_array = False, is_ref = False):
        self.token = name_token
        self.name = name
        self.module_name = module_name
        self.array_dim_count = 0
        self.gtp_list = []
        if not self.token.is_reserved and token_list and token_list.peek().is_sym("<"):
            #解析泛型参数
            token_list.pop_sym("<")
            self.gtp_list = parse_gtp_list(token_list, dep_module_map)
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
        self.is_checked = False
        self.is_freezed = False

    def _set_is_XXX(self):
        assert self.array_dim_count >= 0
        self.is_array = self.array_dim_count != 0
        self.is_nil = self.token.is_reserved("nil")
        self.is_obj_type = self.is_nil or self.is_array or self.token.is_name
        self.is_void = self.token.is_reserved("void")
        if self.is_void:
            assert not self.is_array
        self.is_bool_type = self.token.is_reserved("bool") and not self.is_array
        self.is_integer_type = (self.token.is_reserved and
                                self.name in ("schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "literal_int") and
                                not self.is_array)
        self.is_unsigned_integer_type = self.is_integer_type and self.name in ("char", "ushort", "uint", "ulong", "literal_int")
        self.is_literal_int = self.is_integer_type and self.name == "literal_int"
        self.is_float_type = self.token.is_reserved and self.name in ("float", "double") and not self.is_array
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

    def __setattr__(self, name, value):
        if self.__dict__.get("is_freezed", False):
            raise Exception("Bug")
        self.__dict__[name] = value

    def __delattr__(self, name):
        if self.__dict__.get("is_freezed", False):
            raise Exception("Bug")
        del self.__dict__[name]

    def __eq__(self, other):
        return (self.name == other.name and self.module_name == other.module_name and self.gtp_list == other.gtp_list and
                self.array_dim_count == other.array_dim_count)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(str(self))

    def to_array_type(self, array_dim_count):
        tp = _Type((self.token, self.name), None, None, module_name = self.module_name)
        tp.gtp_list = self.gtp_list
        tp.array_dim_count = self.array_dim_count + array_dim_count
        tp._set_is_XXX()
        tp.set_is_checked()
        return tp

    def to_elem_type(self):
        assert self.array_dim_count > 0
        tp = _Type((self.token, self.name), None, None, module_name = self.module_name)
        tp.gtp_list = self.gtp_list
        tp.array_dim_count = self.array_dim_count - 1
        tp._set_is_XXX()
        tp.set_is_checked()
        return tp

    def get_coi(self):
        assert self.token.is_name and self.module_name is not None and not self.is_array
        m = larc_module.module_map[self.module_name]
        coi = m.get_coi(self)
        assert coi is not None
        return coi

    #check完成或无需check的时候
    def set_is_checked(self):
        self.is_checked = True
        self.is_freezed = True #锁住type，禁止更改
        if self.is_array:
            _reg_array(self) #注册数组信息

    def check(self, curr_module, gtp_map = None, used_dep_module_set = None):
        if not self.is_checked:
            self._check(curr_module, gtp_map, used_dep_module_set)
            self.set_is_checked()

    def _check(self, curr_module, gtp_map, used_dep_module_set):
        if self.token.is_reserved:
            #忽略基础类型（及其数组类型）
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
        #check并标准化coi类型，不影响是否为数组
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
        #确保已经check过了
        for tp in self, type:
            if tp.module_name is None:
                assert tp.token.is_reserved and not tp.token.is_name
            else:
                assert tp.token.is_name and not tp.token.is_reserved
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
        if self.is_obj_type and not self.is_array:
            #目标类型为接口或类，非数组，分几种情况检查
            coi = self.get_coi()
            if coi.is_intf_any():
                #任何类型都能赋值给Any接口
                return True
            if type.is_array:
                #数组可以复制给实现了数组内建方法的接口
                return coi.can_convert_from_array(type)
            if type.is_obj_type:
                from_coi = type.get_coi()
                #若self是接口，则检查其他对象或接口到接口的转换
                if coi.can_convert_from(from_coi):
                    return True

        return False

    def can_force_convert_from(self, type):
        if self.can_convert_from(type):
            #能隐式转换，则也能强制转换
            return True

        if type.is_nil:
            #无法隐式转nil，则肯定不能强转
            return False

        if not type.is_literal_int and type.can_convert_from(self):
            #能反向隐式转换，则可以强转
            return True

        #接下来就是正反向都无法转换的情形，这时候还能强转的就只能是number类型之间的了
        if self.is_number_type and type.is_number_type:
            return True

        return False

for _tp in _BASE_TYPE_LIST + ("literal_int", "nil"):
    exec '%s_TYPE = _Type((larc_token.make_fake_token_reserved("%s"), "%s"), None, None)' % (_tp.upper(), _tp, _tp)
    exec "%s_TYPE.set_is_checked()" % _tp.upper()
STR_TYPE = _Type((larc_token.make_fake_token_name("String"), "String"), None, None, module_name = "__builtins")
STR_TYPE.set_is_checked()
VALID_ARRAY_IDX_TYPES = [SCHAR_TYPE, CHAR_TYPE]
for _tp in "short", "int", "long":
    VALID_ARRAY_IDX_TYPES.append(eval("%s_TYPE" % _tp.upper()))
    VALID_ARRAY_IDX_TYPES.append(eval("U%s_TYPE" % _tp.upper()))
PTM_TYPE_LIST = [_tp for _tp in _BASE_TYPE_LIST if _tp != "void"]
del _tp

def parse_type(token_list, dep_module_map, is_ref = False, non_array = False):
    if is_ref:
        assert not non_array
    t = token_list.pop()
    if t.is_reserved and t.value in _BASE_TYPE_LIST:
        return _Type((t, t.value), token_list, dep_module_map, is_ref = is_ref, non_array = non_array)
    if t.is_name:
        if t.value in dep_module_map:
            token_list.pop_sym(".")
            return _Type(token_list.pop_name(), token_list, dep_module_map, module_name = dep_module_map[t.value], is_ref = is_ref,
                         non_array = non_array)
        return _Type((t, t.value), token_list, dep_module_map, is_ref = is_ref, non_array = non_array)
    t.syntax_err()

def _try_parse_type(token_list, curr_module, dep_module_map, gtp_map, used_dep_module_set):
    t = token_list.pop()
    if t.is_reserved and t.value in _BASE_TYPE_LIST:
        tp = _Type((t, t.value), token_list, dep_module_map)
        tp.check(curr_module, gtp_map, used_dep_module_set)
        larc_module.check_new_ginst_during_compile()
        return tp
    if t.is_name:
        name = t.value
        if name in dep_module_map:
            module = larc_module.module_map[dep_module_map[name]]
            token_list.pop_sym(".")
            t, name = token_list.pop_name()
            if module.has_type(name):
                tp = _Type((t, name), token_list, dep_module_map, module_name = module.name)
                tp.check(curr_module, gtp_map, used_dep_module_set)
                larc_module.check_new_ginst_during_compile()
                return tp
        else:
            if gtp_map is not None and name in gtp_map:
                tp = _Type((t, name), token_list, dep_module_map)
                tp.check(curr_module, gtp_map, used_dep_module_set)
                larc_module.check_new_ginst_during_compile()
                return tp
            for module in curr_module, larc_module.builtins_module:
                if module.has_type(name):
                    tp = _Type((t, name), token_list, dep_module_map, module_name = module.name)
                    tp.check(curr_module, gtp_map, used_dep_module_set)
                    larc_module.check_new_ginst_during_compile()
                    return tp
    return None

#若解析类型成功，则统一做check_new_ginst_during_compile，即这个函数只用于编译过程
def try_parse_type(token_list, curr_module, dep_module_map, gtp_map, used_dep_module_set = None):
    revert_idx = token_list.i #用于解析失败时候回滚
    ret = _try_parse_type(token_list, curr_module, dep_module_map, gtp_map, used_dep_module_set)
    if ret is None:
        token_list.revert(revert_idx)
    return ret

def parse_gtp_list(token_list, dep_module_map):
    gtp_list = []
    while True:
        tp = parse_type(token_list, dep_module_map)
        if tp.is_void:
            tp.token.syntax_err("void类型不可作为泛型参数传入")
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
    tp = _Type((larc_token.make_fake_token_name(cls.name), cls.name), None, None, module_name = cls.module.name)
    if cls.is_gcls_inst:
        tp.gtp_list = list(cls.gtp_map.itervalues())
    #这个类型没必要check了，校验一下get_coi正常就直接返回
    tp.set_is_checked()
    assert tp.get_coi() is cls
    return tp

_ARRAY_ELEM_TYPE = object()
_ARRAY_ITER_TYPE = object()
_ARRAY_METHOD_MAP = {"size": (LONG_TYPE, []),
                     "get":  (_ARRAY_ELEM_TYPE, [("idx", LONG_TYPE)]),
                     "set":  (VOID_TYPE, [("idx", LONG_TYPE), ("elem", _ARRAY_ELEM_TYPE)]),
                     "iter": (_ARRAY_ITER_TYPE, [])}

def _gen_array_iter_type(elem_tp):
    t = larc_token.make_fake_token_name("Iter").copy_on_pos(elem_tp.token) #在当前位置弄个假token
    iter_tp = _Type((t, t.value), None, None, module_name = "__builtins")
    iter_tp.gtp_list = [elem_tp] #设置elem_tp为泛型参数
    iter_tp.get_coi() #触发一下，这里也是check里面做的流程
    iter_tp.set_is_checked() #锁住
    return iter_tp

def array_has_method(tp, method):
    assert tp.is_array
    elem_tp = tp.to_elem_type()
    #查找方法
    try:
        ret_type, arg_list = _ARRAY_METHOD_MAP[method.name]
    except KeyError:
        return False
    #检查参数个数
    if len(arg_list) != len(method.arg_map):
        return False
    #检查类型匹配情况
    for tp_want, tp_given in zip([ret_type] + [arg_type for arg_name, arg_type in arg_list], [method.type] + list(method.arg_map.itervalues())):
        if tp_want is _ARRAY_ELEM_TYPE:
            #替换为实际的元素类型进行比较
            tp_want = elem_tp
        if tp_want is _ARRAY_ITER_TYPE:
            #替换为迭代器接口类型
            tp_want = _gen_array_iter_type(elem_tp)
        #需要考虑ref修饰
        if tp_want != tp_given or tp_want.is_ref != tp_given.is_ref:
            return False
    return True

class _ArrayMethod:
    def __init__(self, array_type, name):
        assert array_type.is_array
        elem_type = array_type.to_elem_type()
        ret_type, arg_list = _ARRAY_METHOD_MAP[name]
        if ret_type is _ARRAY_ELEM_TYPE:
            ret_type = elem_type
        if ret_type is _ARRAY_ITER_TYPE:
            ret_type = _gen_array_iter_type(elem_type)

        self.decr_set = set(["public"])
        self.name = name
        self.type = ret_type
        self.arg_map = larc_common.OrderedDict()
        for arg_name, arg_type in arg_list:
            assert arg_name not in self.arg_map
            if arg_type is _ARRAY_ELEM_TYPE:
                arg_type = elem_type
            if arg_type is _ARRAY_ITER_TYPE:
                arg_type = _gen_array_iter_type(elem_type)
            self.arg_map[arg_name] = arg_type

def iter_array_method_list(tp):
    for name in _ARRAY_METHOD_MAP:
        yield _ArrayMethod(tp, name)

def get_array_method(tp, name):
    return _ArrayMethod(tp, name) if name in _ARRAY_METHOD_MAP else None

def get_array_construct_arg_map():
    arg_map = larc_common.OrderedDict()
    arg_map["size"] = LONG_TYPE
    return arg_map

array_type_set = set()
def _reg_array(tp):
    assert tp.is_array
    while tp.is_array and tp not in array_type_set:
        array_type_set.add(tp)
        tp = tp.to_elem_type()
        #注册了一个新的数组，且tp是其元素，用tp构建一个ArrayIter的instance
        t = larc_token.make_fake_token_name("ArrayIter").copy_on_pos(tp.token) #在当前位置弄个假token
        array_iter_tp = _Type((t, t.value), None, None, module_name = "__builtins")
        array_iter_tp.gtp_list = [tp] #设置tp为泛型参数
        array_iter_tp.get_coi() #通过get_coi触发构建ArrayIter instance，由于ArrayIter<E>的实现中存在Iter<E>，后者也会被自动创建
        array_iter_tp.set_is_checked() #锁住
