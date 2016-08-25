package larva_runtime

import (
    "larva_mod___builtins"
)

func Lar_panic(obj LarPtr) {
    panic(obj)
}

func Lar_panic_string(s string) {
    Lar_panic(larva_mod___builtins.NewLarObj_str_from_literal(s))
}
