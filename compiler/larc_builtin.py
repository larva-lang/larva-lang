#coding=utf8

"""
内置部分初始化
注：builtin只有类和函数，没有变量，对外统一是可调用接口
"""

import larc_common

#初始化所有内置接口

builtin_if_set = set() #接口表
builtin_if_name_set = set()
builtin_class_map = {}
builtin_exc_cls_name_set = set()

class _ExcClass:
    def __init__(self, name):
        self.name = name
        if name == "Exception":
            self.base_class_module = None
            self.base_class_name = None
            self.base_class = None
        else:
            self.base_class_module = "*"
            self.base_class_name = "Exception"
            self.base_class = builtin_class_map["Exception"]
        self.method_map = larc_common.OrderedDict()
        self.method_map[("__init__", 0)] = None
        self.method_map[("__init__", 1)] = None
        self.attr_set = larc_common.OrderedSet()

def _init_builtin_if():
    #内置异常
    for name in ("Exception", "IndexError", "ValueError", "AssertionError"):
        for arg_count in (0, 1):
            builtin_if_set.add((name, arg_count))
        builtin_if_name_set.add(name)
        builtin_class_map[name] = _ExcClass(name)
        builtin_exc_cls_name_set.add(name)

    #其他内置接口
    for name, arg_count_list in {"long" : (1, 2),
                                 "float" : (1,),
                                 "str" : (1,),
                                 "tuple" : (1,),
                                 "list" : (1,),
                                 "set" : (0, 1),
                                 "range" : (1, 2, 3),
                                 "bitmap" : (1,),
                                 "file" : (1,),
                                 "sorted" : (1, 2, 3),
                                 "len" : (1,),
                                 "sum" : (1,),
                                 "pow" : (2,),
                                 "max" : (1,),
                                 "min" : (1,),
                                 "bin" : (1,)}.iteritems():
        for arg_count in arg_count_list:
            builtin_if_set.add((name, arg_count))
            builtin_if_name_set.add(name)
_init_builtin_if()
