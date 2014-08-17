//元组类型
public final class LarObjTuple extends LarObj
{
    //元组的迭代器
    private static final class LarObjTupleIterator extends LarObj
    {
        private LarObj[] m_list;
        private int m_index;

        LarObjTupleIterator(LarObj[] list)
        {
            m_list = list;
            m_index = 0;
        }

        public LarObj f_has_next() throws Exception
        {
            return m_index < m_list.length ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj f_next() throws Exception
        {
            LarObj obj = m_list[m_index];
            ++ m_index;
            return obj;
        }
    }

    private final LarObj[] m_list;
    private int m_hash;

    public static LarObjTuple from_var_arg(LarObj ...list)
    {
        return new LarObjTuple(list);
    }

    private LarObjTuple(LarObj[] list)
    {
        m_list = list;
        m_hash = -1;
    }

    LarObjTuple(int count)
    {
        m_list = new LarObj[count];
        m_hash = -1;
    }

    public String get_type_name()
    {
        return "tuple";
    }

    public boolean op_bool() throws Exception
    {
        return m_list.length != 0;
    }

    public int op_len() throws Exception
    {
        return m_list.length;
    }
    public int op_hash() throws Exception
    {
        if (m_hash == -1)
        {
            m_hash = 0;
            for (int i = 0; i < m_list.length; ++ i)
            {
                m_hash = m_hash * 7 + m_list[i].op_hash();
            }
            if (m_hash == -1)
            {
                m_hash = 0;
            }
        }
        return m_hash;
    }

    //列表下标操作，允许负索引
    public LarObj op_get_item(LarObj arg_index) throws Exception
    {
        long index = arg_index.op_int();
        if (index < 0)
        {
            index += m_list.length;
        }
        if (index < 0 || index >= m_list.length)
        {
            throw new Exception("tuple索引越界");
        }
        return m_list[(int)index];
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjTuple)
        {
            //元组连接
            LarObjTuple t = (LarObjTuple)obj;
            LarObjTuple new_t = new LarObjTuple(m_list.length + t.m_list.length);
            int index = 0;
            for (int i = 0; i < m_list.length; ++ i)
            {
                new_t.m_list[index] = m_list[i];
                ++ index;
            }
            for (int i = 0; i < t.m_list.length; ++ i)
            {
                new_t.m_list[index] = t.m_list[i];
                ++ index;
            }
            return new_t;
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        long times = obj.op_int();
        if (times < 0)
        {
            throw new Exception("tuple乘以负数");
        }
        if (times == 0)
        {
            return new LarObjTuple(0);
        }
        if (Integer.MAX_VALUE / times < m_list.length)
        {
            throw new Exception("tuple大小超限");
        }
        LarObjTuple new_t = new LarObjTuple(m_list.length * (int)times);
        int index = 0;
        for (; times > 0; -- times)
        {
            for (int i = 0; i < m_list.length; ++ i)
            {
                new_t.m_list[index] = m_list[i];
                ++ index;
            }
        }
        return new_t;
    }
    public LarObj op_reverse_mul(LarObj obj) throws Exception
    {
        return op_mul(obj); //交换律
    }

    public boolean op_contain(LarObj obj) throws Exception
    {
        for (int i = 0; i < m_list.length; ++ i)
        {
            if (m_list[i].op_eq(obj))
            {
                return true;
            }
        }
        return false;
    }
    public boolean op_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjTuple)
        {
            LarObj[] list = ((LarObjTuple)obj).m_list;
            if (m_list.length != list.length)
            {
                return false;
            }
            for (int i = 0; i < m_list.length; ++ i)
            {
                if (!m_list[i].op_eq(list[i]))
                {
                    return false;
                }
            }
            return true;
        }
        return obj.op_reverse_eq(this);
    }
    public int op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjTuple)
        {
            LarObj[] list = ((LarObjTuple)obj).m_list;
            for (int i = 0; i < m_list.length && i < list.length; ++ i)
            {
                int r = m_list[i].op_cmp(list[i]);
                if (r != 0)
                {
                    return r;
                }
            }
            if (m_list.length > list.length)
            {
                return 1;
            }
            if (m_list.length < list.length)
            {
                return -1;
            }
            return 0;
        }
        return obj.op_reverse_cmp((LarObj)this);
    }

    public LarObj f_iterator() throws Exception
    {
        return new LarObjTupleIterator(m_list);
    }
}
