"""
2D Heat Equation Algorithm Module

Solve the two-dimensional heat equation based on the Schrödingerization method:

∂u/∂t = a1 * ∂²u/∂x² + a2 * ∂²u/∂y²
"""

# ==========================================================
# Server preamble section, adjust accordingly
from typing import Dict, Any, List, Optional
import time
import os
import sys
import scipy.sparse as sp
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

# Import unitarylab package

from unitarylab import Circuit
from unitarylab.library.equation import parse_equation


# ==========================================================
# Equation execution function

class Heat2dEquationAlgorithm(BaseAlgorithm):
    """Thermal Equation Algorithm

    Solve the two-dimensional forward thermal equation based on the Schrödingerization method:

    ∂u/∂t = a1 * ∂²u/∂x² + a2 * ∂²u/∂y²

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

        # Parse solving method and dispatch to method-specific functions
        method = eq.solver.type
        if method == 'classical':
            return self._solve_classical(eq)
        elif method == 'trotter':
            return self._solve_trotter(eq, backend=backend, device=device, dtype=dtype)
        elif method == 'block':
            return self._solve_block(eq)
        else:
            raise ValueError(f'method {method} is not supported!')

    def _solve_classical(self, eq):
        from unitarylab.library.equation.schrodingerization import schro_classical as schro
        from unitarylab.library.equation.differential_operator import CDiff
        from unitarylab.library.equation.schrodingerization import circuit_classical

        # ========== Stage 1: Method-specific parameters ==========
        # Parse equation-specificparameters
        L, T, source, nx, na, R, point, order, f0 = eq.get_common_coefficients()
        # derivative = eq.get_derivative_1d()
        bd = eq.boundary.type
        scheme = eq.discrete.type
        a1 = eq.get_parameter('a1')
        a2 = eq.get_parameter('a2')


        Nx = 2**nx
        dx = L / (Nx + 1)
        x = np.arange(dx, L, dx)
        y = np.arange(dx, L, dx)
        if bd == 'periodic':
            dx = L / Nx
            x = np.arange(0, L, dx)
            y = np.arange(0, L, dx)
    
        u0 = f0(x[:,None], y[None,:]) 
        u0 = u0.flatten()

        self.logger.info(f"- Diffusion coefficient a1 = {a1}, a2 = {a2}")
        self.logger.info(f"- Computation domain length L = {L}")
        self.logger.info(f"- Final time T = {T}")
        self.logger.info(f"- Spatial qubits nx = {nx}")
        self.logger.info(f"- Ancilla qubits na = {na}")
        self.logger.info(f"- Boundary condition: {bd}")
        self.logger.info("Stage 1/5: Parameter parsing complete ✓")

        # ========== Stage 2: Build finite difference matrix ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 2/5: Building finite difference matrix...")

        A0 = CDiff(N=Nx, dx=dx, order=2, scheme=scheme, boundary=bd).get_matrix()
        A = a1 * sp.kron(A0, sp.eye(Nx)) + a2 * sp.kron(sp.eye(Nx), A0)
        # b0 = eq.get_rhs_1d(Nx, dx, scheme=scheme) + source(x)
        b0 = source(x)
        b = a1 * np.kron(b0, np.ones(Nx)) + a2 * np.kron(np.ones(Nx), b0)
        self.logger.info("Stage 2/5: Finite difference matrix complete ✓")

        # ========== Stage 3: Execute quantum circuit ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 3/5: Starting computation...")

        start_time = time.time()
        u = schro(A, u0, T=T, na=na, R=R, order=order, point=point, b=b)
        u = u.reshape((Nx, Nx))
        qc = circuit_classical(nx, na, dim = 2)
        end_time = time.time()

        self.logger.info(f"- Actual computation time: {end_time - start_time:.4f} seconds")
        self.logger.info("Stage 3/5: Quantum circuit execution complete ✓")

        # ========== Stage 4: Generate solution plot ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 4/5: Generating solution visualization...")

        name = f"2D Heat Classical nx={nx} na={na} T={T}"
        solution_plot_path = self._generate_solution_plot(name, x, y, u)

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
            "message": "2D Heat equation solved",
            "grid": {"n_points": 2**nx, "dx": dx},
            "x": x.tolist() if hasattr(x, 'tolist') else x,
            "y": y.tolist() if hasattr(y, 'tolist') else y,
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
        # derivative = eq.get_derivative_1d()
        bd = eq.boundary.type
        scheme = eq.discrete.type
        a1 = eq.get_parameter('a1')
        a2 = eq.get_parameter('a2')
        dt = eq.solver.dt
        Nt = int(T / dt)

        Nx = 2**nx
        dx = L / (Nx + 1)
        x = np.arange(dx, L, dx)
        y = np.arange(dx, L, dx)
        if bd == "periodic":
            dx = L / Nx
            x = np.arange(0, L, dx)
            y = np.arange(0, L, dx)
        elif bd == "neumann":
            dx = L / (Nx - 1)
            x = np.arange(0, L + dx, dx)
            y = np.arange(0, L + dx, dx)
        u0 = f0(x[:,None], y[None,:])
        u0 = u0.flatten()

        self.logger.info(f"- Diffusion coefficient a1 = {a1}")
        self.logger.info(f"- Diffusion coefficient a2 = {a2}")
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
        func1 = TDiff(nx, dx, 2, scheme=scheme, boundary=bd).data()[0]
        D1 = lambda a: func1(a * dt/R)
        H1 = Circuit(2*nx)
        H1.append(D1(a1), range(nx))
        H1.append(D1(a2), range(nx, 2*nx))

        H2 = None

        self.logger.info("Stage 2/5: Quantum circuit complete ✓")

        # ========== Stage 3: Execute quantum circuit ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 3/5: Starting quantum circuit execution...")
        self.logger.info(f"- Total time steps: {Nt}")

        start_time = time.time()
        u, qc = schro(u0=u0, H1=H1, H2=H2, Nt=Nt, na=na, R=R, order=order, point=point, device=device)
        u = u.reshape((Nx, Nx))
        end_time = time.time()

        self.logger.info(f"- Actual computation time: {end_time - start_time:.4f} seconds")
        self.logger.info("Stage 3/5: Quantum circuit execution complete ✓")

        # ========== Stage 4: Generate solution plot ==========
        self.logger.info("=" * 50)
        self.logger.info("Stage 4/5: Generating solution visualization...")

        name = f"2D Heat Lie-Trotter nx={nx} na={na} T={T} dt={dt}"
        solution_plot_path = self._generate_solution_plot(name, x, y, u)

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
            "message": "2D Heat equation solved",
            "grid": {"n_points": 2**nx, "dx": dx, "dt": dt, "nt": Nt},
            "x": x.tolist() if hasattr(x, 'tolist') else x,
            "y": y.tolist() if hasattr(y, 'tolist') else y,
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

    def _generate_solution_plot(
        self,
        name: str,
        x,
        y,
        u,
        format: str = 'svg'
    ) -> str:
        """
        Generate the computational results graph and save it to the algorithm folder.

        :param x: Spatial grid point

        :param y: Spatial grid point

        :param u: Final solution

        :param name: Graph title

        :return: Saved filename (relative to the algorithm folder)
        """
        
        self.set_plt(self.color)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 8), dpi=100, subplot_kw={'projection': '3d'})
        fig.patch.set_alpha(0)

        # Plot解
        X, Y = np.meshgrid(x, y)
        contour = ax.plot_surface(X, Y, u, cmap='viridis')
        ax.patch.set_alpha(0)
        plt.colorbar(contour, ax=ax, label='u(x, y, t)')

        # Set title和标签
        ax.set_title(f"{name}", fontsize=14)
        ax.set_xlabel("x", fontsize=12)
        ax.set_ylabel("y", fontsize=12)
        ax.grid(True, alpha=0.3)

        # Save imageto algorithm folder
        filename = f'{name.replace(" ", "_")}_solution.{format}'
        solution_path = os.path.join(self.algo_dir, filename)
        fig.savefig(solution_path, format=format, bbox_inches="tight", transparent=True)

        # Clean资源
        plt.close(fig)

        self.logger.debug(f"Solution plot saved to: {solution_path}")

        # Return文件名（相对路径）
        return filename


if __name__ == "__main__":
    result = Heat2dEquationAlgorithm().run()
    print("Execution completed:", list(result.keys()))
