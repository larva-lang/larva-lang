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
        LarObj iter = seq.meth_iterator();
        for (int i = 0; i < n; ++ i)
        {
            if (!iter.meth_has_next().op_bool())
            {
                throw new Exception("unpack序列长度不足：需要" + n + "，得到" + i);
            }
            a[i] = iter.meth_next();
        }
        if (iter.meth_has_next().op_bool())
        {
            throw new Exception("unpack序列过长，需要" + n);
        }
        return a;
    }

    public static long convert_to_int(long n) throws Exception
    {
        return n;
    }
    public static long convert_to_int(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjStr)
        {
            try
            {
                return Long.parseLong(((LarObjStr)obj).m_value);
            }
            catch (NumberFormatException exc)
            {
                throw new Exception("字符串无法转为int：'" + obj.op_str() + "'");
            }
        }
        return obj.to_int();
    }
    public static long convert_to_int(LarObj arg_str, long radix) throws Exception
    {
        if (!(arg_str instanceof LarObjStr))
        {
            throw new Exception("指定进制转换为int类型时，参数需为str类型");
        }
        String s = ((LarObjStr)arg_str).m_value;
        if (radix == 0)
        {
            //根据实际情况来解析
            if (s.length() == 0)
            {
                throw new Exception("空字符串无法转为int");
            }
            String exc_info = "字符串无法转为int：'" + s + "'";
            String sign = "";
            if (s.charAt(0) == '-')
            {
                sign = "-";
                s = s.substring(1);
            }
            if (s.length() == 0)
            {
                throw new Exception(exc_info);
            }
            if (s.charAt(0) != '0')
            {
                //十进制数
                try
                {
                    return Long.parseLong(sign + s);
                }
                catch (NumberFormatException exc)
                {
                    throw new Exception(exc_info);
                }
            }
            if (s.length() == 1)
            {
                //字符串是"0"或"-0"
                return 0;
            }
            //以0开头的字符串
            char second_char = s.charAt(1);
            if (second_char >= '0' && second_char <= '9')
            {
                s = s.substring(1);
                radix = 8;
            }
            else if (second_char == 'b' || second_char == 'B')
            {
                s = s.substring(2);
                radix = 2;
            }
            else if (second_char == 'o' || second_char == 'O')
            {
                s = s.substring(2);
                radix = 8;
            }
            else if (second_char == 'x' || second_char == 'X')
            {
                s = s.substring(2);
                radix = 16;
            }
            else
            {
                throw new Exception(exc_info);
            }
            try
            {
                return Long.parseLong(sign + s, (int)radix);
            }
            catch (NumberFormatException exc)
            {
                throw new Exception(exc_info);
            }
        }
        //其余情况利用系统的实现
        if (radix < Character.MIN_RADIX || radix > Character.MAX_RADIX)
        {
            throw new Exception("非法的进制：" + radix);
        }
        try
        {
            return Long.parseLong(s, (int)radix);
        }
        catch (NumberFormatException exc)
        {
            throw new Exception("字符串无法以" + radix + "进制转为int：'" + s + "'");
        }
    }
    public static long convert_to_int(LarObj arg_str, LarObj arg_radix) throws Exception
    {
        return convert_to_int(arg_str, arg_radix.as_int());
    }

    public static long int_div(long a, long b) throws Exception
    {
        if (b == 0)
        {
            throw new Exception("被零除");
        }
        return a / b;
    }
    public static long int_mod(long a, long b) throws Exception
    {
        if (b == 0)
        {
            throw new Exception("被零除");
        }
        return a % b;
    }
    public static long int_shl(long a, long b) throws Exception
    {
        if (b < 0 || b >= 64)
        {
            throw new Exception("无效的int移位位数：" + b);
        }
        return a << b;
    }
    public static long int_shr(long a, long b) throws Exception
    {
        if (b < 0 || b >= 64)
        {
            throw new Exception("无效的int移位位数：" + b);
        }
        return a >> b;
    }
    public static long int_ushr(long a, long b) throws Exception
    {
        if (b < 0 || b >= 64)
        {
            throw new Exception("无效的int移位位数：" + b);
        }
        return a >>> b;
    }
}
