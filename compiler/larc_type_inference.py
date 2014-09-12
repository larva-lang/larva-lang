#coding=utf8

"""
larva程序的类型推导优化
"""

"""
使用简化版的类型推导算法：
1 推导仅针对int类型
2 优化对象：
  模块非导出全局变量、函数，函数和方法中与导出接口无关的局部变量
3 由于是动态类型语言，且考虑到外部模块的实现不可控，
  规定：导出变量、函数，以及所有属性、方法相关变量均为object
4 容器（list、dict、tuple）的元素统一为object
"""

import larc_common
import larc_module
