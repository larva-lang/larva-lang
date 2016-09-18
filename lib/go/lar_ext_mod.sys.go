package lar_mod_sys

import (
    "os"
    "larva_obj"
    "lar_mod_io"
)

func NativeInit() {
    G_stdout = lar_mod_io.NewLarObj_File_from_file_handler(os.Stdout)
}

var G_stdout larva_obj.LarPtr
