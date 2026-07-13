"""
AQC Algorithm Module
=====================

Discrete adiabatic quantum linear system solver (QLSP).
Solves Ax = b via a Trotterized discrete adiabatic evolution.
"""

from .algorithm import AQCAlgorithm, test

__all__ = [
    'AQCAlgorithm',
    'test'
]
