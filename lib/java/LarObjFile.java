import java.io.*;

//文件类型
public final class LarObjFile extends LarObj
{
    private String m_file_name;
    private File m_file;

    LarObjFile(LarObj arg_file_name) throws Exception
    {
        if (!(arg_file_name instanceof LarObjStr))
        {
            throw new Exception("文件名需要一个字符串");
        }
        m_file_name = ((LarObjStr)arg_file_name).m_value;
        m_file = new File(m_file_name);
    }

    public String get_type_name()
    {
        return "file";
    }

    public String op_str()
    {
        return "<file '" + m_file_name + "'>";
    }

    public LarObj f_read_lines() throws Exception
    {
        BufferedReader reader = new BufferedReader(new FileReader(m_file));
        LarObjList list = new LarObjList();
        for (;;)
        {
            String line = reader.readLine();
            if (line == null)
            {
                return list;
            }
            list.f_add(new LarObjStr(line));
        }
    }
}
