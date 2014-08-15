//整数类型
public final class LarObjInt extends LarObj
{
    public final long m_value; //因为其它地方计算要直接用，就public

    LarObjInt(long value)
    {
        m_value = value;
    }

    public String get_type_name()
    {
        return "int";
    }

    public boolean op_bool() throws Exception
    {
        return m_value != 0;
    }
    public long op_int() throws Exception
    {
        return m_value;
    }
    public String op_str()
    {
        return "" + m_value;
    }

    public int op_hash() throws Exception
    {
        return (int)(m_value ^ (m_value >>> 32));
    }

    public LarObj op_invert() throws Exception
    {
        return new LarObjInt(~m_value);
    }
    public LarObj op_pos() throws Exception
    {
        return this;
    }
    public LarObj op_neg() throws Exception
    {
        return new LarObjInt(-m_value);
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value + ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_sub(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value - ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_sub(this);
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value * ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_mul(this);
    }
    public LarObj op_div(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value == 0)
            {
                throw new Exception("被零除");
            }
            return new LarObjInt(m_value / value);
        }
        return obj.op_reverse_div(this);
    }
    public LarObj op_mod(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value == 0)
            {
                throw new Exception("被零除");
            }
            return new LarObjInt(m_value % value);
        }
        return obj.op_reverse_mod(this);
    }

    public LarObj op_and(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value & ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_and(this);
    }
    public LarObj op_or(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value | ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_or(this);
    }
    public LarObj op_xor(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value ^ ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_xor(this);
    }
    public LarObj op_shl(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value < 0 || value >= 64)
            {
                throw new Exception("无效的int移位位数：" + value);
            }
            return new LarObjInt(m_value << value);
        }
        return obj.op_reverse_shl(this);
    }
    public LarObj op_shr(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value < 0 || value >= 64)
            {
                throw new Exception("无效的int移位位数：" + value);
            }
            return new LarObjInt(m_value >> value);
        }
        return obj.op_reverse_shr(this);
    }
    public LarObj op_ushr(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value < 0 || value >= 64)
            {
                throw new Exception("无效的int移位位数：" + value);
            }
            return new LarObjInt(m_value >>> value);
        }
        return obj.op_reverse_ushr(this);
    }

    public boolean op_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return m_value == ((LarObjInt)obj).m_value;
        }
        return obj.op_reverse_eq(this);
    }
    public int op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (m_value < value)
            {
                return -1;
            }
            if (m_value > value)
            {
                return 1;
            }
            return 0;
        }
        return obj.op_reverse_cmp(this);
    }
}
