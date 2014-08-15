#coding=utf8

"""
编译器主模块
"""

import sys
import getopt
import os
import larc_common
import larc_builtin
import larc_module
import larc_prog
import larc_output

def _show_usage_and_exit():
    larc_common.exit("使用方法：%s 主模块.lar" % sys.argv[0])

def main():
    #解析命令行参数
    opt_list, args = getopt.getopt(sys.argv[1 :], "", [])

    if len(args) != 1:
        _show_usage_and_exit()

    module_map = {} #已编译的模块，模块名映射模块Module对象
    module_map.update(larc_builtin.module_map)

    src_dir, main_file = os.path.split(args[0])
    src_dir = os.path.abspath(src_dir)
    if not main_file.endswith(".lar"):
        larc_common.exit("非法的主模块名[%s]" % main_file)
    main_module_name = main_file[: -4]

    if main_module_name in module_map:
        larc_common.exit("错误：主模块名和内置模块同名")

    #从主模块开始，编译所有涉及到的模块
    compiling_set = set([main_module_name]) #需要编译的模块名集合
    while compiling_set:
        new_compiling_set = set()
        for module_name in compiling_set:
            if module_name in module_map:
                #已编译过
                continue
            module_map[module_name] = m = (
                larc_module.Module(src_dir, module_name))
            new_compiling_set |= m.dep_module_set
        compiling_set = new_compiling_set

    prog = larc_prog.Prog(main_module_name, module_map)

    output_lib = larc_output.to_java
    out_dir = src_dir

    lib_path = (
        os.path.join(
            os.path.split(
                os.path.split(os.path.abspath(sys.argv[0]))[0])[0], "lib"))

    output_lib.output(out_dir, prog, lib_path)

if __name__ == "__main__":
    main()
