type lar_type_bool bool
type lar_type_schar int8
type lar_type_char uint8
type lar_type_short int16
type lar_type_ushort uint16
type lar_type_int int32
type lar_type_uint uint32
type lar_type_long int64
type lar_type_ulong uint64
type lar_type_float float32
type lar_type_double float64

func lar_util_create_lar_str_from_go_str(s string) *lar_cls_10___builtins_6_String {
	ls := lar_cls_10___builtins_6_String(s)
	return &ls
}
