/*
LarBaseObj，包含大多数内置操作和方法的接口
这样编译器就不用自己生成LarObj的大部分内容了
编译期才能得知的接口由编译器自己生成LarObj
继承关系：
LarObj extends LarBaseObj
LarObjXXX extends LarObj
*/
public class LarBaseObj
{
    //LarBaseObj和LarObj不允许出现实例化，如果调用到这个方法，则是编译器和环境出现bug，预警用
    public String get_type_name()
    {
        return "object";
    }

    /*
    隐式类型转换，仅限内建或扩展的数字类型
    数字类型最好都内置，统一管理
    as_xxx接口用于严格的类型转换，只允许整数、浮点数等大类内部进行无损转换
    to_xxx允许数字类型进行有损转换
    */
    public long as_int() throws Exception
    {
        throw new Exception("类型'" + get_type_name() + "'非整数");
    }
    public double as_float() throws Exception
    {
        throw new Exception("类型'" + get_type_name() + "'非浮点数");
    }

    public long to_int() throws Exception
    {
        throw new Exception("类型'" + get_type_name() + "'无法隐式转换为int");
    }
    public double to_float() throws Exception
    {
        throw new Exception("类型'" + get_type_name() + "'无法隐式转换为float");
    }

    /*
    op_*是运算操作或内部实现需要的对象方法
    */

