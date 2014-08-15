public final class LarObjNil extends LarObj
{
    public String get_type_name()
    {
        return "nil";
    }

    public boolean op_bool() throws Exception
    {
        return false;
    }
    public String op_str()
    {
        return "nil";
    }

    public int op_hash() throws Exception
    {
        return 0;
    }

    public boolean op_eq(LarObj obj) throws Exception
    {
        return obj instanceof LarObjNil;
    }
    public boolean op_reverse_eq(LarObj obj) throws Exception
    {
        return false;
    }
}
