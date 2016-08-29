package larva_obj

type LarObjBase struct {
    This LarObjIntf
    Type_name string
}

func (self *LarObjBase) Get_type_name() string {
    return self.Type_name
}
