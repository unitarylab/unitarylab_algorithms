import time
import os
import math
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


class AmplitudeAmplificationAlgorithm(BaseAlgorithm):
    """
    Amplitude Amplification Algorithm Module

    Functionality: Amplifies the amplitude of target states through Grover iterations,
    increasing the probability of measuring the target state.
    Applicable to scenarios requiring enhanced success probability of specific quantum states.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Amplitude Amplification Algorithm", prefix="AA", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, U: Circuit, good_zero_qubits: List[int], p: float, 
            reps: Optional[int] = None) -> Dict[str, Any]:
        """
        Run the amplitude amplification algorithm.

        Parameters:
            U: Initial state preparation circuit (without ancilla qubit)
            good_zero_qubits: Bit indices defining the target state (these bits must be |0⟩)
            p: Initial success probability (used to automatically infer Grover iteration count)
            reps: Manually specified iteration count (overrides p calculation if provided)

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {
            "U": "Given quantum circuit",
            "Target State": good_zero_qubits,
            "Initial Success Probability": p,
            "Repetitions": reps
        }
        self.update_input(input)

        # Stage 1: Parameter preparation
        self.log(f"Stage 1: Parameter preparation")
        
        n_data = U.get_num_qubits()
        ancilla = n_data
        
        if reps is None:
            if not (0.0 < p < 1.0):
                raise ValueError("Initial probability p must satisfy 0 < p < 1")
            reps = self._get_optimal_iterations(p)
            
        self.log(f"  Data register size: {n_data} (total {n_data + 1} qubits)")
        self.log(f"  Target state condition: Qubits {good_zero_qubits} must all be |0>")
        self.log(f"  Initial success probability p: {p:.4f}")
        self.log(f"  Initial angle theta/2: {math.asin(math.sqrt(p)):.4f} radians")
        self.log(f"  Iteration count: {reps}")

        # Stage 2: Quantum circuit construction
        self.log(f"Stage 2: Building quantum circuit")
        
        gs = Circuit(n_data + 1, name='Amplitude_Amplification')
        data_qubits = list(range(n_data))

        gs.append(U, data_qubits)

        for _ in range(reps):
            self._build_oracle(gs, zero_qubits=good_zero_qubits, ancilla=ancilla)
            self._build_diffuser(gs, U=U, data_qubits=data_qubits, ancilla=ancilla)

        # Stage 3: Quantum simulation
        self.log(f"Stage 3: Executing quantum simulation")
        
        start_time = time.time()
        re_state = gs.execute()
        state_basis_dict = re_state.calculate_state(data_qubits)
        end_time = time.time()
        comp_time = end_time - start_time

        self.log(f"  Computation time: {comp_time:.4f} seconds")
        self.log(f"  Number of valid measured basis states: {len(state_basis_dict)}")

        # Stage 4: Classical post-processing
        self.log(f"Stage 4: Classical post-processing (verifying amplification effect)")
        
        target_prob = 0.0
        for basis_str, state_info in state_basis_dict.items():
            is_target = all(basis_str[q] == '0' for q in good_zero_qubits)
            if is_target:
                if isinstance(state_info, dict):
                    if 'prob' in state_info:
                        target_prob += float(state_info['prob'])
                    elif 'probability' in state_info:
                        target_prob += float(state_info['probability'])
                    elif 'amp' in state_info:
                        target_prob += abs(state_info['amp']) ** 2
                    else:
                        target_prob += float(list(state_info.values())[0])
                else:
                    target_prob += float(state_info)

        is_success = target_prob > p
        
        self.log(f"  Initial target state probability: {p:.4f}")
        self.log(f"  Amplified angle {reps*2+1} times theta/2: {(reps*2+1)*math.asin(math.sqrt(p)):.4f} radians")
        self.log(f"  Amplified target state probability: {target_prob:.4f}")
        self.log(f"  Result verification: {'success' if is_success else 'failed'}")

        # Stage 5: Export circuit diagram
        self.log(f"Stage 5: Exporting circuit diagram")
        
        output = {
            "Amplified Target Probability": target_prob,
            "Initial Success Probability": p,
            "Repetitions": reps,
            "Computation Time (s)": comp_time,
            "Data register size": n_data
        }
        self.update_output(output)
        self.status = "success" if is_success else "failed"
        self.summary = f"Algorithm execution successful with amplified probability {target_prob:.4f}" if is_success else "Algorithm execution failed"

        # Save results
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        return self._build_return_dict(is_success, circuit_path, filename, gs)

    def _prepare_kickback_ancilla_minus(self, gs: Circuit, ancilla: int) -> None:
        """Prepare ancilla qubit in |-> = H X |0> state."""
        gs.x(ancilla)
        gs.h(ancilla)

    def _unprepare_kickback_ancilla_minus(self, gs: Circuit, ancilla: int) -> None:
        """Restore ancilla qubit to |0> state."""
        gs.h(ancilla)
        gs.x(ancilla)

    def _build_oracle(self, gs: Circuit, zero_qubits: List[int], ancilla: int) -> None:
        """Build Oracle, apply phase flip to computational basis states where zero_qubits are all |0>."""
        self._prepare_kickback_ancilla_minus(gs, ancilla)

        for q in zero_qubits:
            gs.x(q)

        controls = list(zero_qubits)
        if len(controls) == 0:
            gs.z(ancilla)
        elif len(controls) == 1:
            gs.cx(controls[0], ancilla)
        else:
            gs.mcx(controls, ancilla)

        for q in zero_qubits:
            gs.x(q)

        self._unprepare_kickback_ancilla_minus(gs, ancilla)

    def _build_diffuser(self, gs: Circuit, U: Circuit, data_qubits: List[int], ancilla: int) -> None:
        """Build diffusion operator, implementing reflection about |psi> = U|0..0> state."""
        gs.append(U.dagger(), data_qubits)
        self._build_oracle(gs, zero_qubits=list(data_qubits), ancilla=ancilla)
        gs.append(U, data_qubits)

    def _get_optimal_iterations(self, p: float) -> int:
        """Calculate optimal iteration count based on initial probability p."""
        theta = math.asin(math.sqrt(p))
        r = int(round((math.pi / (4.0 * theta)) - 0.5))
        return max(0, r)


def test(p = 0.1, reps = 3):
    """
    Test the amplitude amplification algorithm with a simple 2-qubit example.

    Parameters:
        p: Initial success probability (used to construct the test circuit)
        reps: Manually specified iteration count (overrides p calculation if provided)

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    if not isinstance(p, float):
        p = float(p)
    if not isinstance(reps, int):
        reps = int(reps)
        
    theta = math.acos(math.sqrt(p))
    U_test = Circuit(2, name='U')
    U_test.ry(2 * theta, 0)  # Rotate to achieve initial probability p for |00> state

    good_zero_qubits = [0, 1]  # Target state is |00>

    algo = AmplitudeAmplificationAlgorithm(text_mode="legacy")
    result = algo.run(
        U=U_test, 
        good_zero_qubits=good_zero_qubits, 
        p=p, 
        reps=reps
    )

    return result


if __name__ == "__main__":
    p = 0.1 # [PARAM]
    reps = 3 # [PARAM]
    test(p=p, reps=reps)
