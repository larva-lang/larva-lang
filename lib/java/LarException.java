/*
内置异常类集合
*/
public final class LarException extends Exception
{
    public LarObj m_obj;

    LarException(LarObj obj)
    {
        m_obj = obj;
    }

    //具体的异常，LarObjException是基类，其余都是它的子类
    public static class LarObjException extends LarObj
    {
        public LarObj m_obj = new LarObjStr("");
        
        LarObjException(String s)
        {
            m_obj = new LarObjStr(s);
        }
        LarObjException(LarObj obj)
        {
            m_obj = obj;
        }
        
        public String get_type_name()
        {
            return "Exception";
        }

        public String op_str() throws Exception
        {
            return get_type_name() + "[" + m_obj.op_str() + "]";
        }
    }

    public static class LarObjIndexError extends LarObjException
    {
        LarObjIndexError(String s)
        {
            super(s);
        }
        LarObjIndexError(LarObj obj)
        {
            super(obj);
        }
        
        public String get_type_name()
        {
            return "IndexError";
        }
    }
    public static class LarObjValueError extends LarObjException
    {
        LarObjValueError(String s)
        {
            super(s);
        }
        LarObjValueError(LarObj obj)
        {
            super(obj);
        }
        
        public String get_type_name()
        {
            return "ValueError";
        }
    }
    public static class LarObjAssertionError extends LarObjException
    {
        LarObjAssertionError(String s)
        {
            super(s);
        }
        LarObjAssertionError(LarObj obj)
        {
            super(obj);
        }
        
        public String get_type_name()
        {
            return "AssertionError";
        }
    }
}
