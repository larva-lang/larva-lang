import java.math.*;

//长整数类型，无限精度
public final class LarObjLong extends LarObj
{
    private final BigInteger LONG_MAX = BigInteger.valueOf(Long.MAX_VALUE);
    private final BigInteger LONG_MIN = BigInteger.valueOf(Long.MIN_VALUE);

    private final BigInteger m_value;
    private int m_hash;

    LarObjLong(String value)
    {
        m_value = new BigInteger(value);
        m_hash = -1; //缓存hash值，-1表示还未计算
    }

    LarObjLong(BigInteger value)
    {
        m_value = value;
        m_hash = -1; //缓存hash值，-1表示还未计算
    }

    public double to_double() throws Exception
    {
        double value = m_value.doubleValue();
        if (value == Double.POSITIVE_INFINITY || value == Double.NEGATIVE_INFINITY)
        {
            throw new Exception("long过大，无法转为float值");
        }
        return value;
    }

    public String get_type_name()
    {
        return "long";
    }

    public boolean op_bool() throws Exception
    {
        return !m_value.equals(BigInteger.ZERO);
    }
    public long op_int() throws Exception
    {
        if (m_value.compareTo(LONG_MIN) < 0 || m_value.compareTo(LONG_MAX) > 0)
        {
            throw new Exception("long过大，无法转为int值");
        }
        return m_value.longValue();
    }
    public String op_str()
    {
        return m_value.toString();
    }

    public int op_hash() throws Exception
    {
        if (m_hash == -1)
        {
            m_hash = m_value.hashCode();
            if (m_hash == -1)
            {
                m_hash = 0;
            }
        }
        return m_hash;
    }

    public LarObj op_invert() throws Exception
    {
        return new LarObjLong(m_value.not());
    }
    public LarObj op_pos() throws Exception
    {
        return this;
    }
    public LarObj op_neg() throws Exception
    {
        return new LarObjLong(m_value.negate());
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return new LarObjLong(m_value.add(((LarObjLong)obj).m_value));
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(m_value.add(BigInteger.valueOf(((LarObjInt)obj).m_value)));
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_reverse_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).add(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的加法运算'+'");
    }
    public LarObj op_sub(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return new LarObjLong(m_value.subtract(((LarObjLong)obj).m_value));
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(m_value.subtract(BigInteger.valueOf(((LarObjInt)obj).m_value)));
        }
        return obj.op_reverse_sub(this);
    }
    public LarObj op_reverse_sub(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).subtract(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的减法运算'-'");
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return new LarObjLong(m_value.multiply(((LarObjLong)obj).m_value));
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(m_value.multiply(BigInteger.valueOf(((LarObjInt)obj).m_value)));
        }
        return obj.op_reverse_mul(this);
    }
    public LarObj op_reverse_mul(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).multiply(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的乘法运算'*'");
    }
    public LarObj op_div(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            BigInteger value = ((LarObjLong)obj).m_value;
            if (value.equals(BigInteger.ZERO))
            {
                throw new Exception("被零除");
            }
            return new LarObjLong(m_value.divide(value));
        }
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value == 0)
            {
                throw new Exception("被零除");
            }
            return new LarObjLong(m_value.divide(BigInteger.valueOf(value)));
        }
        return obj.op_reverse_div(this);
    }
    public LarObj op_reverse_div(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            if (m_value.equals(BigInteger.ZERO))
            {
                throw new Exception("被零除");
            }
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).divide(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的除法运算'/'");
    }
    public LarObj op_mod(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            BigInteger value = ((LarObjLong)obj).m_value;
            if (value.equals(BigInteger.ZERO))
            {
                throw new Exception("被零除");
            }
            return new LarObjLong(m_value.mod(value));
        }
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value == 0)
            {
                throw new Exception("被零除");
            }
            return new LarObjLong(m_value.mod(BigInteger.valueOf(value)));
        }
        return obj.op_reverse_mod(this);
    }
    public LarObj op_reverse_mod(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            if (m_value.equals(BigInteger.ZERO))
            {
                throw new Exception("被零除");
            }
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).mod(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的模运算'%'");
    }

    public LarObj op_and(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return new LarObjLong(m_value.and(((LarObjLong)obj).m_value));
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(m_value.and(BigInteger.valueOf(((LarObjInt)obj).m_value)));
        }
        return obj.op_reverse_and(this);
    }
    public LarObj op_reverse_and(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).and(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的按位与运算'&'");
    }
    public LarObj op_or(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return new LarObjLong(m_value.or(((LarObjLong)obj).m_value));
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(m_value.or(BigInteger.valueOf(((LarObjInt)obj).m_value)));
        }
        return obj.op_reverse_or(this);
    }
    public LarObj op_reverse_or(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).or(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的按位或运算'|'");
    }
    public LarObj op_xor(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return new LarObjLong(m_value.xor(((LarObjLong)obj).m_value));
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(m_value.xor(BigInteger.valueOf(((LarObjInt)obj).m_value)));
        }
        return obj.op_reverse_xor(this);
    }
    public LarObj op_reverse_xor(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjLong(BigInteger.valueOf(((LarObjInt)obj).m_value).xor(m_value));
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的异或运算'^'");
    }
    public LarObj op_shl(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value < 0 || value > Integer.MAX_VALUE)
            {
                throw new Exception("无效的long移位位数：" + value);
            }
            return new LarObjLong(m_value.shiftLeft((int)value));
        }
        return obj.op_reverse_shl(this);
    }
    public LarObj op_shr(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value < 0 || value > Integer.MAX_VALUE)
            {
                throw new Exception("无效的long移位位数：" + value);
            }
            return new LarObjLong(m_value.shiftRight((int)value));
        }
        return obj.op_reverse_shr(this);
    }

    public boolean op_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return m_value.equals(((LarObjLong)obj).m_value);
        }
        if (obj instanceof LarObjInt)
        {
            return m_value.equals(BigInteger.valueOf(((LarObjInt)obj).m_value));
        }
        return obj.op_reverse_eq(this);
    }
    public boolean op_reverse_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return BigInteger.valueOf(((LarObjInt)obj).m_value).equals(m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的等价判断'=='");
    }
    public int op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjLong)
        {
            return m_value.compareTo(((LarObjLong)obj).m_value);
        }
        if (obj instanceof LarObjInt)
        {
            return m_value.compareTo(BigInteger.valueOf(((LarObjInt)obj).m_value));
        }
        return obj.op_reverse_cmp(this);
    }
    public int op_reverse_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return BigInteger.valueOf(((LarObjInt)obj).m_value).compareTo(m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的比较运算");
    }
}
