import java.math.BigInteger;

//长整数类型，无限精度
public final class LarObjLong extends LarObj
{
    private final BigInteger LONG_MAX = BigInteger.valueOf(Long.MAX_VALUE);
    private final BigInteger LONG_MIN = BigInteger.valueOf(Long.MIN_VALUE);

    public final BigInteger m_value;

    LarObjLong(long n)
    {
        this(BigInteger.valueOf(n));
    }

    LarObjLong(String value)
    {
        this(new BigInteger(value));
    }

    LarObjLong(BigInteger value)
    {
        m_value = value;
    }
    
    LarObjLong(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            BigInteger value;
            try
            {
                value = new BigInteger(((LarObjStr)obj).m_value);
            }
            catch (NumberFormatException exc)
            {
                throw new Exception("字符串无法转为long：'" + obj.op_str() + "'");
            }
            m_value = value;
            return;
        }
        m_value = obj.to_long();
    }

    LarObjLong(LarObj arg_str, LarObj arg_radix) throws Exception
    {
        if (!(arg_str instanceof LarObjStr))
        {
            throw new Exception("指定进制转换为long类型时，参数需为str类型");
        }
        String s = ((LarObjStr)arg_str).m_value;
        long radix = arg_radix.as_int();
        BigInteger value;
        if (radix == 0)
        {
            //根据实际情况来解析
            if (s.length() == 0)
            {
                throw new Exception("空字符串无法转为long");
            }
            String exc_info = "字符串无法转为long：'" + s + "'";
            String sign = "";
            if (s.charAt(0) == '-')
            {
                sign = "-";
                s = s.substring(1);
            }
            if (s.length() == 0)
            {
                throw new Exception(exc_info);
            }
            if (s.charAt(0) != '0')
            {
                //十进制数
                try
                {
                    value = new BigInteger(sign + s);
                }
                catch (NumberFormatException exc)
                {
                    throw new Exception(exc_info);
                }
                m_value = value;
                return;
            }
            if (s.length() == 1)
            {
                //字符串是"0"或"-0"
                m_value = BigInteger.ZERO;
                return;
            }
            //以0开头的字符串
            char second_char = s.charAt(1);
            if (second_char >= '0' && second_char <= '9')
            {
                s = s.substring(1);
                radix = 8;
            }
            else if (second_char == 'b' || second_char == 'B')
            {
                s = s.substring(2);
                radix = 2;
            }
            else if (second_char == 'o' || second_char == 'O')
            {
                s = s.substring(2);
                radix = 8;
            }
            else if (second_char == 'x' || second_char == 'X')
            {
                s = s.substring(2);
                radix = 16;
            }
            else
            {
                throw new Exception(exc_info);
            }
            try
            {
                value = new BigInteger(sign + s, (int)radix);
            }
            catch (NumberFormatException exc)
            {
                throw new Exception(exc_info);
            }
            m_value = value;
            return;
        }
        //其余情况利用系统的实现
        if (radix < Character.MIN_RADIX || radix > Character.MAX_RADIX)
        {
            throw new Exception("非法的进制：" + radix);
        }
        try
        {
            value = new BigInteger(s, (int)radix);
        }
        catch (NumberFormatException exc)
        {
            throw new Exception("字符串无法以" + radix + "进制转为long：'" + s + "'");
        }
        m_value = value;
    }

    public LarObj pow(long e) throws Exception
    {
        if (e < 0 || e > Integer.MAX_VALUE)
        {
            throw new Exception("整数幂运算的指数错误：" + e);
        }
        return new LarObjLong(m_value.pow((int)e));
    }

    public String get_type_name()
    {
        return "long";
    }

    public long as_int() throws Exception
    {
        if (m_value.compareTo(LONG_MIN) < 0 || m_value.compareTo(LONG_MAX) > 0)
        {
            throw new Exception("long过大，无法转为int值");
        }
        return m_value.longValue();
    }

    public long to_int() throws Exception
    {
        if (m_value.compareTo(LONG_MIN) < 0 || m_value.compareTo(LONG_MAX) > 0)
        {
            throw new Exception("long过大，无法转为int值");
        }
        return m_value.longValue();
    }
    public BigInteger to_long() throws Exception
    {
        return m_value;
    }
    public double to_float() throws Exception
    {
        double value = m_value.doubleValue();
        if (value == Double.POSITIVE_INFINITY || value == Double.NEGATIVE_INFINITY)
        {
            throw new Exception("long过大，无法转为float值");
        }
        return value;
    }

    public boolean op_bool() throws Exception
    {
        return !m_value.equals(BigInteger.ZERO);
    }
    public String op_str()
    {
        return m_value.toString();
    }

    public long op_hash() throws Exception
    {
        //确保在int范围内hash一致
        return m_value.longValue();
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
    public long op_cmp(LarObj obj) throws Exception
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
    public long op_reverse_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return BigInteger.valueOf(((LarObjInt)obj).m_value).compareTo(m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的比较运算");
    }
}
