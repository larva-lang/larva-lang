#coding=utf8

"""
类型相关
"""

import copy

import larc_common
import larc_module
import larc_token

_BASE_TYPE_LIST = ("void", "bool", "schar", "char", "short", "ushort", "int", "uint", "long", "ulong", "float", "double")

class _Type:
    def __init__(self, (name_token, name), token_list, dep_module_map, module_name = None, non_array = False, is_ref = False,
                 is_closure = False):
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
        self.is_closure = is_closure
        self._set_is_XXX()
        self.is_checked = False
        self.is_freezed = False

    def _set_is_XXX(self):
        assert self.array_dim_count >= 0
        self.is_array = self.array_dim_count != 0
        self.is_nil = self.token.is_reserved("nil")
        self.is_obj_type = self.is_nil or self.is_array or self.token.is_name
        self.is_coi_type = self.token.is_name and not self.is_array #非数组的coi，意即在check之后可以get_coi
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
        self.is_nil_ref = self.name == "nil_ref"

    #转为字符串，ignore_builtins_module_prefix表示是否忽略掉“__builtins.”模块前缀
    def to_str(self, ignore_builtins_module_prefix):
        s = self.name
        if self.module_name is not None:
            if ignore_builtins_module_prefix and self.module_name == "__builtins":
                pass
            else:
                s = self.module_name + "." + s
        if self.gtp_list:
            s += "<%s>" % ", ".join([tp.to_str(ignore_builtins_module_prefix = ignore_builtins_module_prefix) for tp in self.gtp_list])
        s += "[]" * self.array_dim_count
        return s

    __str__ = __repr__ = lambda self: self.to_str(ignore_builtins_module_prefix = False)

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
        assert array_dim_count > 0
        tp = _Type((self.token, self.name), None, None, module_name = self.module_name)
        tp.gtp_list = self.gtp_list
        tp.array_dim_count = self.array_dim_count + array_dim_count
        tp.is_closure = self.is_closure
        tp._set_is_XXX()
        tp._set_is_checked()
        return tp

    def to_elem_type(self):
        assert self.is_array
        tp = _Type((self.token, self.name), None, None, module_name = self.module_name)
        tp.gtp_list = self.gtp_list
        tp.array_dim_count = self.array_dim_count - 1
        tp.is_closure = self.is_closure
        tp._set_is_XXX()
        tp._set_is_checked()
        return tp

    def get_coi(self):
        assert self.token.is_name and self.module_name is not None and not self.is_array
        m = larc_module.module_map[self.module_name]
        coi = m.get_coi(self)
        assert coi is not None
        return coi

    #check完成或无需check的时候
    def _set_is_checked(self):
        self.is_checked = True
        self.is_freezed = True #锁住type，禁止更改
        if self.is_array:
            _reg_array(self) #注册数组信息

    #忽略泛型类型，对其他部分做check，用于泛型类和函数中类型的预check，和实际check流程类似，主要目的是完善module信息并检查权限
    def check_ignore_gtp(self, curr_module, gtp_name_set):
        if self.token.is_reserved:
            #忽略基础类型（及其数组类型）
            assert not self.gtp_list
            return
        assert self.token.is_name
        #先check泛型参数
        for tp in self.gtp_list:
            tp.check_ignore_gtp(curr_module, gtp_name_set)
        #构建find_path并查找类型
        if self.module_name is None:
            if self.name in gtp_name_set:
                if self.gtp_list:
                    self.token.syntax_err("泛型参数不可作为泛型类型使用")
                #忽略泛型类型
                return
            find_path = curr_module, larc_module.builtins_module
        else:
            find_path = larc_module.module_map[self.module_name],
        #check并标准化coi类型，不影响是否为数组
        for m in find_path:
            if m.has_coi(self.name):
                coi = m.get_coi_original(self.name)
                if m is not curr_module:
                    #非当前模块，检查权限
                    if "public" not in coi.decr_set:
                        if self.module_name is None:
                            #如果走到这里，说明是引用了一个内建模块的私有成员，不应该报没有权限，因此continue，会跳到for的else报找不到类型
                            continue
                        self.token.syntax_err("无法使用类型'%s'：没有权限" % self)
                if coi.gtp_name_list:
                    if self.gtp_list:
                        if len(coi.gtp_name_list) != len(self.gtp_list):
                            self.token.syntax_err("泛型参数数量错误：需要%d个，传入了%d个" % (len(coi.gtp_name_list), len(self.gtp_list)))
                    else:
                        self.token.syntax_err("泛型类型'%s'无法单独使用" % coi)
                else:
                    if self.gtp_list:
                        self.token.syntax_err("'%s'不是泛型类型" % coi)
                self.module_name = m.name
                break
        else:
            self.token.syntax_err("找不到类型'%s'" % self)

    def check(self, curr_module, gtp_map = None, used_dep_module_set = None):
        if not self.is_checked:
            self._check(curr_module, gtp_map, used_dep_module_set)
            self._set_is_checked()

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
                self.is_closure = tp.is_closure
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
                if m is not curr_module:
                    #非当前模块，检查权限
                    if "public" not in coi.decr_set:
                        if self.module_name is None:
                            #continue的理由同上，参考check_ignore_gtp中相关代码的注释
                            continue
                        self.token.syntax_err("无法使用类型'%s'：没有权限" % self)
                self.module_name = m.name #check的同时也将不带模块的类型标准化
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
            assert tp.is_checked and tp.is_freezed

        #nil和literal_int类型仅作为字面量的类型，转换的目标类型不可能是它们
        assert not (self.is_nil or self.is_literal_int)

        if self == type:
            #完全一样
            return True
        if self.is_obj_type and type.is_nil:
            #允许nil直接赋值给任何对象
            return True
        if self == GO_ANY_INTF_TYPE or type == GO_ANY_INTF_TYPE:
            #特殊处理：禁止larva类型和GoAny的互转
            return false
        if self.is_coi_type:
            #目标类型为接口或类，非数组，分几种情况检查
            coi = self.get_coi()
            if coi.is_intf_with_no_method():
                #void之外的任何类型都能赋值给无任何方法的接口
                return not type.is_void
            if type.is_array:
                #数组可以赋值给实现了数组内建方法的接口
                return coi.can_convert_from(gen_arr_type(type).get_coi())
            if type.is_obj_type:
                from_coi = type.get_coi()
                #若self是接口，则检查其他对象或接口到接口的转换
                return coi.can_convert_from(from_coi)

        #其余情况都不行
        return False

    def can_force_convert_from(self, type):
        if self.can_convert_from(type):
            #能隐式转换，则也能强制转换
            return True

        #number类型之间可以强转
        if self.is_number_type and type.is_number_type:
            return True

        #其余情况不能强转
        return False

