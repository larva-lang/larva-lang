package LARVA_NATIVE

import (
    "runtime"
    "strings"
    "fmt"
)

/*
tb信息格式：

Traceback:
  File '文件', line 行号, in 函数或方法名或<module>
  ......
Throwed: 抛出的异常的字符串描述

其中堆栈信息的方向是从栈底开始显示，即每行信息是下一行的调用者
*/
func lar_func_10___builtins_5_throw(t lar_intf_10___builtins_9_Throwable) {
    var tb_line_list []string
    tb_line_list = append(tb_line_list, "Throwed: " + lar_util_convert_lar_str_to_go_str(t.method_to_str()))
    for i := 1; true; i ++ {
        pc, file, line, ok := runtime.Caller(i)
        if !ok {
            break
        }
        func_name := runtime.FuncForPC(pc).Name()
        if strings.HasSuffix(func_name, ".Lar_booter_start_prog") {
            break
        }
        file, line, func_name, ok = lar_util_convert_go_tb_to_lar_tb(file, line, func_name)
        if ok {
            tb_line := fmt.Sprintf("  File '%s', line %d, in %s", file, line, func_name)
            if tb_line_list[len(tb_line_list) - 1] != tb_line {
                tb_line_list = append(tb_line_list, tb_line)
            }
        }
    }
    tb_line_list = append(tb_line_list, "Traceback:")
    //上面是反着写info的，reverse一下
    tb_line_count := len(tb_line_list)
    for i := 0; i < tb_line_count / 2; i ++ {
        tb_line_list[i], tb_line_list[tb_line_count - 1 - i] = tb_line_list[tb_line_count - 1 - i], tb_line_list[i]
    }

    tb := lar_util_create_lar_str_from_go_str(strings.Join(tb_line_list, "\n"))
    panic(lar_new_obj_lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable(t, tb))
}

func lar_func_10___builtins_15_rethrow_catched(c *lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable) {
    panic(c)
}

func lar_func_10___builtins_24__go_recovered_to_catched(r interface{}) *lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable {
    if r == nil {
        return nil
    }
    c, ok := r.(*lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable)
    if !ok {
        //不是larva自己的异常
        panic(r)
    }
    return c
}
