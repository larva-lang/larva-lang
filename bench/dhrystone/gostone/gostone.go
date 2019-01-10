package main

import (
    "time"
    "fmt"
)

const LOOPS = 50000000

type Record struct {
    PtrComp *Record
    Discr int32
    EnumComp int32
    IntComp int32
    StringComp string
}

func copyRecord(nr *Record, r *Record) {
    nr.PtrComp = r.PtrComp
    nr.Discr = r.Discr
    nr.EnumComp = r.EnumComp
    nr.IntComp = r.IntComp
    nr.StringComp = r.StringComp
}

var Ident1 int32
var Ident2 int32
var Ident3 int32
var Ident4 int32
var Ident5 int32

var IntGlob int32
var BoolGlob bool
var Char1Glob uint8
var Char2Glob uint8
var Array1Glob0 [51]int32
var Array2Glob0 [51][51]int32
var Array1Glob []int32 = Array1Glob0[:]
var Array2Glob [][51]int32 = Array2Glob0[:]

var PtrGlb *Record
var PtrGlbNext *Record

func Func3(EnumParIn int32) bool {
    EnumLoc := EnumParIn
    if EnumLoc == Ident3 {
        return true
    }
    return false
}

func Func2(StrParI1 string, StrParI2 string) bool {
    var IntLoc int32
    IntLoc = 1
    var CharLoc uint8
    CharLoc = 0
    for IntLoc <= 1 {
        if Func1(StrParI1[IntLoc], StrParI2[IntLoc + 1]) == Ident1 {
            CharLoc = 'A'
            IntLoc ++
        }
    }
    if CharLoc >= 'W' && CharLoc <= 'Z' {
        IntLoc = 7
    }
    if CharLoc == 'X' {
        return true;
    } else {
        if StrParI1 > StrParI2 {
            IntLoc += 7
            return true
        } else {
            return false
        }
    }
}

func Func1(CharPar1 uint8, CharPar2 uint8) int32 {
    CharLoc1 := CharPar1
    CharLoc2 := CharLoc1
    if CharLoc2 != CharPar2 {
        return Ident1
    } else {
        return Ident2
    }
}

func Proc8(Array1Par []int32, Array2Par [][51]int32, IntParI1 int32, IntParI2 int32) {
    var IntLoc int32
    IntLoc = IntParI1 + 5
    Array1Par[IntLoc] = IntParI2
    Array1Par[IntLoc+1] = Array1Par[IntLoc]
    Array1Par[IntLoc+30] = IntLoc
    for IntIndex := IntLoc; IntIndex <= IntLoc + 1; IntIndex ++ {
        Array2Par[IntLoc][IntIndex] = IntLoc
    }
    Array2Par[IntLoc][IntLoc - 1] ++
    Array2Par[IntLoc + 20][IntLoc] = Array1Par[IntLoc]
    IntGlob = 5
}

func Proc7(IntParI1 int32, IntParI2 int32) int32 {
    IntLoc := IntParI1 + 2
    IntParOut := IntParI2 + IntLoc
    return IntParOut
}

func Proc6(EnumParIn int32) int32 {
    var EnumParOut int32
    EnumParOut = EnumParIn
    if !Func3(EnumParIn) {
        EnumParOut = Ident4
    }
    if !(EnumParIn == Ident1) {
        EnumParOut = Ident1
    } else if EnumParIn == Ident2 {
        if IntGlob > 100 {
            EnumParOut = Ident1
        } else {
            EnumParOut = Ident4
        }
    } else if EnumParIn == Ident3 {
        EnumParOut = Ident2
    } else if EnumParIn == Ident4 {
    } else if EnumParIn == Ident5 {
        EnumParOut = Ident3
    }
    return EnumParOut
}

func Proc5() {
    Char1Glob = 'A'
    BoolGlob = false
}

func Proc4() {
    BoolLoc := Char1Glob == 'A'
    BoolLoc = BoolLoc || BoolGlob
    Char2Glob = 'B'
}

