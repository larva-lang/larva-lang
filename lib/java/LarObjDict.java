//字典类型，hash表实现
public final class LarObjDict extends LarObj
{
    private static final LarObj DUMMY = new LarObj();
    private static final LarObj INT_TAG = new LarObj();

    private static final class LarObjDictIterator extends LarObj
    {
        private LarObjDict m_dict;
        private long m_version;
        private int m_index;
        
        LarObjDictIterator(LarObjDict dict)
        {
            m_dict = dict;
            m_version = m_dict.m_version;
            m_index = -1;
            next_index();
        }
        
        private void next_index()
        {
            for (++ m_index; m_index < m_dict.m_key_list.length; ++ m_index)
            {
                LarObj key = m_dict.m_key_list[m_index];
                if (key != null && key != LarObjDict.DUMMY)
                {
                    return;
                }
            }
        }
        
        public LarObj meth_has_next() throws Exception
        {
            if (m_version != m_dict.m_version)
            {
                throw new Exception("dict迭代器失效");
            }
            return m_index < m_dict.m_key_list.length ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj meth_next() throws Exception
        {
            if (m_version != m_dict.m_version)
            {
                throw new Exception("dict迭代器失效");
            }
            LarObj key = m_dict.m_key_list[m_index];
            if (key == LarObjDict.INT_TAG)
            {
                key = new LarObjInt(m_dict.m_key_list_int[m_index]);
            }
            next_index();
            return key;
        }
    }

    private LarObj[] m_key_list;
    private long[] m_key_list_int;
    private LarObj[] m_value_list;
    private long[] m_value_list_int;
    private int m_count;
    private long m_version;

    LarObjDict()
    {
        m_key_list = new LarObj[8];
        m_key_list_int = new long[8];
        m_value_list = null;
        m_value_list_int = new long[8];
        m_count = 0;
        m_version = 0;
    }

    private int get_entry_index(LarObj[] list, long[] list_int, LarObj key) throws Exception
    {
        if (key instanceof LarObjInt)
        {
            return get_entry_index(list, list_int, ((LarObjInt)key).m_value);
        }
        //从hash表中查找key，如查不到则返回一个插入空位
        /*
        hash表算法简述：
        采用开放定址hash，表大小为2的幂，利用位运算代替求余数
        这种情况下探测步长为奇数即可遍历整张表，证明：
        设表大小为n，步长为i，则从任意位置开始，若经过k步第一次回到原点，则i*k被n整除
        最小的k为n/gcd(n,i)，则若要令k=n，i必须和n互质，由于n是2的幂，因此i选奇数即可
        */
        int mask = list.length - 1;
        long hash = key.op_hash();
        int h = (int)(hash + (hash >>> 32));
        int start = (h + (h >> 4)) & mask;
        int step = h | 1;
        int first_dummy_index = -1;
        for (int index = (start + step) & mask; index != start; index = (index + step) & mask)
        {
            LarObj entry = list[index];
            if (entry == null)
            {
                //结束查找
                return first_dummy_index == -1 ? index : first_dummy_index;
            }
            if (entry == DUMMY)
            {
                if (first_dummy_index == -1)
                {
                    //记录第一个dummy
                    first_dummy_index = index;
                }
                continue;
            }
            if (entry == INT_TAG ? key.op_eq(list_int[index]) : entry.op_eq(key))
            {
                return index;
            }
        }
        //运气差，整张表都没有null
        if (first_dummy_index != -1)
        {
            return first_dummy_index;
        }
        throw new Exception("内部错误：dict被填满");
    }
    private int get_entry_index(LarObj[] list, long[] list_int, long key) throws Exception
    {
        //针对key是int的特化版本，算法说明见原版本代码
        int mask = list.length - 1;
        int h = (int)(key + (key >>> 32));
        int start = (h + (h >> 4)) & mask;
        int step = h | 1;
        int first_dummy_index = -1;
        for (int index = (start + step) & mask; index != start; index = (index + step) & mask)
        {
            LarObj entry = list[index];
            if (entry == null)
            {
                //结束查找
                return first_dummy_index == -1 ? index : first_dummy_index;
            }
            if (entry == DUMMY)
            {
                if (first_dummy_index == -1)
                {
                    //记录第一个dummy
                    first_dummy_index = index;
                }
                continue;
            }
            if (entry == INT_TAG)
            {
                if (list_int[index] == key)
                {
                    return index;
                }
            }
            else
            {
                if (entry.op_eq(key))
                {
                    return index;
                }
            }
        }
        //运气差，整张表都没有null
        if (first_dummy_index != -1)
        {
            return first_dummy_index;
        }
        throw new Exception("内部错误：dict被填满");
    }

