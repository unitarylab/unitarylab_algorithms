"""
VQLS Algorithm — Variational Quantum Linear Solver.

Solves Ax = b for arbitrary 2^n x 2^n matrices using a hardware-efficient
variational ansatz, three cost-function modes, and COBYLA optimisation.

Features:
  - PS-encoding C-Z_j for efficient Hadamard-test circuits
  - j=-1 shortcut (psi_norm skips U_b/U_b_dagger)
  - U_b decomposition to primitive gates (no black boxes)
  - epsilon early-stopping with theoretical guarantee

Usage:
    from algorithms.linear_algebra.vqls import VQLSAlgorithm
    algo = VQLSAlgorithm(text_mode="plain")
    result = algo.run(A, b, cost_function="global", n_layers=4, maxiter=500)
"""

from .algorithm import VQLSAlgorithm, test

__all__ = ["VQLSAlgorithm", "test"]
