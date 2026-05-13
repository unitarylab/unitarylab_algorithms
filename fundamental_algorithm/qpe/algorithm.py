import time
import os
import numpy as np
from typing import Dict, Any, List, Optional

# Import core project components
from unitarylab.core import Circuit
from unitarylab.library import IQFT
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QPEAlgorithm(BaseAlgorithm):
    """Quantum Phase Estimation Algorithm Module.

    This module implements the Quantum Phase Estimation (QPE) algorithm for extracting
    eigenphases of unitary operators.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Quantum Phase Estimation Algorithm", prefix="QPE", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, U: Circuit, d: int, 
            prepare_target: Optional[Circuit] = None) -> Dict[str, Any]:
        """Execute quantum phase estimation algorithm.

        Parameters:
            U: Unitary operator circuit whose phase is to be estimated
            d: Number of phase register qubits (precision is 1/2^d)
            prepare_target: Circuit to prepare eigenstate (defaults to |0> state)
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Unitary operator": U.name, "Precision bits": d}
        self.update_input(input)

        self.log(f"Stage 1: Validating and parsing parameters")
        
        n_target = U.get_num_qubits()
        total_qubits = d + n_target
        
        self.log(f"  Phase register: {d} Qubits")
        self.log(f"  Target register: {n_target} Qubits")
        self.log(f"  Total qubits: {total_qubits}")
        self.log(f"  Theoretical phase resolution: 1/{2**d} ≈ {1/(2**d):.6f}")

        self.log(f"Stage 2: Building QPE core circuit")
        
        gs = self.build_qpe_circuit(U, d, prepare_target)
        
        self.log(f"  Built controlled U operator sequence")
        self.log(f"  Connected IQFT module")

        self.log(f"Stage 3: Executing quantum simulation")
        
        sim_start = time.time()
        final_state = gs.execute()
        
        sim_time = time.time() - sim_start
        
        self.log(f"  Underlying simulation computation time: {sim_time:.4f} seconds")

        self.log(f"Stage 4: Executing classical post-processing")
        
        phase_qubits = list(range(d))
        phase_probs = final_state._phase_probabilities_from_state(phase_qubits, endian="little", threshold=1e-8)
        
        sorted_phases = sorted(phase_probs.items(), key=lambda item: item[1], reverse=True)
        best_bits_str = sorted_phases[0][0]
        best_prob = sorted_phases[0][1]
        
        phi_est = int(best_bits_str, 2) / (2 ** d)
        
        self.log(f"  Optimal phase bit string: |{best_bits_str}> (probability: {best_prob:.4f})")
        self.log(f"  Equivalent decimal estimated phase: {phi_est:.6f}")

        self.log(f"Stage 5: Exporting circuit diagram")
        
        output = {"Estimated phase": phi_est, "Best phase bit string": best_bits_str, "Best phase probability": best_prob, "Computation time (s)": sim_time, "Phase probabilities": sorted_phases[:3]}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Execution successful. Estimated phase: {phi_est:.6f} (bits: {best_bits_str}, prob: {best_prob:.4f})"
                
        # Save results
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, gs)

    def build_qpe_circuit(self, U: Circuit, d: int, prepare_target: Optional[Circuit] = None) -> Circuit:
        """Build pure QPE circuit and return as independent Circuit, convenient for embedding in other algorithms."""
        n_target = U.get_num_qubits()
        gs = Circuit(d + n_target, name=f"QPE_d{d}")
        phase_qubits = list(range(d))
        target_qubits = list(range(d, d + n_target))

        if prepare_target is not None:
            if prepare_target.get_num_qubits() != n_target:
                raise ValueError("prepare_target qubit count must match U.")
            gs.append(prepare_target, target_qubits)

        for q in phase_qubits:
            gs.h(q)

        for k in range(d):
            power = 2 ** k
            gs.append(U.repeat(power), target=target_qubits, control=phase_qubits[k], control_state='1')

        iqft_circ = IQFT(d)
        gs.append(iqft_circ, phase_qubits)

        return gs


def test(p = 0.25, n = 3):
    """Test quantum phase estimation algorithm. Given a phase, construct a rotation gate with that phase and verify if the algorithm can estimate it correctly.

    Parameters:
        p: Target probability amplitude squared (0 < p < 1) for the state |1> under the unitary operator (e.g., T gate corresponds to p=0.25)
        n: Number of phase register qubits (precision bits)
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    
    U = Circuit(1, name='U')
    U.p(2 * np.pi * p, 0)
    
    prep_state = Circuit(1, name='|1>')
    prep_state.x(0)
    
    algo = QPEAlgorithm(text_mode="legacy")
    result = algo.run(U=U, d=n, prepare_target=prep_state)
    return result

if __name__ == "__main__":

    p = 0.25 # [PARAM]
    n = 3 # [PARAM]
    test(p=p, n=n)