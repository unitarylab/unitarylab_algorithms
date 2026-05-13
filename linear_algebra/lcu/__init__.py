"""
Linear Combination of Unitaries (LCU) Module

============================================= This module decomposes non-unitary operators into weighted sums of unitary operators.

Through the interference of the V operator and the SELECT operator, it embeds arbitrary matrices into quantum circuits within a probabilistic framework.

It is the core foundation of advanced quantum linear algebra algorithms such as Hamiltonian Simulation and HHL.
"""

from .algorithm import LCUAlgorithm, test

__all__ = [
    'LCUAlgorithm',
    'test'
]