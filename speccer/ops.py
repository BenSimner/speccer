# ops.py - Operations over strategies
# author: Ben Simner
from __future__ import generator_stop

import typing
import logging
import contextlib
import collections

from . import strategy
from . import typeable
from . import _errors

log = logging.getLogger('ops')

__all__ = [
    'value_args',
    'values',
    'mapS',
    'implies',
    'assume',
]

def assume(b):
    '''Assume b is like a silent assertion
    if b is True, it's a no-op
    if b is False, it silently fails (in this case it raises a FailedAssumption which is caught by the strategy'''
    if not b:
        raise _errors.FailedAssumption

def implies(f, t: type):
    ''' f => t
    '''
    impl_name = f.__name__

    # generate a new type which is t[f]
    typ = typeable.from_type(t)
    t_pretty = typ.pretty()
    t_name = '{}->{}'.format(impl_name, t_pretty)
    t_new = type(t_name, (typ.typ,), {})
    t_new._failed_implications = 0

    @mapS(strategy.Strategy[typ.typ], register_type=t_new)
    def newStrat(d, v, *args):
        try:
            if f(v) is False:
                raise AssertionError('{}[{}] failed'.format(impl_name, t_pretty))
        except AssertionError:
            t_new._failed_implications += 1
        else:
            yield v

    newStrat.__name__ = t_name
    newStrat.__qualname__ = t_name
    return t_new

def values(depth, t, **kwargs):
    yield from strategy.Strategy.get_strat_instance(t)(depth, **kwargs)

def value_args(depth, *types, **kwargs):
    '''Creates a `Strategy' which generates all tuples of type *types
    i.e.
        value_args(1, str, int) ->
            ('a', 0)
            ('a', 1)
            ('a', -1)
            ('b', 0)
            ('b', 1)
            ('b', -1)
            ...
            ('bb' 0)
            ('bb' 1)
            ('bb' -1)

    If any given type has no strategy instance then a MissingStrategyError is put there instead
    i.e.
        value_args(1, int, MyTypeWithNoStratInstance) ->
            (0, MissingStrategyError)
            (1, MissingStrategyError)
            (-1, MissingStrategyError)
    '''
    yield from strategy.generate_args_from_strategies(*map(lambda t: values(depth, t, **kwargs), types))

def mapS(strat, register_type=None, autoregister=False, **kwargs):
    '''
    Maps some function over a Strategy _class_.
    To automatically register the new strategy either set
        autoregister=True   overwrite the old strategy with this one
        register_type=t     register this strategy for type 't'

    i.e.
    @mapS(Strategy[int])
    def NewIntStrat(depth, value):
        yield 'new({})'.format(value)

    NewIntStrat(3) ~= ['new(0)', 'new(1)', 'new(-1)', 'new(2)', 'new(-2)', 'new(3)', 'new(-3)']
    '''
    def decorator(f):
        class MapStrat(strat, autoregister=autoregister, **kwargs):
            def generate(self, depth, *args):
                val_gens = collections.deque()

                def _yield_one():
                    if not val_gens:
                        raise StopIteration

                    g = val_gens.popleft()

                    try:
                        v = next(g)
                    except StopIteration:
                        return _yield_one()

                    val_gens.append(g)
                    return v

                s = strat(depth, *args)
                gen = iter(s)
                while True:
                    try:
                        v = next(gen)
                    except StopIteration:
                        # TODO(BenSimner) this seems horribly wrong
                        # except that the below code needs to access the generator
                        # and so no for loop allowed
                        return

                    val_gens.append(f(depth, v, *args))
                    with contextlib.suppress(StopIteration):
                        yield _yield_one()

        if register_type:
            strategy.register(register_type, MapStrat)

        MapStrat.__name__ = f.__name__
        MapStrat.__qualname__ = f.__qualname__
        MapStrat.__module__ = strat.__module__
        return MapStrat
    return decorator