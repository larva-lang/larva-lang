package larva_mod___builtins

import (
    "larva_runtime"
)

//float

type LarObj_float struct {
    larva_runtime.LarObjBase
    v float64
}

func NewLarObj_float_from_literal(v float64) larva_runtime.LarPtr {
    o := new(LarObj_float)
    o.v = v
    o.This = o
    o.Type_name = "__builtins.float"
    return larva_runtime.LarPtr{M_obj_ptr : &o.This}
}

func (self *LarObj_float) Method_to_int_0() larva_runtime.LarPtr {
    return larva_runtime.LarPtr{M_int : int64(self.v)}
}

//str

type LarObj_str struct {
    larva_runtime.LarObjBase
    v string
}

func NewLarObj_str_from_literal(v string) larva_runtime.LarPtr {
    o := new(LarObj_str)
    o.v = v
    o.This = o
    o.Type_name = "__builtins.str"
    return larva_runtime.LarPtr{M_obj_ptr : &o.This}
}

func NewLarObj_str() larva_runtime.LarPtr {
    return NewLarObj_str_from_literal("")
}

func (self *LarObj_str) OP_init_1(obj larva_runtime.LarPtr) larva_runtime.LarPtr {
    self.v = obj.OP_str()
    return larva_runtime.NIL
}

//list

type LarObj_list struct {
    larva_runtime.LarObjBase
    l []larva_runtime.LarPtr
}

func NewLarObj_list() larva_runtime.LarPtr {
    o := new(LarObj_list)
    o.This = o
    o.Type_name = "__builtins.list"
    return larva_runtime.LarPtr{M_obj_ptr : &o.This}
}

func (self *LarObj_list) Method_add_1(obj larva_runtime.LarPtr) larva_runtime.LarPtr {
    self.l = append(self.l, obj)
    return self.This
}

//range

type LarObj_range struct {
    larva_runtime.LarObjBase
    curr int64
    stop int64
    step int64
}

func NewLarObj_range() larva_runtime.LarPtr {
    o := new(LarObj_range)
    o.This = o
    o.Type_name = "__builtins.range"
    return larva_runtime.LarPtr{M_obj_ptr : &o.This}
}

func (self *LarObj_range) init(start, stop, step int64) larva_runtime.LarPtr {
    if (step == 0)
    {
        Lar_panic_string("range step is zero")
    }

    self.curr = start
    self.stop = stop
    self.step = step

    return larva_runtime.NIL
}

func (self *LarObj_range) OP_init_1(stop larva_runtime.LarPtr) larva_runtime.LarPtr {
    return self.init(0, stop.As_int(), 1)
}

func (self *LarObj_range) OP_init_2(start, stop larva_runtime.LarPtr) larva_runtime.LarPtr {
    return self.init(start.As_int(), stop.As_int(), 1)
}

func (self *LarObj_range) OP_init_3(start, stop, step larva_runtime.LarPtr) larva_runtime.LarPtr {
    return self.init(start.As_int(), stop.As_int(), step.As_int())
}
