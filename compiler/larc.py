#coding=utf8

"""
编译器主模块
"""

import sys
import getopt
import os
import larc_common
import larc_module
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
    larc_module.module_map["__builtins"] = larc_module.Module(os.path.join(lib_dir, "__builtins.lar"))

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

    #主模块main函数检查
    if ("main", 1) not in main_module.func_map:
        larc_common.exit("主模块[%s]没有func main(argv)" % main_module.name)

    #检查子类的继承是否合法
    '''
    for m in larc_module.module_map.itervalues():
        m.check_sub_class()
    '''

    #正式编译各模块
    for m in larc_module.module_map.itervalues():
        m.compile()

    #暂时写死output流程
    output_lib = larc_output.to_go
    output_lib.main_module_name = main_module.name
    output_lib.out_dir = os.path.join(src_dir, main_module.name)
    output_lib.runtime_dir = os.path.join(os.path.dirname(lib_dir), "runtime")
    output_lib.output()

if __name__ == "__main__":
    main()
