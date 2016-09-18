package larva_obj

var mod_inited bool = false
func Init() {
    if !mod_inited {
        mod_inited = true
    }
}

var NewLarObj_str_from_literal func (s string) LarPtr
var Lar_panic_string func (s string)

var NIL LarPtr
var TRUE LarPtr
var FALSE LarPtr

func Lar_bool_from_bool(v bool) LarPtr {
    if v {
        return TRUE
    }
    return FALSE
}

type LarObjIntfBase interface {
    Get_type_name() string

    As_bool() bool
    Bool_not() LarPtr
    As_float() float64
    As_str() string
}