    private void rehash() throws Exception
    {
        //如果可能，扩大hash表
        int size = m_key_list.length <= 1 << 24 ? m_key_list.length << 4 : m_key_list.length << 1; //新表大小为原先16或2倍
        if (size < 0)
        {
            //表大小已经是最大了，分情况处理
            if (m_count < m_key_list.length - 1)
            {
                //还没有满
                return;
            }
            throw new Exception("dict大小超限");
        }
        LarObj[] new_key_list = new LarObj[size];
        long[] new_key_list_int = new long[size];
        LarObj[] new_value_list = m_value_list == null ? null : new LarObj[size];
        long[] new_value_list_int = m_value_list_int == null ? null : new long[size];
        for (int i = 0; i < m_key_list.length; ++ i)
        {
            LarObj key = m_key_list[i];
            if (key == null || key == DUMMY)
            {
                continue;
            }
            int index = (key == INT_TAG ? get_entry_index(new_key_list, new_key_list_int, m_key_list_int[i]) :
                                          get_entry_index(new_key_list, new_key_list_int, key));
            new_key_list[index] = key;
            new_key_list_int[index] = m_key_list_int[i];
            if (new_value_list != null)
            {
                new_value_list[index] = m_value_list[i];
            }
            else
            {
                new_value_list_int[index] = m_value_list_int[i];
            }
        }
        m_key_list = new_key_list;
        m_key_list_int = new_key_list_int;
        m_value_list = new_value_list;
        m_value_list_int = new_value_list_int;
        ++ m_version;
    }

    public LarObjDict init_item(long key, long value) throws Exception
    {
        op_set_item(key, value);
        return this;
    }
    public LarObjDict init_item(long key, LarObj value) throws Exception
    {
        op_set_item(key, value);
        return this;
    }
    public LarObjDict init_item(LarObj key, long value) throws Exception
    {
        op_set_item(key, value);
        return this;
    }
    public LarObjDict init_item(LarObj key, LarObj value) throws Exception
    {
        op_set_item(key, value);
        return this;
    }
    
    public String get_type_name()
    {
        return "dict";
    }

    public boolean op_bool() throws Exception
    {
        return m_count != 0;
    }

    public long op_len() throws Exception
    {
        return m_count;
    }

