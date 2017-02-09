import attr
import typing

@attr.s
class Typeable:
    typ = attr.ib()
    origin = attr.ib()
    args = attr.ib()
    arity = attr.ib()

    def pretty(self):
        if not self.origin:
            name = self.typ.__name__
        else:
            name = self.origin.pretty()

        if self.args:
            args = [from_type(a).pretty() for a in self.args]
            return '{}[{}]'.format(name, ', '.join(args))

        return '{}'.format(name)

def from_type(t):
    '''Converts a type `t` to a Typeable
    '''
    if isinstance(t, Typeable):
        return t

    return _from_typing36(t)

def _from_typing36(t):
    '''Support for 3.6 version of typing module
    '''

    try:
        origin = t.__origin__
    except AttributeError:
        # not typing.Generic
        return Typeable(typ=t, origin=None, args=[], arity=0)

    # is a base type
    if not origin:
        return Typeable(typ=t, origin=None, args=[], arity=1)

    args = [from_type(t_) for t_ in t.__args__]
    return Typeable(typ=t, origin=from_type(origin), args=args, arity=get_arity(origin, args))

def get_arity(origin, args=[]):
    '''Gets the arity of some typing type
    '''
    if isinstance(origin, typing.Generic):
        return 1 - (1 if args else 0)

    return 0
