package LARVA_NATIVE

func lar_booter_start_co(co lar_intf_10___builtins_9_Coroutine) {
    co.method_run()
}

func lar_func_10___builtins_15_start_coroutine(co lar_intf_10___builtins_9_Coroutine) {
    go lar_booter_start_co(co)
}
