package larva_obj

var NewLarObj_str_from_literal func (s string) LarPtr
var Lar_panic_string func (s string)

var NIL LarPtr
var TRUE LarPtr
var FALSE LarPtr

type LarObjIntfBase interface {
    Get_type_name() string
}
