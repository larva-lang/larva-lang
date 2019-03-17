import os, sys

curr_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(curr_dir + "/..")
dir_suffix = "/test/syntax/bad_case/relative_import/path_to_other_module"
assert curr_dir.endswith(dir_suffix)
larva_dir = curr_dir[: -len(dir_suffix)]
os.system("python %s/compiler/larc.py --module_path=. path_to_other_module" % larva_dir)
