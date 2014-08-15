#coding=utf8

"""
内置部分初始化
注：内置模块只有类和函数，没有变量，对外统一是可调用接口
"""

#P.S.内置接口和模块实际可以用extern模块的形式，暂时没空做extern功能，先硬编码

#-------------------------------------------------------------------------------
#初始化所有内置函数

builtin_if_set = set() #函数接口表

#range
for arg_count in (1, 2, 3):
    builtin_if_set.add(("range", arg_count))

builtin_if_name_set = set([name for name, arg_count in builtin_if_set])

#-------------------------------------------------------------------------------
#初始化所有内置模块

#这个对象接口和larc_module.Module一致，只是global_var_map和func_map的value为空
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
