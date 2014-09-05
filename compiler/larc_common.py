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

#由于py2.7才有collections.OrderedDict，自实现一个
class OrderedDict:
    def __init__(self):
        self.l = []
        self.d = {}

    def __iter__(self):
        return iter(self.l)

    def __len__(self):
        return len(self.l)

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        if k not in self.d:
            self.l.append(k)
        self.d[k] = v

    def itervalues(self):
        for k in self.l:
            yield self.d[k]

    def iteritems(self):
        for k in self.l:
            yield k, self.d[k]

class OrderedSet:
    def __init__(self):
        self.d = OrderedDict()

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def add(self, k):
        self.d[k] = None
