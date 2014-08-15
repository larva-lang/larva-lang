//列表类型
public final class LarObjList extends LarObj
{
    //列表的迭代器
    private static final class LarObjListIterator extends LarObj
    {
        private LarObjList m_list;
        private int m_index;
        
        LarObjListIterator(LarObjList list)
        {
            m_list = list;
            m_index = 0;
        }
        
        public LarObj f_has_next() throws Exception
        {
            return m_index < m_list.m_count ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj f_next() throws Exception
        {
            LarObj obj = m_list.m_list[m_index];
            ++ m_index;
            return obj;
        }
    }

    private static final int MAX_SIZE = Integer.MIN_VALUE >>> 1; //最大元素个数

    private LarObj[] m_list;
    private int m_count;

    LarObjList()
    {
        m_list = new LarObj[8];
        m_count = 0;
    }

    LarObjList(int hint_size) throws Exception
    {
        m_list = new LarObj[8];
        m_count = 0;
        adjust_size(hint_size);
    }
    
    private void adjust_size(int hint_size) throws Exception
    {
        if (hint_size < 0 || hint_size > MAX_SIZE)
        {
            throw new Exception("list大小超限");
        }
        int size = m_list.length;
        if (size >= hint_size)
        {
            return;
        }
        while (size < hint_size)
        {
            size <<= 1;
        }
        LarObj[] new_list = new LarObj[size];
        for (int i = 0; i < m_count; ++ i)
        {
            new_list[i] = m_list[i];
        }
        m_list = new_list;
    }
    
    public String get_type_name()
    {
        return "list";
    }

    public boolean op_bool() throws Exception
    {
        return m_count != 0;
    }

    public int op_len() throws Exception
    {
        return m_count;
    }

    //列表下标操作，允许负索引
    public LarObj op_get_item(LarObj arg_index) throws Exception
    {
        long index = arg_index.op_int();
        if (index < 0)
        {
            index += m_count;
        }
        if (index < 0 || index >= m_count)
        {
            throw new Exception("list索引越界");
        }
        return m_list[(int)index];
    }
    public void op_set_item(LarObj arg_index, LarObj obj) throws Exception
    {
        long index = arg_index.op_int();
        if (index < 0)
        {
            index += m_count;
        }
        if (index < 0 || index >= m_count)
        {
            throw new Exception("list索引越界");
        }
        m_list[(int)index] = obj;
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjList)
        {
            //列表连接
            LarObjList list = (LarObjList)obj;
            LarObjList new_list = new LarObjList(m_count + list.m_count);
            for (int i = 0; i < m_count; ++ i)
            {
                new_list.m_list[new_list.m_count] = m_list[i];
                ++ new_list.m_count;
            }
            for (int i = 0; i < list.m_count; ++ i)
            {
                new_list.m_list[new_list.m_count] = list.m_list[i];
                ++ new_list.m_count;
            }
            return new_list;
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        long times = obj.op_int();
        if (times < 0)
        {
            throw new Exception("list乘以负数");
        }
        if (times == 0)
        {
            return new LarObjList();
        }
        if (MAX_SIZE / times < m_count) //这个判断要考虑溢出，不能m_count * times > MAX_SIZE
        {
            throw new Exception("list大小超限");
        }
        LarObjList new_list = new LarObjList(m_count * (int)times);
        for (; times > 0; -- times)
        {
            for (int i = 0; i < m_count; ++ i)
            {
                new_list.m_list[new_list.m_count] = m_list[i];
                ++ new_list.m_count;
            }
        }
        return new_list;
    }
    public LarObj op_reverse_mul(LarObj obj) throws Exception
    {
        return op_mul(obj); //交换律
    }

    public boolean op_contain(LarObj obj) throws Exception
    {
        for (int i = 0; i < m_count; ++ i)
        {
            if (m_list[i].op_eq(obj))
            {
                return true;
            }
        }
        return false;
    }

    public LarObj f_add(LarObj obj) throws Exception
    {
        if (m_count == m_list.length)
        {
            adjust_size(m_count + 1);
        }
        m_list[m_count] = obj;
        ++ m_count;
        return this;
    }

    public LarObj f_iterator() throws Exception
    {
        return new LarObjListIterator(this);
    }
}
