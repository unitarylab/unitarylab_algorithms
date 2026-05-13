"""
Schrödingerization Module
=========================

This module provides quantum algorithms for solving partial differential equations (PDEs):
"""

from .equation_heat import HeatEquationAlgorithm
from .equation_advection import AdvectionEquationAlgorithm
from .equation_heat2d import Heat2dEquationAlgorithm


from .base import BaseAlgorithm, create_algorithm_logger

__all__ = [
    "HeatEquationAlgorithm",
    "AdvectionEquationAlgorithm",
    "Heat2dEquationAlgorithm",
    "BaseAlgorithm",
    "create_algorithm_logger",
]