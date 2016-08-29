package lar_mod___builtins

import (
    "larva_obj"
    "larva_exc"
)

func init() {
    larva_exc.NewLarObj_str_from_literal = NewLarObj_str_from_literal
}

//float

type LarObj_float struct {
    larva_obj.LarObjBase
    v float64
}

func NewLarObj_float_from_literal(v float64) larva_obj.LarPtr {
    o := new(LarObj_float)
    o.v = v
    o.This = o
    o.Type_name = "__builtins.float"
    return larva_obj.LarPtr{M_obj_ptr : &o.This}
}

func (self *LarObj_float) Method_to_int_0() larva_obj.LarPtr {
    return larva_obj.LarPtr{M_int : int64(self.v)}
}

//str

type LarObj_str struct {
    larva_obj.LarObjBase
    v string
}

func NewLarObj_str_from_literal(v string) larva_obj.LarPtr {
    o := new(LarObj_str)
    o.v = v
    o.This = o
    o.Type_name = "__builtins.str"
    return larva_obj.LarPtr{M_obj_ptr : &o.This}
}

func NewLarObj_str() larva_obj.LarPtr {
    return NewLarObj_str_from_literal("")
}

func (self *LarObj_str) OP_init_1(obj larva_obj.LarPtr) larva_obj.LarPtr {
    self.v = obj.OP_str()
    return larva_obj.NIL
}

//list

type LarObj_list struct {
    larva_obj.LarObjBase
    l []larva_obj.LarPtr
}

func NewLarObj_list() larva_obj.LarPtr {
    o := new(LarObj_list)
    o.This = o
    o.Type_name = "__builtins.list"
    return larva_obj.LarPtr{M_obj_ptr : &o.This}
}

func (self *LarObj_list) Method_add_1(obj larva_obj.LarPtr) larva_obj.LarPtr {
    self.l = append(self.l, obj)
    return larva_obj.LarPtr{M_obj_ptr : &self.This}
}

//range

type LarObj_range struct {
    larva_obj.LarObjBase
    curr int64
    stop int64
    step int64
}

func NewLarObj_range() larva_obj.LarPtr {
    o := new(LarObj_range)
    o.This = o
    o.Type_name = "__builtins.range"
    return larva_obj.LarPtr{M_obj_ptr : &o.This}
}

func (self *LarObj_range) init(start, stop, step int64) larva_obj.LarPtr {
    if step == 0 {
        larva_exc.Lar_panic_string("range step is zero")
    }

    self.curr = start
    self.stop = stop
    self.step = step

    return larva_obj.NIL
}

func (self *LarObj_range) OP_init_1(stop larva_obj.LarPtr) larva_obj.LarPtr {
    return self.init(0, stop.As_int(), 1)
}

func (self *LarObj_range) OP_init_2(start, stop larva_obj.LarPtr) larva_obj.LarPtr {
    return self.init(start.As_int(), stop.As_int(), 1)
}

func (self *LarObj_range) OP_init_3(start, stop, step larva_obj.LarPtr) larva_obj.LarPtr {
    return self.init(start.As_int(), stop.As_int(), step.As_int())
}
