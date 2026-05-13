"""
Hadamard Transform Module

======================================== Implements an n-qubit global Hadamard transform, supporting superposition state generation and reflexivity verification.
"""

from .algorithm import HadamardTransformAlgorithm, test

__all__ = [
    'HadamardTransformAlgorithm',
    'test',
]
