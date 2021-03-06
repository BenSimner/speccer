# strategy.py - Strategies for producing arguments to model commands
# author: Ben Simner
#from __future__ import generator_stop

import abc
import heapq
import logging
import inspect
import functools
import collections

from . import _errors
from . import grapher
from . import typeable
from . import ops

generation_graph = grapher.Graph()

__all__ = [
    'Strategy',
    'register',
    'has_strat_instance',
    'get_strat_instance',
]

class PairGen:
    @functools.total_ordering
    class _Pair:
        def __init__(self, *x):
            self.x = x

        def __repr__(self):
            return 'Pair{x}'.format(self.x)

        def __eq__(self, o):
            return all(map(lambda x, y: x == y, self.x, o.x))

        def __lt__(self, o):
            return all(map(lambda x, y: x < y, self.x, o.x))

    # A priority queue
    # (x, y) < (a, b) => x < a AND y < b
    def __init__(self, n=2):
        pair = PairGen._Pair(*tuple(0 for _ in range(n)))
        self._n = n
        self._memo = {}
        self._pq = []

        # max_sizes, only generate up to this.
        self.max_sizes = [-1 for _ in range(n)]
        self.continuation = {}

        heapq.heappush(self._pq, pair)

    def update(self, i):
        '''Increment max_sizes for index i
        '''
        self.max_sizes[i] += 1
        if i in self.continuation:
            t = self.continuation[i]
            pair = PairGen._Pair(*t)
            heapq.heappush(self._pq, pair)
            del self.continuation[i]

    def __iter__(self):
        return self

    def __next__(self):
        if not self._pq:
            raise StopIteration

        pair = heapq.heappop(self._pq)
        t = pair.x

        for i in range(self._n):
            v = t[i] + 1
            tp = t[:i] + (v,) + t[i + 1:]

            if v > self.max_sizes[i]:
                if i not in self.continuation:
                    self.continuation[i] = tp
                continue

            if tp not in self._memo:
                pair = PairGen._Pair(*tp)
                heapq.heappush(self._pq, pair)
                self._memo[tp] = True

        return t

def generate_args_from_strategies(*iters):
    log = logging.getLogger('generate_args_from_strategies({})'.format(iters))

    gens = collections.deque(map(iter, iters))
    n = len(gens)
    log.debug('n={}'.format(n))

    values = [[] for _ in range(n)]
    ds = collections.deque(enumerate(values))

    pair_gen = PairGen(n=n)
    pair_next = None
    c = 0

    def _check():
        nonlocal pair_next, pair_gen
        while True:
            if not pair_next:
                try:
                    pair_next = next(pair_gen)
                except StopIteration:
                    return

            log.debug('values = {}, t = {}'.format(values, pair_next))

            t = ()
            for i in range(n):
                j = pair_next[i]
                t += (values[i][j],)
            else:
                pair_next = None
                yield t
                continue
            break

    while gens:
        gen = gens.popleft()
        di, d = ds.popleft()

        try:
            v = next(gen)
        except StopIteration:
            continue
        except _errors.MissingStrategyError:
            v = _errors.MissingStrategyError
            ds.append((di, d))
        else:
            ds.append((di, d))

        pair_gen.update(di)
        d.append(v)
        c += 1
        gens.append(gen)
        if c >= n:
            yield from _check()

    if c >= n:
        yield from _check()

def has_strat_instance(t):
    try:
        Strategy.get_strat_instance(t)
        return True
    except _errors.MissingStrategyError:
        return False

def get_strat_instance(t):
    '''Gets the strategy instance registered to some type 't'
    '''
    return Strategy.get_strat_instance(t)

def register(t, strategy, override=True):
    '''Register a :class:`Strategy` instance for
    type 't'
    '''
    if t in StratMeta.__strats__ and not override:
        raise ValueError

    StratMeta.__strats__[t] = strategy

def _pprint_stack(stack):
    print('; '.join([
        '{}.generate'.format('None' if 'cls' not in fi.frame.f_locals else fi.frame.f_locals['cls'].__qualname__)
        for fi in stack
        if fi.function == 'generate'
    ]))

