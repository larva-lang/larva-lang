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

def main():
    #定位目录
    THIS_SCRIPT_NAME_SUFFIX = "/compiler/larc.py"
    this_script_name = os.path.realpath(sys.argv[0])
    assert this_script_name.endswith(THIS_SCRIPT_NAME_SUFFIX)
    larva_dir = this_script_name[: -len(THIS_SCRIPT_NAME_SUFFIX)]

    def _show_usage_and_exit():
        print >> sys.stderr, """
Larva编译器

使用方法

    python larc.py OPTIONS MAIN_MODULE_SPEC [ARGS]

各参数说明

    OPTIONS: [-u] [-o OUT_BIN] [--run]

{u}

{o}

        --run
            编译后立即执行

        -o和--run至少要指定一个，若都指定，则先输出为可执行程序然后执行

{MAIN_MODULE_SPEC}

    ARGS

        运行模块时的命令行参数，指定--run选项的时候有效，如未指定--run，则不能指定ARGS
""".format(**eval(open(larva_dir + "/compiler/help").read()))
        sys.exit(1)

    #解析命令行参数
    try:
        opt_list, args = getopt.getopt(sys.argv[1 :], "uo:m:", ["run"])
    except getopt.GetoptError:
        _show_usage_and_exit()
    opt_map = dict(opt_list)
    larc_module.need_update_git = "-u" in opt_map
    out_bin = opt_map.get("-o")
    if out_bin is not None:
        if os.path.exists(out_bin) and not os.path.isfile(out_bin):
            larc_common.exit("[%s]不是一个常规文件" % out_bin)
    need_run = "--run" in opt_map
    if out_bin is None and not need_run: #至少要指定一种行为
        _show_usage_and_exit()

    main_module_name = opt_map.get("-m")
    if main_module_name is None:
        if len(args) < 1:
            _show_usage_and_exit()
        main_module_path = larc_common.abs_path(args[0])
        if not os.path.isdir(main_module_path):
            larc_common.exit("无效的主模块路径[%s]：不存在或不是目录" % main_module_path)
        args_for_run = args[1 :]
    else:
        main_module_path = None
        args_for_run = args[:]
    if not need_run and args_for_run:
        _show_usage_and_exit()

    #获取标准库、用户库和临时输出的目录，并做检查
    compiler_dir = larva_dir + "/compiler"
    std_lib_dir = larva_dir + "/lib"
    assert os.path.isdir(std_lib_dir)
    usr_lib_dir_original = os.getenv("LARVA_USR_LIB_DIR", "~/larva")
    usr_lib_dir = larc_common.abs_path(usr_lib_dir_original)
    if not os.path.isdir(usr_lib_dir):
        larc_common.exit("无效的用户库路径：[%s]不存在或不是一个目录" % usr_lib_dir_original)
    if usr_lib_dir in ("/tmp", "/usr", "/var", "/dev", "/root", "/etc", "/home", "/sbin"):
        larc_common.exit("请不要用[%s]作为用户库路径" % usr_lib_dir)
    tmp_out_dir_original = os.getenv("LARVA_TMP_OUT_DIR", "/tmp/.larva_tmp_out")
    tmp_out_dir = larc_common.abs_path(tmp_out_dir_original)
    if not os.path.exists(tmp_out_dir):
        os.makedirs(tmp_out_dir)
    if not os.path.isdir(tmp_out_dir):
        larc_common.exit("无效的临时输出路径：[%s]不存在或不是一个目录" % tmp_out_dir_original)

    if std_lib_dir.startswith(usr_lib_dir) or usr_lib_dir.startswith(std_lib_dir):
        larc_common.exit("环境检查失败：标准库和用户库路径存在包含关系：[%s] & [%s]" % (std_lib_dir, usr_lib_dir))

    #larva对标准库第一级模块有一些命名要求，虽然内建模块不会被一般用户修改，但为了稳妥还是检查下，免得开发者不小心弄了个非法名字
    first_level_std_module_set = set()
    for fn in os.listdir(std_lib_dir):
        if os.path.isdir(std_lib_dir + "/" + fn):
            if not larc_token.is_valid_name(fn):
                larc_common.exit("环境检查失败：标准库模块[%s]名字不是合法的标识符" % fn)
            #第一级模块名不能有除了私有模块前导之外的下划线
            if fn.count("_") != (2 if fn.startswith("__") else 0):
                larc_common.exit("环境检查失败：标准库模块[%s]名字含有非法的下划线" % fn)
            first_level_std_module_set.add(fn)

    std_lib_internal_module_list = "__builtins", "__internal", "__array", "__runtime"

    #检查一下几个特殊的标准库模块，必须有
    for mn in std_lib_internal_module_list:
        if mn not in first_level_std_module_set:
            larc_common.exit("环境检查失败：标准库模块[%s]缺失" % mn)

    #对于用户库中的模块，如果不是git地址，则也要满足合法标识符条件，且不能和标准库的冲突
    for fn in os.listdir(usr_lib_dir):
        if os.path.isdir(usr_lib_dir + "/" + fn):
            if "." not in fn:
                if not larc_token.is_valid_name(fn):
                    larc_common.exit("环境检查失败：用户库模块[%s]名字不是合法的标识符" % fn)
                if fn in first_level_std_module_set:
                    larc_common.exit("环境检查失败：用户库模块[%s]和标准库同名模块冲突" % fn)

    #校验通过，设置到module模块中
    larc_module.std_lib_dir = std_lib_dir
    larc_module.usr_lib_dir = usr_lib_dir

    def fix_git_module_name(mn):
        parts = mn.split("/")
        if len(parts) > 3 and "." in parts[0]:
            git_repo = "/".join(parts[: 3])
            mn_of_repo = "/".join(parts[3 :])
            if larc_module.is_valid_git_repo(git_repo):
                mn = '"%s"/%s' % (git_repo, mn_of_repo)
        return mn

    if main_module_path is not None:
        #处理main_module_path，提取main_module_name
        if main_module_path.startswith(std_lib_dir + "/"):
            main_module_name = main_module_path[len(std_lib_dir) + 1 :]
            if main_module_name in std_lib_internal_module_list:
                larc_common.exit("不能以'%s'作为主模块" % main_module_name)
        elif main_module_path.startswith(usr_lib_dir + "/"):
            main_module_name = fix_git_module_name(main_module_path[len(usr_lib_dir) + 1 :])
        else:
            larc_common.exit("主模块路径不存在于标准库或用户库[%s]" % main_module_path)
    else:
        #如果module_name是不带引号的git路径，则像上面一样修正一下
        main_module_name = fix_git_module_name(main_module_name)

    #检查
    if not larc_module.is_valid_module_name(main_module_name):
        larc_common.exit("非法的主模块名'%s'" % main_module_name)
    git_repo, mnpl = larc_module.split_module_name(main_module_name)
    if any([mnp.startswith("__") for mnp in mnpl]):
        larc_common.exit("不能使用私有模块作为主模块'%s'" % main_module_name)

    #预处理内建模块族
    larc_module.builtins_module = larc_module.module_map["__builtins"] = larc_module.Module("__builtins")
    assert larc_module.builtins_module.get_dep_module_set() == set(["__internal"]) #内建模块只能而且必须导入__internal模块
    internal_module = larc_module.module_map["__internal"] = larc_module.Module("__internal")
    assert not internal_module.get_dep_module_set() #__internal模块不能导入其他模块
    larc_module.array_module = larc_module.module_map["__array"] = larc_module.Module("__array")
    larc_module.module_map["__runtime"] = larc_module.Module("__runtime")

    #预处理主模块
    larc_module.module_map[main_module_name] = main_module = larc_module.Module(main_module_name)
    module_tmp_out_dir = tmp_out_dir + "/" + main_module_name.replace('"', "")

    #预处理所有涉及到的模块
    compiling_set = (larc_module.builtins_module.get_dep_module_set() | larc_module.array_module.get_dep_module_set() |
                     main_module.get_dep_module_set()) #需要预处理的模块名集合
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

    #检查循环import
    for m in larc_module.module_map.itervalues():
        m.check_cycle_import()

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
    larc_output.out_dir = module_tmp_out_dir
    larc_output.output(out_bin, need_run, args_for_run)

if __name__ == "__main__":
    main()