#生成默认类型对象，其中literal_int和nil类型内部使用，String类型虽然是class，但由于代码中有str literal，也需预先生成
for _tp in _BASE_TYPE_LIST + ("literal_int", "nil"):
    exec '%s_TYPE = _Type((larc_token.make_fake_token_reserved("%s"), "%s"), None, None)' % (_tp.upper(), _tp, _tp)
    exec "%s_TYPE._set_is_checked()" % _tp.upper()
ANY_INTF_TYPE = _Type((larc_token.make_fake_token_name("Any"), "Any"), None, None, module_name = "__builtins")
ANY_INTF_TYPE._set_is_checked()
STR_TYPE = _Type((larc_token.make_fake_token_name("String"), "String"), None, None, module_name = "__builtins")
STR_TYPE._set_is_checked()
NIL_REF_TYPE = _Type((larc_token.make_fake_token_name("nil_ref"), "nil_ref"), None, None)
NIL_REF_TYPE._set_is_checked()

#所有整数类型都可以作为数组下标
VALID_ARRAY_IDX_TYPES = [SCHAR_TYPE, CHAR_TYPE]
for _tp in "short", "int", "long":
    VALID_ARRAY_IDX_TYPES.append(eval("%s_TYPE" % _tp.upper()))
    VALID_ARRAY_IDX_TYPES.append(eval("U%s_TYPE" % _tp.upper()))
del _tp

def is_type(tp):
    return isinstance(tp, _Type)

def parse_type(token_list, dep_module_map, is_ref = False, non_array = False):
    if is_ref:
        assert not non_array #ref只出现在函数参数，所以必然是要完整parse的
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
                    if (module is not curr_module and module is larc_module.builtins_module and
                        "public" not in module.get_coi_original(name).decr_set):
                        #内建模块的私有类型原则上是不对外的，当做不存在
                        return None
                    tp = _Type((t, name), token_list, dep_module_map, module_name = module.name)
                    tp.check(curr_module, gtp_map, used_dep_module_set)
                    larc_module.check_new_ginst_during_compile()
                    return tp
    return None