class StratMeta(abc.ABCMeta):
    '''Metaclass for an strat generator
    handles setting up the LUT
    '''
    # global LUT of all strategies
    __strats__ = {}

    def __init__(self, *args, **kwargs):
        pass

    def __new__(mcls, name, bases, namespace, subtype=None, autoregister=True):
        cls = super().__new__(mcls, name, bases, namespace)

        for base in bases:
            try:
                if base.subtype:
                    cls.subtype = base.subtype

                    if autoregister:
                        register(base.subtype, cls)
            except AttributeError:
                pass

        if subtype:
            cls.subtype = subtype

        # seems fragile, overwrite __getattribute__ for this?
        cls.__autoregister__ = autoregister
        return cls

    def __getitem__(self, args):
        if not isinstance(args, tuple):
            args = (args,)

        sub, = args

        try:
            return self.get_strat_instance(sub)
        except _errors.MissingStrategyError:
            pass

        return self.new(sub)

    def new(self, t):
        return self.__class__(
            self.__name__,
            (self,) + self.__bases__,
            dict(self.__dict__),
            subtype=t)

    def get_strat_instance(self, t):
        # see if we have an instance for t, outright
        log = logging.getLogger('strategy.getStratInstance({t})'.format(t=t))
        log.debug('get')
        try:
            if isinstance(t, typeable.Typeable):
                return StratMeta.__strats__[t.typ]
            else:
                return StratMeta.__strats__[t]
        except (KeyError, TypeError):  # accept TypeError to allow unhashable types, for aliasing
            # for typing.Generic instances
            # try break up t into its origin and paramters
            # and see if we have a strat instances for those.
            # if we do, compose them together.
            # and put that composition in our StratMeta dict.
            # this allows generation of higher-kinded types such as List[~T]
            typ = typeable.from_type(t)
            log.debug('found typeable={typ}'.format(typ=typ))

            if typ.origin is None:
                log.debug('Cannot generate strategy for that type, no origin.')
                raise _errors.MissingStrategyError('Cannot generate new strategy for type {}'.format(typ))

            strat_origin = self.get_strat_instance(typ.origin)
            s = self.new(typ.typ)
            log.debug('new type, with origin={origin}'.format(origin=strat_origin))

            def generate(self, d, *args, **kwargs):
                log.debug('generate(depth={d}, *{args}, **{kwargs})'.format(d=d, args=args, kwargs=kwargs))
                new_args = [a.typ for a in typ.args] + list(args)
                yield from strat_origin(d, *new_args, **kwargs)

            args = ', '.join(t.pretty() for t in typ.args) # TODO: make this use typeable
            name = 'Generated_{}[{}]'.format(strat_origin.__name__, args)
            GenStrat = type(name, (s,), dict(generate=generate))
            GenStrat.__module__ = strat_origin.__module__
            StratMeta.__strats__[typ.typ] = GenStrat
            return GenStrat
        raise _errors.MissingStrategyError('Cannot get Strategy instance for ~{}'.format(t))

class StrategyIterator:
    def __init__(self, strat):
        self.log = logging.getLogger('strategy.StrategyIterator({})'.format(str(strat)))
        self.strategy = strat
        sig = inspect.signature(strat.generate)
        params = sig.parameters
        kws = {}
        self.log.debug('init')
        for kw in params:
            if kw in strat._kws:
                self.log.debug('add keyword {kw}'.format(kw=kw))
                kws[kw] = strat._kws[kw]
            elif params[kw].kind == inspect.Parameter.VAR_KEYWORD:
                self.log.debug('merge keywords on VAR_KEYWORD {kw}'.format(kw=kw))
                kws.update(strat._kws)
                break

        self._generator = strat.generate(strat._depth, *strat._args, **kws)

    def __next__(self):
        self.log.debug('next()'.format(strat=self.strategy))
        if self.strategy._depth > 0:
            with generation_graph.push_node(label=str(self.strategy)) as n:
                try:
                    v = next(self._generator)
                except _errors.FailedAssumption:
                    print('e: failed assumption')
                    raise RuntimeError('e: failed assumption, NotImplemented')
                n.name = str(v)
                return v
        # with PEP479 this will not automatically stop the parent generator
        # it is important therefore to wrap the generator next() call in a try
        # and except the StopIteration else it bubbles up like other exceptions
        raise StopIteration

    def __iter__(self):
        return self

    def __repr__(self):
        return 'StrategyInstance({})'.format(repr(self.strategy))

class Strategy(metaclass=StratMeta):
    '''A :class:`Strategy` is a method of generating values of some type
    in a deterministic, gradual way - building smaller values first

    In future: this will be a wrapper around a generator (defined by `Strategy.generate')
    '''

    def __init__(self, depth, *args, **kws):
        self.log = logging.getLogger('strategy.{}'.format(str(self)))
        self.log.debug('{}.new({})'.format(self.__class__.__name__, depth))
        self._nodes = []
        self._depth = depth
        self._args = args
        self._kws = kws

    @abc.abstractmethod
    def generate(self, depth, *type_params, **kwargs):
        '''Generator for all values of depth 'depth'

        Allows extra args for higher-kinded types
        '''

    def __iter__(self):
        return StrategyIterator(self)

    def __next__(self):
        raise NotImplementedError

    def __str__(self):
        return self.__class__.__name__

    @property
    def name(self):
        return self.__class__.__qualname__

    def __repr__(self):
        name = self.__class__.__name__
        return '{}({})'.format(name, self._depth)

    @classmethod
    def Map(cls, t, autoregister=True):
        def decorator(f):
            class MappedStrat(Strategy[t], autoregister=autoregister):
                def generate(self, depth, *args, **kwargs):
                    with generation_graph.push_node(name=f.__name__):
                       for k in cls(depth):
                            yield from f(depth - 1, k, *args, **kwargs)

            MappedStrat.__name__ = f.__name__
            MappedStrat.__qualname__ = f.__qualname__
            MappedStrat.__module__ = cls.__module__
            return MappedStrat
        return decorator