#include <iostream>
#include <time.h>
#include <string.h>

using namespace std;

struct Record
{
    Record *PtrComp;
    int Discr;
    int EnumComp;
    int IntComp;
    char StringComp[32];

    Record()
    {
        PtrComp = NULL;
        Discr = 0;
        EnumComp = 0;
        IntComp = 0;
        //StringComp = NULL;
    }

    Record(const Record *p)
    {
        *this = *p;
    }
};

static const int LOOPS = 50000000;

static const int Ident1 = 1;
static const int Ident2 = 2;
static const int Ident3 = 3;
static const int Ident4 = 4;
static const int Ident5 = 5;

static int IntGlob = 0;
static bool BoolGlob = false;
static char Char1Glob = '\0';
static char Char2Glob = '\0';
static int Array1Glob[51];
static int Array2Glob[51][51];

static Record *PtrGlb = NULL;
static Record *PtrGlbNext = NULL;

static bool Func3(int EnumParIn)
{
    int EnumLoc = EnumParIn;
    if (EnumLoc == Ident3)
    {
        return true;
    }
    return false;
}

static int Func1(char CharPar1, char CharPar2);

static bool Func2(char *StrParI1, char *StrParI2)
{
    int IntLoc = 1;
    char CharLoc = '\0';
    while (IntLoc <= 1)
    {
        if (Func1(StrParI1[IntLoc], StrParI2[IntLoc + 1]) == Ident1)
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
        if (strcmp(StrParI1, StrParI2) > 0)
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

static int Func1(char CharPar1, char CharPar2)
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

static void Proc8(int Array1Par[51], int Array2Par[51][51], int IntParI1, int IntParI2)
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

static int Proc7(int IntParI1, int IntParI2)
{
    int IntLoc = IntParI1 + 2;
    int IntParOut = IntParI2 + IntLoc;
    return IntParOut;
}

static int Proc6(int EnumParIn)
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

static void Proc5()
{
    Char1Glob = 'A';
    BoolGlob = false;
}

static void Proc4()
{
    bool BoolLoc = Char1Glob == 'A';
    BoolLoc = BoolLoc || BoolGlob;
    Char2Glob = 'B';
}

static Record *Proc3(Record *PtrParOut)
{
    if (PtrGlb != NULL)
    {
        PtrParOut = PtrGlb->PtrComp;
    }
    else
    {
        IntGlob = 100;
    }
    PtrGlb->IntComp = Proc7(10, IntGlob);
    return PtrParOut;
}

static int Proc2(int IntParIO)
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

static Record *Proc1(Record *PtrParIn)
{
    Record *NextRecord = new Record(PtrGlb);
    PtrParIn->PtrComp = NextRecord;
    PtrParIn->IntComp = 5;
    NextRecord->IntComp = PtrParIn->IntComp;
    delete NextRecord->PtrComp;
    NextRecord->PtrComp = PtrParIn->PtrComp;
    NextRecord->PtrComp = Proc3(NextRecord->PtrComp);
    if (NextRecord->Discr == Ident1)
    {
        NextRecord->IntComp = 6;
        NextRecord->EnumComp = Proc6(PtrParIn->EnumComp);
        NextRecord->PtrComp = PtrGlb->PtrComp;
        NextRecord->IntComp = Proc7(NextRecord->IntComp, 10);
    }
    else
    {
        PtrParIn = new Record(NextRecord);
    }
    NextRecord->PtrComp = NULL;
    return PtrParIn;
}

static void Proc0()
{
    PtrGlbNext = new Record();
    PtrGlb = new Record();
    PtrGlb->PtrComp = PtrGlbNext;
    PtrGlb->Discr = Ident1;
    PtrGlb->EnumComp = Ident3;
    PtrGlb->IntComp = 40;
    strcpy(PtrGlb->StringComp, "DHRYSTONE PROGRAM, SOME STRING");
    char String1Loc[32];
    strcpy(String1Loc, "DHRYSTONE PROGRAM, 1'ST STRING");
    Array2Glob[8][7] = 10;

    for (int i = 0; i < LOOPS; ++ i)
    {
        Proc5();
        Proc4();
        int IntLoc1 = 2;
        int IntLoc2 = 3;
        char String2Loc[32];
        strcpy(String2Loc, "DHRYSTONE PROGRAM, 2'ND STRING");
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
        Record *NewPtrGlb = Proc1(PtrGlb);
        if (PtrGlb != NewPtrGlb)
        {
            delete PtrGlb;
            PtrGlb = NewPtrGlb;
        }
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

int main(int argc, char *argv[])
{
    double ts = (double)clock() / CLOCKS_PER_SEC;
    Proc0();
    double te = (double)clock() / CLOCKS_PER_SEC;
    double tm = te - ts;
    cout << "Time used: " << tm << " sec" << endl;
    cout << "This machine benchmarks at " << LOOPS / tm << " CppStones/second" << endl;
}
