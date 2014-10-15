import java.util.Arrays;

//列表类型
public final class LarObjList extends LarSeqObj
{
    private static final int MAX_SIZE = Integer.MIN_VALUE >>> 1; //最大元素个数

    private LarObj[] m_list;
    private long[] m_list_int;

    LarObjList()
    {
        m_list = null;
        m_list_int = new long[8];
        m_len = 0; //用m_len来记录实际长度
    }

    LarObjList(int hint_size) throws Exception
    {
        this();
        adjust_size(hint_size);
    }

    LarObjList(LarObj obj) throws Exception
    {
        this();
        extend(obj);
    }

    private void extend(LarObj obj) throws Exception
    {
        for (LarObj iter = obj.meth_iterator(); iter.meth_has_next().op_bool();)
        {
            meth_add(iter.meth_next());
        }
    }

    private void adjust_size(int hint_size) throws Exception
    {
        if (hint_size < 0 || hint_size > MAX_SIZE)
        {
            throw new Exception("list大小超限");
        }
        int size = m_list == null ? m_list_int.length : m_list.length;
        if (size >= hint_size)
        {
            return;
        }
        while (size < hint_size)
        {
            size <<= 1;
        }
        if (m_list == null)
        {
            long[] new_list_int = new long[size];
            for (int i = 0; i < m_len; ++ i)
            {
                new_list_int[i] = m_list_int[i];
            }
            m_list_int = new_list_int;
        }
        else
        {
            LarObj[] new_list = new LarObj[size];
            for (int i = 0; i < m_len; ++ i)
            {
                new_list[i] = m_list[i];
            }
            m_list = new_list;
        }
    }
    
    private void list_int_2_list()
    {
        m_list = new LarObj[m_list_int.length];
        for (int i = 0; i < m_len; ++ i)
        {
            m_list[i] = new LarObjInt(m_list_int[i]);
        }
        m_list_int = null;
    }

    public LarObjList init_item(LarObj obj) throws Exception
    {
        meth_add(obj);
        return this;
    }
    public LarObjList init_item(long n) throws Exception
    {
        meth_add(n);
        return this;
    }

    public String get_type_name()
    {
        return "list";
    }

    public LarObj seq_get_item(int index) throws Exception
    {
        return m_list == null ? new LarObjInt(m_list_int[index]) : m_list[index];
    }
    public long seq_get_item_int(int index) throws Exception
    {
        return m_list == null ? m_list_int[index] : m_list[index].as_int();
    }

    public void seq_set_item(int index, LarObj obj) throws Exception
    {
        if (m_list == null)
        {
            if (obj instanceof LarObjInt)
            {
                m_list_int[index] = ((LarObjInt)obj).m_value;
                return;
            }
            list_int_2_list();
        }
        m_list[index] = obj;
    }
    public void seq_set_item(int index, long n) throws Exception
    {
        if (m_list == null)
        {
            m_list_int[index] = n;
        }
        else
        {
            m_list[index] = new LarObjInt(n);
        }
    }

    public LarObj seq_get_slice(int start, int end, int step) throws Exception
    {
        LarObjList list = new LarObjList();
        if (m_list == null)
        {
            if (step > 0)
            {
                while (start < end)
                {
                    list.meth_add(m_list_int[start]);
                    start += step;
                }
            }
            else
            {
                while (start > end)
                {
                    list.meth_add(m_list_int[start]);
                    start += step;
                }
            }
        }
        else
        {
            if (step > 0)
            {
                while (start < end)
                {
                    list.meth_add(m_list[start]);
                    start += step;
                }
            }
            else
            {
                while (start > end)
                {
                    list.meth_add(m_list[start]);
                    start += step;
                }
            }
        }
        return list;
    }

