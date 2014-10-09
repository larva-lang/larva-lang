//字符串对象
public final class LarObjStr extends LarSeqObj
{
    public final String m_value;
    private long m_hash;

    LarObjStr(String value)
    {
        m_len = value.length();
        m_value = value;
        m_hash = -1; //缓存hash值，-1表示还未计算
    }

    LarObjStr(long n)
    {
        this("" + n);
    }

    LarObjStr(LarObj obj) throws Exception
    {
        this(obj.op_str());
    }

    public String get_type_name()
    {
        return "str";
    }

    public LarObj seq_get_item(int index) throws Exception
    {
        return new LarObjStr(m_value.substring(index, index + 1));
    }
    public LarObj seq_get_slice(int start, int end, int step) throws Exception
    {
        char[] new_s = new char[m_len];
        int new_len = 0;
        if (step > 0)
        {
            while (start < end)
            {
                new_s[new_len] = m_value.charAt(start);
                ++ new_len;
                start += step;
            }
        }
        else
        {
            while (start > end)
            {
                new_s[new_len] = m_value.charAt(start);
                ++ new_len;
                start += step;
            }
        }
        return new LarObjStr(new String(new_s, 0, new_len));
    }

    public String op_str()
    {
        return m_value;
    }

    public long op_hash() throws Exception
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

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            return new LarObjStr(m_value + ((LarObjStr)obj).m_value);
        }
        return obj.op_reverse_add(this);
    }

    public boolean op_contain(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            return m_value.contains(((LarObjStr)obj).m_value);
        }
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的'in'运算");
    }
    public boolean op_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            return m_value.equals(((LarObjStr)obj).m_value);
        }
        return obj.op_reverse_eq(this);
    }
    public long op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            return m_value.compareTo(((LarObjStr)obj).m_value);
        }
        return obj.op_reverse_cmp(this);
    }

    public LarObj meth_ord_at(LarObj arg_index) throws Exception
    {
        return new LarObjInt((long)m_value.charAt(get_index(arg_index)));
    }
    
    public LarObj meth_split() throws Exception
    {
        //根据whitespace分割字符串，忽略首尾空白
        LarObjList list = new LarObjList();
        int start = -1;
        for (int i = 0; i < m_len; ++ i)
        {
            char ch = m_value.charAt(i);
            if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n' || ch == 0xb/*\v*/ || ch == 0xc/*\f*/)
            {
                if (start != -1)
                {
                    //一个子串结束
                    list.meth_add(new LarObjStr(m_value.substring(start, i)));
                    start = -1;
                }
            }
            else
            {
                if (start == -1)
                {
                    //新字符串开始
                    start = i;
                }
            }
        }
        if (start != -1)
        {
            //无尾部空白，最后一个子串
            list.meth_add(new LarObjStr(m_value.substring(start)));
        }
        return list;
    }
    public LarObj meth_split(LarObj obj) throws Exception
    {
        if (!(obj instanceof LarObjStr))
        {
            throw new Exception("split参数类型为'" + obj.get_type_name() + "'，需要str");
        }
        String s = ((LarObjStr)obj).m_value;
        //根据s分割字符串
        LarObjList list = new LarObjList();
        int start = 0;
        for (;;)
        {
            int index = m_value.indexOf(s, start);
            if (index == -1)
            {
                list.meth_add(new LarObjStr(m_value.substring(start)));
                return list;
            }
            list.meth_add(new LarObjStr(m_value.substring(start, index)));
            start = index + s.length();
        }
    }
}
