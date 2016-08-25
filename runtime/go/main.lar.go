package main

import (
    "os"
    "larva_mod___builtins"
    "larva_runtime"
)

func main() {
    argv := larva_mod___builtins.NewLarObj_list()
    for i := 0; i < len(os.Args); i ++ {
        argv.Method_add_1(larva_mod___builtins.NewLarObj_str_from_literal(os.Args[i]))
    }
    os.Exit(larva_runtime.Start_prog(argv))
}
