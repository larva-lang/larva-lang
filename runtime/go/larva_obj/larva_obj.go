package larva_obj

var Lar_panic_string func (s string)

type LarObjIntfBase interface {
    Get_type_name() string

    OP_bool() bool
    OP_str() string

    OP_invert() LarPtr
    OP_pos() LarPtr
    OP_neg() LarPtr

    OP_get_item(k LarPtr) LarPtr
    OP_set_item(k, v LarPtr)

    OP_item_iadd(k, obj LarPtr)
    OP_item_isub(k, obj LarPtr)
    OP_item_imul(k, obj LarPtr)
    OP_item_idiv(k, obj LarPtr)
    OP_item_imod(k, obj LarPtr)

    OP_item_iand(k, obj LarPtr)
    OP_item_ior(k, obj LarPtr)
    OP_item_ixor(k, obj LarPtr)

    OP_item_ishl(k, obj LarPtr)
    OP_item_ishr(k, obj LarPtr)

    OP_get_slice(start, stop, step LarPtr) LarPtr
    OP_set_slice(start, stop, step, obj LarPtr)

    OP_inc() LarPtr
    OP_dec() LarPtr

    OP_add(obj LarPtr) LarPtr
    OP_radd(obj LarPtr) LarPtr
    OP_iadd(obj LarPtr) LarPtr
    OP_sub(obj LarPtr) LarPtr
    OP_rsub(obj LarPtr) LarPtr
    OP_isub(obj LarPtr) LarPtr
    OP_mul(obj LarPtr) LarPtr
    OP_rmul(obj LarPtr) LarPtr
    OP_imul(obj LarPtr) LarPtr
    OP_div(obj LarPtr) LarPtr
    OP_rdiv(obj LarPtr) LarPtr
    OP_idiv(obj LarPtr) LarPtr
    OP_mod(obj LarPtr) LarPtr
    OP_rmod(obj LarPtr) LarPtr
    OP_imod(obj LarPtr) LarPtr

    OP_and(obj LarPtr) LarPtr
    OP_rand(obj LarPtr) LarPtr
    OP_iand(obj LarPtr) LarPtr
    OP_or(obj LarPtr) LarPtr
    OP_ror(obj LarPtr) LarPtr
    OP_ior(obj LarPtr) LarPtr
    OP_xor(obj LarPtr) LarPtr
    OP_rxor(obj LarPtr) LarPtr
    OP_ixor(obj LarPtr) LarPtr

    OP_shl(obj LarPtr) LarPtr
    OP_rshl(obj LarPtr) LarPtr
    OP_ishl(obj LarPtr) LarPtr
    OP_shr(obj LarPtr) LarPtr
    OP_rshr(obj LarPtr) LarPtr
    OP_ishr(obj LarPtr) LarPtr

    OP_eq(obj LarPtr) bool
    OP_cmp(obj LarPtr) int64
}

/*
compiler generate code:
type LarObjIntf interface {
    LarObjIntfBase
    ...other method from compiler
}
*/
