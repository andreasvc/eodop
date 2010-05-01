#!/bin/sh
# remove epsilon productions such as:
#16     @275
# input:
#freq	lhs	rhs_1	...	rhs_n
#16              @275
#13      NP      DT      N
#13      NP
#1      CJT:np
#13      NP@23   DT@2    N
#16      @274    @275

#13      NP      DT      N
egrep "[a-zA-Z:]+@?[0-9]*	[a-zA-Z]+" $1
#egrep "/[a-zA-Z]+\t[a-zA-Z]+/" $1
