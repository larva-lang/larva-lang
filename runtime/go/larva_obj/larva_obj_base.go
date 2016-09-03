package larva_obj

import (
    "fmt"
)

type LarObjBase struct {
    This LarObjIntf
    Type_name string
}

func (self *LarObjBase) To_lar_ptr() LarPtr {
    return LarPtr{M_obj_ptr : &self.This}
}

func (self *LarObjBase) Get_type_name() string {
    return self.Type_name
}

func (self *LarObjBase) As_bool() bool {
    Lar_panic_string(fmt.Sprintf("%s is not bool type", self.Type_name))
    return false
}

func (self *LarObjBase) As_float() float64 {
    Lar_panic_string(fmt.Sprintf("%s is not float type", self.Type_name))
    return 0.0
}

func (self *LarObjBase) As_str() string {
    Lar_panic_string(fmt.Sprintf("%s is not str type", self.Type_name))
    return ""
}
