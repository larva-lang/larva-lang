package lar_mod___builtins

import (
    "fmt"
    "larva_obj"
    "larva_exc"
)

func init() {
    larva_obj.NewLarObj_str_from_literal = NewLarObj_str_from_literal
    larva_obj.NIL = newLarObj_nil().To_lar_ptr()
    larva_obj.TRUE = newLarObj_bool_from_literal(true)
    larva_obj.FALSE = newLarObj_bool_from_literal(false)

    larva_exc.NewLarObj_str_from_literal = NewLarObj_str_from_literal
}

func NativeInit() {
}

//nil

type LarObj_nil struct {
    larva_obj.LarObjBase
}

func newLarObj_nil() *LarObj_nil {
    o := new(LarObj_nil)
    o.This = o
    o.Type_name = "__builtins.nil_type"
    return o
}

func (self *LarObj_nil) Method___bool() larva_obj.LarPtr {
    return larva_obj.FALSE
}

var nil_str_obj larva_obj.LarPtr = NewLarObj_str_from_literal("nil")

func (self *LarObj_nil) Method___str() larva_obj.LarPtr {
    return nil_str_obj
}

//bool

type LarObj_bool struct {
    larva_obj.LarObjBase
    v bool
}

func newLarObj_bool() *LarObj_bool {
    o := new(LarObj_bool)
    o.This = o
    o.Type_name = "__builtins.bool"
    return o
}

func newLarObj_bool_from_literal(v bool) larva_obj.LarPtr {
    o := newLarObj_bool()
    o.v = v
    return o.To_lar_ptr()
}

func NewLarObj_bool_0() larva_obj.LarPtr {
    o := newLarObj_bool()
    o.Method___init_0()
    return o.To_lar_ptr()
}

func (self *LarObj_bool) As_bool() bool {
    return self.v
}

func (self *LarObj_bool) Bool_not() larva_obj.LarPtr {
    if self.v {
        return larva_obj.FALSE
    }
    return larva_obj.TRUE
}

func (self *LarObj_bool) Method___bool() larva_obj.LarPtr {
    return self.To_lar_ptr()
}

var true_str_obj larva_obj.LarPtr = NewLarObj_str_from_literal("true")
var false_str_obj larva_obj.LarPtr = NewLarObj_str_from_literal("false")

func (self *LarObj_bool) Method___str() larva_obj.LarPtr {
    if self.v {
        return true_str_obj
    }
    return false_str_obj
}

func (self *LarObj_bool) Method___init_0() larva_obj.LarPtr {
    self.v = false
    return larva_obj.NIL
}

//float

type LarObj_float struct {
    larva_obj.LarObjBase
    v float64
}

func NewLarObj_float() *LarObj_float {
    o := new(LarObj_float)
    o.This = o
    o.Type_name = "__builtins.float"
    return o
}

func NewLarObj_float_from_literal(v float64) larva_obj.LarPtr {
    o := NewLarObj_float()
    o.v = v
    return o.To_lar_ptr()
}

func NewLarObj_float_0() larva_obj.LarPtr {
    o := NewLarObj_float()
    o.Method___init_0()
    return o.To_lar_ptr()
}

func (self *LarObj_float) As_float() float64 {
    return self.v
}

func (self *LarObj_float) Method___bool() larva_obj.LarPtr {
    if self.v == 0.0 {
        return larva_obj.FALSE
    }
    return larva_obj.TRUE
}

func (self *LarObj_float) Method___str() larva_obj.LarPtr {
    return NewLarObj_str_from_literal(fmt.Sprint(self.v))
}

func (self *LarObj_float) Method___sub(obj larva_obj.LarPtr) larva_obj.LarPtr {
    if obj.M_obj_ptr == nil {
        return NewLarObj_float_from_literal(self.v - float64(obj.M_int))
    }
    switch v := (*obj.M_obj_ptr).(type) {
        case *LarObj_float:
            return NewLarObj_float_from_literal(self.v - v.v)
    }
    return (*obj.M_obj_ptr).Method___rsub(self.To_lar_ptr())
}

func (self *LarObj_float) Method___rdiv(obj larva_obj.LarPtr) larva_obj.LarPtr {
    if obj.M_obj_ptr == nil {
        return NewLarObj_float_from_literal(float64(obj.M_int) / self.v)
    }
    return self.LarObjBase.Method___rdiv(obj)
}

