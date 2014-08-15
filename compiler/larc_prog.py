#coding=utf8

"""
链接larva程序
"""

import larc_common

class Prog:
    def __init__(self, main_module_name, module_map):
        self.main_module_name = main_module_name
        self.module_map = module_map
        self._check_main_func()
        self._link()

    def _check_main_func(self):
        main_module = self.module_map[self.main_module_name]
        if ("main", 0) not in main_module.func_map:
            larc_common.exit("链接错误：主模块'%s'缺少main函数" %
                             self.main_module_name)

    def _link(self):
        for module in self.module_map.itervalues():
            module.link(self.module_map)
