import logging
import time
import os
import numpy as np
import mpmath as mp
from typing import Dict, Any, List

# Import project core components
from numpy.polynomial.chebyshev import chebval
from unitarylab.core import Circuit, Register
from unitarylab.library.linear_solver import QSVTSolver
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QSVTLinearSolverAlgorithm(BaseAlgorithm):
    """QSVT Linear Solver Algorithm Module.

    This module implements quantum linear system solving based on QSVT.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="QSVT Linear Solver", prefix="QSVT_QLSA", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, A, b, epsilon, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """
        Execute the main flow of the QSVT-based linear solver.

        Args:
            A (np.ndarray): The coefficient matrix A.
            b (np.ndarray): The right-hand-side vector b.
            epsilon (float): Target approximation accuracy.

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Matrix in the linear system": A, "Source vector": b, "Target precision (epsilon)": epsilon}
        self.update_input(input)

        self.log(f"Calling the QSVT linear solver from unitarylab...")
        
        start_time = time.time()
        circuit, solution, scaling_factor = QSVTSolver(A, b, epsilon, backend=backend, device=device, dtype=dtype)
        comp_time = time.time() - start_time

        self.log(f"  - QSVT linear solver completed in {comp_time:.4f} seconds")

        # Stage 5: Save results and generate output
        self.log(f"Saving results and generating output...")

        output = {"Solution vector": solution, "Scaling factor applied": scaling_factor, "Simulation time (s)": comp_time}
        self.update_output(output)
        self.status = 'success'
        self.summary = f"QSVT linear solver executed successfully in {comp_time:.4f} seconds. Solution vector: {solution}, Scaling factor: {scaling_factor}"

        circuit_path = self.save_circuit(circuit)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, circuit)

def test(A=[[0.8, 0], [0, 0.4]], b=[1., 2.], epsilon=0.01):
    A = np.array(A)
    b = np.array(b)

    algo = QSVTLinearSolverAlgorithm(text_mode="legacy")
    result = algo.run(A=A, b=b, epsilon=epsilon)
    return result


if __name__ == "__main__":
    A = [[0.8, 0], [0, 0.4]]  # [PARAM]
    b = [1., 2.]  # [PARAM]
    epsilon = 0.0001  # [PARAM]

    test(A=A, b=b, epsilon=epsilon)