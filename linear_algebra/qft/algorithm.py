import time
import os
import numpy as np
from typing import Dict, Any, List, Optional

# Import core project components
from numpy.fft import fft, ifft
from unitarylab.core import Circuit
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QFTAlgorithm(BaseAlgorithm):
    """Quantum Fourier Transform Algorithm Module.

    This module implements the Quantum Fourier Transform (QFT) algorithm.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Quantum Fourier Transform Algorithm", prefix="QFT", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, n: int, state: np.ndarray = None, inverse: bool = False, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute quantum Fourier transform algorithm.

        Parameters:
            n: Number of qubits for the QFT
            state: Initial state vector (optional)
            inverse: Whether to execute the inverse QFT

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Number of qubits": n, "Initial state": state if state is not None else "default |0...0>", "Inverse": inverse}
        self.update_input(input)

        self.log(f"Stage 1: Constructing QFT circuit for {n} qubits (inverse={inverse})")
        qft = Circuit(n, name="QFT")
        for i in range(n-1, -1, -1):
            qft.h(i)
            for j in range(i-1, -1, -1):
                qft.mcp(np.pi/2**(i-j), j, i)
        for i in range(n//2):
            qft.swap(i, n - 1 - i)

        if inverse:
            qft = qft.dagger()
            qft.update_name("IQFT")
            qft.gate_sequence.update_name("IQFT")
        self.log(f"  Constructed {'inverse' if inverse else ''} QFT circuit")

        self.log(f"Stage 2: Performing quantum simulation")
        
        gs = Circuit(n, name="QFT Example")
        if state is not None:
            state = np.asarray(state, dtype=complex) / np.linalg.norm(state)
            gs.initialize(state, range(n))
            self.log(f"  Set initial state vector (normalized): {state}")
        else:
            self.log(f"  Using default initial state |0...0>")
        gs.append(qft, range(n))

        sim_start = time.time()
        final_state = gs.execute(backend=backend, device=device, dtype=dtype).state
        
        sim_time = time.time() - sim_start
        
        self.log(f"  Underlying simulation computation time: {sim_time:.4f} seconds")

        self.log(f"Stage 3: Executing classical numpy FFT for verification")
        if state is None:
            state = np.zeros(2**n)
            state[0] = 1.0
        expected_state = fft(state) / np.sqrt(2**n) if inverse else ifft(state) * np.sqrt(2**n)
        error = np.linalg.norm(final_state - expected_state)

        self.log(f"  Computed expected state vector using numpy {'FFT' if inverse else 'iFFT'}")
        self.log(f"  Final state vector from simulation: {final_state}")
        self.log(f"  Expected state vector from numpy: {expected_state}")
        self.log(f"  Verification error: {error:.4f}")

        self.log(f"Stage 5: Exporting circuit diagram")
        
        output = {"Final state": final_state, "Expected state": expected_state, "Verification error": error, "Computation time (s)": sim_time}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Execution successful. Verification error: {error:.4f}"
                
        # Save results
        circuit_path = self.save_circuit(gs.decompose())
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, gs)


def test(n=4, state=None, inverse=False):
    """Test quantum Fourier transform algorithm with specified parameters.

    Parameters:
        n: Number of qubits for the QFT
        state: Initial state vector (optional)
        inverse: Whether to execute the inverse QFT

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    if state is not None:
        state = np.asarray(state, dtype=complex)
        if state.ndim != 1 or state.size != 2**n:
            raise ValueError(f"Initial state vector must be a 1D array of size {2**n}")
    
    inverse = bool(inverse)
    algo = QFTAlgorithm(text_mode="legacy")
    result = algo.run(n=n, state=state, inverse=inverse)
    return result

if __name__ == "__main__":

    n = 3 # [PARAM]
    state = [1, 0, 0, 0, 0, 0, 0, 0] # [PARAM]
    inverse = False # [PARAM]
    test(n=n, state=state, inverse=inverse)