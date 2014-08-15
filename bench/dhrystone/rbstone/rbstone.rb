class Record

	attr_reader :PtrComp, :Discr, :EnumComp, :IntComp, :StringComp
	attr_writer :PtrComp, :Discr, :EnumComp, :IntComp, :StringComp

    def initialize()
        @PtrComp = nil
        @Discr = 0
        @EnumComp = 0
        @IntComp = 0
        @StringComp = nil
	end

    def assign(other)
        @PtrComp = other.PtrComp
        @Discr = other.Discr
        @EnumComp = other.EnumComp
        @IntComp = other.IntComp
        @StringComp = other.StringComp
	end

end

LOOPS = 500000

Ident1 = 1
Ident2 = 2
Ident3 = 3
Ident4 = 4
Ident5 = 5

$IntGlob = 0
$BoolGlob = FALSE
$Char1Glob = 0
$Char2Glob = 0
$Array1Glob = [0] * 51
$Array2Glob = []
for i in Range.new(1, 51)
	$Array2Glob << [0] * 51
end

$PtrGlb = nil
$PtrGlbNext = nil

def func3(enumParIn)
    enumLoc = enumParIn
    if enumLoc == Ident3
		return TRUE
	end
    return FALSE
end

def func2(strParI1, strParI2)
    intLoc = 1
    while intLoc <= 1
        if func1(strParI1[intLoc].bytes[0], strParI2[intLoc + 1].bytes[0]) == Ident1
            charLoc = 65
            intLoc += 1
		end
	end
    if charLoc >= 87 && charLoc <= 90
        intLoc = 7
	end
    if charLoc == 88
        return TRUE
    else
        if strParI1 > strParI2
            intLoc = intLoc + 7
            return TRUE
        else
            return FALSE
		end
	end
end

def func1(charPar1, charPar2)
    charLoc1 = charPar1
    charLoc2 = charLoc1
    if charLoc2 != charPar2
        return Ident1
    else
        return Ident2
	end
end

def proc8(array1Par, array2Par, intParI1, intParI2)
    intLoc = intParI1 + 5
    array1Par[intLoc] = intParI2
    array1Par[intLoc + 1] = array1Par[intLoc]
    array1Par[intLoc + 30] = intLoc
    for intIndex in [intLoc, intLoc + 1]
        array2Par[intLoc][intIndex] = intLoc
	end
    array2Par[intLoc][intLoc - 1] += 1
    array2Par[intLoc + 20][intLoc] = array1Par[intLoc]
    $IntGlob = 5
end

def proc7(intParI1, intParI2)
    intLoc = intParI1 + 2
    intParOut = intParI2 + intLoc
    return intParOut
end

def proc6(enumParIn)
    enumParOut = enumParIn
    if !func3(enumParIn)
        enumParOut = Ident4
	end
    if enumParIn == Ident1
        enumParOut = Ident1
    elsif enumParIn == Ident2
        if $IntGlob > 100
            enumParOut = Ident1
        else
            enumParOut = Ident4
		end
    elsif enumParIn == Ident3
        enumParOut = Ident2
    elsif enumParIn == Ident4
    elsif enumParIn == Ident5
        enumParOut = Ident3
	end
    return enumParOut
end

def proc5()
    $Char1Glob = 65
    $BoolGlob = FALSE
end

def proc4()
    boolLoc = $Char1Glob == 65
    boolLoc = boolLoc || $BoolGlob
    $Char2Glob = 66
end

def proc3(ptrParOut)
    if $PtrGlb != nil
        ptrParOut = $PtrGlb.PtrComp
    else
        $IntGlob = 100
	end
    $PtrGlb.IntComp = proc7(10, $IntGlob)
    return ptrParOut
end

def proc2(intParIO)
    intLoc = intParIO + 10
    while 1
        if $Char1Glob == 65
            intLoc = intLoc - 1
            intParIO = intLoc - $IntGlob
            enumLoc = Ident1
		end
        if enumLoc == Ident1
            break
		end
	end
    return intParIO
end

def proc1(ptrParIn)
    nextRecord = ptrParIn.PtrComp
	nextRecord.assign($PtrGlb)
    ptrParIn.IntComp = 5
    nextRecord.IntComp = ptrParIn.IntComp
    nextRecord.PtrComp = ptrParIn.PtrComp
    nextRecord.PtrComp = proc3(nextRecord.PtrComp)
    if nextRecord.Discr == Ident1
        nextRecord.IntComp = 6
        nextRecord.EnumComp = proc6(ptrParIn.EnumComp)
        nextRecord.PtrComp = $PtrGlb.PtrComp
        nextRecord.IntComp = proc7(nextRecord.IntComp, 10)
    else
        ptrParIn.assign(nextRecord)
	end
    return ptrParIn
end

def Proc0()
    $PtrGlbNext = Record.new()
    $PtrGlb = Record.new()
    $PtrGlb.PtrComp = $PtrGlbNext
    $PtrGlb.Discr = Ident1
    $PtrGlb.EnumComp = Ident3
    $PtrGlb.IntComp = 40
    $PtrGlb.StringComp = "DHRYSTONE PROGRAM, SOME STRING"
    string1Loc = "DHRYSTONE PROGRAM, 1'ST STRING"
    $Array2Glob[8][7] = 10

    for i in Range.new(1, LOOPS)
        proc5
        proc4
        intLoc1 = 2
        intLoc2 = 3
        string2Loc = "DHRYSTONE PROGRAM, 2'ND STRING"
        enumLoc = Ident2
        $BoolGlob = !func2(string1Loc, string2Loc)
        intLoc3 = 0
        while intLoc1 < intLoc2
            intLoc3 = 5 * intLoc1 - intLoc2
            intLoc3 = proc7(intLoc1, intLoc2)
            intLoc1 = intLoc1 + 1
		end
        proc8($Array1Glob, $Array2Glob, intLoc1, intLoc3)
        $PtrGlb = proc1($PtrGlb)
        charIndex = 65
        while charIndex <= $Char2Glob
            if enumLoc == func1(charIndex, 67)
                enumLoc = proc6(Ident1)
			end
            charIndex += 1
		end
        intLoc3 = intLoc2 * intLoc1
        intLoc2 = intLoc3 / intLoc1
        intLoc2 = 7 * (intLoc3 - intLoc2) - intLoc1
        intLoc1 = proc2(intLoc1)
	end
end

def main()
    starttime = Time.now
    Proc0()
    tm = Time.now - starttime
    puts "Time used: %f sec" % tm
    puts "This machine benchmarks at %f RbStones/second" % (LOOPS / tm)
end

main