func (self *LarObj_float) Method___init_0() larva_obj.LarPtr {
    self.v = 0.0
    return larva_obj.NIL
}

func (self *LarObj_float) Method_to_int_0() larva_obj.LarPtr {
    return larva_obj.LarPtr{M_int : int64(self.v)}
}

//str

type LarObj_str struct {
    larva_obj.LarObjBase
    v string
}

func NewLarObj_str() *LarObj_str {
    o := new(LarObj_str)
    o.This = o
    o.Type_name = "__builtins.str"
    return o
}

func NewLarObj_str_from_literal(v string) larva_obj.LarPtr {
    o := NewLarObj_str()
    o.v = v
    return o.To_lar_ptr()
}

func NewLarObj_str_0() larva_obj.LarPtr {
    o := NewLarObj_str()
    o.Method___init_0()
    return o.To_lar_ptr()
}

func NewLarObj_str_1(obj larva_obj.LarPtr) larva_obj.LarPtr {
    o := NewLarObj_str()
    o.Method___init_1(obj)
    return o.To_lar_ptr()
}

func (self *LarObj_str) As_str() string {
    return self.v
}

func (self *LarObj_str) Method___bool() larva_obj.LarPtr {
    if len(self.v) == 0 {
        return larva_obj.FALSE
    }
    return larva_obj.TRUE
}

func (self *LarObj_str) Method___str() larva_obj.LarPtr {
    return self.To_lar_ptr()
}

func (self *LarObj_str) Method___init_0() larva_obj.LarPtr {
    self.v = ""
    return larva_obj.NIL
}

func (self *LarObj_str) Method___init_1(obj larva_obj.LarPtr) larva_obj.LarPtr {
    self.v = obj.Method___str().As_str()
    return larva_obj.NIL
}

func (self *LarObj_str) Method___add(obj larva_obj.LarPtr) larva_obj.LarPtr {
    return NewLarObj_str_from_literal(self.v + obj.Method___str().As_str())
}

func (self *LarObj_str) Method___eq(obj larva_obj.LarPtr) larva_obj.LarPtr {
    if obj.M_obj_ptr != nil {
        switch v := (*obj.M_obj_ptr).(type) {
            case *LarObj_str:
                return larva_obj.Lar_bool_from_bool(self.v == v.v)
        }
    }
    return self.LarObjBase.Method___eq(obj)
}

func (self *LarObj_str) Method___cmp(obj larva_obj.LarPtr) larva_obj.LarPtr {
    if obj.M_obj_ptr != nil {
        switch v := (*obj.M_obj_ptr).(type) {
            case *LarObj_str:
                if self.v < v.v {
                    return larva_obj.LarPtr{M_int : -1}
                }
                if self.v > v.v {
                    return larva_obj.LarPtr{M_int : 1}
                }
                return larva_obj.LarPtr{M_int : 0}
        }
    }
    return self.LarObjBase.Method___cmp(obj)
}

func (self *LarObj_str) Method_ord_at_1(obj larva_obj.LarPtr) larva_obj.LarPtr {
    idx := obj.As_int()
    curr_len := int64(len(self.v))
    if idx < 0 {
        idx += curr_len
    }
    if idx < 0 || idx >= curr_len {
        larva_exc.Lar_panic_string(fmt.Sprintf("string index out of range %v", idx))
    }
    return larva_obj.LarPtr{M_int : int64(self.v[idx])}
}

//list

type LarObj_list struct {
    larva_obj.LarObjBase
    l []larva_obj.LarPtr
}

func NewLarObj_list() *LarObj_list {
    o := new(LarObj_list)
    o.This = o
    o.Type_name = "__builtins.list"
    return o
}

func NewLarObj_list_0() larva_obj.LarPtr {
    o := NewLarObj_list()
    o.Method___init_0()
    return o.To_lar_ptr()
}

func NewLarObj_list_from_var_arg(args ...larva_obj.LarPtr) larva_obj.LarPtr {
    o := NewLarObj_list()
    o.l = make([]larva_obj.LarPtr, len(args))
    copy(o.l, args)
    return o.To_lar_ptr()
}

func (self *LarObj_list) Method___bool() larva_obj.LarPtr {
    if len(self.l) == 0 {
        return larva_obj.FALSE
    }
    return larva_obj.TRUE
}

func (self *LarObj_list) Method___init_0() larva_obj.LarPtr {
    return larva_obj.NIL
}

