//浮点数类型
public final class LarObjFloat extends LarObj
{
    public final double m_value;

    LarObjFloat(double value)
    {
        //将-0.0处理为0.0
        m_value = Double.doubleToLongBits(value) == Long.MIN_VALUE ? 0.0 : value;
    }

    public String get_type_name()
    {
        return "float";
    }

    public double as_float() throws Exception
    {
        return m_value;
    }

    public long to_int() throws Exception
    {
        if (m_value < Long.MIN_VALUE || m_value > Long.MAX_VALUE)
        {
            throw new Exception("浮点数过大，无法转为int：" + m_value);
        }
        return (long)m_value;
    }
    public double to_float() throws Exception
    {
        return m_value;
    }

    public boolean op_bool() throws Exception
    {
        return m_value != 0.0;
    }
    public String op_str()
    {
        return "" + m_value;
    }

    public long op_hash() throws Exception
    {
        return Double.doubleToLongBits(m_value);
    }

    public LarObj op_pos() throws Exception
    {
        return this;
    }
    public LarObj op_neg() throws Exception
    {
        return new LarObjFloat(-m_value);
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjFloat)
        {
            return new LarObjFloat(m_value + ((LarObjFloat)obj).m_value);
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjFloat(m_value + ((LarObjInt)obj).m_value);
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjFloat(m_value + ((LarObjLong)obj).to_float());
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_reverse_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjFloat(((LarObjInt)obj).m_value + m_value);
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjFloat(((LarObjLong)obj).to_float() + m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的加法运算'+'");
    }
    public LarObj op_sub(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjFloat)
        {
            return new LarObjFloat(m_value - ((LarObjFloat)obj).m_value);
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjFloat(m_value - ((LarObjInt)obj).m_value);
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjFloat(m_value - ((LarObjLong)obj).to_float());
        }
        return obj.op_reverse_sub(this);
    }
    public LarObj op_reverse_sub(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjFloat(((LarObjInt)obj).m_value - m_value);
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjFloat(((LarObjLong)obj).to_float() - m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的减法运算'-'");
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjFloat)
        {
            return new LarObjFloat(m_value * ((LarObjFloat)obj).m_value);
        }
        if (obj instanceof LarObjInt)
        {
            return new LarObjFloat(m_value * ((LarObjInt)obj).m_value);
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjFloat(m_value * ((LarObjLong)obj).to_float());
        }
        return obj.op_reverse_mul(this);
    }
    public LarObj op_reverse_mul(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return new LarObjFloat(((LarObjInt)obj).m_value * m_value);
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjFloat(((LarObjLong)obj).to_float() * m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的乘法运算'*'");
    }
    public LarObj op_div(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjFloat)
        {
            double value = ((LarObjFloat)obj).m_value;
            if (value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(m_value / value);
        }
        if (obj instanceof LarObjInt)
        {
            double value = ((LarObjInt)obj).m_value;
            if (value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(m_value / value);
        }
        if (obj instanceof LarObjLong)
        {
            double value = ((LarObjLong)obj).to_float();
            if (value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(m_value / value);
        }
        return obj.op_reverse_div(this);
    }
    public LarObj op_reverse_div(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            if (m_value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(((LarObjInt)obj).m_value / m_value);
        }
        if (obj instanceof LarObjLong)
        {
            if (m_value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(((LarObjLong)obj).to_float() / m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的除法运算'/'");
    }
    public LarObj op_mod(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjFloat)
        {
            double value = ((LarObjFloat)obj).m_value;
            if (value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(m_value % value);
        }
        if (obj instanceof LarObjInt)
        {
            double value = ((LarObjInt)obj).m_value;
            if (value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(m_value % value);
        }
        if (obj instanceof LarObjLong)
        {
            double value = ((LarObjLong)obj).to_float();
            if (value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(m_value % value);
        }
        return obj.op_reverse_mod(this);
    }
    public LarObj op_reverse_mod(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            if (m_value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(((LarObjInt)obj).m_value % m_value);
        }
        if (obj instanceof LarObjLong)
        {
            if (m_value == 0.0)
            {
                throw new Exception("被零除");
            }
            return new LarObjFloat(((LarObjLong)obj).to_float() % m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的模运算'%'");
    }

    public boolean op_eq(LarObj obj) throws Exception
    {
        /*
        一般而言只需要直接做==比较即可，但若均为NaN值，则直接判断==结果为false，因此做bits比较
        和整数的比较，由于java的long和BigInteger自动转为double后不可能为NaN，就无需如此处理
        */
        if (obj instanceof LarObjFloat)
        {
            return Double.doubleToLongBits(m_value) == Double.doubleToLongBits(((LarObjFloat)obj).m_value);
        }
        if (obj instanceof LarObjInt)
        {
            return m_value == ((LarObjInt)obj).m_value;
        }
        if (obj instanceof LarObjLong)
        {
            return m_value == ((LarObjLong)obj).to_float();
        }
        return obj.op_reverse_eq(this);
    }
    public boolean op_reverse_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            return ((LarObjInt)obj).m_value == m_value;
        }
        if (obj instanceof LarObjLong)
        {
            return ((LarObjLong)obj).to_float() == m_value;
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的等价判断'=='");
    }
    public long op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjFloat)
        {
            double value = ((LarObjFloat)obj).m_value;
            if (m_value > value)
            {
                return 1;
            }
            if (m_value < value)
            {
                return -1;
            }
            return 0;
        }
        if (obj instanceof LarObjInt)
        {
            double value = ((LarObjInt)obj).m_value;
            if (m_value > value)
            {
                return 1;
            }
            if (m_value < value)
            {
                return -1;
            }
            return 0;
        }
        if (obj instanceof LarObjLong)
        {
            double value = ((LarObjLong)obj).to_float();
            if (m_value > value)
            {
                return 1;
            }
            if (m_value < value)
            {
                return -1;
            }
            return 0;
        }
        return obj.op_reverse_cmp(this);
    }
    public long op_reverse_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            double value = ((LarObjInt)obj).m_value;
            if (value > m_value)
            {
                return 1;
            }
            if (value < m_value)
            {
                return -1;
            }
            return 0;
        }
        if (obj instanceof LarObjLong)
        {
            double value = ((LarObjLong)obj).to_float();
            if (value > m_value)
            {
                return 1;
            }
            if (value < m_value)
            {
                return -1;
            }
            return 0;
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的比较运算");
    }
}