func Proc3(PtrParOut *Record) *Record {
    if PtrGlb != nil {
        PtrParOut = PtrGlb.PtrComp
    } else {
        IntGlob = 100
    }
    PtrGlb.IntComp = Proc7(10, IntGlob)
    return PtrParOut
}

func Proc2(IntParIO int32) int32 {
    IntLoc := IntParIO + 10
    var EnumLoc int32
    EnumLoc = 0
    for true {
        if Char1Glob == 'A' {
            IntLoc --
            IntParIO = IntLoc - IntGlob
            EnumLoc = Ident1
        }
        if EnumLoc == Ident1 {
            break
        }
    }
    return IntParIO
}

func Proc1(PtrParIn *Record) {
    NextRecord := PtrParIn.PtrComp
    copyRecord(NextRecord, PtrGlb)
    PtrParIn.IntComp = 5
    NextRecord.IntComp = PtrParIn.IntComp
    NextRecord.PtrComp = PtrParIn.PtrComp
    NextRecord.PtrComp = Proc3(NextRecord.PtrComp)
    if NextRecord.Discr == Ident1 {
        NextRecord.IntComp = 6
        NextRecord.EnumComp = Proc6(PtrParIn.EnumComp)
        NextRecord.PtrComp = PtrGlb.PtrComp
        NextRecord.IntComp = Proc7(NextRecord.IntComp, 10)
    } else {
        copyRecord(PtrParIn, NextRecord)
    }
}

func Proc0() {
    PtrGlbNext = new(Record)
    PtrGlb = new(Record)
    PtrGlb.PtrComp = PtrGlbNext
    PtrGlb.Discr = Ident1
    PtrGlb.EnumComp = Ident3
    PtrGlb.IntComp = 40
    PtrGlb.StringComp = "DHRYSTONE PROGRAM, SOME STRING"
    String1Loc := "DHRYSTONE PROGRAM, 1'ST STRING"
    Array2Glob[8][7] = 10

    for i := 0; i < LOOPS; i ++ {
        Proc5()
        Proc4()
        var IntLoc1 int32
        IntLoc1 = 2
        var IntLoc2 int32
        IntLoc2 = 3
        String2Loc := "DHRYSTONE PROGRAM, 2'ND STRING"
        EnumLoc := Ident2
        BoolGlob = !Func2(String1Loc, String2Loc)
        var IntLoc3 int32
        IntLoc3 = 0
        for IntLoc1 < IntLoc2 {
            IntLoc3 = 5 * IntLoc1 - IntLoc2;
            IntLoc3 = Proc7(IntLoc1, IntLoc2);
            IntLoc1 = IntLoc1 + 1;
        }
        Proc8(Array1Glob, Array2Glob, IntLoc1, IntLoc3);
        Proc1(PtrGlb);
        var CharIndex uint8;
        CharIndex = 'A';
        for CharIndex <= Char2Glob {
            if EnumLoc == Func1(CharIndex, 'C') {
                EnumLoc = Proc6(Ident1);
            }
            CharIndex ++;
        }
        IntLoc3 = IntLoc2 * IntLoc1;
        IntLoc2 = IntLoc3 / IntLoc1;
        IntLoc2 = 7 * (IntLoc3 - IntLoc2) - IntLoc1;
        IntLoc1 = Proc2(IntLoc1);
    }
}

func main() {
    Ident1 = 1
    Ident2 = 2
    Ident3 = 3
    Ident4 = 4
    Ident5 = 5
    
    IntGlob = 0
    BoolGlob = false
    Char1Glob = 0
    Char2Glob = 0
    for i := 0; i < 51; i ++ {
        Array1Glob[i] = 0
        for j := 0; j < 51; j ++ {
            Array2Glob[i][j] = 0
        }
    }
    PtrGlb = nil
    PtrGlbNext = nil

    ts := time.Now()
    Proc0()
    tm := time.Now().Sub(ts)
    float_tm := float64(tm) / 1e9
    fmt.Printf("Time Used %f\n", float_tm)
    fmt.Printf("This machine benchmarks at %f GoStones/second\n", LOOPS / float_tm);
}