    //内部类型转换
    public boolean op_bool() throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的bool转换");
    }
    public String op_str()
    {
        return "<" + get_type_name() + "的实例>";
    }

    //其它内部运算
    public int op_len() throws Exception
    {
        throw new Exception("类型'" + get_type_name() + "'无长度");
    }
    public int op_hash() throws Exception
    {
        throw new Exception("类型'" + get_type_name() + "'不可hash");
    }

    //单目运算符
    public LarObj op_invert() throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的取反运算'~'");
    }
    public LarObj op_pos() throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的取正运算'+'");
    }
    public LarObj op_neg() throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的取负运算'-'");
    }

    //下标运算
    public LarObj op_get_item(LarObj key) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的下标取值运算");
    }
    public void op_set_item(LarObj key, LarObj value) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的下标赋值运算");
    }

    //分片运算
    public LarObj op_get_slice(LarObj start, LarObj end, LarObj step) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的分片取值运算");
    }
    public void op_set_slice(LarObj start, LarObj end, LarObj step, LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + get_type_name() + "'的分片赋值运算");
    }

    /*
    反向运算：
    二元运算的op_reverse_*是反向运算方法，若一个正向运算未实现，则尝试进行反向运算
    例如：对于a+b，会调用到a.op_add(b)，若没有实现或在op_add实现中发现类型不符，
    则调用b.op_reverse_add(a)，但需约定：反向运算方法若行不通不可反过来调用正向运算方法，防止无限递归
    主要为一些方便性，比如list的扩展，[nil]*100和100*[nil]均可
    二元运算中，最终执行哪个操作数的方法，称以此操作数为主导
    基本实现原则：以使用频率低的类型主导，以提高效率，即减少常用类型方法中的instanceof判断
    方法中多个instanceof判断也应合理安排判断顺序，将常用的放前面
    
    增量赋值运算：
    二元运算的op_inplace_*是增量赋值运算方法，实现+=之类的操作，下述以+=为例说明，其余类同
    对于大部分运算而言，a+=b和a=a+b的区别仅在于表达式a只被求值一次，这个由编译器保证，因此直接调用普通运算方法
    某些对象的+=运算和+运算含义不同，例如list：
    l+=[4,5,6]和l=l+[4,5,6]不同，前者相当于在l末尾追加内容，后者则是生成一个新列表再赋值给l
    为兼容以上两种情况，a+=b会被编译成a=a.op_inplace_add(b)，
    前者会直接调用op_add，后者则在自实现op_inplace_add时返回this即可
    注：没有实现反向增量赋值运算，感觉没有必要，看python里面也没有，不过一时也想不出禁止它的理由，以后再说了
    */

    //算术运算
    public LarObj op_add(LarObj obj) throws Exception
    {
        return obj.op_reverse_add((LarObj)this);
    }
    public LarObj op_reverse_add(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的加法运算'+'");
    }
    public LarObj op_inplace_add(LarObj obj) throws Exception
    {
        return op_add(obj);
    }
    public LarObj op_sub(LarObj obj) throws Exception
    {
        return obj.op_reverse_sub((LarObj)this);
    }
    public LarObj op_reverse_sub(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的减法运算'-'");
    }
    public LarObj op_inplace_sub(LarObj obj) throws Exception
    {
        return op_sub(obj);
    }
    public LarObj op_mul(LarObj obj) throws Exception
    {
        return obj.op_reverse_mul((LarObj)this);
    }
    public LarObj op_reverse_mul(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的乘法运算'*'");
    }
    public LarObj op_inplace_mul(LarObj obj) throws Exception
    {
        return op_mul(obj);
    }
    public LarObj op_div(LarObj obj) throws Exception
    {
        return obj.op_reverse_div((LarObj)this);
    }
    public LarObj op_reverse_div(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的除法运算'/'");
    }
    public LarObj op_inplace_div(LarObj obj) throws Exception
    {
        return op_div(obj);
    }
    public LarObj op_mod(LarObj obj) throws Exception
    {
        return obj.op_reverse_mod((LarObj)this);
    }
    public LarObj op_reverse_mod(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的模运算'%'");
    }
    public LarObj op_inplace_mod(LarObj obj) throws Exception
    {
        return op_mod(obj);
    }

    //位运算
    public LarObj op_and(LarObj obj) throws Exception
    {
        return obj.op_reverse_and((LarObj)this);
    }
    public LarObj op_reverse_and(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的按位与运算'&'");
    }
    public LarObj op_inplace_and(LarObj obj) throws Exception
    {
        return op_and(obj);
    }
    public LarObj op_or(LarObj obj) throws Exception
    {
        return obj.op_reverse_or((LarObj)this);
    }
    public LarObj op_reverse_or(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的按位或运算'|'");
    }
    public LarObj op_inplace_or(LarObj obj) throws Exception
    {
        return op_or(obj);
    }
    public LarObj op_xor(LarObj obj) throws Exception
    {
        return obj.op_reverse_xor((LarObj)this);
    }
    public LarObj op_reverse_xor(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的异或运算'^'");
    }
    public LarObj op_inplace_xor(LarObj obj) throws Exception
    {
        return op_xor(obj);
    }
    public LarObj op_shl(LarObj obj) throws Exception
    {
        return obj.op_reverse_shl((LarObj)this);
    }
    public LarObj op_reverse_shl(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的左移运算'<<'");
    }
    public LarObj op_inplace_shl(LarObj obj) throws Exception
    {
        return op_shl(obj);
    }
    public LarObj op_shr(LarObj obj) throws Exception
    {
        return obj.op_reverse_shr((LarObj)this);
    }
    public LarObj op_reverse_shr(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的右移运算'>>'");
    }
    public LarObj op_inplace_shr(LarObj obj) throws Exception
    {
        return op_shr(obj);
    }
    public LarObj op_ushr(LarObj obj) throws Exception
    {
        return obj.op_reverse_ushr((LarObj)this);
    }
    public LarObj op_reverse_ushr(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的无符号右移运算'>>>'");
    }
    public LarObj op_inplace_ushr(LarObj obj) throws Exception
    {
        return op_ushr(obj);
    }

    /*
    比较运算，larva内部强制规定返回类型，及其必须满足其对应的一些定律，
    即：
    1 返回类型，contain和eq为boolean，cmp为int，小于、大于、等于分别对应返回值为负数、0、正数
    2 ne使用eq取非来实现，cmp返回0/非0和eq返回true/false原则上需对应，但一般情况下编译器会尽量选择eq方法，
      而不是判断cmp结果是否为0
    3 交换律，a==b当且仅当b==a，a<b当且仅当b>a，a<=b当且仅当b>=a
    4 not in使用contain取非实现
    */
    public boolean op_contain(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的'in'运算");
    }
    public boolean op_eq(LarObj obj) throws Exception
    {
        return obj.op_reverse_eq((LarObj)this);
    }
    public boolean op_reverse_eq(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的等价判断'=='");
    }
    public int op_cmp(LarObj obj) throws Exception
    {
        return obj.op_reverse_cmp((LarObj)this);
    }
    public int op_reverse_cmp(LarObj obj) throws Exception
    {
        throw new Exception("未实现类型'" + obj.get_type_name() + "'和'" + get_type_name() + "'的比较运算");
    }

    /*
    内部类型默认有的方法，如果代码中出现，则可能被LarObj覆盖，这个没有关系
    写在这里主要是防止某些方法的隐式调用，比如迭代器的
    */
    public LarObj f_add(LarObj obj) throws Exception
    {
        throw new Exception("找不到类型'" + get_type_name() + "'的方法：add，1个参数");
    }
    public LarObj f_ord_at(LarObj obj) throws Exception
    {
        throw new Exception("找不到类型'" + get_type_name() + "'的方法：ord_at，1个参数");
    }
    public LarObj f_iterator() throws Exception
    {
        throw new Exception("找不到类型'" + get_type_name() + "'的方法：iterator，0个参数");
    }
    public LarObj f_has_next() throws Exception
    {
        throw new Exception("找不到类型'" + get_type_name() + "'的方法：has_next，0个参数");
    }
    public LarObj f_next() throws Exception
    {
        throw new Exception("找不到类型'" + get_type_name() + "'的方法：next，0个参数");
    }
}
