"""
Grover's Algorithm Module

========================================== Implements Grover's search algorithm for finding a specific item in an unsorted database.

Provides quadratic speedup for unstructured search problems.
"""

from .algorithm import GroverAlgorithm, test

__all__ = [
    'GroverAlgorithm',
    'test'
]