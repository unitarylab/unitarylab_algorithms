"""
Amplitude Estimation Module

========================================== Utilizes quantum phase estimation (QPE) and the Grover iterative operator to convert amplitude into phase information.

Estimates the success probability of the target quantum state with high accuracy and quadratic speedup efficiency.
"""

from .algorithm import AmplitudeEstimationAlgorithm, test

__all__ = [
    'AmplitudeEstimationAlgorithm',
    'test'
]