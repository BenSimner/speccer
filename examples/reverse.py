#!/usr/bin/env python3
from speccer import *
from typing import T, List

def is_sorted(xs: List[T]) -> bool:
    '''Returns True if 'xs' is sorted ascending, O(nlgn)
    '''
    return list(sorted(xs)) == xs

def prop_sortedReversed():
    '''a List of int's is sorted when reversed

    (obviously False, to test output)
    '''
    return forall(List[int],
                  lambda xs: assertThat(is_sorted, list(reversed(xs))))

if __name__ == '__main__':
    spec(3, prop_sortedReversed)

'''
Sample Output:

>> spec(3, prop_sortedReversed)
......E
========================================
Failure after 7 call(s)
In Property `prop_sortedReversed`
----------------------------------------
Found Counterexample:
prop_sortedReversed:FORALL(List[int]) ->
 xs=[-1, 0]

Reason:
 is_sorted([0, -1]) is false

FAIL.
'''
