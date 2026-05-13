"""
Quantum Fourier Transform (QFT) Module

====================================== The core quantum algorithm for performing the Quantum Fourier Transform.

It is a key component in many quantum algorithms, such as Shor's algorithm for factoring and quantum phase estimation.
"""

from .algorithm import QFTAlgorithm, test

__all__ = [
    'QFTAlgorithm',
    'test'
]