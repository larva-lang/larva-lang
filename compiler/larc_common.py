#coding=utf8

"""
编译器公共定义和一些基础功能
"""

import os, sys, time
from StringIO import StringIO

COMPILING_TIMESTAMP = int(time.time() * 1000)

_ERR_EXIT_CODE = 157 #编译失败时的exit码

_recoverable_detecting    = False      #是否尝试在编译错误时恢复，即是否用子进程试编译
_child_report_fd          = -1         #子进程用来汇报信息的fd
_show_msg_in_child        = False      #子进程出错退出的时候是否照流程显示错误信息
_get_err_exit_report_info = lambda: "" #错误退出时若需要汇报信息，则通过这个注册的回调获取

def enable_recoverable_detecting():
    global _recoverable_detecting
    _recoverable_detecting = True

_verbose_mode = False
_verbose_indent_count = 0

def enable_verbose_mode():
    global _verbose_mode
    _verbose_mode = True

def inc_verbose_indent():
    global _verbose_indent_count
    assert _verbose_indent_count >= 0
    _verbose_indent_count += 1

def dec_verbose_indent():
    global _verbose_indent_count
    _verbose_indent_count -= 1
    assert _verbose_indent_count >= 0

def verbose_log(msg):
    if _verbose_mode:
        print time.strftime("[%H:%M:%S]") + "  " * _verbose_indent_count, msg

#fork一个子进程继续执行编译操作，子进程可通过管道报结果，返回None表示为子进程，返回字符串表示为父进程等待到的子进程的结果
def fork():
    global _child_report_fd
    fd_r, fd_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        #子进程，注册管道fd，重置子进程的信息上报配置后返回None
        os.close(fd_r)
        _child_report_fd = fd_w
        set_show_msg_in_child(False)
        reg_get_err_exit_report_info(lambda: "")
        return None
    #父进程，等待子进程的编译结果
    os.close(fd_w)
    result = ""
    while True:
        r = os.read(fd_r, 1024)
        if r == "":
            break
        result += r
    os.close(fd_r)
    return result

def _report_info(s):
    while s:
        sent_len = os.write(_child_report_fd, s)
        assert 0 < sent_len <= len(s)
        s = s[sent_len :]

def child_exit_succ(s):
    _report_info(s)
    sys.exit(0)

def reg_get_err_exit_report_info(get_err_exit_report_info):
    global _get_err_exit_report_info
    _get_err_exit_report_info = get_err_exit_report_info

def set_show_msg_in_child(show_msg_in_child):
    global _show_msg_in_child
    _show_msg_in_child = show_msg_in_child

def is_child():
    return _child_report_fd >= 0

def _output_ginst_create_chain(f):
    import larc_module
    ginst_create_chain = []
    ginst = larc_module.ginst_being_processed[-1]
    while ginst is not None:
        ginst_create_chain.append(ginst)
        ginst = ginst.ginst_creator
    if not ginst_create_chain:
        return
    print >> f, "泛型实例构造链："
    for ginst in reversed(ginst_create_chain):
        print >> f, ginst.creator_token.pos_desc(), ginst

def exit(msg):
    if _child_report_fd < 0 or _show_msg_in_child:
        print >> sys.stderr, "错误：" + msg
        _output_ginst_create_chain(sys.stderr)
        print >> sys.stderr
    if _child_report_fd >= 0:
        _report_info(_get_err_exit_report_info())
    sys.exit(_ERR_EXIT_CODE)

#warning信息不实时输出，而是记录在set中（顺便去重），在编译之后统一输出
_warning_set = set()
def warning(msg):
    f = StringIO()
    print >> f, "警告：" + msg
    _output_ginst_create_chain(f)
    _warning_set.add(f.getvalue())

def output_all_warning():
    for w in _warning_set:
        print >> sys.stderr, w

'''
由于一开始设计的时候是遇到错误就退出（也是默认模式），为支持监测多个错误但是又不想改动太大，就搞了这么个模式
try_tasks_and_do在_recoverable_detecting模式下会fork后尝试执行每个task（考虑到性能，是批量进行的），仅当尝试的task都成功的时候才真正执行
由于是尝试后再在主进程执行，因此需要保证task不要有进程外的副作用
'''
def try_tasks_and_do(tasks):
    if _recoverable_detecting:
        ok = True
        start_idx = 0
        while start_idx < len(tasks):
            result = fork()
            if result is None:
                #子进程，尝试编译剩下的task，直到遇到一个失败的或全部成功
                set_show_msg_in_child(True)
                i = start_idx
                reg_get_err_exit_report_info(lambda: str(i))
                while i < len(tasks):
                    f, arg, kwarg = tasks[i]
                    f(*arg, **kwarg)
                    i += 1
                child_exit_succ(str(i))
            assert result
            result = int(result)
            if result < len(tasks):
                ok = False #出现错误，断点重试了
            start_idx = int(result) + 1
        if not ok:
            sys.exit(_ERR_EXIT_CODE)

    for f, arg, kwarg in tasks:
        f(*arg, **kwarg)

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

_id = 0
def new_id():
    global _id
    _id += 1
    return _id

def open_src_file(fn):
    f = open(fn)
    f.seek(0, os.SEEK_END)
    if f.tell() > 1024 ** 2:
        exit("源代码文件[%s]过大" % fn)
    f.seek(0, os.SEEK_SET)
    f_cont = f.read()
    try:
        f_cont.decode("utf8")
    except UnicodeDecodeError:
        exit("源代码文件[%s]不是utf8编码" % fn)
    if "\r" in f_cont:
        warning("源代码文件[%s]含有回车符‘\\r’" % fn)
    f.seek(0, os.SEEK_SET)
    return f

#自定义的abs_path，扩展了一些功能
def abs_path(path):
    if path.startswith("~/"):
        #将~/开头的路径转为对应的HOME路径
        home_path = os.getenv("HOME")
        assert home_path
        path = home_path + path[1 :]
    return os.path.abspath(path)
