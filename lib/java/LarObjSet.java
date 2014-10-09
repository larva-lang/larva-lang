//集合类型，hash表实现
public final class LarObjSet extends LarObj
{
    private static final class Entry
    {
        private LarObj m_key;
        private long m_key_int;

        Entry()
        {
        }

        Entry(LarObj key)
        {
            set_key(key);
        }

        LarObj get_key()
        {
            if (m_key == null)
            {
                return new LarObjInt(m_key_int);
            }
            return m_key;
        }
        void set_key(LarObj key)
        {
            if (key instanceof LarObjInt)
            {
                m_key = null;
                m_key_int = ((LarObjInt)key).m_value;
            }
            else
            {
                m_key = key;
            }
        }
    }

    private static final Entry DUMMY = new Entry();

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
                Entry entry = m_set.m_list[m_index];
                if (entry != null && entry != LarObjSet.DUMMY)
                {
                    return;
                }
            }
        }
        
        public LarObj meth_has_next() throws Exception
        {
            if (m_version != m_set.m_version)
            {
                throw new Exception("set迭代器失效");
            }
            return m_index < m_set.m_list.length ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj meth_next() throws Exception
        {
            if (m_version != m_set.m_version)
            {
                throw new Exception("set迭代器失效");
            }
            LarObj key = m_set.m_list[m_index].get_key();
            next_index();
            return key;
        }
    }

    private Entry[] m_list;
    private int m_count;
    private long m_version;

    LarObjSet()
    {
        m_list = new Entry[8];
        m_count = 0;
        m_version = 0;
    }

    private int get_entry_index(Entry[] list, LarObj key) throws Exception
    {
        if (key instanceof LarObjInt)
        {
            return get_entry_index(list, ((LarObjInt)key).m_value);
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
            Entry entry = list[index];
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
            if (entry.get_key().op_eq(key))
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
    private int get_entry_index(Entry[] list, long key) throws Exception
    {
        //get_entry_index(Entry[] list, LarObj key)针对key是int的特化版本，算法说明见原版本代码
        int mask = list.length - 1;
        int h = LarObjInt.hash(key);
        int start = (h + (h >> 4)) & mask;
        int step = h | 1;
        int first_dummy_index = -1;
        for (int index = (start + step) & mask; index != start; index = (index + step) & mask)
        {
            Entry entry = list[index];
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
            if (entry.m_key == null)
            {
                if (entry.m_key_int == key)
                {
                    return index;
                }
            }
            else
            {
                /*
                表中的key非int，一般来说这个分支很少走到，new一个对象效率也能接受
                当然后面可以给LarObj增加boolean op_eq(long)这种特化版本
                */
                if (entry.m_key.op_eq(new LarObjInt(key)))
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
        throw new Exception("内部错误：set被填满");
    }

    private void rehash() throws Exception
    {
        //如果可能，扩大hash表
        int size = m_list.length <= 1 << 24 ? m_list.length << 4 : m_list.length << 1; //新表大小为原先16或2倍
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
        Entry[] new_list = new Entry[size];
        for (int i = 0; i < m_list.length; ++ i)
        {
            Entry entry = m_list[i];
            if (entry == null || entry == DUMMY)
            {
                continue;
            }
            int index = entry.m_key == null ? get_entry_index(new_list, entry.m_key_int) : get_entry_index(new_list, entry.m_key);
            new_list[index] = entry;
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

    public long op_len() throws Exception
    {
        return m_count;
    }

    public boolean op_contain(LarObj key) throws Exception
    {
        Entry entry = m_list[get_entry_index(m_list, key)];
        return entry != null && entry != DUMMY;
    }

    public LarObj meth_add(LarObj key) throws Exception
    {
        if (m_count >= m_list.length / 2)
        {
            //装载率太高
            rehash();
        }
        int index = get_entry_index(m_list, key);
        Entry entry = m_list[index];
        if (entry == null || entry == DUMMY)
        {
            //新元素
            m_list[index] = new Entry(key);
            ++ m_count;
            ++ m_version;
        }
        return this;
    }

    public LarObj meth_iterator() throws Exception
    {
        return new LarObjSetIterator(this);
    }

}
