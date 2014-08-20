//列表类型
public final class LarObjList extends LarSeqObj
{
    private static final int MAX_SIZE = Integer.MIN_VALUE >>> 1; //最大元素个数

    private LarObj[] m_list;

    LarObjList()
    {
        m_list = new LarObj[8];
        m_len = 0; //用m_len来记录实际长度
    }

    LarObjList(int hint_size) throws Exception
    {
        m_list = new LarObj[8];
        m_len = 0;
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
        for (int i = 0; i < m_len; ++ i)
        {
            new_list[i] = m_list[i];
        }
        m_list = new_list;
    }
    
    public String get_type_name()
    {
        return "list";
    }

    public LarObj seq_get_item(int index) throws Exception
    {
        return m_list[index];
    }
    public void seq_set_item(int index, LarObj obj) throws Exception
    {
        m_list[index] = obj;
    }
    public LarObj seq_get_slice(int start, int end, int step) throws Exception
    {
        LarObjList list = new LarObjList();
        if (step > 0)
        {
            while (start < end)
            {
                list.f_add(m_list[start]);
                start += step;
            }
        }
        else
        {
            while (start > end)
            {
                list.f_add(m_list[start]);
                start += step;
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
                new_list.m_list[new_list.m_len] = m_list[i];
                ++ new_list.m_len;
            }
            for (int i = 0; i < list.m_len; ++ i)
            {
                new_list.m_list[new_list.m_len] = list.m_list[i];
                ++ new_list.m_len;
            }
            return new_list;
        }
        return obj.op_reverse_add(this);
    }
    public LarObj op_inplace_add(LarObj obj) throws Exception
    {
        //+=运算，相当于将obj中的元素都添加过来
        for (LarObj iter = obj.f_iterator(); iter.f_has_next().op_bool();)
        {
            f_add(iter.f_next());
        }
        //根据增量赋值运算规范，返回自身
        return this;
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
        if (MAX_SIZE / times < m_len) //这个判断要考虑溢出，不能m_len * times > MAX_SIZE
        {
            throw new Exception("list大小超限");
        }
        LarObjList new_list = new LarObjList(m_len * (int)times);
        for (; times > 0; -- times)
        {
            for (int i = 0; i < m_len; ++ i)
            {
                new_list.m_list[new_list.m_len] = m_list[i];
                ++ new_list.m_len;
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
        for (int i = 0; i < m_len; ++ i)
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
        if (m_len == m_list.length)
        {
            adjust_size(m_len + 1);
        }
        m_list[m_len] = obj;
        ++ m_len;
        return this;
    }
}
