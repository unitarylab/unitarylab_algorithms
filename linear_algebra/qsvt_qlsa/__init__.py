"""
The QSVT Linear Solver module:

==========================================================
Approximates inverse proportional functions using the Quantum Singular Value Transform (QSVT) technique, thereby achieving matrix inversion.

Represents the most state-of-the-art, theoretically optimal solution framework in quantum linear algebra.

Widely applied in numerical solutions of differential equations and advanced scientific computing.
"""

from .algorithm import QSVTLinearSolverAlgorithm, test

__all__ = [
    'QSVTLinearSolverAlgorithm',
    'test'
]