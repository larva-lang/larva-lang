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
}
