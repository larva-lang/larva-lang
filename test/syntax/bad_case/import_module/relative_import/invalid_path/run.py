import os, sys

curr_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(curr_dir + "/..")
dir_suffix = "/test/syntax/bad_case/relative_import/invalid_path"
assert curr_dir.endswith(dir_suffix)
larva_dir = curr_dir[: -len(dir_suffix)]
os.system("python %s/compiler/larc.py --module_path=. invalid_path" % larva_dir)
