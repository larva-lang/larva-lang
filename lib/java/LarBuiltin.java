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

    //因为暂时没做内建类的编译期确定，弄个接口在这里，以后去掉
    public static LarObjRange f_range(LarObj arg_max) throws Exception
    {
        return new LarObjRange(0, arg_max.op_int(), 1);
    }
}
