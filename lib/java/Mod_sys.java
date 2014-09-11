//sys模块，系统相关
public final class Mod_sys
{
    public static LarObj g_argv = LarBuiltin.NIL;

    public static void set_argv(String[] argv) throws Exception
    {
        //java中好像拿不到命令行的启动的class或jar文件的参数，弄个nil占位
        g_argv = new LarObjList().meth_add(LarBuiltin.NIL);
        for (int i = 0; i < argv.length; ++ i)
        {
            g_argv.meth_add(new LarObjStr(argv[i]));
        }
    }
    
    public static void init()
    {
    }

    //正常退出程序
    public static LarObj f_exit() throws Exception
    {
        System.exit(0);
        return LarBuiltin.NIL;
    }

    //以exit_code为返回码退出程序
    public static LarObj f_exit(LarObj obj) throws Exception
    {
        long exit_code = obj.as_int();
        if (exit_code < Integer.MIN_VALUE || exit_code > Integer.MAX_VALUE)
        {
            throw new Exception("非法的exit返回码：" + exit_code);
        }
        System.exit((int)exit_code);
        return LarBuiltin.NIL;
    }
}
