import (
    "unsafe"
    "math"
)

type lar_util_intf_stru struct {
    tab unsafe.Pointer
    data unsafe.Pointer
}

func lar_util_is_same_intf(a, b interface{}) bool {
    return ((*lar_util_intf_stru)(unsafe.Pointer(&a))).data == ((*lar_util_intf_stru)(unsafe.Pointer(&b))).data
}

func lar_util_fmod_float(a, b float32) float32 {
    return float32(math.Mod(float64(a), float64(b)))
}

func lar_util_fmod_double(a, b float64) float64 {
    return math.Mod(a, b)
}

const (
    RBC_NONE        = 0
    RBC_RET         = 1
    RBC_BREAK       = 2
    RBC_CONTINUE    = 3
)

type lar_util_go_tb struct {
    file string
    line int
}

type lar_util_lar_tb struct {
    file string
    line int
    fom_name string
}

func lar_util_convert_go_tb_to_lar_tb(file string, line int, func_name string) (string, int, string) {
    lar_tb, ok := lar_util_tb_map[lar_util_go_tb{file: file, line: line}]
    if !ok {
        //没找到对应的，原样返回
        return file, line, func_name
    }
    return lar_tb.file, lar_tb.line, lar_tb.fom_name
}
