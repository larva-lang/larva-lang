//序列类对象，提供一些序列公用算法接口，相关序列类extends这个类
public class LarSeqObj extends LarObj
{
    private static final class LarObjSeqIterator extends LarObj
    {
        private final LarSeqObj m_obj;
        private int m_index;
        
        LarObjSeqIterator(LarSeqObj obj)
        {
            m_obj = obj;
            m_index = 0;
        }
        
        public LarObj f_has_next() throws Exception
        {
            return m_index < m_obj.m_len ? LarBuiltin.TRUE : LarBuiltin.FALSE;
        }

        public LarObj f_next() throws Exception
        {
            LarObj obj = m_obj.seq_get_item(m_index);
            ++ m_index;
            return obj;
        }
    }

    //序列子类必须实现的接口
    public LarObj seq_get_item(int index) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的下标取值运算");
    }
    public void seq_set_item(int index, LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的下标赋值运算");
    }
    public LarObj seq_get_slice(int start, int end, int step) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的分片取值运算");
    }
    public void seq_set_slice(int start, int end, int step, LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的分片赋值运算");
    }

    public int m_len;

    public boolean op_bool() throws Exception
    {
        return m_len != 0;
    }

    public int op_len() throws Exception
    {
        return m_len;
    }

    public int get_index(LarObj arg_index) throws Exception
    {
        long original_index = arg_index.as_int();
        long index = original_index;
        if (index < 0)
        {
            index += m_len;
        }
        if (index < 0 || index >= m_len)
        {
            throw new Exception("索引越界：" + original_index);
        }
        return (int)index;
    }

    public LarObj op_get_item(LarObj arg_index) throws Exception
    {
        return seq_get_item(get_index(arg_index));
    }

    public void op_set_item(LarObj arg_index, LarObj obj) throws Exception
    {
        seq_set_item(get_index(arg_index), obj);
    }

    public static final class SliceInfo
    {
        public int m_start;
        public int m_end;
        public int m_step;
        
        SliceInfo(int start, int end, int step)
        {
            m_start = start;
            m_end = end;
            m_step = step;
        }
    }
    
    public SliceInfo get_slice_info(LarObj arg_start, LarObj arg_end, LarObj arg_step) throws Exception
    {
        long step = arg_step == null ? 1 : arg_step.as_int();
        if (step == 0)
        {
            throw new Exception("分片步长为零");
        }
        long start, end;
        if (step > 0)
        {
            //正向
            if (arg_start == null)
            {
                start = 0;
            }
            else
            {
                start = arg_start.as_int();
                if (start < 0)
                {
                    start += m_len;
                    if (start < 0)
                    {
                        start = 0;
                    }
                }
                else if (start > m_len)
                {
                    start = m_len;
                }
            }
            if (arg_end == null)
            {
                end = m_len;
            }
            else
            {
                end = arg_end.as_int();
                if (end < 0)
                {
                    end += m_len;
                    if (end < 0)
                    {
                        end = 0;
                    }
                }
                else if (end > m_len)
                {
                    end = m_len;
                }
            }
            long max_step = end - start;
            if (max_step <= 0)
            {
                max_step = 1;
            }
            if (step > max_step)
            {
                step = max_step;
            }
        }
        else
        {
            //反向
            if (arg_start == null)
            {
                start = m_len - 1;
            }
            else
            {
                start = arg_start.as_int();
                if (start < 0)
                {
                    start += m_len;
                    if (start < 0)
                    {
                        start = -1;
                    }
                }
                else if (start >= m_len)
                {
                    start = m_len - 1;
                }
            }
            if (arg_end == null)
            {
                end = -1;
            }
            else
            {
                end = arg_end.as_int();
                if (end < 0)
                {
                    end += m_len;
                    if (end < 0)
                    {
                        end = -1;
                    }
                }
                else if (end >= m_len)
                {
                    end = m_len - 1;
                }
            }
            long min_step = end - start;
            if (min_step >= 0)
            {
                min_step = -1;
            }
            if (step < min_step)
            {
                step = min_step;
            }
        }
        return new SliceInfo((int)start, (int)end, (int)step);
    }
    
    public LarObj op_get_slice(LarObj arg_start, LarObj arg_end, LarObj arg_step) throws Exception
    {
        SliceInfo slice_info = get_slice_info(arg_start, arg_end, arg_step);
        return seq_get_slice(slice_info.m_start, slice_info.m_end, slice_info.m_step);
    }

    public void op_set_slice(LarObj arg_start, LarObj arg_end, LarObj arg_step, LarObj obj) throws Exception
    {
        SliceInfo slice_info = get_slice_info(arg_start, arg_end, arg_step);
        seq_set_slice(slice_info.m_start, slice_info.m_end, slice_info.m_step, obj);
    }

    public LarObj f_iterator() throws Exception
    {
        return new LarObjSeqIterator(this);
    }
}
