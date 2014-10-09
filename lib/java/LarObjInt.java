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

    public long as_int() throws Exception
    {
        return m_value;
    }

    public long to_int() throws Exception
    {
        return m_value;
    }
    public double to_float() throws Exception
    {
        return (double)m_value;
    }

    public boolean op_bool() throws Exception
    {
        return m_value != 0;
    }
    public String op_str()
    {
        return "" + m_value;
    }

    public long op_hash() throws Exception
    {
        return m_value;
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
    public LarObj op_add(long n) throws Exception
    {
        return new LarObjInt(m_value + n);
    }
    public LarObj op_reverse_add(long n) throws Exception
    {
        return new LarObjInt(n + m_value);
    }
    public LarObj op_inplace_add(long n) throws Exception
    {
        return this.op_add(n);
    }
    public LarObj op_sub(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value - ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_sub(this);
    }
    public LarObj op_sub(long n) throws Exception
    {
        return new LarObjInt(m_value - n);
    }
    public LarObj op_reverse_sub(long n) throws Exception
    {
        return new LarObjInt(n - m_value);
    }
    public LarObj op_inplace_sub(long n) throws Exception
    {
        return this.op_sub(n);
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value * ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_mul(this);
    }
    public LarObj op_mul(long n) throws Exception
    {
        return new LarObjInt(m_value * n);
    }
    public LarObj op_reverse_mul(long n) throws Exception
    {
        return new LarObjInt(n * m_value);
    }
    public LarObj op_inplace_mul(long n) throws Exception
    {
        return this.op_mul(n);
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
    public LarObj op_div(long n) throws Exception
    {
        if (n == 0)
        {
            throw new Exception("被零除");
        }
        return new LarObjInt(m_value / n);
    }
    public LarObj op_reverse_div(long n) throws Exception
    {
        if (m_value == 0)
        {
            throw new Exception("被零除");
        }
        return new LarObjInt(n / m_value);
    }
    public LarObj op_inplace_div(long n) throws Exception
    {
        return this.op_div(n);
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
    public LarObj op_mod(long n) throws Exception
    {
        if (n == 0)
        {
            throw new Exception("被零除");
        }
        return new LarObjInt(m_value % n);
    }
    public LarObj op_reverse_mod(long n) throws Exception
    {
        if (m_value == 0)
        {
            throw new Exception("被零除");
        }
        return new LarObjInt(n % m_value);
    }
    public LarObj op_inplace_mod(long n) throws Exception
    {
        return this.op_mod(n);
    }

    public LarObj op_and(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value & ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_and(this);
    }
    public LarObj op_and(long n) throws Exception
    {
        return new LarObjInt(m_value & n);
    }
    public LarObj op_reverse_and(long n) throws Exception
    {
        return new LarObjInt(n & m_value);
    }
    public LarObj op_inplace_and(long n) throws Exception
    {
        return this.op_and(n);
    }
    public LarObj op_or(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value | ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_or(this);
    }
    public LarObj op_or(long n) throws Exception
    {
        return new LarObjInt(m_value | n);
    }
    public LarObj op_reverse_or(long n) throws Exception
    {
        return new LarObjInt(n | m_value);
    }
    public LarObj op_inplace_or(long n) throws Exception
    {
        return this.op_or(n);
    }
    public LarObj op_xor(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjInt(m_value ^ ((LarObjInt)obj).m_value);
        }
        return obj.op_reverse_xor(this);
    }
    public LarObj op_xor(long n) throws Exception
    {
        return new LarObjInt(m_value ^ n);
    }
    public LarObj op_reverse_xor(long n) throws Exception
    {
        return new LarObjInt(n ^ m_value);
    }
    public LarObj op_inplace_xor(long n) throws Exception
    {
        return this.op_xor(n);
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
    public LarObj op_shl(long n) throws Exception
    {
        if (n < 0 || n >= 64)
        {
            throw new Exception("无效的int移位位数：" + n);
        }
        return new LarObjInt(m_value << n);
    }
    public LarObj op_reverse_shl(long n) throws Exception
    {
        if (m_value < 0 || m_value >= 64)
        {
            throw new Exception("无效的int移位位数：" + m_value);
        }
        return new LarObjInt(n << m_value);
    }
    public LarObj op_inplace_shl(long n) throws Exception
    {
        return this.op_shl(n);
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
    public LarObj op_shr(long n) throws Exception
    {
        if (n < 0 || n >= 64)
        {
            throw new Exception("无效的int移位位数：" + n);
        }
        return new LarObjInt(m_value >> n);
    }
    public LarObj op_reverse_shr(long n) throws Exception
    {
        if (m_value < 0 || m_value >= 64)
        {
            throw new Exception("无效的int移位位数：" + m_value);
        }
        return new LarObjInt(n >> m_value);
    }
    public LarObj op_inplace_shr(long n) throws Exception
    {
        return this.op_shr(n);
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
    public LarObj op_ushr(long n) throws Exception
    {
        if (n < 0 || n >= 64)
        {
            throw new Exception("无效的int移位位数：" + n);
        }
        return new LarObjInt(m_value >>> n);
    }
    public LarObj op_reverse_ushr(long n) throws Exception
    {
        if (m_value < 0 || m_value >= 64)
        {
            throw new Exception("无效的int移位位数：" + m_value);
        }
        return new LarObjInt(n >>> m_value);
    }
    public LarObj op_inplace_ushr(long n) throws Exception
    {
        return this.op_ushr(n);
    }

    public boolean op_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return m_value == ((LarObjInt)obj).m_value;
        }
        return obj.op_reverse_eq(this);
    }
    public boolean op_eq(long n) throws Exception
    {
        return m_value == n;
    }
    public boolean op_reverse_eq(long n) throws Exception
    {
        return n == m_value;
    }
    public long op_cmp(LarObj obj) throws Exception
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
    public long op_cmp(long n) throws Exception
    {
        if (m_value < n)
        {
            return -1;
        }
        if (m_value > n)
        {
            return 1;
        }
        return 0;
    }
    public long op_reverse_cmp(long n) throws Exception
    {
        return -this.op_cmp(n);
    }
}