#若解析类型成功，则统一做check_new_ginst_during_compile，即这个函数只用于编译过程
def try_parse_type(token_list, curr_module, dep_module_map, gtp_map, var_map_stk, used_dep_module_set = None):
    t = token_list.peek()
    if t.is_name and not larc_module.decide_if_name_maybe_type_by_lcgb(t.value, var_map_stk, gtp_map, dep_module_map, curr_module):
        return None

    revert_idx = token_list.i #用于解析失败时候回滚
    ret = _try_parse_type(token_list, curr_module, dep_module_map, gtp_map, used_dep_module_set)
    if ret is None:
        token_list.revert(revert_idx)
    return ret

def parse_gtp_list(token_list, dep_module_map):
    gtp_list = []
    while True:
        t = token_list.peek()
        if t.is_sym and t.value in (">", ">>"):
            token_list.pop_sym()
            break

        tp = parse_type(token_list, dep_module_map)
        if tp.is_void:
            tp.token.syntax_err("void类型不可作为泛型参数传入")
        gtp_list.append(tp)

        t = token_list.peek()
        if not (t.is_sym and t.value in (">", ">>", ",")):
            t.syntax_err("需要','或'>'")
        if t.value == ",":
            token_list.pop_sym()

    if t.is_sym(">>"):
        token_list.split_shr_sym()
    if not gtp_list:
        t.syntax_err("泛型参数列表不能为空")
    return gtp_list

#通用小函数 ----------------------------------------------------------

#构建一个类型为cls的type，主要用于this表达式
def gen_type_from_cls(cls):
    tp = _Type((larc_token.make_fake_token_name(cls.name), cls.name), None, None, module_name = cls.module.name)
    if cls.is_gcls_inst:
        tp.gtp_list = list(cls.gtp_map.itervalues())
    #这个类型没必要check了，校验一下get_coi正常就直接返回
    tp._set_is_checked()
    assert tp.get_coi() is cls
    return tp

#构建一个闭包的类型，用于闭包表达式
def gen_closure_type(closure):
    tp = _Type((larc_token.make_fake_token_name(closure.name), closure.name), None, None, module_name = closure.module.name, is_closure = True)
    #这个类型没必要check了，校验一下get_coi正常就直接返回
    tp._set_is_checked()
    assert tp.get_coi() is closure
    return tp

#构建一个_Iter<E>的type，方便foreach语法检查
def gen_internal_iter_type(elem_tp, t):
    t = larc_token.make_fake_token_name("_Iter").copy_on_pos(t) #在当前位置弄个假token
    iter_tp = _Type((t, t.value), None, None, module_name = "__builtins")
    iter_tp.gtp_list = [elem_tp] #设置elem_tp为泛型参数
    iter_tp.get_coi() #触发一下，这里也是check里面做的流程
    iter_tp._set_is_checked() #锁住
    larc_module.check_new_ginst_during_compile()
    return iter_tp

#数组类型相关 ------------------------------------------------------

def gen_arr_type(tp):
    assert tp.is_array
    return _gen_arr_type(tp.to_elem_type())

def _gen_arr_type(elem_tp):
    t = larc_token.make_fake_token_name("Arr").copy_on_pos(elem_tp.token) #在当前位置弄个假token
    arr_tp = _Type((t, t.value), None, None, module_name = "__array")
    arr_tp.gtp_list = [elem_tp] #设置elem_tp为泛型参数
    arr_tp.get_coi() #触发一下，这里也是check里面做的流程
    arr_tp._set_is_checked() #锁住
    #这里暂时不需要check_new_ginst_during_compile，因为调用这个函数的时候要么arr已经存在了，要么是在其他type的check流程中
    return arr_tp

def iter_array_method_list(tp):
    arr_coi = gen_arr_type(tp).get_coi()
    for method in arr_coi.method_map.itervalues():
        if "public" not in method.decr_set:
            continue
        yield method

def get_array_method(tp, name):
    arr_coi = gen_arr_type(tp).get_coi()
    if name in arr_coi.method_map:
        method = arr_coi.method_map[name]
        if "public" in method.decr_set:
            return method
    return None

array_type_set = set()
def _reg_array(tp):
    assert tp.is_array
    while tp.is_array and tp not in array_type_set:
        array_type_set.add(tp)
        tp = tp.to_elem_type()
        #注册了一个新的数组，且tp是其元素，用tp构建一个数组泛型类Arr的instance
        _gen_arr_type(tp)

