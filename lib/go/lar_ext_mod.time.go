package lar_mod_time

import (
    "time"
    "larva_obj"
    "lar_mod___builtins"
)

func NativeInit() {
}

func Func_time_0() larva_obj.LarPtr {
    return lar_mod___builtins.NewLarObj_float_from_literal(float64(time.Now().UnixNano()) / 1e9)
}
