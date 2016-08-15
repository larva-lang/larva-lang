#coding=utf8

"""
编译larva语句
"""

import larc_expr

class _Stmt:
    def __init__(self, type, **kw_arg):
        self.type = type
        for k, v in kw_arg.iteritems():
            setattr(self, k, v)

    def link(self, curr_module, module_map, local_var_set, curr_class = None):
        if self.type in ("break", "continue"):
            return
        if self.type == "print":
            for expr in self.expr_list:
                expr.link(curr_module, module_map, local_var_set, curr_class)
            return
        if self.type == "return":
            if self.expr is not None:
                self.expr.link(curr_module, module_map, local_var_set,
                               curr_class)
        if self.type in ("expr", "for", "while", "=", "%=", "^=", "&=", "*=",
                         "-=", "+=", "|=", "/=", "<<=", ">>=", ">>>="):
            self.expr.link(curr_module, module_map, local_var_set, curr_class)
        if self.type in ("for", "=", "%=", "^=", "&=", "*=", "-=", "+=",
                         "|=", "/=", "<<=", ">>=", ">>>="):
            self.lvalue.link(curr_module, module_map, local_var_set,
                             curr_class)
        if self.type in ("for", "while"):
            for stmt in self.stmt_list:
                stmt.link(curr_module, module_map, local_var_set, curr_class)
        if self.type == "if":
            for expr, stmt_list in self.if_list:
                expr.link(curr_module, module_map, local_var_set, curr_class)
                for stmt in stmt_list:
                    stmt.link(curr_module, module_map, local_var_set,
                              curr_class)
            if self.else_stmt_list is not None:
                for stmt in self.else_stmt_list:
                    stmt.link(curr_module, module_map, local_var_set,
                              curr_class)
        if self.type == "try":
            for stmt in self.try_stmt_list:
                stmt.link(curr_module, module_map, local_var_set, curr_class)
            for i in xrange(len(self.except_list)):
                except_token, exc_cls_module, exc_cls_name, stmt_list = (
                    self.except_list[i])
                if exc_cls_name is not None:
                    #检查是否为异常类
                    if exc_cls_module is None:
                        #当前模块的类或内置类
                        if exc_cls_name in curr_module.class_map:
                            cls = curr_module.class_map[exc_cls_name]
                        elif exc_cls_name in larc_builtin.builtin_class_map:
                            #内置类
                            cls = larc_builtin.builtin_class_map[exc_cls_name]
                            self.except_list[i] = (
                                except_token, "*", exc_cls_name, stmt_list)
                        else:
                            except_token.syntax_err(
                                "找不到类'%s'" % exc_cls_name)
                    else:
                        #外部模块类
                        cls = (
                            module_map[exc_cls_module].class_map[exc_cls_name])
                    while cls.base_class is not None:
                        cls = cls.base_class
                    if cls is not larc_builtin.builtin_class_map["Exception"]:
                        except_token.syntax_err("except非Exception类")
                for stmt in stmt_list:
                    stmt.link(curr_module, module_map, local_var_set,
                              curr_class)
            if self.finally_stmt_list is not None:
                for stmt in self.finally_stmt_list:
                    stmt.link(curr_module, module_map, local_var_set,
                              curr_class)
        if self.type == "assert":
            self.expr.link(curr_module, module_map, local_var_set, curr_class)
            if self.exc_obj_expr is not None:
                self.exc_obj_expr.link(curr_module, module_map, local_var_set,
                                       curr_class)
        if self.type == "raise":
            self.expr.link(curr_module, module_map, local_var_set, curr_class)

def _parse_global_var_declare(token_list, global_var_set):
    while True:
        var_name = token_list.pop_name()
        global_var_set.add(var_name)
        if not token_list or token_list.peek().is_indent:
            #语句结束
            return
        token_list.pop_sym(",")

def _parse_print(token_list):
    #解析print语句，返回表达式列表和是否换行
    if not token_list or token_list.peek().is_indent:
        #空print
        return [], True
    expr_list = []
    while True:
        #状态：解析表达式
        expr_list.append(larc_expr.parse_expr(token_list, True))
        #状态：等待语句结束或","
        if not token_list or token_list.peek().is_indent:
            #语句结束
            return expr_list, True
        #语句未结束
        token_list.pop_sym(",")
        if not token_list or token_list.peek().is_indent:
            #在逗号后结束，不换行
            return expr_list, False

def _parse_for(token_list, curr_indent_count, loop_deep):
    t = token_list.peek()
    """说明：
       原本是for后面整个作为一个* in *表达式解析，但是对于unpack：
       for i, j in a, b:
       就会失败，因为逗号比in优先级低
       对i,j和a,b加括号的话又麻烦，这里in应该作为一个关键字而非运算符
       因此特殊处理，解析左值的时候，碰到in停止"""
    lvalue = larc_expr.parse_expr(token_list, end_at_in = True)
    if not lvalue.is_lvalue:
        t.syntax_err("for语句中'in'左边非左值表达式")
    t = token_list.pop()
    if not t.is_in:
        t.syntax_err("需要'in'")
    expr = larc_expr.parse_expr(token_list)
    token_list.pop_sym(":")
    stmt_list, global_var_set = (
        parse_stmt_list(token_list, curr_indent_count, loop_deep + 1))
    return lvalue, expr, stmt_list, global_var_set