func (self *LarObj_list) Method_add_1(obj larva_obj.LarPtr) larva_obj.LarPtr {
    self.l = append(self.l, obj)
    return self.To_lar_ptr()
}

func (self *LarObj_list) Method_len_0() larva_obj.LarPtr {
    return larva_obj.LarPtr{M_int : int64(len(self.l))}
}

func (self *LarObj_list) Method___mul(obj larva_obj.LarPtr) larva_obj.LarPtr {
    n := obj.As_int()
    if n < 0 {
        larva_exc.Lar_panic_string(fmt.Sprintf("list mul by %v", n))
    }
    old_len := int64(len(self.l))
    new_l := make([]larva_obj.LarPtr, old_len * n)
    for i := int64(0); i < n; i ++ {
        for j := int64(0); j < old_len; j++ {
            new_l[i * old_len + j] = self.l[j]
        }
    }
    self.l = new_l
    return self.To_lar_ptr()
}

func (self *LarObj_list) Method___get_item(k larva_obj.LarPtr) larva_obj.LarPtr {
    idx := k.As_int()
    curr_len := int64(len(self.l))
    if idx < 0 {
        idx += curr_len
    }
    if idx < 0 || idx >= curr_len {
        larva_exc.Lar_panic_string(fmt.Sprintf("list index out of range %v", idx))
    }
    return self.l[idx]
}

func (self *LarObj_list) Method___set_item(k, v larva_obj.LarPtr) larva_obj.LarPtr {
    idx := k.As_int()
    curr_len := int64(len(self.l))
    if idx < 0 {
        idx += curr_len
    }
    if idx < 0 || idx >= curr_len {
        larva_exc.Lar_panic_string(fmt.Sprintf("list index out of range %v", idx))
    }
    self.l[idx] = v
    return larva_obj.NIL
}

//range

type LarObj_range struct {
    larva_obj.LarObjBase
    curr int64
    stop int64
    step int64
}

func NewLarObj_range() *LarObj_range {
    o := new(LarObj_range)
    o.This = o
    o.Type_name = "__builtins.range"
    return o
}

func NewLarObj_range_1(stop larva_obj.LarPtr) larva_obj.LarPtr {
    o := NewLarObj_range()
    o.Method___init_1(stop)
    return o.To_lar_ptr()
}

func NewLarObj_range_2(start, stop larva_obj.LarPtr) larva_obj.LarPtr {
    o := NewLarObj_range()
    o.Method___init_2(start, stop)
    return o.To_lar_ptr()
}

func NewLarObj_range_3(start, stop, step larva_obj.LarPtr) larva_obj.LarPtr {
    o := NewLarObj_range()
    o.Method___init_3(start, stop, step)
    return o.To_lar_ptr()
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

func (self *LarObj_range) Method___init_1(stop larva_obj.LarPtr) larva_obj.LarPtr {
    return self.init(0, stop.As_int(), 1)
}

func (self *LarObj_range) Method___init_2(start, stop larva_obj.LarPtr) larva_obj.LarPtr {
    return self.init(start.As_int(), stop.As_int(), 1)
}

func (self *LarObj_range) Method___init_3(start, stop, step larva_obj.LarPtr) larva_obj.LarPtr {
    return self.init(start.As_int(), stop.As_int(), step.As_int())
}

func (self *LarObj_range) Method_iter_new_0() larva_obj.LarPtr {
    return self.To_lar_ptr()
}

func (self *LarObj_range) Method_iter_end_0() larva_obj.LarPtr {
    if self.step > 0 {
        return larva_obj.Lar_bool_from_bool(self.stop <= self.curr)
    }
    return larva_obj.Lar_bool_from_bool(self.stop >= self.curr)
}

func (self *LarObj_range) Method_iter_get_item_0() larva_obj.LarPtr {
    return larva_obj.LarPtr{M_int : self.curr}
}

func (self *LarObj_range) Method_iter_next_0() larva_obj.LarPtr {
    if self.step > 0 {
        if self.stop <= self.curr {
            larva_exc.Lar_panic_string("range iter ended")
        }
        distance := self.stop - self.curr
        if distance > 0 && distance < self.step {
            self.curr = self.stop
        } else {
            self.curr += self.step
        }
    } else {
        if self.stop >= self.curr {
            larva_exc.Lar_panic_string("range iter ended")
        }
        distance := self.curr - self.stop
        if distance > 0 && distance < -self.step {
            self.curr = self.stop
        } else {
            self.curr += self.step
        }
    }
    return larva_obj.NIL
}
