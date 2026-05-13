import time
import numpy as np
import os
from typing import Dict, Any, List, Tuple, Union
from scipy.linalg import expm
from unitarylab.library.hamiltonian import hamiltonian_simulation
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class CartanDecompositionAlgorithm(BaseAlgorithm):
    """Cartan Decomposition Algorithm Module.

    This module implements the Cartan decomposition algorithm for Hamiltonian simulation, partitioning the Lie algebra into symmetric subalgebra k and antisymmetric space m. 
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Cartan Algorithm", prefix="CARTAN", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, H: Union[np.ndarray, list], t: float, error: float, **kwargs: Any):
        """
        Initialize a Cartan-Lax simulator.

        This function creates a CartanLax simulator instance, which requires a
        real symmetric Hamiltonian. The emitted circuit has the Cartan form
        K * exp(-i eta) * K^dagger, where K is obtained from product-form Lax updates.

        Parameters:
            H : Union[numpy.ndarray, list]
                Hamiltonian to simulate (matrix or list of Pauli terms; currently matrix).
            t : float
                Total evolution time.
            error : float
                Stopping tolerance for the off-h component norm.
            **kwargs : Any
                Optional keyword arguments:
                    evol_time : float
                        Override for the evolution time passed to the simulator.
                    lr : float
                        Base integration step size for the Lax flow.
                    max_steps : int
                        Hard cap on the number of Lax update steps.
                    reps : int
                        Baseline iteration budget before adaptive scaling.

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Hamiltonian": H, "Evolution time": t, "error": error}
        self.update_input(input)

        self.log(f"Running Cartan Decomposition Algorithm from unitarylab")
        start_time = time.time()

        evol_time = kwargs.get('evol_time', t)
        lr = kwargs.get('lr', 1e-3)
        max_steps = kwargs.get('max_steps', 100000)
        reps = kwargs.get('reps', 5000)
        runable = hamiltonian_simulation(
            H,
            evol_time,
            method='cartan-lax',
            target_error=error,
            lr=lr,
            max_steps=max_steps,
            reps=reps,
        )
        comp_time = time.time() - start_time

        self.log(f"Cartan Decomposition completed in {comp_time:.6f} seconds.")
        
        U_exact = expm(-1j * H * evol_time)
        output = {"Evolution result": runable.evolution_result, "Final total error": runable.total_error, "Computation time (s)": comp_time, "Exact evolution": U_exact}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Cartan Decomposition completed with total error {runable.total_error:.2e} in {comp_time:.2f} seconds."

        gs = runable.circuit
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, gs)

def test(H=np.array([[2, 1], [1, 2]]), t=1.0, error=1e-3):
    """
    Initialize a Cartan-Lax simulator.

    This function creates a CartanLax simulator instance, which requires a
    real symmetric Hamiltonian. The emitted circuit has the Cartan form
    K * exp(-i eta) * K^dagger, where K is obtained from product-form Lax updates.

    Parameters:
        H : Union[numpy.ndarray, list]
            Hamiltonian to simulate (matrix or list of Pauli terms; currently matrix).
        t : float
            Total evolution time.
        error : float
            Stopping tolerance for the off-h component norm.
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    error = float(error)
    H = np.array(H)
    
    algo = CartanDecompositionAlgorithm(text_mode="legacy")
    result = algo.run(H, t, error)
    return result

if __name__ == "__main__":
    # Construct a test set
    H = np.array([[2, 1], [1, 3]])  # [PARAM]
    t = 1.0  # [PARAM]
    error = 1e-3 # [PARAM]
    test(H, t, error)
