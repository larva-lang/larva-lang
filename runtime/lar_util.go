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
