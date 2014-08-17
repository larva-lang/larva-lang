//整数类型
public final class LarObjInt extends LarObj
{
    public final long m_value; //因为其它地方计算要直接用，就public

    LarObjInt(long value)
    {
        m_value = value;
    }
    
    LarObjInt(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            try
            {
                m_value = Long.parseLong(((LarObjStr)obj).m_value);
            }
            catch (NumberFormatException exc)
            {
                throw new Exception("字符串无法转为整数：'" + obj.op_str() + "'");
            }
            return;
        }
        if (obj instanceof LarObjFloat)
        {
            double value = ((LarObjFloat)obj).m_value;
            if (value < Long.MIN_VALUE || value > Long.MAX_VALUE)
            {
                throw new Exception("浮点数过大，无法转为整数：" + value);
            }
            m_value = (long)value;
            return;
        }
        m_value = obj.op_int();
    }

    LarObjInt(LarObj arg_str, LarObj arg_radix) throws Exception
    {
        if (!(arg_str instanceof LarObjStr))
        {
            throw new Exception("指定进制转换为int类型时，参数需为str类型");
        }
        String s = ((LarObjStr)arg_str).m_value;
        long radix = arg_radix.op_int();
        if (radix == 0)
        {
            //根据实际情况来解析
            if (s.length() == 0)
            {
                throw new Exception("空字符串无法转为整数");
            }
            String exc_info = "字符串无法转为整数：'" + s + "'";
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
                m_value = Long.parseLong(sign + s);
                return;
            }
            if (s.length() == 1)
            {
                //字符串是"0"或"-0"
                m_value = 0;
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
                m_value = Long.parseLong(s, (int)radix);
            }
            catch (NumberFormatException exc)
            {
                throw new Exception(exc_info);
            }
            return;
        }
        //其余情况利用系统的实现
        if (radix < Character.MIN_RADIX || radix > Character.MAX_RADIX)
        {
            throw new Exception("非法的进制：" + radix);
        }
        try
        {
            m_value = Long.parseLong(s, (int)radix);
        }
        catch (NumberFormatException exc)
        {
            throw new Exception("字符串无法以" + radix + "进制转为整数：'" + s + "'");
        }
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
