//布尔类型
public final class LarObjBool extends LarObj
{
    private final boolean m_value;
    
    LarObjBool(boolean value)
    {
        m_value = value;
    }

    public String get_type_name()
    {
        return "bool";
    }

    public boolean op_bool() throws Exception
    {
        return m_value;
    }
    public String op_str()
    {
        return m_value ? "true" : "false";
    }

    public int op_hash() throws Exception
    {
        return m_value ? 1 : 0;
    }

    public boolean op_eq(LarObj obj) throws Exception
    {
        if (obj instanceof LarObjBool)
        {
            //bool只能和自己做全等比较
            boolean value = ((LarObjBool)obj).m_value;
            return m_value && value || !m_value && !value;
        }
        return obj.op_reverse_eq(this);
    }
}