    public LarObj op_get_item(LarObj key) throws Exception
    {
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            throw new Exception("dict中找不到元素：" + key.op_str());
        }
        return m_value_list == null ? new LarObjInt(m_value_list_int[index]) : m_value_list[index];
    }
    public LarObj op_get_item(long key) throws Exception
    {
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            throw new Exception("dict中找不到元素：" + key);
        }
        return m_value_list == null ? new LarObjInt(m_value_list_int[index]) : m_value_list[index];
    }
    public long op_get_item_int(LarObj key) throws Exception
    {
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            throw new Exception("dict中找不到元素：" + key.op_str());
        }
        return m_value_list == null ? m_value_list_int[index] : m_value_list[index].as_int();
    }
    public long op_get_item_int(long key) throws Exception
    {
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            throw new Exception("dict中找不到元素：" + key);
        }
        return m_value_list == null ? m_value_list_int[index] : m_value_list[index].as_int();
    }

    private void set_key(int index, LarObj key)
    {
        if (key instanceof LarObjInt)
        {
            m_key_list[index] = INT_TAG;
            m_key_list_int[index] = ((LarObjInt)key).m_value;
        }
        else
        {
            m_key_list[index] = key;
        }
    }
    private void set_key(int index, long key)
    {
        m_key_list[index] = INT_TAG;
        m_key_list_int[index] = key;
    }
    private void value_list_int_2_value_list()
    {
        m_value_list = new LarObj[m_key_list.length];
        for (int i = 0; i < m_key_list.length; ++ i)
        {
            LarObj entry = m_key_list[i];
            if (entry != null && entry != DUMMY)
            {
                m_value_list[i] = new LarObjInt(m_value_list_int[i]);
            }
        }
        m_value_list_int = null;
    }
    private void set_value(int index, LarObj value)
    {
        if (m_value_list == null)
        {
            if (value instanceof LarObjInt)
            {
                m_value_list_int[index] = ((LarObjInt)value).m_value;
                return;
            }
            value_list_int_2_value_list();
        }
        m_value_list[index] = value;
    }
    private void set_value(int index, long value)
    {
        if (m_value_list == null)
        {
            m_value_list_int[index] = value;
        }
        else
        {
            m_value_list[index] = new LarObjInt(value);
        }
    }
    public void op_set_item(LarObj key, LarObj value) throws Exception
    {
        if (m_count >= m_key_list.length / 2)
        {
            //装载率太高
            rehash();
        }
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            //新元素
            set_key(index, key);
            set_value(index, value);
            ++ m_count;
            ++ m_version;
        }
        else
        {
            set_value(index, value);
        }
    }
    public void op_set_item(long key, LarObj value) throws Exception
    {
        if (m_count >= m_key_list.length / 2)
        {
            //装载率太高
            rehash();
        }
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            //新元素
            set_key(index, key);
            set_value(index, value);
            ++ m_count;
            ++ m_version;
        }
        else
        {
            set_value(index, value);
        }
    }
    public void op_set_item(LarObj key, long value) throws Exception
    {
        if (m_count >= m_key_list.length / 2)
        {
            //装载率太高
            rehash();
        }
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            //新元素
            set_key(index, key);
            set_value(index, value);
            ++ m_count;
            ++ m_version;
        }
        else
        {
            set_value(index, value);
        }
    }
    public void op_set_item(long key, long value) throws Exception
    {
        if (m_count >= m_key_list.length / 2)
        {
            //装载率太高
            rehash();
        }
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            //新元素
            set_key(index, key);
            set_value(index, value);
            ++ m_count;
            ++ m_version;
        }
        else
        {
            set_value(index, value);
        }
    }

    public boolean op_contain(LarObj key) throws Exception
    {
        LarObj entry = m_key_list[get_entry_index(m_key_list, m_key_list_int, key)];
        return entry != null && entry != DUMMY;
    }

    public LarObj meth_iterator() throws Exception
    {
        return new LarObjDictIterator(this);
    }

    public LarObj meth_get(LarObj key) throws Exception
    {
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            return LarBuiltin.NIL;
        }
        return m_value_list == null ? new LarObjInt(m_value_list_int[index]) : m_value_list[index];
    }
    
    public LarObj meth_pop(LarObj key) throws Exception
    {
        int index = get_entry_index(m_key_list, m_key_list_int, key);
        LarObj entry = m_key_list[index];
        if (entry == null || entry == DUMMY)
        {
            throw new Exception("dict中找不到元素：" + key.op_str());
        }
        LarObj ret;
        if (m_value_list == null)
        {
            ret = new LarObjInt(m_value_list_int[index]);
        }
        else
        {
            ret = m_value_list[index];
            m_value_list[index] = null;
        }
        m_key_list[index] = DUMMY;
        -- m_count;
        ++ m_version;
        return ret;
    }
}
