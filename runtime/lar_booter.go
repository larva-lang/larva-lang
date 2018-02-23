import (
    "os"
)

func lar_booter_start_prog(main_mod_init_func func (), main_func func (*[]*lar_cls_10___builtins_6_String) int32,
                           argv *[]*lar_cls_10___builtins_6_String) int {
    defer func () {
        c := lar_func_10___builtins_10_catch_base(recover())
        if c != nil {
            println("程序异常退出：")
            println(lar_util_convert_lar_str_to_go_str(c.m_traceback))
            os.Exit(2)
        }
    }()
    lar_env_init_mod___builtins()
    main_mod_init_func()
    return int(main_func(argv))
}

func lar_booter_start_co(co lar_intf_10___builtins_9_Coroutine) {
    defer func () {
        c := lar_func_10___builtins_10_catch_base(recover())
        if c != nil {
            println("程序异常退出：")
            println(lar_util_convert_lar_str_to_go_str(c.m_traceback))
            os.Exit(2)
        }
    }()
    co.method_run()
}
