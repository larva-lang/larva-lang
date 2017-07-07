#coding=utf8

"""
编译器主模块
"""

import sys
import getopt
import os
import larc_common
import larc_module
import larc_type
import larc_output

def _show_usage_and_exit():
    larc_common.exit("使用方法：%s 主模块.lar" % sys.argv[0])

def _find_module_file(module_dir_list, module_name):
    #按目录查找
    for module_dir in module_dir_list:
        module_file_path_name = os.path.join(module_dir, module_name) + ".lar"
        if os.path.exists(module_file_path_name):
            return module_file_path_name
    larc_common.exit("找不到模块：%s" % module_name)

def main():
    #解析命令行参数
    opt_list, args = getopt.getopt(sys.argv[1 :], "", [])

    if len(args) != 1:
        _show_usage_and_exit()

    #通用目录
    compiler_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_dir = os.path.join(os.path.dirname(compiler_dir), "lib")

    #预处理builtins等模块
    for name in "__builtins", "concurrent":
        larc_module.module_map[name] = larc_module.Module(os.path.join(lib_dir, name + ".lar"))
    larc_module.builtins_module = larc_module.module_map["__builtins"]

    #先预处理主模块
    main_file_path_name = os.path.abspath(args[0])
    if not main_file_path_name.endswith(".lar"):
        larc_common.exit("非法的主模块文件名[%s]" % main_file_path_name)
    if not os.path.exists(main_file_path_name):
        larc_common.exit("找不到主模块文件[%s]" % main_file_path_name)
    main_module = larc_module.Module(main_file_path_name)
    larc_module.module_map[main_module.name] = main_module

    #模块查找的目录列表
    src_dir = os.path.dirname(main_file_path_name)
    module_dir_list = [src_dir, lib_dir]

    #预处理所有涉及到的模块
    compiling_set = main_module.dep_module_set #需要预处理的模块名集合
    while compiling_set:
        new_compiling_set = set()
        for module_name in compiling_set:
            if module_name in larc_module.module_map:
                #已预处理过
                continue
            module_file_path_name = _find_module_file(module_dir_list, module_name)
            larc_module.module_map[module_name] = m = larc_module.Module(module_file_path_name)
            new_compiling_set |= m.dep_module_set
        compiling_set = new_compiling_set

    raise "todo"

    #先扩展嵌套typedef，然后单独对typedef的type进行check
    larc_module.builtins_module.expand_typedef()
    for m in larc_module.module_map.itervalues():
        if m is not larc_module.builtins_module:
            m.expand_typedef()
    larc_module.builtins_module.expand_typedef()
    for m in larc_module.module_map.itervalues():
        if m is not larc_module.builtins_module:
            m.check_type_for_typedef()

    #统一check_type
    larc_module.builtins_module.check_type()
    for m in larc_module.module_map.itervalues():
        if m is not larc_module.builtins_module:
            m.check_type()

    #主模块main函数检查
    if "main" not in main_module.func_map:
        larc_common.exit("主模块[%s]没有main函数" % main_module.name)
    main_func = main_module.func_map["main"]
    if main_func.type != larc_type.INT_TYPE:
        larc_common.exit("主模块[%s]的main函数返回类型必须为int" % main_module.name)
    if len(main_func.arg_map) != 1:
        larc_common.exit("主模块[%s]的main函数只能有一个类型为'String[]'的参数" % main_module.name)
    tp = main_func.arg_map.itervalues().next()
    if tp.array_dim_count != 1 or tp.is_ref or tp.to_elem_type() != larc_type.STR_TYPE:
        larc_common.exit("主模块[%s]的main函数的参数类型必须为'String[]'" % main_module.name)
    if "public" not in main_func.decr_set:
        larc_common.exit("主模块[%s]的main函数必须是public的" % main_module.name)

    #检查子类的继承是否合法
    larc_module.builtins_module.check_sub_class()
    for m in larc_module.module_map.itervalues():
        if m is not larc_module.builtins_module:
            m.check_sub_class()

    #todo：其他一些模块元素的检查和进一步预处理

    #正式编译各模块
    larc_module.builtins_module.compile()
    for m in larc_module.module_map.itervalues():
        if m is not larc_module.builtins_module:
            m.compile()

    #暂时写死output流程
    output_lib = larc_output.to_go
    output_lib.main_module_name = main_module.name
    output_lib.out_dir = os.path.join(src_dir, main_module.name)
    output_lib.runtime_dir = os.path.join(os.path.dirname(lib_dir), "runtime")
    output_lib.output()

if __name__ == "__main__":
    main()
