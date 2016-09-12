package lar_mod_sys

import (
    "os"
    "larva_obj"
    "lar_mod_io"
)

var G_stdout larva_obj.LarPtr = lar_mod_io.NewLarObj_File_from_file_handler(os.Stdout)