    public LarObj op_add(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjList)
        {
            //列表连接
            LarObjList list = (LarObjList)obj;
            LarObjList new_list = new LarObjList(m_len + list.m_len);
            for (int i = 0; i < m_len; ++ i)
            {
                if (m_list == null)
                {
                    new_list.meth_add(m_list_int[i]);
                }
                else
                {
                    new_list.meth_add(m_list[i]);
                }
            }
            for (int i = 0; i < list.m_len; ++ i)
            {
                if (list.m_list == null)
                {
                    new_list.meth_add(list.m_list_int[i]);
                }
                else
                {
                    new_list.meth_add(list.m_list[i]);
                }
            }
            return new_list;
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_inplace_add(LarObj obj) throws Exception
    {
        //+=运算，相当于将obj中的元素都添加过来
        extend(obj);
        return this; //根据增量赋值运算规范，返回自身
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        long times = obj.as_int();
        if (times < 0)
        {
            throw new Exception("list乘以负数");
        }
        if (times == 0)
        {
            return new LarObjList();
        }
        if (MAX_SIZE / times < m_len) //这个判断要考虑溢出，不能m_len * times > MAX_SIZE
        {
            throw new Exception("list大小超限");
        }
        LarObjList new_list = new LarObjList(m_len * (int)times);
        for (; times > 0; -- times)
        {
            for (int i = 0; i < m_len; ++ i)
            {
                if (m_list == null)
                {
                    new_list.meth_add(m_list_int[i]);
                }
                else
                {
                    new_list.meth_add(m_list[i]);
                }
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
        if (m_list == null)
        {
            for (int i = 0; i < m_len; ++ i)
            {
                if (obj.op_eq(m_list_int[i]))
                {
                    return true;
                }
            }
        }
        else
        {
            for (int i = 0; i < m_len; ++ i)
            {
                if (m_list[i].op_eq(obj))
                {
                    return true;
                }
            }
        }
        return false;
    }
    public boolean op_contain(long n) throws Exception
    {
        if (m_list == null)
        {
            for (int i = 0; i < m_len; ++ i)
            {
                if (m_list_int[i] == n)
                {
                    return true;
                }
            }
        }
        else
        {
            for (int i = 0; i < m_len; ++ i)
            {
                if (m_list[i].op_eq(n))
                {
                    return true;
                }
            }
        }
        return false;
    }

    public LarObj meth_add(LarObj obj) throws Exception
    {
        if (m_len == (m_list == null ? m_list_int.length : m_list.length))
        {
            adjust_size(m_len + 1);
        }
        if (m_list == null)
        {
            if (obj instanceof LarObjInt)
            {
                m_list_int[m_len] = ((LarObjInt)obj).m_value;
                ++ m_len;
                return this;
            }
            list_int_2_list();
        }
        m_list[m_len] = obj;
        ++ m_len;
        return this;
    }

    public LarObj meth_add(long n) throws Exception
    {
        if (m_list == null)
        {
            if (m_len == m_list_int.length)
            {
                adjust_size(m_len + 1);
            }
            m_list_int[m_len] = n;
            ++ m_len;
            return this;
        }
        if (m_len == m_list.length)
        {
            adjust_size(m_len + 1);
        }
        m_list[m_len] = new LarObjInt(n);
        ++ m_len;
        return this;
    }

    //懒得考虑qsort的太多因素，直接用shell了，序列是Sedgewick的
    static final int[] INC_LIST = new int[]{
        1073643521, 603906049, 268386305, 150958081, 67084289, 37730305, 16764929, 9427969, 4188161, 2354689, 1045505,
        587521, 260609, 146305, 64769, 36289, 16001, 8929, 3905, 2161, 929, 505, 209, 109, 41, 19, 5, 1};
    public LarObj meth_sort() throws Exception
    {
        if (m_list == null)
        {
            Arrays.sort(m_list_int, 0, m_len);
            return this;
        }
        for (int inc_idx = 0; inc_idx < INC_LIST.length; ++ inc_idx)
        {
            int inc = INC_LIST[inc_idx];
            for (int i = inc; i < m_len; ++ i)
            {
                LarObj tmp = m_list[i];
                int j;
                for (j = i; j >= inc; j -= inc)
                {
                    if (m_list[j - inc].op_cmp(tmp) <= 0)
                    {
                        break;
                    }
                    m_list[j] = m_list[j - inc];
                }
                m_list[j] = tmp;
            }
        }
        return this;
    }
    
    public LarObj meth_pop() throws Exception
    {
        if (m_len > 0)
        {
            -- m_len;
            if (m_list == null)
            {
                return new LarObjInt(m_list_int[m_len]);
            }
            LarObj obj = m_list[m_len];
            m_list[m_len] = null;
            return obj;
        }
        throw new Exception("从空list中pop");
    }
}
