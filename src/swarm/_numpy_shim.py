"""NumPy compatibility shim — stdlib-only substitute for swarm module.

Provides the minimal numpy functions used by the swarm optimization
algorithms (PSO, ABC, stigmergy) when numpy is not installed.

Supported operations:
  - np.array(lst) — wraps list
  - np.ndarray — alias for list
  - np.mean(arr) — arithmetic mean
  - np.sqrt(x) — square root
  - np.ceil(x) — ceiling
  - np.clip(val, lo, hi) — clip to range
  - np.random.uniform(lo, hi, size) — uniform random
  - np.random.rand(dim) — random in [0,1)
  - np.linalg.norm(v) — Euclidean norm
  - np.ndindex(*shape) — iterate over indices
"""

from __future__ import annotations

import math
import random as _random


class _NdArray(list):
    """Thin list wrapper that mimics numpy.ndarray for basic ops."""
    def __init__(self, iterable):
        super().__init__(float(x) if not isinstance(x, (int, float)) else x for x in iterable)

    def __add__(self, other):
        if isinstance(other, (int, float)):
            return _NdArray([x + other for x in self])
        return _NdArray([a + b for a, b in zip(self, other)])

    def __sub__(self, other):
        if isinstance(other, (int, float)):
            return _NdArray([x - other for x in self])
        return _NdArray([a - b for a, b in zip(self, other)])

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return _NdArray([x * other for x in self])
        return _NdArray([a * b for a, b in zip(self, other)])

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return _NdArray([x / other for x in self])
        return _NdArray([a / b for a, b in zip(self, other)])

    def __neg__(self):
        return _NdArray([-x for x in self])

    def __abs__(self):
        return _NdArray([abs(x) for x in self])

    def copy(self):
        return _NdArray(list(self))


class _Linalg:
    @staticmethod
    def norm(v, axis=None):
        if axis == 1 and isinstance(v, (list, _NdArray)) and len(v) > 0 and isinstance(v[0], (list, _NdArray)):
            return _NdArray([math.sqrt(sum(x * x for x in row)) for row in v])
        if isinstance(v, list):
            v = _NdArray(v)
        return math.sqrt(sum(x * x for x in v))


class _Random:
    @staticmethod
    def uniform(lo, hi, size):
        return _NdArray([_random.uniform(lo, hi) for _ in range(size)])

    @staticmethod
    def rand(*dims):
        if len(dims) == 1:
            return _NdArray([_random.random() for _ in range(dims[0])])
        return _NdArray([_random.random() for _ in range(dims[0])])


class _Numpy:
    """Stand-in for numpy module exposing only functions used by swarm."""

    ndarray = _NdArray

    @staticmethod
    def array(obj, dtype=None):
        if isinstance(obj, _NdArray):
            return obj
        return _NdArray(obj)

    @staticmethod
    def mean(arr, axis=None):
        if isinstance(arr, (list, _NdArray)):
            if len(arr) == 0:
                return 0.0
            total = sum(arr)
            if axis == 0 and isinstance(arr[0], (list, _NdArray)):
                return _NdArray([sum(col) / len(arr) for col in zip(*arr)])
            return total / len(arr)
        return arr

    @staticmethod
    def sqrt(x):
        return math.sqrt(x)

    @staticmethod
    def ceil(x):
        return math.ceil(x)

    @staticmethod
    def clip(val, lo, hi):
        if isinstance(val, (list, _NdArray)):
            return _NdArray([max(lo, min(hi, v)) for v in val])
        return max(lo, min(hi, val))

    linalg = _Linalg()
    random = _Random()

    @staticmethod
    def ndindex(*shape):
        if len(shape) == 1:
            for i in range(shape[0]):
                yield (i,)
        else:
            for i in range(shape[0]):
                for j in range(shape[1]):
                    yield (i, j)


np = _Numpy()
