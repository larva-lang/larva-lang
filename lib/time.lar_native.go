import (
    "time"
)

func lar_func_4_time_4_time() float64 {
    return float64(time.Now().UnixNano()) / 1e9
}
