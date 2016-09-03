package larva_obj

import (
    "fmt"
)

type LarPtr struct {
    M_int int64
    M_obj_ptr *LarObjIntf
}

func (ptr *LarPtr) As_int() int64 {
    if ptr.M_obj_ptr != nil {
        Lar_panic_string(fmt.Sprintf("%s is not int type", (*ptr.M_obj_ptr).Get_type_name()))
    }
    return ptr.M_int
}

func (ptr *LarPtr) Get_type_name() string {
    if ptr.M_obj_ptr != nil {
        return (*ptr.M_obj_ptr).Get_type_name()
    }
    return "__builtins.int"
}

func int_to_shift_count(n int64) uint {
    if n < 0 || n >= 64 {
        Lar_panic_string(fmt.Sprintf("invalid shift count %d", n))
    }
    return uint(n)
}
