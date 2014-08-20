#coding=utf8

"""
编译器主模块
"""

import sys
import getopt
import os
from collections import OrderedDict
import larc_common
import larc_builtin
import larc_module
import larc_prog
import larc_output

def _show_usage_and_exit():
    larc_common.exit("使用方法：%s 主模块.lar" % sys.argv[0])

def _find_module_file(module_dir_list, module_name):
    #按目录查找，每个目录下优先级：lar、lar_ext
    for module_dir in module_dir_list:
        for ext in (".lar", ".lar_ext"):
            module_file_path_name = os.path.join(module_dir, module_name) + ext
            if os.path.exists(module_file_path_name):
                return module_file_path_name
    larc_common.exit("找不到模块：%s" % module_name)

def main():
    #解析命令行参数
    opt_list, args = getopt.getopt(sys.argv[1 :], "", [])

    if len(args) != 1:
        _show_usage_and_exit()

    module_map = OrderedDict() #已编译的模块，模块名映射模块Module对象

    #先编译主模块
    main_file_path_name = os.path.abspath(args[0])
    if main_file_path_name.endswith(".lar"):
        main_module = larc_module.Module(main_file_path_name)
    elif main_file_path_name.endswith(".lar_ext"):
        main_module = larc_module.ExternModule(main_file_path_name)
    else:
        larc_common.exit("非法的主模块文件名[%s]" % main_file_path_name)
    module_map[main_module.name] = main_module

    #模块查找的目录列表
    src_dir = os.path.dirname(main_file_path_name)
    compiler_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_dir = os.path.join(os.path.dirname(compiler_dir), "lib")
    module_dir_list = [src_dir, lib_dir]

    #编译所有涉及到的模块
    compiling_set = main_module.dep_module_set #需要编译的模块名集合
    compiling_set |= set(["sys"]) #因为要接收argv，sys模块必须有
    while compiling_set:
        new_compiling_set = set()
        for module_name in compiling_set:
            if module_name in module_map:
                #已编译过
                continue
            module_file_path_name = (
                _find_module_file(module_dir_list, module_name))
            if module_file_path_name.endswith(".lar"):
                module_map[module_name] = m = (
                    larc_module.Module(module_file_path_name))
            elif module_file_path_name.endswith(".lar_ext"):
                module_map[module_name] = m = (
                    larc_module.ExternModule(module_file_path_name))
            else:
                raise Exception("unreachable")
            new_compiling_set |= m.dep_module_set
        compiling_set = new_compiling_set

    prog = larc_prog.Prog(main_module.name, module_map)

    output_lib = larc_output.to_java
    out_dir = src_dir

    output_lib.output(out_dir, prog, lib_dir)

if __name__ == "__main__":
    main()
