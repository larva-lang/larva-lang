package LARVA_NATIVE

import (
    "time"
)

type lar_cls_4_time_5__Time struct {
    ntm time.Time
}

func (this *lar_cls_4_time_5__Time) method_unix_nano() int64 {
    return this.ntm.UnixNano()
}

func (this *lar_cls_4_time_5__Time) method_format(layout *lar_cls_10___builtins_6_String) *lar_cls_10___builtins_6_String {
    return lar_util_create_lar_str_from_go_str(this.ntm.Format(lar_util_convert_lar_str_to_go_str(layout)))
}

func lar_func_4_time_3_now() *lar_cls_4_time_4_Time {
    return &lar_cls_4_time_4_Time{
        m_t: &lar_cls_4_time_5__Time{
            ntm: time.Now(),
        },
    }
}

func lar_func_4_time_10_sleep_nano(nano_sec int64) {
    time.Sleep(time.Duration(nano_sec))
}
