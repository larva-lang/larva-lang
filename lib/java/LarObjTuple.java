//元组类型
public final class LarObjTuple extends LarSeqObj
{
    private final LarObj[] m_list;
    private long m_hash;

    public static LarObjTuple from_var_arg(LarObj ...list)
    {
        return new LarObjTuple(list);
    }

    private LarObjTuple(LarObj[] list)
    {
        m_len = list.length;
        m_list = list;
        m_hash = -1;
    }

    LarObjTuple(int count)
    {
        m_len = count;
        m_list = new LarObj[count];
        m_hash = -1;
    }

    LarObjTuple(LarObj obj) throws Exception
    {
        LarObjList list = new LarObjList(obj);
        m_len = list.m_len;
        m_list = new LarObj[m_len];
        for (int i = 0; i < m_len; ++ i)
        {
            m_list[i] = list.seq_get_item(i);
        }
        m_hash = -1;
    }

    public String get_type_name()
    {
        return "tuple";
    }

    public long op_hash() throws Exception
    {
        if (m_hash == -1)
        {
            m_hash = 0;
            for (int i = 0; i < m_len; ++ i)
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

    public LarObj seq_get_item(int index) throws Exception
    {
        return m_list[index];
    }
    public LarObj seq_get_slice(int start, int end, int step) throws Exception
    {
        LarObj[] new_list = new LarObj[m_len];
        int new_len = 0;
        if (step > 0)
        {
            while (start < end)
            {
                new_list[new_len] = m_list[start];
                ++ new_len;
                start += step;
            }
        }
        else
        {
            while (start > end)
            {
                new_list[new_len] = m_list[start];
                ++ new_len;
                start += step;
            }
        }
        LarObj[] list = new LarObj[new_len];
        for (int i = 0; i < new_len; ++ i)
        {
            list[i] = new_list[i];
        }
        return new LarObjTuple(list);
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjTuple)
        {
            //元组连接
            LarObjTuple t = (LarObjTuple)obj;
            LarObjTuple new_t = new LarObjTuple(m_len + t.m_len);
            int index = 0;
            for (int i = 0; i < m_len; ++ i)
            {
                new_t.m_list[index] = m_list[i];
                ++ index;
            }
            for (int i = 0; i < t.m_len; ++ i)
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
        long times = obj.as_int();
        if (times < 0)
        {
            throw new Exception("tuple乘以负数");
        }
        if (times == 0)
        {
            return new LarObjTuple(0);
        }
        if (Integer.MAX_VALUE / times < m_len)
        {
            throw new Exception("tuple大小超限");
        }
        LarObjTuple new_t = new LarObjTuple(m_len * (int)times);
        int index = 0;
        for (; times > 0; -- times)
        {
            for (int i = 0; i < m_len; ++ i)
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
        for (int i = 0; i < m_len; ++ i)
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
            if (m_len != list.length)
            {
                return false;
            }
            for (int i = 0; i < m_len; ++ i)
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
    public long op_cmp(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjTuple)
        {
            LarObj[] list = ((LarObjTuple)obj).m_list;
            for (int i = 0; i < m_len && i < list.length; ++ i)
            {
                long r = m_list[i].op_cmp(list[i]);
                if (r != 0)
                {
                    return r;
                }
            }
            if (m_len > list.length)
            {
                return 1;
            }
            if (m_len < list.length)
            {
                return -1;
            }
            return 0;
        }
        return obj.op_reverse_cmp((LarObj)this);
    }
}
