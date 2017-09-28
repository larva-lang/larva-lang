type lar_cls_10___builtins_6_String string

func lar_util_create_lar_str_from_go_str(s string) *lar_cls_10___builtins_6_String {
	ls := lar_cls_10___builtins_6_String(s)
	return &ls
}

func lar_util_convert_lar_str_to_go_str(s *lar_cls_10___builtins_6_String) string {
    return string(*s)
}
