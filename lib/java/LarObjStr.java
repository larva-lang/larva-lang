//字符串对象
public final class LarObjStr extends LarObj
{
    //字符串的迭代器
    private static final class LarObjStrIterator extends LarObj
    {
        private final String m_value;
        private int m_index;
        
        LarObjStrIterator(String value)
        {
            m_value = value;
            m_index = 0;
        }
        
        public LarObj f_has_next() throws Exception
        {
            return m_index < m_value.length() ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj f_next() throws Exception
        {
            LarObj obj = new LarObjStr(m_value.substring(m_index, m_index + 1));
            ++ m_index;
            return obj;
        }
    }

    public final String m_value;
    private int m_hash;

    LarObjStr(String value)
    {
        m_value = value;
        m_hash = -1; //缓存hash值，-1表示还未计算
    }

    public String get_type_name()
    {
        return "str";
    }

    public boolean op_bool() throws Exception
    {
        return m_value.length() != 0;
    }
    public String op_str()
    {
        return m_value;
    }

    public int op_len() throws Exception
    {
        return m_value.length();
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

    public LarObj op_get_item(LarObj key) throws Exception
    {
        long index = key.op_int();
        if (index < 0)
        {
            index += m_value.length();
        }
        if (index < 0 || index >= m_value.length())
        {
            throw new Exception("str index out of range");
        }
        return new LarObjStr(m_value.substring((int)index, (int)index + 1));
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
    public int op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            return m_value.compareTo(((LarObjStr)obj).m_value);
        }
        return obj.op_reverse_cmp(this);
    }

    public LarObj f_ord_at(LarObj arg_index) throws Exception
    {
        long index = arg_index.op_int();
        if (index < 0)
        {
            index += m_value.length();
        }
        if (index < 0 || index >= m_value.length())
        {
            throw new Exception("str index out of range");
        }
        return new LarObjInt((long)m_value.charAt((int)index));
    }

    public LarObj f_iterator() throws Exception
    {
        return new LarObjStrIterator(m_value);
    }
}
