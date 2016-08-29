package larva_obj

import (
    "fmt"
    "larva_exc"
)

type LarPtr struct {
    M_int int64
    M_obj_ptr *LarObj
}

func (ptr *LarPtr) As_int() int64 {
    if (ptr.M_obj_ptr != nil)
    {
        larva_exc.Lar_panic_string(fmt.Sprintf("%s not int type", ptr.M_obj_ptr.Get_type_name()))
    }
    return ptr.M_int
}

type LarObjBase struct {
    This LarObj
    Type_name string
}

func (self *LarObjBase) Get_type_name() string {
    return self.Type_name
}
