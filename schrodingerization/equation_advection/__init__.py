"""
Advection Equation Algorithm Module

Solve the one-dimensional advection equation based on the Schrödingerization method:

∂u/∂t + a * ∂u/∂x = 0
"""
from .algorithm import AdvectionEquationAlgorithm

# ========== 算法元数据 (必需) ==========
# 算法注册名称 - 用于 API 调用（使用文件夹名称）
ALGORITHM_NAME = "advection"

# 算法类 - 必须继承 BaseAlgorithm
ALGORITHM_CLASS = AdvectionEquationAlgorithm

# 算法描述 (可选)
ALGORITHM_DESCRIPTION = "基于 Schrödingerization 方法求解一维平流方程"

__all__ = ["AdvectionEquationAlgorithm", "ALGORITHM_NAME", "ALGORITHM_CLASS", "ALGORITHM_DESCRIPTION"]
