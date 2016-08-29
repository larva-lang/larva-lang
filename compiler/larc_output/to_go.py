#coding=utf8

"""
输出为go代码
"""

import os
import shutil
import sys

import larc_module

main_module_name = None
out_dir = None
runtime_dir = None
out_prog_dir = None

class _Code:
    class _CodeBlk:
        def __init__(self, code, end_line):
            self.code = code
            self.end_line = end_line

        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                return
            assert len(self.code.indent) >= 4
            self.code.indent = self.code.indent[: -4]
            self.code += self.end_line

    def __init__(self, file_path_name):
        self.file_path_name = file_path_name
        self.indent = ""
        self.line_list = []

    def __iadd__(self, line):
        self.line_list.append(self.indent + line)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return
        f = open(self.file_path_name, "w")
        for line in self.line_list:
            print >> f, line

    def new_blk(self, title, start_with_blank_line = True):
        if start_with_blank_line:
            self += ""
        end_line = "}"
        if title == "import":
            self += title + " ("
            end_line = ")"
        elif title:
            self += title + " {"
        else:
            self += "{"
        self.indent += " " * 4
        return self._CodeBlk(self, end_line)

def _output_main_pkg():
    main_lar_mod_name = "lar_mod_" + main_module_name
    with _Code(os.path.join(out_prog_dir, "lar_prog.%s.go" % main_module_name)) as code:
        code += "package main"
        with code.new_blk("import"):
            code += '"os"'
            code += '"larva_booter"'
            code += '"%s"' % main_lar_mod_name
        with code.new_blk("func main()"):
            code += "os.Exit(larva_booter.Start_prog(%s.Func_main))" % main_lar_mod_name

def _output_module(module):
    has_native_item = module.has_native_item()
    mod_dir = os.path.join(out_dir, "src", "lar_mod_" + module.name)
    os.makedirs(mod_dir)
    with _Code(os.path.join(mod_dir, "lar_mod.%s.go" % module.name)) as code:
        code += "package lar_mod_" + module.name
    if has_native_item:
        shutil.copy(os.path.join(module.dir, "go", "lar_ext_mod.%s.go" % module.name), mod_dir)

def _copy_runtime():
    out_runtime_dir = os.path.join(out_dir, "src")
    for pkg_dir in os.listdir(os.path.join(runtime_dir)):
        dst_dir = os.path.join(out_dir, "src", pkg_dir)
        pkg_dir = os.path.join(runtime_dir, pkg_dir)
        if os.path.isdir(pkg_dir):
            shutil.copytree(pkg_dir, dst_dir)

def _gen_makefile():
    if sys.platform.lower().startswith("win"):
        f = open(os.path.join(out_dir, "make.bat"), "w")
        print >> f, "@set GOPATH=%s" % out_dir
        print >> f, "go build -o %s.exe src/lar_prog_%s/lar_prog.%s.go" % (main_module_name, main_module_name, main_module_name)
        print >> f, "@if %ERRORLEVEL% == 0 goto success"
        print >> f, "@pause"
        print >> f, ":success"
    else:
        raise Exception("Not implemented on '%s'" % sys.platform)

def output():
    global runtime_dir, out_prog_dir
    runtime_dir = os.path.join(runtime_dir, "go")
    out_prog_dir = os.path.join(out_dir, "src", "lar_prog_" + main_module_name)

    shutil.rmtree(out_dir, True)
    os.makedirs(out_prog_dir)

    _output_main_pkg()
    for m in larc_module.module_map.itervalues():
        _output_module(m)
    _copy_runtime()
    _gen_makefile()
