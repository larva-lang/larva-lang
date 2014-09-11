/*
内置模块
*/
public final class LarBuiltin
{
    public static final LarObjNil NIL = new LarObjNil();
    public static final LarObjBool TRUE = new LarObjBool(true);
    public static final LarObjBool FALSE = new LarObjBool(false);

    public static void init()
    {
    }
    
    public static LarObj f_sorted(LarObj obj) throws Exception
    {
        return (new LarObjList(obj)).f_sort();
    }

    public static LarObj f_sum(LarObj obj) throws Exception
    {
        LarObj s = new LarObjInt(0);
        for (LarObj iter = obj.f_iterator(); iter.f_has_next().op_bool();)
        {
            s = s.op_add(iter.f_next());
        }
        return s;
    }

    public static LarObj f_pow(LarObj x, LarObj y) throws Exception
    {
        if (x instanceof LarObjFloat || y instanceof LarObjFloat)
        {
            return new LarObjFloat(Math.pow(x.to_float(), y.to_float()));
        }

        if (x instanceof LarObjInt)
        {
            x = new LarObjLong(x);
        }
        else if (!(x instanceof LarObjLong))
        {
            throw new Exception("pow底数类型错误：'" + x.get_type_name() + "'");
        }
        return ((LarObjLong)x).pow(y.as_int());
    }

    public static LarObj f_max(LarObj obj) throws Exception
    {
        LarObj iter = obj.f_iterator();
        if (iter.f_has_next().op_bool())
        {
            LarObj result = iter.f_next();
            while (iter.f_has_next().op_bool())
            {
                LarObj x = iter.f_next();
                if (x.op_cmp(result) > 0)
                {
                    result = x;
                }
            }
            return result;
        }
        throw new Exception("max输入参数为空迭代");
    }

    public static LarObj f_min(LarObj obj) throws Exception
    {
        LarObj iter = obj.f_iterator();
        if (iter.f_has_next().op_bool())
        {
            LarObj result = iter.f_next();
            while (iter.f_has_next().op_bool())
            {
                LarObj x = iter.f_next();
                if (x.op_cmp(result) < 0)
                {
                    result = x;
                }
            }
            return result;
        }
        throw new Exception("min输入参数为空迭代");
    }

    public static LarObj f_bin(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjInt)
        {
            long value = ((LarObjInt)obj).m_value;
            if (value < 0)
            {
                return new LarObjStr("-" + Long.toBinaryString(-value));
            }
            else
            {
                return new LarObjStr(Long.toBinaryString(value));
            }
        }
        if (obj instanceof LarObjLong)
        {
            return new LarObjStr(((LarObjLong)obj).m_value.toString(2));
        }
        throw new Exception("bin输入参数类型非整数");
    }
}
