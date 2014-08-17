#coding=utf8

"""
内置部分初始化
注：builtin只有类和函数，没有变量，对外统一是可调用接口
"""

#初始化所有内置接口

builtin_if_set = set() #函数接口表

def _init_builtin_if():
    #各种内部类型的接口
    for name, arg_count_list in {"int" : (1, 2),
                                 "range" : (1, 2, 3),
                                 "len" : (1,)}.iteritems():
        for arg_count in arg_count_list:
            builtin_if_set.add((name, arg_count))
_init_builtin_if()

builtin_if_name_set = set([name for name, arg_count in builtin_if_set])

"""
class _Module:
    def __init__(self, name):
        self.name = name
        self.global_var_map = {}
        self.func_map = {}
        self.func_name_set = set()
        self.is_extern = True

    def link(self, module_name):
        #内置模块无需链接
        pass

_module_time = _Module("time")
_module_time.func_map[("time", 0)] = None
_module_time.func_name_set.add("time")

module_map = {"time" : _module_time}
"""
