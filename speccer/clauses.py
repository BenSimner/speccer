from builtins import tuple as _tuple
import enum
import collections

class PropertyType(enum.Enum):
    FORALL = 1
    EXISTS = 2
    EMPTY = 3

class Property(tuple):
    def __new__(cls, type, args):
        return _tuple.__new__(cls, (type, args))

    def __init__(self, *args):
        self.strategies = {}
        self.name = '<unknown_property>'

    def __str__(self):
        return self.name

def empty():
    return Property(PropertyType.EMPTY, [])

def forall(*args):
    '''Forall `type` the function 'f' holds
    where f either returns `bool` or another `Property`
    '''
    *types, f = args
    return Property(PropertyType.FORALL, [types, f])

def exists(*args):
    '''There exists some `type` such that the function 'f' holds
    where f either returns `bool` or another `Property`
    '''
    *types, f = args
    return Property(PropertyType.EXISTS, [types, f])

p = forall(int, lambda x: None)
p = exists(int, p)