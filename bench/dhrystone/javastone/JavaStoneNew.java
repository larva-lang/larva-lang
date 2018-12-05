class JavaStoneNew
{
    static class Record
    {
        public Record PtrComp;
        public int Discr;
        public int EnumComp;
        public int IntComp;
        public String StringComp;

        Record()
        {
            PtrComp = null;
            Discr = 0;
            EnumComp = 0;
            IntComp = 0;
            StringComp = null;
        }

        Record(Record other)
        {
            PtrComp = other.PtrComp;
            Discr = other.Discr;
            EnumComp = other.EnumComp;
            IntComp = other.IntComp;
            StringComp = other.StringComp;
        }
    }

    static final int LOOPS = 50000000;

    static final int Ident1 = 1;
    static final int Ident2 = 2;
    static final int Ident3 = 3;
    static final int Ident4 = 4;
    static final int Ident5 = 5;

    static int IntGlob = 0;
    static boolean BoolGlob = false;
    static char Char1Glob = '\0';
    static char Char2Glob = '\0';
    static int[] Array1Glob = new int[51];
    static int[][] Array2Glob = new int[51][51];

    static Record PtrGlb = null;
    static Record PtrGlbNext = null;

    public static boolean Func3(int EnumParIn)
    {
        int EnumLoc = EnumParIn;
        if (EnumLoc == Ident3)
        {
            return true;
        }
        return false;
    }

    public static boolean Func2(String StrParI1, String StrParI2)
    {
        int IntLoc = 1;
        char CharLoc = '\0';
        while (IntLoc <= 1)
        {
            if (Func1(StrParI1.charAt(IntLoc), StrParI2.charAt(IntLoc + 1)) == Ident1)
            {
                CharLoc = 'A';
                ++ IntLoc;
            }
        }
        if (CharLoc >= 'W' && CharLoc <= 'Z')
        {
            IntLoc = 7;
        }
        if (CharLoc == 'X')
        {
            return true;
        }
        else
        {
            if (StrParI1.compareTo(StrParI2) > 0)
            {
                IntLoc += 7;
                return true;
            }
            else
            {
                return false;
            }
        }
    }

    public static int Func1(char CharPar1, char CharPar2)
    {
        int CharLoc1 = CharPar1;
        int CharLoc2 = CharLoc1;
        if (CharLoc2 != CharPar2)
        {
            return Ident1;
        }
        else
        {
            return Ident2;
        }
    }
    
    public static void Proc8(int[] Array1Par, int[][] Array2Par, int IntParI1, int IntParI2)
    {
        int IntLoc = IntParI1 + 5;
        Array1Par[IntLoc] = IntParI2;
        Array1Par[IntLoc + 1] = Array1Par[IntLoc];
        Array1Par[IntLoc + 30] = IntLoc;
        for (int IntIndex = IntLoc; IntIndex <= IntLoc + 1; ++ IntIndex)
        {
            Array2Par[IntLoc][IntIndex] = IntLoc;
        }
        ++ Array2Par[IntLoc][IntLoc - 1];
        Array2Par[IntLoc + 20][IntLoc] = Array1Par[IntLoc];
        IntGlob = 5;
    }

    public static int Proc7(int IntParI1, int IntParI2)
    {
        int IntLoc = IntParI1 + 2;
        int IntParOut = IntParI2 + IntLoc;
        return IntParOut;
    }

    public static int Proc6(int EnumParIn)
    {
        int EnumParOut = EnumParIn;
        if (!Func3(EnumParIn))
        {
            EnumParOut = Ident4;
        }
        if (!(EnumParIn == Ident1))
        {
            EnumParOut = Ident1;
        }
        else if (EnumParIn == Ident2)
        {
            if (IntGlob > 100)
            {
                EnumParOut = Ident1;
            }
            else
            {
                EnumParOut = Ident4;
            }
        }
        else if (EnumParIn == Ident3)
        {
            EnumParOut = Ident2;
        }
        else if (EnumParIn == Ident4)
        {
        }
        else if (EnumParIn == Ident5)
        {
            EnumParOut = Ident3;
        }
        return EnumParOut;
    }

    public static void Proc5()
    {
        Char1Glob = 'A';
        BoolGlob = false;
    }

    public static void Proc4()
    {
        boolean BoolLoc = Char1Glob == 'A';
        BoolLoc = BoolLoc || BoolGlob;
        Char2Glob = 'B';
    }

    public static Record Proc3(Record PtrParOut)
    {
        if (PtrGlb != null)
        {
            PtrParOut = PtrGlb.PtrComp;
        }
        else
        {
            IntGlob = 100;
        }
        PtrGlb.IntComp = Proc7(10, IntGlob);
        return PtrParOut;
    }

    public static int Proc2(int IntParIO)
    {
        int IntLoc = IntParIO + 10;
        int EnumLoc = 0;
        while (true)
        {
            if (Char1Glob == 'A')
            {
                -- IntLoc;
                IntParIO = IntLoc - IntGlob;
                EnumLoc = Ident1;
            }
            if (EnumLoc == Ident1)
            {
                break;
            }
        }
        return IntParIO;
    }

    public static Record Proc1(Record PtrParIn)
    {
        Record NextRecord = new Record(PtrGlb);
        PtrParIn.PtrComp = NextRecord;
        PtrParIn.IntComp = 5;
        NextRecord.IntComp = PtrParIn.IntComp;
        NextRecord.PtrComp = PtrParIn.PtrComp;
        NextRecord.PtrComp = Proc3(NextRecord.PtrComp);
        if (NextRecord.Discr == Ident1)
        {
            NextRecord.IntComp = 6;
            NextRecord.EnumComp = Proc6(PtrParIn.EnumComp);
            NextRecord.PtrComp = PtrGlb.PtrComp;
            NextRecord.IntComp = Proc7(NextRecord.IntComp, 10);
        }
        else
        {
            PtrParIn = new Record(NextRecord);
        }
        NextRecord.PtrComp = null;
        return PtrParIn;
    }

    public static void Proc0()
    {
        PtrGlbNext = new Record();
        PtrGlb = new Record();
        PtrGlb.PtrComp = PtrGlbNext;
        PtrGlb.Discr = Ident1;
        PtrGlb.EnumComp = Ident3;
        PtrGlb.IntComp = 40;
        PtrGlb.StringComp = "DHRYSTONE PROGRAM, SOME STRING";
        String String1Loc = "DHRYSTONE PROGRAM, 1'ST STRING";
        Array2Glob[8][7] = 10;

        for (int i = 0; i < LOOPS; ++ i)
        {
            Proc5();
            Proc4();
            int IntLoc1 = 2;
            int IntLoc2 = 3;
            String String2Loc = "DHRYSTONE PROGRAM, 2'ND STRING";
            int EnumLoc = Ident2;
            BoolGlob = !Func2(String1Loc, String2Loc);
            int IntLoc3 = 0;
            while (IntLoc1 < IntLoc2)
            {
                IntLoc3 = 5 * IntLoc1 - IntLoc2;
                IntLoc3 = Proc7(IntLoc1, IntLoc2);
                ++ IntLoc1;
            }
            Proc8(Array1Glob, Array2Glob, IntLoc1, IntLoc3);
            PtrGlb = Proc1(PtrGlb);
            char CharIndex = 'A';
            while (CharIndex <= Char2Glob)
            {
                if (EnumLoc == Func1(CharIndex, 'C'))
                {
                    EnumLoc = Proc6(Ident1);
                }
                ++ CharIndex;
            }
            IntLoc3 = IntLoc2 * IntLoc1;
            IntLoc2 = IntLoc3 / IntLoc1;
            IntLoc2 = 7 * (IntLoc3 - IntLoc2) - IntLoc1;
            IntLoc1 = Proc2(IntLoc1);
        }
    }

    public static void main(String[] argv)
    {
        long ts = System.currentTimeMillis();
        Proc0();
        double time = (System.currentTimeMillis() - ts) / 1000.0;
        System.out.println("Time used: " + time + " sec");
        System.out.println("This machine benchmarks at " + LOOPS / time + " JavaStones/second");
    }
}
