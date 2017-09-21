package main

import (
    "os"
    "larva_booter"
    "lar_mod_hello_world"
)

func main() {
    lar_mod_hello_world.Init()
    os.Exit(larva_booter.Start_prog(lar_mod_hello_world.Func_main_1))
}
