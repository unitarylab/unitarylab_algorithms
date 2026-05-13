"""
2D Heat Equation Algorithm Module

Solve the two-dimensional heat equation based on the Schrödingerization method:

∂u/∂t = a1 * ∂²u/∂x² + a2 * ∂²u/∂y²
"""
from .algorithm import Heat2dEquationAlgorithm

# ========== 算法元数据 (必需) ==========
# 算法注册名称 - 用于 API 调用（使用文件夹名称）
ALGORITHM_NAME = "heat2d"

# 算法类 - 必须继承 BaseAlgorithm
ALGORITHM_CLASS = Heat2dEquationAlgorithm

# 算法描述 (可选)
ALGORITHM_DESCRIPTION = "基于 Schrödingerization 方法求解二维热方程"

__all__ = ["Heat2dEquationAlgorithm", "ALGORITHM_NAME", "ALGORITHM_CLASS", "ALGORITHM_DESCRIPTION"]
