"""
The Hadamard Test module

========================================= Estimates the complex expectation of a unitary operator U using auxiliary bit measurements.

Encapsulates expectation estimation, state overlap test (SWAP test), and single-bit phase estimation.
"""

from .algorithm import HadamardTestAlgorithm, test

__all__ = [
    'HadamardTestAlgorithm',
]