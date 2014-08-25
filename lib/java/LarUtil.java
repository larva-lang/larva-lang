/*
一些底层函数和接口
*/
public final class LarUtil
{
    public static LarObj[] make_array(LarObj ...a)
    {
        return a;
    }

    public static LarObj[] unpack_seq(LarObj seq, int n) throws Exception
    {
        LarObj[] a = new LarObj[n];
        LarObj iter = seq.f_iterator();
        for (int i = 0; i < n; ++ i)
        {
            if (!iter.f_has_next().op_bool())
            {
                throw new Exception("unpack序列长度不足：需要" + n + "，得到" + i);
            }
            a[i] = iter.f_next();
        }
        if (iter.f_has_next().op_bool())
        {
            throw new Exception("unpack序列过长，需要" + n);
        }
        return a;
    }
}
