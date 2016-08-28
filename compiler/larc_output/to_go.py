#coding=utf8

"""
输出为go代码
"""

import os
import shutil
import sys

import larc_module

out_dir = None
runtime_dir = None

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

def _output_main_pkg(main_module_name):
    prog_dir = os.path.join(out_dir, "src", "lar_prog_" + main_module_name)
    os.makedirs(prog_dir)
    with _Code(os.path.join(prog_dir, "lar_prog.%s.go" % main_module_name)) as code:
        code += "package main"
        with code.new_blk("import"):
            code += '"os"'
            code += '"larva_runtime"'
            code += '"lar_mod_%s"' % main_module_name
        with code.new_blk("func main()"):
            code += "os.Exit(larva_runtime.Start_prog(lar_mod_%s.Func_main))"

def _output_module(module):
    print module.name

def _copy_runtime():
    runtime_out_dir = os.path.join(out_dir, "src", "larva_runtime")
    os.makedirs(runtime_out_dir)
    for fn in os.listdir(os.path.join(runtime_dir, "go")):
        shutil.copy(os.path.join(runtime_dir, "go", fn), runtime_out_dir)

def _gen_makefile(main_module_name):
    if sys.platform.lower().startswith("win"):
        f = open(os.path.join(out_dir, "make.bat"), "w")
        print >> f, "set GOPATH=%s" % out_dir
        print >> f, "go build lar_prog_" + main_module_name
    else:
        raise Exception("Not implemented on '%s'" % sys.platform)

def output(main_module_name):
    shutil.rmtree(out_dir, True)
    os.makedirs(os.path.join(out_dir, "src"))
    _output_main_pkg(main_module_name)
    for m in larc_module.module_map.itervalues():
        _output_module(m)
    _copy_runtime()
    _gen_makefile(main_module_name)
