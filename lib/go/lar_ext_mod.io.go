package lar_mod_io

import (
    "fmt"
    "os"
    "larva_obj"
)

func NativeInit() {
}

//File

type LarObj_File struct {
    larva_obj.LarObjBase
    f *os.File
}

func NewLarObj_File() *LarObj_File {
    o := new(LarObj_File)
    o.This = o
    o.Type_name = "io.File"
    return o
}

func NewLarObj_File_from_file_handler(f *os.File) larva_obj.LarPtr {
    o := NewLarObj_File()
    o.f = f
    return o.To_lar_ptr()
}

func (self *LarObj_File) Method_writeln_1(s larva_obj.LarPtr) larva_obj.LarPtr {
    fmt.Fprintln(self.f, s.As_str())
    return larva_obj.NIL
}
