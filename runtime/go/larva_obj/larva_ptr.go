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

func (ptr *LarPtr) OP_str() string {
    if ptr.M_obj_ptr != nil {
        return (*ptr.M_obj_ptr).OP_str()
    }
    return int_OP_str(ptr.M_int)
}
