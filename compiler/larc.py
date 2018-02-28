#coding=utf8

"""
编译器主模块
"""

import sys
import getopt
import os
import larc_common
import larc_token
import larc_module
import larc_type
import larc_output

def _show_usage_and_exit():
    larc_common.exit("使用方法：%s [--run] 主模块名" % sys.argv[0])

def _find_module_file(module_dir_list, module_name):
    #按模块查找路径逐个目录找
    for module_dir in module_dir_list:
        module_pkg_path = os.path.join(module_dir, module_name)
        if os.path.isdir(module_pkg_path):
            return module_pkg_path
    larc_common.exit("找不到模块：%s" % module_name)

def main():
    #解析命令行参数
    opt_list, args = getopt.getopt(sys.argv[1 :], "", ["run"])
    opt_map = dict(opt_list)

    if len(args) != 1:
        _show_usage_and_exit()

    #通用目录
    compiler_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_dir = os.path.join(os.path.dirname(compiler_dir), "lib")

    #预处理builtins等模块
    for name in "__builtins",:
        larc_module.module_map[name] = larc_module.Module(_find_module_file([lib_dir], name))
    larc_module.builtins_module = larc_module.module_map["__builtins"]

    #先预处理主模块
    main_file_path_name = os.path.abspath(args[0])
    main_module_name = os.path.basename(main_file_path_name)
    if not (larc_token.is_valid_name(main_module_name) and main_module_name != "__builtins"):
        larc_common.exit("非法的主模块名[%s]" % main_module_name)
    if not os.path.exists(main_file_path_name):
        larc_common.exit("找不到主模块目录[%s]" % main_file_path_name)
    if not os.path.isdir(main_file_path_name):
        larc_common.exit("主模块[%s]不是一个目录" % main_file_path_name)
    main_module = larc_module.Module(main_file_path_name)
    larc_module.module_map[main_module.name] = main_module

    #模块查找路径的目录列表
    src_dir = os.path.dirname(main_file_path_name)
    #路径顺序规则为：主模块所在目录->参数指定路径（多个则按顺序）->larva的lib目录
    module_dir_list = [src_dir, lib_dir]

    #预处理所有涉及到的模块
    compiling_set = main_module.get_dep_module_set() #需要预处理的模块名集合
    while compiling_set:
        new_compiling_set = set()
        for module_name in compiling_set:
            if module_name in larc_module.module_map:
                #已预处理过
                continue
            module_file_path_name = _find_module_file(module_dir_list, module_name)
            larc_module.module_map[module_name] = m = larc_module.Module(module_file_path_name)
            new_compiling_set |= m.get_dep_module_set()
        compiling_set = new_compiling_set
    assert larc_module.module_map.value_at(0) is larc_module.builtins_module

    #模块元素级别的check_type，先对非泛型元素做check，然后对泛型实例采用类似深度优先的方式，直到没有ginst生成
    for m in larc_module.module_map.itervalues():
        m.check_type_for_non_ginst()
    larc_module.check_type_for_ginst()

    #扩展通过usemethod继承的方法
    for m in larc_module.module_map.itervalues():
        m.expand_usemethod()

    #主模块main函数检查
    main_module.check_main_func()

    #编译各模块代码，先编译非泛型元素，然后反复编译到没有ginst生成，类似上面的check type过程
    for m in larc_module.module_map.itervalues():
        m.compile_non_ginst()
    while True:
        for m in larc_module.module_map.itervalues():
            if m.compile_ginst():
                #有一个模块刚编译了新的ginst，有可能生成新ginst，重启编译流程
                break
        else:
            #所有ginst都编译完毕
            break

    #输出目标代码
    larc_output.main_module_name = main_module.name
    larc_output.out_dir = os.path.join(src_dir, main_module.name) + ".lar_out"
    larc_output.runtime_dir = os.path.join(os.path.dirname(lib_dir), "runtime")
    larc_output.output("--run" in opt_map)

if __name__ == "__main__":
    main()
