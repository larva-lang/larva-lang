package larva_exc

import (
    "larva_obj"
)

var mod_inited bool = false
func Init() {
    if !mod_inited {
        larva_obj.Init()
        mod_inited = true
    }
}

var NewLarObj_str_from_literal func (s string) larva_obj.LarPtr

func init() {
    larva_obj.Lar_panic_string = Lar_panic_string
}

func Lar_recover(r interface{}) *larva_obj.LarPtr {
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
    println(s)
    Lar_panic(NewLarObj_str_from_literal(s))
}
