#coding=utf8

"""
链接larva程序
"""

import larc_common
import larc_module
import larc_type_inference

class Prog:
    def __init__(self, main_module_name, module_map):
        self.main_module_name = main_module_name
        self.module_map = module_map
        self._check_main_func()
        self._link()

    def _check_main_func(self):
        main_module = self.module_map[self.main_module_name]
        if ("main", 0) not in main_module.export_func_set:
            larc_common.exit("链接错误：主模块'%s'缺少main函数" %
                             self.main_module_name)

    def _link(self):
        for module in self.module_map.itervalues():
            if isinstance(module, larc_module.ExternModule):
                #暂定外部模块的类不声明extends
                continue
            module.link_class_extends(self.module_map)
        for module in self.module_map.itervalues():
            if isinstance(module, larc_module.ExternModule):
                #外部模块无需链接
                continue
            module.link(self.module_map)
        for module in self.module_map.itervalues():
            if isinstance(module, larc_module.ExternModule):
                #外部模块无需类型推导
                continue
            larc_type_inference.Device(module).work()
