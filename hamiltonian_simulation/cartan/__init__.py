"""
Cartan Decomposition Module
===========================

Algorithms for Cartan decomposition of Lie algebras, used for circuit 
synthesis and Hamiltonian simulation optimization.
"""

from .algorithm import CartanDecompositionAlgorithm, test

__all__ = [
    'CartanDecompositionAlgorithm',
    'test',
]