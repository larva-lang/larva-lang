import (
    "fmt"
    "strconv"
)

type lar_cls_10___builtins_6_String string

func (this *lar_cls_10___builtins_6_String) method_char_at(idx lar_type_long) lar_type_char {
    return lar_type_char(string(*this)[idx])
}

func (this *lar_cls_10___builtins_6_String) method_cmp(other *lar_cls_10___builtins_6_String) lar_type_int {
    this_s := string(*this)
    other_s := string(*other)
    if this_s < other_s {
        return -1
    }
    if this_s > other_s {
        return 1
    }
    return 0
}

func (this *lar_cls_10___builtins_6_String) method_parse_int(base lar_type_int, n *lar_type_int) *lar_cls_10___builtins_5_Error {
    r, err := strconv.ParseInt(string(*this), int(base), 32)
    if err != nil {
        return lar_new_obj_lar_cls_10___builtins_5_Error(-1, lar_util_create_lar_str_from_go_str("parse error"))
    }
    *n = lar_type_int(r)
    return nil
}

func lar_util_create_lar_str_from_go_str(s string) *lar_cls_10___builtins_6_String {
	ls := lar_cls_10___builtins_6_String(s)
	return &ls
}

func lar_util_convert_lar_str_to_go_str(s *lar_cls_10___builtins_6_String) string {
    return string(*s)
}

func lar_str_fmt(format string, a ...interface{}) *lar_cls_10___builtins_6_String {
    ls := lar_cls_10___builtins_6_String(fmt.Sprintf(format, a...))
    return &ls
}
