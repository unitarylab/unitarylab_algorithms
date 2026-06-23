import time
import os
import numpy as np
from scipy.optimize import minimize
from typing import Dict, Any

# Import project core components
from unitarylab.core import Register, Circuit
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QSPAlgorithm(BaseAlgorithm):
    """QSP Algorithm Module.

    This module implements Hamiltonian simulation based on Quantum Signal Processing.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="QSP Algorithm", prefix="QSP", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, t: float, d: int, x: float = 0.5, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute QSP algorithm for simulating $cos(t * x)$ evolution.

        Parameters:
            t: Target evolution time
            d: Polynomial degree
            x: Test eigenvalue
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Evolution time (t)": t, "Polynomial degree (d)": d, "Test eigenvalue (x)": x}
        self.update_input(input)

        self.log(f"Stage 1: Target function analysis and phase sequence optimization")
        
        self.log(f"  Target evolution operator: cos({t:.4f} * x)")
        self.log(f"  Optimization algorithm: L-BFGS-B (sampling points: {2*d+1})")
        
        phases = self._find_phases(t, d)

        self.log(f"Stage 2: Construct QSP quantum circuit building blocks")
        
        reg = Register('q', 1)
        qc = Circuit(reg, name=f"QSP_Evolution")
        
        theta = np.arccos(np.clip(x, -1, 1))
        
        self.log(f"  Mount initial phase rotation: Rz({2*phases[0]:.4f})")
        qc.rz(2 * phases[0], 0) 
        
        self.log(f"  Loop mount {d} groups [signal operator W(x) + phase rotation Rz]")
        for k in range(1, d + 1):
            qc.rx(2 * theta, 0)
            qc.rz(2 * phases[k], 0)

        self.log(f"Stage 3: Execute quantum simulation calculation")
        
        sim_start = time.time()
        final_state = qc.execute(backend=backend, device=device, dtype=dtype).state
        sim_time = time.time() - sim_start
        
        self.log(f"  Underlying simulation computation time: {sim_time:.6f} seconds")

        self.log(f"Stage 4: Accuracy comparison analysis and post-processing")
        
        qsp_val = complex(final_state[0]) if hasattr(final_state, '__getitem__') else 0.0
        ideal_val = np.cos(t * x)
        abs_error = float(np.abs(qsp_val - ideal_val))
        
        self.log(f"  Test point x = {x}")
        self.log(f"  Theoretical expected real part: {ideal_val:.6f}, simulated real part: {qsp_val.real:.6f}")
        self.log(f"  Absolute error (L2): {abs_error:.6e}")

        self.log(f"Stage 5: Export quantum circuit diagram")
        
        output = {"Estimated value": qsp_val, "Ideal value": ideal_val, "Absolute error": abs_error, "Computation time (s)": sim_time}
        self.update_output(output)
        self.status = "success"
        self.summary = f"QSP simulation completed with absolute error {abs_error:.6e} for test eigenvalue x={x} at evolution time t={t} using polynomial degree d={d}."

        circuit_path = self.save_circuit(qc)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, qc)

    def _find_phases(self, t, d):
        """Find target phase sequence."""
        x_samples = np.linspace(-1, 1, 2*d+1)

        def get_p_val(x, phs):
            theta = np.arccos(np.clip(x, -1, 1))
            W = np.array([[x, 1j*np.sqrt(1-x**2)], [1j*np.sqrt(1-x**2), x]])
            def Rz(p): return np.array([[np.exp(1j*p), 0], [0, np.exp(-1j*p)]])
            U = Rz(phs[0])
            for k in range(1, len(phs)):
                U = U @ W @ Rz(phs[k])
            return U[0, 0]
        
        loss = lambda phs: np.mean([abs(get_p_val(x, phs) - np.cos(t * x))**2 for x in x_samples])
        res = minimize(loss, np.random.randn(d+1)*0.1, method='L-BFGS-B')
        return res.x

def test(t=1.0, d=10, x=0.5):
    """Test QSP algorithm for simulating $cos(t * x)$ evolution.

    Parameters:
        t: Target evolution time
        d: Polynomial degree
        x: Test eigenvalue
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    # Execute test
    algo = QSPAlgorithm(text_mode="legacy")
    result = algo.run(t=t, d=d, x=x)
    return result


if __name__ == "__main__":
    t = 7  # [PARAM]
    d = 10  # [PARAM]
    x = 0.1  # [PARAM]
    test(t=t, d=d, x=x)
