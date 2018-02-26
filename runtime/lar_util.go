import (
    "reflect"
    "math"
)

func lar_util_is_same_intf(a, b interface{}) bool {
    return reflect.ValueOf(&a).Elem().InterfaceData()[1] == reflect.ValueOf(&b).Elem().InterfaceData()[1]
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

func lar_util_convert_go_tb_to_lar_tb(file string, line int, func_name string) (string, int, string, bool) {
    lar_tb, ok := lar_util_tb_map[lar_util_go_tb{file: file, line: line}]
    if !ok {
        //没找到对应的，原样返回
        return file, line, func_name, true
    }
    if lar_tb == nil {
        return "", 0, "", false
    }
    return lar_tb.file, lar_tb.line, lar_tb.fom_name, true
}
