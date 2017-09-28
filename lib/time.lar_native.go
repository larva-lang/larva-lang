import (
    "time"
)

func lar_func_4_time_4_time() lar_type_double {
    return lar_type_double(time.Now().UnixNano()) / 1e9
}
