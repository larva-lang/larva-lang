#coding=utf8

"""
编译器公共定义
"""

import sys

def exit(msg):
    print >> sys.stderr, msg.decode("utf8")
    sys.exit(1)

def warning(msg):
    print >> sys.stderr, msg.decode("utf8")
