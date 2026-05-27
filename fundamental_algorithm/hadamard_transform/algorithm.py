import time
import os
import numpy as np
from typing import Dict, Any, List, Optional

# Import core project components
from unitarylab.core import Circuit, Register
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class HadamardTransformAlgorithm(BaseAlgorithm):
    """Hadamard Transform Algorithm Module.

    This module implements n-qubit global Hadamard transform, supporting superposition
    state generation and reflexivity verification.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Hadamard Transform Algorithm", prefix="HA", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, n: int = 3, mode: str = "superposition", backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute Hadamard transform algorithm.

        Parameters:
            n: Number of qubits
            mode: Execution mode, choose 'superposition' or 'reflexive_test'
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Number of qubits": n}
        self.update_input(input)

        self.log(f"Stage 1: Preparing algorithm parameters")
        
        if n < 1:
            raise ValueError("Number of qubits n must be >= 1")
        if mode not in ["superposition", "reflexive_test"]:
            raise ValueError("mode must be 'superposition' or 'reflexive_test'")
            
        self.log(f"  Target register size: n = {n}")
        self.log(f"  Execution mode: {mode}")

        self.log(f"Stage 2: Building quantum circuit")
        
        gs = Circuit(n, name=f'Hadamard_{mode}')
        target_qubits = list(range(n))

        original_state = None

        if mode == "superposition":
            self._apply_hadamard_layer(gs, target_qubits)
            self.log(f"  Added Hadamard gates to all {n} qubits")
            
        elif mode == "reflexive_test":
            rng = np.random.default_rng()
            psi = rng.normal(size=2**n) + 1j * rng.normal(size=2**n)
            original_state = psi / np.linalg.norm(psi)
            
            gs.initialize(original_state, target=target_qubits)
            self.log(f"  Initialized random quantum state")
            
            for i in range(2):
                self._apply_hadamard_layer(gs, target_qubits)
            self.log(f"  Applied Hadamard transform 2 consecutive times")

        self.log(f"Stage 3: Executing quantum simulation")
        
        start_time = time.time()
        raw_result = gs.execute(backend=backend, device=device, dtype=dtype)
        
        if mode == "superposition":
            prob_dict = raw_result.probabilities
        else:
            prob_dict = {}

        end_time = time.time()
        comp_time = end_time - start_time

        self.log(f"  Computation time: {comp_time:.4f} seconds")
        self.log(f"  State vector dimension: {len(raw_result.state)}")

        self.log(f"Stage 4: Executing result verification and post-processing")
        
        is_success = False
        msg = ""
        max_deviation = 0.0

        if mode == "superposition":
            expected_prob = 1.0 / (2 ** n)
            is_uniform = all(np.isclose(p, expected_prob, atol=1e-5) for p in prob_dict.values())
            is_success = is_uniform and len(prob_dict) == (2 ** n)
            msg = "Algorithm execution successful" if is_success else "Algorithm execution failed"
            
            self.log(f"  Theoretical basis state probability: {expected_prob:.4f}")
            self.log(f"  Number of valid measured basis states: {len(prob_dict)}")
            self.log(f"  Uniformity verification: {'passed' if is_success else 'failed'}")
            
        elif mode == "reflexive_test":
            is_success = np.allclose(raw_result.state, original_state, atol=1e-10)
            max_deviation = np.max(np.abs(raw_result.state - original_state))
            msg = "Algorithm execution successful" if is_success else "Algorithm execution failed"
            
            self.log(f"  Maximum amplitude deviation: {max_deviation:.2e}")
            self.log(f"  State restoration verification: {'passed' if is_success else 'failed'}")

        self.log(f"Stage 5: Exporting circuit diagram")

        output = {"Computation time (s)": comp_time, "Probability distribution": prob_dict, "State vector": self._as_statevector(raw_result.state)}
        self.update_output(output)
        self.status = "success"
        self.summary = msg
        
        # Save results
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, gs)

    def _apply_hadamard_layer(self, gs: Circuit, target_qubits: List[int]) -> None:
        """Apply Hadamard gate to specified list of qubits."""
        for q in target_qubits:
            gs.h(q)

    def _as_statevector(self, res) -> np.ndarray:
        """Convert execution result to NumPy vector."""
        return np.asarray(res, dtype=complex)

    def _probabilities(self, statevec: np.ndarray, threshold: float = 1e-12) -> Dict[str, float]:
        """Calculate probability distribution and convert to binary string dictionary."""
        probs = np.abs(statevec) ** 2
        n = int(np.log2(len(probs)))
        out = {}
        for idx, p in enumerate(probs):
            if p < threshold: continue
            bits = format(idx, f"0{n}b")
            out[bits] = float(p)
        return dict(sorted(out.items()))

def test(n=3):
    """Execute Hadamard transform algorithm.

    Parameters:
        n: Number of qubits
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    algo = HadamardTransformAlgorithm(text_mode="legacy")

    result = algo.run(n, 'superposition')
    return result

if __name__ == "__main__":
    n = 3 # [PARAM]
    test(n)