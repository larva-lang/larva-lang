import (
    "fmt"
    "os"
)

func lar_booter_exit_with_catched(c *lar_gcls_inst_10___builtins_7_Catched_1_lar_intf_10___builtins_9_Throwable) {
    fmt.Fprintln(os.Stderr, lar_str_to_go_str(c.m_tb))
    os.Exit(2)
}

func lar_booter_check_go_panic() {
    r := recover()
    if r != nil {
        fmt.Fprintln(os.Stderr, "process crash, traceback:")
        fmt.Fprintln(os.Stderr, lar_str_to_go_str(lar_exc_create_catched_throwable(nil, 5).m_tb))
        panic(r)
    }
}

func lar_booter_start_prog(main_mod_init_func func (), main_func func ()) {
    defer lar_booter_check_go_panic()
    defer func () {
        c := lar_func_10___builtins_15_catch_throwable(recover())
        if c != nil {
            lar_booter_exit_with_catched(c)
        }
    }()
    lar_env_init_mod_10___builtins()
    main_mod_init_func()
    main_func()
}

func lar_booter_start_co(co lar_intf_10___builtins_8_Runnable) {
    defer lar_booter_check_go_panic()
    defer func () {
        c := lar_func_10___builtins_15_catch_throwable(recover())
        if c != nil {
            lar_booter_exit_with_catched(c)
        }
    }()
    co.lar_method_run()
}
