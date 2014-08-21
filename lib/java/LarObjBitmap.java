//bitmap类型
public final class LarObjBitmap extends LarSeqObj
{
    private boolean[] m_bm;

    LarObjBitmap(long size) throws Exception
    {
        if (size < 0 || size > Integer.MAX_VALUE)
        {
            throw new Exception("错误的bitmap大小：" + size);
        }
        m_len = (int)size;
        m_bm = new boolean[m_len];
    }

    public String get_type_name()
    {
        return "bitmap";
    }

    public LarObj seq_get_item(int index) throws Exception
    {
        return m_bm[index] ? LarBuiltin.TRUE : LarBuiltin.FALSE;
    }
    public void seq_set_item(int index, LarObj obj) throws Exception
    {
        if (obj instanceof LarObjBool)
        {
            m_bm[index] = ((LarObjBool)obj).m_value;
            return;
        }
        throw new Exception("bitmap元素只能为bool类型");
    }
    public void seq_set_slice(int start, int end, int step, LarObj obj) throws Exception
    {
        if (obj instanceof LarObjBool)
        {
            boolean value = ((LarObjBool)obj).m_value;
            if (step > 0)
            {
                while (start < end)
                {
                    m_bm[start] = value;
                    start += step;
                }
            }
            else
            {
                while (start > end)
                {
                    m_bm[start] = value;
                    start += step;
                }
            }
            return;
        }
        throw new Exception("bitmap元素只能为bool类型");
    }
}