def _parse_return(token_list):
    if not token_list or token_list.peek().is_indent:
        #空return
        return None
    expr = larc_expr.parse_expr(token_list)
    if token_list:
        token_list.peek_indent()
    return expr

def _parse_while(token_list, curr_indent_count, loop_deep):
    expr = larc_expr.parse_expr(token_list, end_at_comma = True)
    token_list.pop_sym(":")
    stmt_list, global_var_set = (
        parse_stmt_list(token_list, curr_indent_count, loop_deep + 1))
    return expr, stmt_list, global_var_set

def _parse_if(token_list, curr_indent_count, loop_deep):
    if_list = []
    if_global_var_set = set()
    while True:
        expr = larc_expr.parse_expr(token_list, end_at_comma = True)
        token_list.pop_sym(":")
        stmt_list, global_var_set = (
            parse_stmt_list(token_list, curr_indent_count, loop_deep))
        if_list.append((expr, stmt_list))
        if_global_var_set |= global_var_set
        if not token_list or token_list.peek_indent() < curr_indent_count:
            #if语句结束
            return if_list, None, if_global_var_set
        token_list.pop_indent(curr_indent_count)
        t = token_list.pop()
        if t.is_elif:
            continue
        if t.is_else:
            break
        token_list.revert()
        token_list.revert()
        return if_list, None, if_global_var_set
    #解析else部分
    token_list.pop_sym(":")
    else_stmt_list, global_var_set = (
        parse_stmt_list(token_list, curr_indent_count, loop_deep))
    if_global_var_set |= global_var_set
    return if_list, else_stmt_list, if_global_var_set

def _parse_try(token_list, curr_indent_count, loop_deep):
    try_global_var_set = set()
    #解析try部分
    token_list.pop_sym(":")
    try_stmt_list, global_var_set = (
        parse_stmt_list(token_list, curr_indent_count, loop_deep))
    try_global_var_set |= global_var_set
    #except或finally
    token_list.pop_indent(curr_indent_count)
    t = token_list.peek()
    if not (t.is_except or t.is_finally):
        t.syntax_err("需要'except'或'finally'")
    token_list.revert()

    #解析except部分
    except_list = []
    while True:
        if not token_list or token_list.peek_indent() < curr_indent_count:
            #try语句结束，且没有finally
            return try_stmt_list, except_list, None, try_global_var_set
        token_list.pop_indent(curr_indent_count)
        t = token_list.pop()
        if not t.is_except:
            #except结束
            if t.is_finally:
                #继续解析finally
                break
            #没有finally
            token_list.revert()
            token_list.revert()
            return try_stmt_list, except_list, None, try_global_var_set
        except_token = t
        t = token_list.pop()
        if t.is_sym(":"):
            exc_cls_module = exc_cls_name = None
        elif t.is_name:
            exc_cls_module = None
            exc_cls_name = t.value
            t = token_list.peek()
            if t.is_sym("."):
                #MODULE.CLASS形式
                token_list.pop_sym(".")
                exc_cls_module = exc_cls_name
                exc_cls_name = token_list.pop_name()
            token_list.pop_sym(":")
        else:
            t.syntax_err("需要异常类名或':'")
        stmt_list, global_var_set = (
            parse_stmt_list(token_list, curr_indent_count, loop_deep))
        except_list.append((except_token, exc_cls_module, exc_cls_name,
                            stmt_list))
        try_global_var_set |= global_var_set

    #解析finally部分
    token_list.pop_sym(":")
    finally_stmt_list, global_var_set= (
        parse_stmt_list(token_list, curr_indent_count, loop_deep))
    try_global_var_set |= global_var_set
    return try_stmt_list, except_list, finally_stmt_list, try_global_var_set

def _parse_assert(token_list):
    expr = larc_expr.parse_expr(token_list, True)
    if token_list.peek().is_indent:
        #没有附加异常对象
        return expr, None
    token_list.pop_sym(",")
    exc_obj_expr = larc_expr.parse_expr(token_list, True)
    return expr, exc_obj_expr

def _parse_raise(token_list):
    return larc_expr.parse_expr(token_list)

