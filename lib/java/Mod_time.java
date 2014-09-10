//time模块，时间相关
public final class Mod_time
{
    public static void init()
    {
    }
    
    //获取当前unix时间，浮点数表示
    public static LarObj f_time()
    {
        return new LarObjFloat(System.currentTimeMillis() / 1000.0);
    }

    public static LarObj f_sleep(LarObj arg_sec) throws Exception
    {
        Thread.sleep((long)(arg_sec.to_float() * 1000));
        return LarBuiltin.NIL;
    }
}
