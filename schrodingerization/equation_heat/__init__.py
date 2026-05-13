"""
Heat Equation Algorithm Module

Solve the one-dimensional heat equation based on the Schrödingerization method:

∂u/∂t = a * ∂²u/∂x²
"""
from .algorithm import HeatEquationAlgorithm

# ========== 算法元数据 (必需) ==========
# 算法注册名称 - 用于 API 调用（使用文件夹名称）
ALGORITHM_NAME = "heat"

# 算法类 - 必须继承 BaseAlgorithm
ALGORITHM_CLASS = HeatEquationAlgorithm

# 算法描述 (可选)
ALGORITHM_DESCRIPTION = "基于 Schrödingerization 方法求解一维热方程"

__all__ = ["HeatEquationAlgorithm", "ALGORITHM_NAME", "ALGORITHM_CLASS", "ALGORITHM_DESCRIPTION"]
