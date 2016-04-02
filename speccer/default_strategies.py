import string
try:
    from typing import List, T
except ImportError:
    print('E: Cannot locate `typing`')
    print('E: Expected Python3.5 or greater')
    import sys
    sys.exit(1)

import logging
from .strategy import *
from . import strategy

LETTERS = string.ascii_lowercase
log = logging.getLogger('default_strategies')

class IntStrat(Strategy[int]):
    def generate(self, depth, partial=0):
        yield 0
        for i in range(1, 1+depth):
            yield i
            yield -i

class ListStrat(Strategy[List[T]]):
    def generate(self, depth, t):
        def mk_list(a: t, b: List[t]) -> List[t]:
            return [a] + b

        yield []
        yield from self.cons(mk_list)
    
class StrStrat(Strategy[str]):
    def generate(self, depth):
        m = min(depth + 1, len(LETTERS))
        yield from LETTERS[:m]

# DEBUG
if False:
    class SimpleIntStrat(IntStrat):
        def generate(self, depth, partial=0):
            yield 0
            yield 1
