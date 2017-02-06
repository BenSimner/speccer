import logging.config

import attr
@attr.s
class _PyState:
    has_typing = attr.ib(default=False)

PyState = _PyState()

from .default_strategies import *
from .model import *
from .strategy import *
from .ops import *
from .spec import *
from .clauses import *
from .pset import *
from .asserts import *

def enableLogging(debug=False):
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[{asctime}] {levelname}, {name}: {message}',
                'datefmt': '%Y/%m/%d %H:%M:%S',
                'style': '{',
            },
        },

        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
        },

        'root': {
            'level': 'DEBUG' if debug else 'INFO',
            'handlers': ['stdout'],
        },
    })
