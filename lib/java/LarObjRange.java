/*
range迭代器对象，左闭右开空间
如：LarObjRange(a,b,c)代表在区间[a,b)中从a开始步长为c的数列，根据c的正负决定是正序或倒序
*/
public final class LarObjRange extends LarObj
{
    private long m_value; //当前值
    private long m_stop; //结束值
    private long m_step; //步长
    
    LarObjRange(long stop) throws Exception
    {
        this(0, stop, 1);
    }

    LarObjRange(long start, long stop) throws Exception
    {
        this(start, stop, 1);
    }

    LarObjRange(long start, long stop, long step) throws Exception
    {
        if (step == 0)
        {
            throw new Exception("range对象步长不能为零");
        }

        m_value = start;
        m_stop = stop;
        m_step = step;
    }

    //迭代器内部实现接口，外部类型确定时使用，提高效率
    public LarObjRange iterator()
    {
        return this;
    }
    public boolean has_next()
    {
        return m_step > 0 ? m_value < m_stop : m_value > m_stop;
    }
    public long next() throws Exception
    {
        if (m_step > 0)
        {
            //正序
            if (m_value < m_stop)
            {
                long ret = m_value; //保存返回值
                /*
                value步进算法说明：
                由于long（int、short、byte都一样）运算溢出的问题，
                在value<stop时也可能stop-value<0，此时说明两者距离超过LONG_MAX，
                应该继续迭代（因为步长step不可能超过LONG_MAX）
                同理也不能先加value再判断是否大于等于stop
                */
                if (m_stop - m_value > 0 && m_stop - m_value < m_step)
                {
                    m_value = m_stop;
                }
                else
                {
                    m_value += m_step;
                }
                return ret;
            }
            throw new Exception("stop iteration");
        }
        //逆序
        if (m_value > m_stop)
        {
            //流程和算法同上
            long ret = m_value;
            if (m_value - m_stop > 0 && m_value - m_stop < -m_step)
            {
                m_value = m_stop;
            }
            else
            {
                m_value += m_step;
            }
            return ret;
        }
        throw new Exception("stop iteration");
    }

    //迭代器标准接口，直接调用上面三个
    public LarObj f_iterator() throws Exception
    {
        return this;
    }
    public LarObj f_has_next() throws Exception
    {
        return has_next() ? LarBuiltin.TRUE : LarBuiltin.FALSE;
    }
    public LarObj f_next() throws Exception
    {
        return new LarObjInt(next());
    }
}
