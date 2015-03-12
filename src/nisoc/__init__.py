
import os
from os.path import join as pathjoin, abspath, dirname

DATA_ROOT = pathjoin(abspath(dirname(__file__)), 'data')

def get_data(path):
    return pathjoin(DATA_ROOT, path)

class NisocException(Exception):
    pass

class NisocConfigurationError(NisocException):
    pass

