#coding=gbk

"""
类型相关
"""

_BASE_TYPE_LIST = ("void", "bool", "byte", "ubyte", "char", "short", "ushort", "int", "uint", "long", "ulong", "float", "double")

#基础类型的可转换表
_BASE_TYPE_CONVERT_TBL = {"byte" : set(["short", "int", "long", "float", "double"]),
                          "ubyte" : set(["short", "ushort", "int", "uint", "long", "ulong", "float", "double"]),
                          "char" : set(["short", "ushort", "int", "uint", "long", "ulong", "float", "double"]),
                          "short" : set(["int", "long", "float", "double"]),
                          "ushort" : set(["int", "uint", "long", "ulong", "float", "double"]),
                          "int" : set(["long", "float", "double"]),
                          "uint" : set(["long", "ulong", "float", "double"]),
                          "long" : set(["float", "double"]),
                          "ulong" : set(["float", "double"]),
                          "float" : set(["double"]),
                          "literal_byte" : set(["byte", "ubyte", "char", "short", "ushort", "int", "uint", "long", "ulong", "float", "double"]),
                          "literal_ubyte" : set(["ubyte", "char", "short", "ushort", "int", "uint", "long", "ulong", "float", "double"]),
                          "literal_short" : set(["short", "ushort", "int", "uint", "long", "ulong", "float", "double"]),
                          "literal_ushort" : set(["ushort", "int", "uint", "long", "ulong", "float", "double"]),
                          "literal_int" : set(["int", "uint", "long", "ulong", "float", "double"])}
