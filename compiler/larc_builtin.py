#coding=utf8

"""
内置部分初始化
注：builtin只有类和函数，没有变量，对外统一是可调用接口
"""

#初始化所有内置接口

builtin_if_set = set() #函数接口表

def _init_builtin_if():
    #各种内部类型的接口
    for name, arg_count_list in {"str" : (1,),
                                 "tuple" : (1,),
                                 "list" : (1,),
                                 "set" : (0, 1),
                                 "range" : (1, 2, 3),
                                 "bitmap" : (1,),
                                 "file" : (1,),
                                 "sorted" : (1,),
                                 "len" : (1,),
                                 "sum" : (1,),
                                 "pow" : (2,),
                                 "max" : (1,),
                                 "min" : (1,),
                                 "bin" : (1,)}.iteritems():
        for arg_count in arg_count_list:
            builtin_if_set.add((name, arg_count))
_init_builtin_if()

builtin_if_name_set = set([name for name, arg_count in builtin_if_set])
