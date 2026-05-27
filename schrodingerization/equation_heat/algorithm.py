"""
Heat Equation Algorithm Module

Solve the one-dimensional heat equation based on the Schrödingerization method:

∂u/∂t = a * ∂²u/∂x²
"""

# ==========================================================
# Universal preamble（本地 + 服务器 双兼容）

from typing import Dict, Any, List, Optional
import json
import os
import time
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
 

# -------------------------
# matplotlib server-safe模式
# -------------------------


# 使用非交互式后端，避免服务器端显示问题
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from unitarylab.library.equation import parse_equation


from unitarylab import Circuit




# ==========================================================

# ==========================================================
# Equation execution function

class HeatEquationAlgorithm(BaseAlgorithm):
    """Thermal Equation Algorithm

    Solve the one-dimensional forward thermal equation based on the Schrödingerization method:

    ∂u/∂t = a * ∂²u/∂x²

    Supported Boundary Conditions:

        - Dirichlet Boundary Conditions: u(0,t) = 0, u(L,t) = 0

        - Periodic Boundary Conditions: u(0,t) = u(L,t)

    Supported Solution Methods:

        - Classical: Classical matrix exponentiation method

        - Trotter: Trotter decomposition method

        - Block: Block coding method
    """

    def run(self, params = None, algo_dir: str = None, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """
        Execute the algorithm to solve the heat equation

        :param params:

            - None: Automatically read from setup.json

            - str: JSON string

            - dict: Parsed parameters

        :return: Algorithm execution result
        """

        if algo_dir is None:
            _this = os.path.abspath(__file__)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(os.path.dirname(_this))), os.path.basename(os.path.dirname(_this)))
            os.makedirs(algo_dir, exist_ok=True)

        self.algo_dir = algo_dir
        self.logger = create_algorithm_logger(algo_dir)


        self.logger.info("=" * 50)
        self.logger.info("Stage 1/5: Parsing heat equation parameters...")

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

        # ---------- Dispatch solver method ----------
        method = eq.solver.type.lower()

        if method == "classical":
            return self._solve_classical(eq)
        elif method == "trotter":
            return self._solve_trotter(eq, backend=backend, device=device, dtype=dtype)
        elif method == "block":
            return self._solve_block(eq)
        else:
            raise ValueError(f"method {method} is not supported!")

    def _solve_classical(self, eq):
        from unitarylab.library.equation.schrodingerization import schro_classical as schro
        from unitarylab.library.equation.differential_operator import CDiff
        from unitarylab.library.equation.schrodingerization import circuit_classical

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
        if bd == "periodic":
            dx = L / Nx
            x = np.arange(0, L, dx)
        elif bd == "neumann":
            dx = L / (Nx - 1)
            x = np.arange(0, L + dx, dx)
        u0 = f0(x)

        self.logger.info(f"- Diffusion coefficient a = {a}")
        self.logger.info(f"- Computation domain length L = {L}")
        self.logger.info(f"- Final time T = {T}")
        self.logger.info(f"- Spatial qubits nx = {nx}")
        self.logger.info(f"- Ancilla qubits na = {na}")
        self.logger.info(f"- Boundary condition: {bd}")
        self.logger.info("Stage 1/5: Parameter parsing complete✓")

        # ========== Stage 2: Build finite difference matrix ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 2/5: Building finite difference matrix...")

        A = a * CDiff(N=Nx, dx=dx, order=2, scheme=scheme, boundary=bd).get_matrix()
        b = eq.get_rhs_1d(Nx, dx, scheme=scheme) + source(x)

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
        self.logger.info("Stage 4/5: Generating solution visualization...")

        name = f"1D Heat Classical nx={nx} na={na} T={T}"
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
            "message": "Heat equation solved",
            "grid": {"n_points": 2**nx, "dx": dx},
            "x": x.tolist() if hasattr(x, 'tolist') else x,
            "u": u.tolist() if hasattr(u, 'tolist') else u,
            "circuit": circuit_plot_paths,  # Return多个电路图数组
            "plot": {
                "format": "svg",
                "filename": solution_plot_path,
            },
        }

    def _solve_trotter(self, eq, backend='torch', device='cpu', dtype=np.complex128):
        from unitarylab.library.equation.schrodingerization import schro_trotter as schro
        from unitarylab.library.equation.differential_operator import TDiff

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
        elif bd == "neumann":
            dx = L / (Nx - 1)
            x = np.arange(0, L + dx, dx)
        u0 = f0(x)

        self.logger.info(f"- Diffusion coefficient a = {a}")
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
        
        func1, func2 = (a * TDiff(nx, dx, 2, scheme=scheme, boundary=bd)).data()
        H1 = func1(dt / R)
        H2 = func2(dt)

        self.logger.info("Stage 2/5: Quantum circuit complete ✓")

        # ========== Stage 3: Execute quantum circuit ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 3/5: Starting quantum circuit execution...")
        self.logger.info(f"- Total time steps: {Nt}")

        start_time = time.time()
        u, qc = schro(u0=u0, H1=H1, H2=H2, Nt=Nt, na=na, R=R, order=order, point=point)
        end_time = time.time()

        self.logger.info(f"- Actual computation time: {end_time - start_time:.4f} seconds")
        self.logger.info("Stage 3/5: Quantum circuit execution complete ✓")

        # ========== Stage 4: Generate solution plot ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 4/5: Generating solution visualization...")

        name = f"1D Heat Lie-Trotter nx={nx} na={na} T={T} dt={dt}"
        solution_plot_path = self._generate_solution_plot(name, x, u)

        self.logger.info("Stage 4/5: Solution visualization complete ✓")

        # ========== Stage 5: Generate circuit diagrams ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 5/5: Generating quantum circuit diagrams...")

        circuit_plot_paths = self._generate_circuit_plots(name, qc, H1, H2)

        self.logger.info("Stage 5/5: Quantum circuit diagrams complete ✓")

        # ========== Done ==========
        self.logger.info("=" * 50)
        self.logger.info("All stages complete, computation successful！")
        self.logger.info("=" * 50)

        return {
            "status": "ok",
            "message": "Heat equation solved",
            "grid": {"n_points": 2**nx, "dx": dx, "dt": dt, "nt": Nt},
            "x": x.tolist() if hasattr(x, 'tolist') else x,
            "u": u.tolist() if hasattr(u, 'tolist') else u,
            "circuit": circuit_plot_paths,  # Return多个电路图数组
            "plot": {
                "format": "svg",
                "filename": solution_plot_path,
            },
        }

    def _solve_block(self, eq):
        self.logger.info('Block encoding will be supported soon! Now falling back to classical method!')
        return self._solve_classical(eq)
    
if __name__ == "__main__":
    result = HeatEquationAlgorithm().run()
    print("Execution completed:", list(result.keys()))
