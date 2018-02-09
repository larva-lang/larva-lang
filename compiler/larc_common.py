#coding=utf8

"""
编译器公共定义
"""

import sys

def _output_ginst_create_chain():
    import larc_module
    ginst_create_chain = []
    ginst = larc_module.ginst_being_processed[-1]
    while ginst is not None:
        ginst_create_chain.append(ginst)
        ginst = ginst.ginst_creator
    if not ginst_create_chain:
        return
    print "泛型实例构造链："
    for ginst in reversed(ginst_create_chain):
        print ginst.creator_token.pos_desc(), ginst

def exit(msg):
    print >> sys.stderr, "Error:", msg.decode("utf8")
    _output_ginst_create_chain()
    print
    sys.exit(1)

def warning(msg):
    print >> sys.stderr, "Warning", msg.decode("utf8")
    _output_ginst_create_chain()
    print

class OrderedDict:
    def __init__(self):
        self.l = []
        self.d = {}

    def __iter__(self):
        return iter(self.l)

    def __len__(self):
        return len(self.l)

    def __nonzero__(self):
        return len(self) > 0

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

    def key_at(self, idx):
        return self.l[idx]

    def value_at(self, idx):
        return self.d[self.l[idx]]

    def copy(self):
        od = OrderedDict()
        for name in self:
            od[name] = self[name]
        return od

class OrderedSet:
    def __init__(self):
        self.d = OrderedDict()

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __nonzero__(self):
        return len(self) > 0

    def add(self, k):
        self.d[k] = None

    def key_at(self, idx):
        return self.d.key_at(idx)

    def value_at(self, idx):
        return self.d.value_at(idx)

    def copy(self):
        os = OrderedSet()
        os.d = self.d.copy()
        return os
