"""
Advection Equation Algorithm Module

Solve the one-dimensional advection equation based on the Schrödingerization method:

∂u/∂t + a * ∂u/∂x = 0
"""

from typing import Dict, Any, Optional
import time
import os
import sys
import numpy as np

try:
    from ..base import BaseAlgorithm, create_algorithm_logger
except ImportError:
    # 单独运行时，将 app/algorithms 目录加入 sys.path，使 base 模块可被找到
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from base import BaseAlgorithm, create_algorithm_logger

# 使用非交互式后端，避免服务器端显示问题
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from unitarylab import Circuit
from unitarylab.library.equation import parse_equation, Equation

# ==========================
# 主算法类
# ==========================

class AdvectionEquationAlgorithm(BaseAlgorithm):
    """
    Algorithm for Advection Equation

    ∂u/∂t + a ∂u/∂x = 0
    """
    # ==========================================================
    # 主入口
    # ==========================================================

    def run(self, params = None, algo_dir: str = None, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:

        
        """
        Execute the algorithm to solve the advection equations

        :param params: JSON string parameters containing equation configuration and solution method configuration

        :return: Algorithm execution result
        """

        if algo_dir is None:
            _this = os.path.abspath(__file__)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(os.path.dirname(_this))), os.path.basename(os.path.dirname(_this)))
            os.makedirs(algo_dir, exist_ok=True)

        self.algo_dir = algo_dir
        self.logger = create_algorithm_logger(algo_dir)

        self.logger.info("=" * 50)
        self.logger.info("Stage 1/5: Parsing advection equation parameters...")

        try:
            if params is None:
                import json as _json
                _setup = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup.json")
                with open(_setup, "r", encoding="utf-8") as _f:
                    params = _json.load(_f)
            eq = parse_equation(params)
        except Exception as e:
            self.logger.error(f"Parameter parsing failed: {e}")
            raise e
        # Parse solving method and dispatch to method-specific functions
        method = eq.solver.type

        if method == 'classical':
            return self._solve_classical(eq)
        elif method == 'trotter':
            return self._solve_trotter(eq, backend=backend, device=device, dtype=dtype)
        else:
            raise ValueError(f'method {method} is not supported!')

    # ==========================================================
    # Classical 求解
    # ==========================================================

    def _solve_classical(self, eq: Equation):

        from unitarylab.library.equation.schrodingerization import schro_classical as schro
        from unitarylab.library.equation.schrodingerization import circuit_classical
        from unitarylab.library.equation.differential_operator.classical_matrices import first_order_derivative
        # ========== Stage 1: Method-specific parameters ==========
        # Parse equation-specificparameters
        L, T, source, nx, na, R, point, order, f0 = eq.get_common_coefficients()
        derivative = eq.get_derivative_1d()
        bd = eq.boundary.type
        scheme = eq.discrete.type
        a = eq.get_parameter('a')

        Nx = 2**nx
        dx = L / (Nx + 1)
        x = np.arange(dx, L, dx)

        if bd == 'periodic':
            dx = L / Nx
            x = np.arange(0, L, dx)

        u0 = f0(x)

        self.logger.info(f"- Advection speed a = {a}")
        self.logger.info(f"- Computation domain length L = {L}")
        self.logger.info(f"- Final time T = {T}")
        self.logger.info(f"- Spatial qubits nx = {nx}")
        self.logger.info(f"- Ancilla qubits na = {na}")
        self.logger.info(f"- Boundary condition: {bd}")
        self.logger.info("Stage 1/5: Parameter parsing complete ✓")
        # ========== Stage 2: Build finite difference matrix ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 2/5: Building finite difference matrix...")

        if scheme == "upwind":
            scheme = "forward" if a >= 0 else "backward"

        A0, b0 = first_order_derivative(N=Nx, dx=dx, boundary_condition=bd, scheme=scheme, g1=eq.boundary.left_value, g2=eq.boundary.right_value)

        A = A0 * a
        b = b0 * a

        self.logger.info("Stage 2/5: Finite difference matrix complete ✓")
        # ========== Stage 3: Execute quantum circuit ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 3/5: Starting computation...")

        start_time = time.time()
        u = schro(A, u0, T=T, na=na, R=R, order=order, point=point, b=b)
        qc = circuit_classical(nx, na)
        end_time = time.time()

        self.logger.info(f"- Actual computation time: {end_time - start_time:.4f} seconds")
        self.logger.info("Stage 3/5: Quantum circuit execution complete ✓")
        # ========== Stage 4: Generate solution plot ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 4/5: Generating solution plot...")

        name = f"1D_Advection_Classical_nx={nx}_na={na}_T={T}"
        solution_plot_path = self._generate_solution_plot(name, x, u)

        self.logger.info("Stage 4/5: Solution plot complete ✓")
        # ========== Stage 5: Generate circuit diagrams ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 5/5: Generating circuit diagrams...")

        circuit_plot_paths = self._generate_circuit_plots(name, qc)
        
        self.logger.info("Stage 5/5: Circuit diagrams complete ✓")
        # ========== Done ==========
        self.logger.info("=" * 50)
        self.logger.info("All stages complete, computation successful！")

        return {
            "status": "ok",
            "message": "Advection equation solved",
            "grid": {"n_points": 2**nx, "dx": dx},
            "x": x.tolist() if hasattr(x, 'tolist') else x,
            "u": u.tolist() if hasattr(u, 'tolist') else u,
            "circuit": circuit_plot_paths,
            "plot": {
                "format": "svg",
                "filename": solution_plot_path,
            },
        }

    # ==========================================================
    # Trotter 求解
    # ==========================================================

    def _solve_trotter(self, eq: Equation, backend='torch', device='cpu', dtype=np.complex128):

        from unitarylab.library.equation.schrodingerization import schro_trotter as schro
        from unitarylab.library.equation.differential_operator import TDiff
        from unitarylab.library.equation.differential_operator.classical_matrices import first_order_derivative as first_order_derivative_classical
        # ========== Stage 1: Method-specific parameters ==========
        # Parse equation-specificparameters
        L, T, source, nx, na, R, point, order, f0 = eq.get_common_coefficients()
        derivative = eq.get_derivative_1d()
        bd = eq.boundary.type
        scheme = eq.discrete.type
        a = eq.get_parameter('a')

        dt = eq.solver.dt
        Nt = int(T / dt)

        Nx = 2**nx
        dx = L / (Nx + 1)
        x = np.arange(dx, L, dx)

        if bd == "periodic":
            dx = L / Nx
            x = np.arange(0, L, dx)

        u0 = f0(x)

        self.logger.info(f"- Advection speed a = {a}")
        self.logger.info(f"- Computation domain length L = {L}")
        self.logger.info(f"- Final time T = {T}")
        self.logger.info(f"- Time step dt = {dt}")
        self.logger.info(f"- Spatial qubits nx = {nx}")
        self.logger.info(f"- Ancilla qubits na = {na}")
        self.logger.info(f"- Boundary condition: {bd}")
        self.logger.info("Stage 1/5: Parameter parsing complete ✓")
        # ========== Stage 2: Build quantum circuit ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 2/5: Building quantum circuit...")

        
        A0, b0 = first_order_derivative_classical(N=Nx, dx=dx, boundary_condition=bd, scheme=scheme, g1=eq.boundary.left_value, g2=eq.boundary.right_value)

        b = b0 * a
        b = b * T if T > 1 else b
        theta = 1 / T if T > 1 else 1
        if scheme == 'upwind':
            func1 = (abs(a) * TDiff(nx, dx, 2, boundary=bd)).data()[0]
            H1 = func1(dt / R)
        elif scheme == 'central':
            func1 = None
            H1 = None
        func2 = (a * TDiff(nx, dx, 1, boundary=bd)).data()[1]
        H2 = func2(dt)

        self.logger.info("Stage 2/5: Quantum circuit complete ✓")
        # ========== Stage 3: Execute quantum circuit ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 3/5: Starting quantum circuit execution...")
        self.logger.info(f"- Total time steps: {Nt}")

        start_time = time.time()
        u, qc = schro(u0=u0, H1=H1, H2=H2, Nt=Nt, na=na, R=R, order=order, point=point, b=b, theta=theta * dt, backend=backend, device=device, dtype=dtype)
        end_time = time.time()
        self.logger.info(f"- Actual computation time: {end_time - start_time:.4f} seconds")
        # self.logger.info(f": {end_time - start_time:.4f} seconds")
        self.logger.info("Stage 3/5: Quantum circuit execution complete ✓")

        # ========== Stage 4: Generate solution plot ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 4/5: Generating solution visualization...")

        name = f"1D Advection Lie-Trotter nx={nx} na={na} T={T} dt={dt}"
        solution_plot_path = self._generate_solution_plot(name, x, u)

        self.logger.info("Stage 4/5: Solution visualization complete ✓")
        # ========== Stage 5: Generate circuit diagrams ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 5/5: Generating quantum circuit diagrams...")
        circuit_plot_paths = self._generate_circuit_plots(name, qc)
        self.logger.info("Stage 5/5: Quantum circuit diagrams complete ✓")
        # ========== Done ==========
        self.logger.info("=" * 50)
        self.logger.info("All stages complete, computation successful！")
        self.logger.info("=" * 50)

        return {
            "status": "ok",
            "message": "Advection equation solved",
            "grid": {"n_points": 2**nx, "dx": dx, "dt": dt, "nt": Nt},
            "x": x.tolist() if hasattr(x, 'tolist') else x,
            "u": u.tolist() if hasattr(u, 'tolist') else u,
            "circuit": circuit_plot_paths,
            "plot": {
                "format": "svg",
                "filename": solution_plot_path,
            },
        }


if __name__ == "__main__":
    result = AdvectionEquationAlgorithm().run()
    print("Execution completed:", list(result.keys()))
