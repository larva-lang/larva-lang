package larva_runtime

import (
    "larva_obj"
    "lar_mod___builtins"
)

func Lar_recover() *larva_obj.LarPtr {
    r := recover()
    if r == nil {
        return nil
    }
    return &r.(larva_obj.LarPtr)
}

func Lar_panic(obj larva_obj.LarPtr) {
    panic(obj)
}

func Lar_panic_string(s string) {
    Lar_panic(lar_mod___builtins.NewLarObj_str_from_literal(s))
}
