"""
Quantum Phase Estimation (QPE) Module

====================================== The core quantum algorithm for extracting the phase of the eigenvalues ​​of a target operator.

It is the underlying dependency of advanced algorithms such as Shor's algorithm, quantum chemical simulations, HHL, and quantum amplitude estimation (QAE).
"""

from .algorithm import QPEAlgorithm, test

__all__ = [
    'QPEAlgorithm',
    'test'
]