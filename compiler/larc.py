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
    larc_common.exit("使用方法：\n"
                     "\t%s --module_path=MODULE_PATH_LIST MAIN_MODULE\n"
                     "\t%s --module_path=MODULE_PATH_LIST --run MAIN_MODULE ARGS" % (sys.argv[0], sys.argv[0]))

def _find_module_file(module_path_list, module_name):
    #按模块查找路径逐个目录找
    assert module_path_list
    if module_name == "__builtins":
        mpl = [module_path_list[0]] #__builtins比较特殊，只从lib_dir找
    else:
        mpl = module_path_list
    for module_dir in mpl:
        module_path = os.path.join(module_dir, *module_name.split("/"))
        if os.path.isdir(module_path):
            return module_path
    t = larc_module.dep_module_token_map.get(module_name)
    if t is None:
        larc_common.exit("找不到模块：%s" % module_name)
    else:
        t.syntax_err("找不到模块：%s" % module_name)

def main():
    #解析命令行参数
    try:
        opt_list, args = getopt.getopt(sys.argv[1 :], "", ["module_path=", "run"])
    except getopt.GetoptError:
        _show_usage_and_exit()
    opt_map = dict(opt_list)
    if "--module_path" not in opt_map:
        _show_usage_and_exit()
    module_path_list = [os.path.abspath(p) for p in opt_map["--module_path"].split(":") if p]
    need_run = "--run" in opt_map

    if len(args) < 1:
        _show_usage_and_exit()
    main_module_name = args[0]
    args_for_run = args[1 :]
    if not need_run and args_for_run:
        _show_usage_and_exit()

    #通用目录
    compiler_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_dir = os.path.join(os.path.dirname(compiler_dir), "lib")
    module_path_list = [lib_dir] + module_path_list
    larc_module.find_module_file = lambda mn: _find_module_file(module_path_list, mn)

    #larva对标准库第一级模块有一些命名要求，虽然内建模块不会被一般用户修改，但为了稳妥还是检查下，免得开发者不小心弄了个非法名字
    for fn in os.listdir(lib_dir):
        #略过内建模块
        if fn == "__builtins":
            continue
        #第一级模块名不能有下划线
        if os.path.isdir(os.path.join(lib_dir, fn)) and "_" in fn:
            larc_common.exit("环境检查失败：内建模块[%s]名字含有下划线" % fn)

    #预处理builtins模块
    larc_module.builtins_module = larc_module.module_map["__builtins"] = larc_module.Module("__builtins")

    #预处理主模块
    if not (all([larc_token.is_valid_name(p) for p in main_module_name.split("/")]) and main_module_name != "__builtins"):
        larc_common.exit("非法的主模块名[%s]" % main_module_name)
    larc_module.module_map[main_module_name] = main_module = larc_module.Module(main_module_name)

    #预处理所有涉及到的模块
    compiling_set = larc_module.builtins_module.get_dep_module_set() | main_module.get_dep_module_set() #需要预处理的模块名集合
    while compiling_set:
        new_compiling_set = set()
        for module_name in compiling_set:
            if module_name in larc_module.module_map:
                #已预处理过
                continue
            larc_module.module_map[module_name] = m = larc_module.Module(module_name)
            new_compiling_set |= m.get_dep_module_set()
        compiling_set = new_compiling_set
    assert larc_module.module_map.value_at(0) is larc_module.builtins_module

    #模块元素级别的check_type，先对非泛型元素做check，然后对泛型实例采用类似深度优先的方式，直到没有ginst生成
    for m in larc_module.module_map.itervalues():
        m.check_type_for_non_ginst()
    larc_module.check_type_for_ginst()

    #扩展接口中通过usemethod继承的方法
    for m in larc_module.module_map.itervalues():
        m.expand_intf_usemethod()

    #扩展类中通过usemethod继承的方法
    for m in larc_module.module_map.itervalues():
        m.expand_cls_usemethod()

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
    larc_output.out_dir = main_module.dir + ".lar_out"
    larc_output.runtime_dir = os.path.join(os.path.dirname(lib_dir), "runtime")
    larc_output.output(need_run, args_for_run)

if __name__ == "__main__":
    main()
