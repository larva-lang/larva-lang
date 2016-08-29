package larva_exc

import (
    "larva_obj"
)

var NewLarObj_str_from_literal func (s string) larva_obj.LarPtr

func init() {
    larva_obj.Lar_panic_string = Lar_panic_string
}

func Lar_recover() *larva_obj.LarPtr {
    r := recover()
    if r == nil {
        return nil
    }
    lar_r := r.(larva_obj.LarPtr)
    return &lar_r
}

func Lar_panic(obj larva_obj.LarPtr) {
    panic(obj)
}

func Lar_panic_string(s string) {
    Lar_panic(NewLarObj_str_from_literal(s))
}
