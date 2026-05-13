"""
Suzuki-Trotter Decomposition Module
===================================

Implementation of higher-order Suzuki-Trotter product formulas for 
Hamiltonian simulation.
"""

from .algorithm import TrotterAlgorithm, test

__all__ = [
    'TrotterAlgorithm',
    'test'
]