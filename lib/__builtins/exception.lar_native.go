import (
    "runtime"
    "strings"
    "fmt"
)

func lar_func_10___builtins_5_throw(t lar_intf_10___builtins_9_Throwable) {
    var tb_list []string
    for i := 0; true; i ++ {
        pc, file, line, ok := runtime.Caller(i)
        if !ok {
            break
        }
        func_name := runtime.FuncForPC(pc).Name()
        tb_list = append(tb_list, fmt.Sprintf("%s:%d:%s", file, line, func_name))
    }
    tb := lar_util_create_lar_str_from_go_str(strings.Join(tb_list, "\n"))
    panic(lar_new_obj_lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable(t, tb))
}

func lar_func_10___builtins_10_catch_base() *lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable {
    r := recover()
    c, ok := r.(*lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable)
    if !ok {
        //不是larvar自己的异常
        panic(r)
    }
    return c
}

func lar_func_10___builtins_7_rethrow(c *lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable) {
    panic(c)
}