#gtp类型推导 ----------------------------------------

def infer_gtp(expr_list_start_token, gtp_name_list, arg_type_list, type_list, ref_tag_list):
    assert len(set(gtp_name_list)) == len(gtp_name_list)
    assert len(arg_type_list) == len(type_list) == len(ref_tag_list)

    class _GtpInferenceResult:
        def __init__(self, gtp_name):
            self.gtp_name = gtp_name

            self.tp = None
            self.is_freezed = False

        def update(self, tp):
            if tp.is_nil or tp.is_literal_int:
                expr_list_start_token.syntax_err("参数#%d无法进行推导：实参类型不可为无类型nil或整数字面量，请指定类型" % (arg_idx + 1))
            if self.tp is None:
                #初次推导
                assert not self.is_freezed
                self.tp = tp
                return
            if self.is_freezed:
                #已经freeze，之前推导的结果必须兼容tp
                if not self.tp.can_convert_from(tp):
                    expr_list_start_token.syntax_err(
                        "无法确定泛型参数'%s'的类型，存在不兼容的推导结果：'%s', '%s'……" % (self.gtp_name, self.tp, tp))
                return
            #之前update过但是未定，从二者之间选择兼容的那个
            if self.tp.can_convert_from(tp):
                return
            if tp.can_convert_from(self.tp):
                self.tp = tp
                return
            expr_list_start_token.syntax_err("无法确定泛型参数'%s'的类型，存在多种不同的推导结果：'%s', '%s'……" % (self.gtp_name, self.tp, tp))

        def freeze(self, tp):
            assert not tp.is_nil and not tp.is_literal_int
            if self.tp is None:
                #初次推导
                self.tp = tp
            elif self.is_freezed:
                #已经freeze，检查推导结果是否一致
                if tp != self.tp:
                    expr_list_start_token.syntax_err(
                        "无法确定泛型参数'%s'的类型，存在多种不同的推导结果：'%s', '%s'……" % (self.gtp_name, self.tp, tp))
            else:
                #已经有推导过但是还未freeze，则tp必须兼容之前的结果
                if tp.can_convert_from(self.tp):
                    self.tp = tp
                else:
                    expr_list_start_token.syntax_err(
                        "无法确定泛型参数'%s'的类型，存在不兼容的推导结果：'%s', '%s'……" % (self.gtp_name, self.tp, tp))
            #将类型确定下来
            assert self.tp is not None
            self.is_freezed = True

        def finish(self):
            if self.tp is None:
                expr_list_start_token.syntax_err("无法确定泛型参数'%s'的类型" % self.gtp_name)
            if self.tp.is_void:
                expr_list_start_token.syntax_err("泛型参数'%s'的类型推导为void" % self.gtp_name)
            return self.tp

    #构建gtp_infer_map，value为推导结果对象
    gtp_infer_map = larc_common.OrderedDict()
    for gtp_name in gtp_name_list:
        gtp_infer_map[gtp_name] = _GtpInferenceResult(gtp_name)

    #通过精确匹配类型来推导arg_type中的泛型参数
    def match_type(arg_type, tp):
        if arg_type.is_array:
            #数组类型匹配
            if tp.array_dim_count < arg_type.array_dim_count:
                expr_list_start_token.syntax_err("参数#%d类型匹配失败：数组维度不匹配，'%s'->'%s'" % (arg_idx + 1, tp, arg_type))
            while arg_type.is_array:
                #arg_type是unchecked，因此不能直接to_elem_type，手动解决
                arg_type = copy.deepcopy(arg_type)
                arg_type.array_dim_count -= 1
                arg_type.is_array = arg_type.array_dim_count != 0
                tp = tp.to_elem_type()
            match_type(arg_type, tp)
            return
        if arg_type.module_name is None:
            if arg_type.token.is_name:
                assert not arg_type.gtp_list and arg_type.name in gtp_infer_map
                assert not tp.is_nil and not tp.is_literal_int
                #parse到了最终泛型参数，可以确定类型了
                gtp_infer_map[arg_type.name].freeze(tp)
                return
            assert arg_type.token.is_reserved
            #基础类型，直接忽略，tp是否匹配的检查让后面去做
            return
        assert arg_type.token.is_name
        coi = larc_module.module_map[arg_type.module_name].get_coi_original(arg_type.name)
        assert len(coi.gtp_name_list) == len(arg_type.gtp_list)
        if not coi.gtp_name_list:
            #非泛型的类或接口，直接忽略
            return
        assert not arg_type.is_array
        if (arg_type.module_name, arg_type.name) != (tp.module_name, tp.name) or tp.is_array or len(arg_type.gtp_list) != len(tp.gtp_list):
            expr_list_start_token.syntax_err("参数#%d类型匹配失败：'%s'->'%s'" % (arg_idx + 1, tp, arg_type))
        for arg_type_gtp, tp_gtp in zip(arg_type.gtp_list, tp.gtp_list):
            match_type(arg_type_gtp, tp_gtp)

    #遍历各匹配对，依次进行推导算法
    for arg_idx, (arg_type, tp, is_ref) in enumerate(zip(arg_type_list, type_list, ref_tag_list)):
        #先检查ref修饰是否一致
        if arg_type.is_ref and not is_ref:
            expr_list_start_token.syntax_err("参数#%d需要ref修饰" % (arg_idx + 1))
        if not arg_type.is_ref and is_ref:
            expr_list_start_token.syntax_err("参数#%d存在无效的ref修饰" % (arg_idx + 1))
        if arg_type.is_ref:
            assert is_ref
            if tp.is_nil_ref:
                expr_list_start_token.syntax_err("参数#%d无法进行推导：实参类型不可为空ref，请指定ref的左值实参" % (arg_idx + 1))
            #带ref修饰的类型需要精确匹配
            match_type(arg_type, tp)
            continue
        assert not is_ref and not tp.is_nil_ref
        #不带ref修饰的类型匹配，需要分几种情况
        if not arg_type.is_array:
            if arg_type.token.is_name:
                if arg_type.module_name is None:
                    #参数类型经历了check_ignore_gtp依然是裸name，且不是数组，则必然是单独的泛型类型
                    assert not arg_type.gtp_list and arg_type.name in gtp_infer_map
                    #用update接口，类型之后还可能被进一步推导为其他兼容类型
                    gtp_infer_map[arg_type.name].update(tp)
                    continue
                coi = larc_module.module_map[arg_type.module_name].get_coi_original(arg_type.name)
                if coi.is_intf and coi.gtp_name_list:
                    #泛型接口，展开双方的接口进行精确匹配
                    def match_method_type(method, tp_method):
                        if tp_method is None:
                            expr_list_start_token.syntax_err(
                                "参数#%d类型匹配失败，接口方法'%s'找不到：'%s'->'%s'" % (arg_idx + 1, method.name, tp, arg_type))
                        if (list(method.decr_set) + list(tp_method.decr_set)).count("public") not in (0, 2):
                            #权限签名不同
                            expr_list_start_token.syntax_err(
                                "参数#%d类型匹配失败，接口方法'%s'权限签名不同：'%s'->'%s'" % (arg_idx + 1, method.name, tp, arg_type))
                        if "public" not in method.decr_set and method.module is not tp_method.module:
                            #权限私有且两个coi不在同一模块，这个接口无权访问
                            expr_list_start_token.syntax_err(
                                "参数#%d类型匹配失败，对接口方法'%s'无访问权限：'%s'->'%s'" % (arg_idx + 1, method.name, tp, arg_type))
                        if len(method.arg_map) != len(tp_method.arg_map):
                            expr_list_start_token.syntax_err(
                                "参数#%d类型匹配失败，接口方法'%s'参数数量不匹配：'%s'->'%s'" % (arg_idx + 1, method.name, tp, arg_type))
                        match_type(method.type, tp_method.type)
                        for method_arg_type, tp_method_arg_type in zip(method.arg_map.itervalues(), tp_method.arg_map.itervalues()):
                            match_type(method_arg_type, tp_method_arg_type)
                    if tp.is_array:
                        for method in coi.method_map.itervalues():
                            match_method_type(method, get_array_method(tp, method.name))
                        continue
                    if tp.module_name is not None:
                        assert tp.token.is_name
                        tp_coi = tp.get_coi()
                        for method in coi.method_map.itervalues():
                            match_method_type(method, tp_coi.method_map[method.name] if method.name in tp_coi.method_map else None)
                        continue
        #其余情况，必须精确匹配
        match_type(arg_type, tp)

    #遍历gtp_map，确保所有类型都推导完毕并生成gtp_list
    gtp_list = [result.finish() for result in gtp_infer_map.itervalues()]
    return gtp_list