def parse_stmt_list(token_list, upper_indent_count, loop_deep):
    """解析语句列表，返回列表和global变量名集合
       larva代码中，global变量名可在任意位置声明，不过最好在开头，免得歧义"""

    #获取当前块的缩进
    curr_indent_count = token_list.peek_indent()
    if curr_indent_count <= upper_indent_count:
        token_list.peek().indent_err()

    #开始解析
    stmt_list = []
    global_var_set = set()
    while token_list:
        indent_count = token_list.peek_indent()
        if indent_count < curr_indent_count:
            #当前块结束，返回
            break

        #解析语句
        token_list.pop_indent(curr_indent_count)
        t = token_list.pop()
        if t.is_pass:
            continue
        if t.is_global:
            _parse_global_var_declare(token_list, global_var_set)
            continue
        if t.is_print:
            expr_list, print_new_line = _parse_print(token_list)
            stmt_list.append(_Stmt("print", expr_list = expr_list,
                                   print_new_line = print_new_line))
            continue
        if t.is_for:
            lvalue, expr, for_stmt_list, for_global_var_set = (
                _parse_for(token_list, curr_indent_count, loop_deep))
            stmt_list.append(_Stmt("for", lvalue = lvalue, expr = expr,
                                   stmt_list = for_stmt_list))
            global_var_set |= for_global_var_set
            continue
        if t.is_continue or t.is_break:
            if loop_deep == 0:
                t.syntax_err("循环外的'%s'" % t.value)
            stmt_list.append(_Stmt(t.value))
            continue
        if t.is_return:
            expr = _parse_return(token_list)
            stmt_list.append(_Stmt("return", expr = expr))
            continue
        if t.is_while:
            expr, while_stmt_list, while_global_var_set = (
                _parse_while(token_list, curr_indent_count, loop_deep))
            stmt_list.append(_Stmt("while", expr = expr,
                                   stmt_list = while_stmt_list))
            global_var_set |= while_global_var_set
            continue
        if t.is_if:
            if_list, else_stmt_list, if_global_var_set = (
                _parse_if(token_list, curr_indent_count, loop_deep))
            stmt_list.append(_Stmt("if", if_list = if_list,
                                   else_stmt_list = else_stmt_list))
            global_var_set |= if_global_var_set
            continue
        if t.is_import:
            t.syntax_err("import必须出现在代码文件开头")
        if t.is_elif:
            t.syntax_err("未匹配的elif")
        if t.is_else:
            t.syntax_err("未匹配的else")
        if t.is_func:
            t.syntax_err("不允许函数嵌套定义")
        if t.is_try:
            (try_stmt_list, except_list, finally_stmt_list,
             try_global_var_set) = (
                 _parse_try(token_list, curr_indent_count, loop_deep))
            stmt_list.append(_Stmt("try", try_stmt_list = try_stmt_list,
                                   except_list = except_list,
                                   finally_stmt_list = finally_stmt_list))
            global_var_set |= try_global_var_set
            continue
        if t.is_except:
            t.syntax_err("未匹配的except")
        if t.is_finally:
            t.syntax_err("未匹配的finally")
        if t.is_assert:
            expr, exc_obj_expr = _parse_assert(token_list)
            stmt_list.append(
                _Stmt("assert", expr = expr, exc_obj_expr = exc_obj_expr))
            continue
        if t.is_raise:
            expr = _parse_raise(token_list)
            stmt_list.append(_Stmt("raise", expr = expr))
            continue

        #剩下的就是表达式和赋值了
        token_list.revert()
        expr = larc_expr.parse_expr(token_list)
        if not token_list or token_list.peek().is_indent:
            #表达式
            stmt_list.append(_Stmt("expr", expr = expr))
            continue
        may_be_assign_token = token_list.peek()
        if (may_be_assign_token.is_sym and
            may_be_assign_token.value in ("=", "%=", "^=", "&=", "*=", "-=",
                                          "+=", "|=", "/=", "<<=", ">>=",
                                          ">>>=")):
            #赋值
            assign_sym = may_be_assign_token.value
            lvalue = expr
            if not lvalue.is_lvalue:
                t.syntax_err("赋值语句'%s'左边非左值表达式" % assign_sym)
            if assign_sym != "=":
                #增量赋值
                if lvalue.op == "[:]":
                    t.syntax_err("分片无法增量赋值")
                if lvalue.op in ("tuple", "list"):
                    t.syntax_err("不支持unpack增量赋值")
            token_list.pop_sym(assign_sym)
            expr = larc_expr.parse_expr(token_list)
            stmt_list.append(_Stmt(assign_sym, lvalue = lvalue, expr = expr))
            continue

    return stmt_list, global_var_set

def check_last_return(stmt_list):
    #检查最后一个return，如果没有则加一个空return
    #本来想做完整的返回/不可达语句检查，但是太麻烦了，以后再说
    #如果转为其他语言，比如java，可能会造成编译错误，暂时先比对代码修改
    def _has_last_return(stmt_list):
        if not stmt_list:
            return False
        stmt = stmt_list[-1]
        if stmt.type == "return":
            return True
        if stmt.type != "if":
            return False
        #最后一个语句是if的时候，需要展开判断
        if stmt.else_stmt_list is None:
            return False
        if not _has_last_return(stmt.else_stmt_list):
            return False
        for expr, if_stmt_list in stmt.if_list:
            if not _has_last_return(if_stmt_list):
                return False
        return True

    if not _has_last_return(stmt_list):
        stmt_list.append(_Stmt("return", expr = None))
