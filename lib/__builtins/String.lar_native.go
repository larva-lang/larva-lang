package LARVA_NATIVE

import (
    "strings"
    "strconv"
    "fmt"
)

type lar_cls_10___builtins_7__String struct {
    s string
}

func lar_new_obj_lar_cls_10___builtins_7__String(arr *[]uint8) *lar_cls_10___builtins_7__String {
    return &lar_cls_10___builtins_7__String{s: string(*arr)}
}

func (this *lar_cls_10___builtins_7__String) method_len() int64 {
    return int64(len(this.s))
}

func (this *lar_cls_10___builtins_7__String) method_char_at(idx int64) uint8 {
    return this.s[idx]
}

func (this *lar_cls_10___builtins_7__String) method_cmp(other *lar_cls_10___builtins_6_String) int32 {
    return int32(strings.Compare(this.s, other.m_s.s))
}

func (this *lar_cls_10___builtins_7__String) method_index(other *lar_cls_10___builtins_6_String) int64 {
    return int64(strings.Index(this.s, other.m_s.s))
}

func (this *lar_cls_10___builtins_7__String) method_to_char_array() *[]uint8 {
    arr := []uint8(this.s)
    return &arr
}

func (this *lar_cls_10___builtins_7__String) method_hash() uint64 {
    var h uint64
    s := this.s
    sl := len(s)
    for i := 0; i < sl; i ++ {
        h = (h + uint64(s[i])) * 1000003
    }
    return h
}

func (this *lar_cls_10___builtins_7__String) method_concat(other *lar_cls_10___builtins_6_String) *lar_cls_10___builtins_6_String {
    return &lar_cls_10___builtins_6_String{
        m_s: &lar_cls_10___builtins_7__String{
            s: this.s + other.m_s.s,
        },
    }
}

func (this *lar_cls_10___builtins_7__String) method_parse_bool() bool {
    s := this.s
    r, err := strconv.ParseBool(s)
    if err != nil {
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_10___builtins_10_ValueError(lar_str_fmt("无效的bool字面量：'%s'", s)))
    }
    return r
}

func (this *lar_cls_10___builtins_7__String) method_parse_long(base int32) int64 {
    s := this.s
    r, err := strconv.ParseInt(s, int(base), 64)
    if err != nil {
        var err_info *lar_cls_10___builtins_6_String
        if base == 0 {
            err_info = lar_str_fmt("无效的long字面量：'%s'", s)
        } else {
            err_info = lar_str_fmt("无效的%d进制long字面量：'%s'", base, s)
        }
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_10___builtins_10_ValueError(err_info))
    }
    return r
}

func (this *lar_cls_10___builtins_7__String) method_parse_ulong(base int32) uint64 {
    s := this.s
    r, err := strconv.ParseUint(s, int(base), 64)
    if err != nil {
        var err_info *lar_cls_10___builtins_6_String
        if base == 0 {
            err_info = lar_str_fmt("无效的ulong字面量：'%s'", s)
        } else {
            err_info = lar_str_fmt("无效的%d进制ulong字面量：'%s'", base, s)
        }
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_10___builtins_10_ValueError(err_info))
    }
    return r
}

func (this *lar_cls_10___builtins_7__String) method_parse_double() float64 {
    s := this.s
    r, err := strconv.ParseFloat(s, 64)
    if err != nil {
        err_info := lar_str_fmt("无效的double字面量：'%s'", s)
        lar_func_10___builtins_5_throw(lar_new_obj_lar_cls_10___builtins_10_ValueError(err_info))
    }
    return r
}

func lar_util_create_lar_str_from_go_str(s string) *lar_cls_10___builtins_6_String {
	return &lar_cls_10___builtins_6_String{
        m_s: &lar_cls_10___builtins_7__String{
            s: s,
        },
    }
}

func lar_util_convert_lar_str_to_go_str(s *lar_cls_10___builtins_6_String) string {
    return s.m_s.s
}

func lar_str_fmt(format string, a ...interface{}) *lar_cls_10___builtins_6_String {
    for i, v := range a {
        s, ok := v.(*lar_cls_10___builtins_6_String)
        if ok {
            a[i] = s.m_s.s
        }
    }
    return lar_util_create_lar_str_from_go_str(fmt.Sprintf(format, a...))
}
