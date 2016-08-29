package larva_booter

import (
    "os"
    "larva_obj"
    "larva_exc"
    "lar_mod___builtins"
)

func Start_prog(main_func func (argv larva_obj.LarPtr) larva_obj.LarPtr) ret int {
    argv := lar_mod___builtins.NewLarObj_list()
    for i := 0; i < len(os.Args); i ++ {
        argv.Method_add_1(lar_mod___builtins.NewLarObj_str_from_literal(os.Args[i]))
    }

    defer func () {
        r := larva_exc.Lar_recover()
        if r != nil {
            larva_exc.Traceback_print_exc()
            ret = 1
        }
    }()
    main_func(argv)
    return 0
}
