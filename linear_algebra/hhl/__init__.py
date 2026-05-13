"""
The HHL Algorithm (Harrow-Hassidim-Lloyd) module

============================================ A landmark quantum algorithm for solving the linear equation system Ax = b.

It extracts matrix eigenvalues ​​through quantum phase estimation (QPE) and performs matrix inversion using controlled rotations.

This algorithm theoretically demonstrates a logarithmic time complexity speedup for quantum computers processing sparse matrices,

and is an absolute cornerstone of quantum mechanics, partial differential equation solving, and advanced scientific computing.
"""

from .algorithm import HHLAlgorithm, test

__all__ = [
    'HHLAlgorithm',
    'test'
]