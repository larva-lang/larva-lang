//集合类型，hash表实现
public final class LarObjSet extends LarObj
{
    private static final LarObj DUMMY = new LarObj();

    private static final class LarObjSetIterator extends LarObj
    {
        private LarObjSet m_set;
        private long m_version;
        private int m_index;
        
        LarObjSetIterator(LarObjSet set)
        {
            m_set = set;
            m_version = m_set.m_version;
            m_index = -1;
            next_index();
        }
        
        private void next_index()
        {
            for (++ m_index; m_index < m_set.m_list.length; ++ m_index)
            {
                LarObj obj = m_set.m_list[m_index];
                if (obj != null && obj != LarObjSet.DUMMY)
                {
                    return;
                }
            }
        }
        
        public LarObj f_has_next() throws Exception
        {
            if (m_version != m_set.m_version)
            {
                throw new Exception("set迭代器失效");
            }
            return m_index < m_set.m_list.length ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj f_next() throws Exception
        {
            if (m_version != m_set.m_version)
            {
                throw new Exception("set迭代器失效");
            }
            LarObj obj = m_set.m_list[m_index];
            next_index();
            return obj;
        }
    }

    private LarObj[] m_list;
    private int m_count;
    private long m_version;

    LarObjSet()
    {
        m_list = new LarObj[8];
        m_count = 0;
        m_version = 0;
    }

    LarObjSet(LarObj obj) throws Exception
    {
        this();
        for (LarObj iter = obj.f_iterator(); iter.f_has_next().op_bool();)
        {
            f_add(iter.f_next());
        }
    }

    private int get_obj_index(LarObj[] list, LarObj obj) throws Exception
    {
        //从hash表中查找obj，如查不到则返回一个插入空位，算法同dict
        int mask = list.length - 1;
        int h = obj.op_hash();
        int start = h & mask;
        int step = h | 1;
        int first_dummy_index = -1;
        for (int index = (start + step) & mask; index != start; index = (index + step) & mask)
        {
            LarObj iter_obj = list[index];
            if (iter_obj == null)
            {
                //结束查找
                return first_dummy_index == -1 ? index : first_dummy_index;
            }
            if (iter_obj == DUMMY)
            {
                if (first_dummy_index == -1)
                {
                    //记录第一个dummy
                    first_dummy_index = index;
                }
                continue;
            }
            if (iter_obj.op_eq(obj))
            {
                return index;
            }
        }
        //运气差，整张表都没有null
        if (first_dummy_index != -1)
        {
            return first_dummy_index;
        }
        throw new Exception("内部错误：set被填满");
    }

    private void rehash() throws Exception
    {
        //如果可能，扩大hash表
        int size = m_list.length << 1; //新表大小为原先2倍
        if (size < 0)
        {
            //表大小已经是最大了，分情况处理
            if (m_count < m_list.length - 1)
            {
                //还没有满
                return;
            }
            throw new Exception("set大小超限");
        }
        LarObj[] new_list = new LarObj[size];
        for (int i = 0; i < m_list.length; ++ i)
        {
            LarObj obj = m_list[i];
            if (obj == null || obj == DUMMY)
            {
                continue;
            }
            int index = get_obj_index(new_list, obj);
            new_list[index] = obj;
        }
        m_list = new_list;
        ++ m_version;
    }

    public String get_type_name()
    {
        return "set";
    }

    public boolean op_bool() throws Exception
    {
        return m_count != 0;
    }

    public int op_len() throws Exception
    {
        return m_count;
    }

    public boolean op_contain(LarObj obj) throws Exception
    {
        LarObj obj_in_set = m_list[get_obj_index(m_list, obj)];
        return obj_in_set != null && obj_in_set != DUMMY;
    }

    public LarObj f_add(LarObj obj) throws Exception
    {
        if (m_count >= m_list.length / 2)
        {
            //装载率太高
            rehash();
        }
        int index = get_obj_index(m_list, obj);
        LarObj obj_in_set = m_list[index];
        if (obj_in_set == null || obj_in_set == DUMMY)
        {
            //新元素
            m_list[index] = obj;
            ++ m_count;
            ++ m_version;
        }
        return this;
    }

    public LarObj f_iterator() throws Exception
    {
        return new LarObjSetIterator(this);
    }
}
