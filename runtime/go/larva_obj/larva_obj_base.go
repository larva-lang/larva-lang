package larva_obj

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
