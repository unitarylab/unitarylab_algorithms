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


class GroverAlgorithm(BaseAlgorithm):
    """
    Grover Algorithm Module (Independent class version)
    Encapsulates the entire process of initial state preparation, Oracle marking, Diffuser reflection,
    and final state verification, including standardized phase logging output and ASCII result panel.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Grover Algorithm", prefix="GROVER", text_mode=text_mode, algo_dir=algo_dir)


    def run(self, n:int, target:str) -> Dict[str, Any]:
        """
        Modifiable input parameters:
             - n: Number of qubits in the data register (integer)
             - target: Target state as a binary string (e.g., '101' for 3 qubits)

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """
        
        input = {"Number of qubits (n)": n, "Target state (binary string)": target}
        self.update_input(input)

        # Stage 1 
        self.log(f"Stage 1/5: Preparing algorithm parameters...")

        # 从 target_state 构建均匀叠加态 U 和 good_zero_qubits
        U = Circuit(n, name='U')
        for q in range(n):
            U.h(q)
        p = 1.0 / (2 ** n)

        # good_zero_qubits: 目标态对应位为 '0' 的比特索引
        target_qubits_index = [i for i in range (n)]
        target_qubits_value = [int(char) for char in target]

        n_data = U.get_num_qubits()
        ancilla = n_data  # Ancilla qubit at the last position
        
        reps = self._get_optimal_iterations(p)
        
        self.log(f"  - Data register size: n = {n_data} (total {n_data + 1} qubits)")
        self.log(f"  - Initial success probability p: {p:.4f}")
        self.log(f"  - Computed iteration count (Reps): {reps}")
        self.log(f"Stage 1/5 complete ✓")

        # Stage 2 
        self.log(f"Stage 2/5: Building quantum circuit...")
        
        gs = Circuit(n_data + 1, name='Grover')
        data_qubits = list(range(n_data))

        # 1) Prepare initial state |psi>
        gs.append(U, data_qubits)

        # 2) Expand Grover/AA iterations
        for _ in range(reps):
            self._build_oracle(gs, target_qubits_index, target_qubits_value, ancilla=ancilla)
            self._build_diffuser(gs, U=U, data_qubits=data_qubits, ancilla=ancilla)
        
        self.log(f"Stage 2/5 complete ✓")

        # Stage 3 
        self.log(f"Stage 3/5: Running quantum simulation...")
        
        start_time = time.time()
        re_state = gs.execute().state
        end_time = time.time()
        comp_time = end_time - start_time

        self.log(f"  - Computation time: {comp_time:.4f} s")
        self.log(f"Stage 3/5 complete ✓")

        # Phase 4 
        self.log(f"Stage 4/5: Running classical post-processing (verifying amplification effect)...")
        
        probabilities = np.abs(re_state) ** 2
        find_max = np.argmax(probabilities)
        target_prob = probabilities[find_max]
        find_state = format(find_max, f'0{n_data}b')

        # Determine if amplification was successful (at least significantly improved over initial p)
        is_success = (find_state == target)
        
        self.log(f"  - Initial target-state probability: {p:.4f}")
        self.log(f"  - Amplified target-state probability: {target_prob:.4f}")
        self.log(f"  - Result check: find target state {find_state}")
        self.log(f"Stage 4/5 complete ✓")
        
        # Stage 5 
        self.log(f"Stage 5/5: Exporting quantum circuit diagram...")

        output = {"Amplified target-state probability": target_prob, "Result": find_state}
        self.update_output(output)
        self.status = 'success' if is_success else 'partial_success'
        self.summary = f"Execution successful. Find state {find_state} with probability {target_prob:.4f}."
        
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        
        return self._build_return_dict(True, circuit_path, filename, gs)
    
    def _prepare_kickback_ancilla_minus(self, gs: Circuit, ancilla: int) -> None:
        """Prepare ancilla in |-> = H X |0>"""
        gs.x(ancilla)
        gs.h(ancilla)

    def _unprepare_kickback_ancilla_minus(self, gs: Circuit, ancilla: int) -> None:
        """Unprepare ancilla back to |0>"""
        gs.h(ancilla)
        gs.x(ancilla)

    def _build_oracle(self, gs: Circuit, target_qubits_index: list[int], target_qubits_value: list[int] | None, ancilla: int) -> None:
        """Phase flip (-1) on computational basis states where `zero_qubits` are |0>"""
        self._prepare_kickback_ancilla_minus(gs, ancilla)

        if target_qubits_value is None:
            target_qubits_value = [0 for _ in target_qubits_index]

        gs.mcx(target_qubits_index, ancilla, target_qubits_value)
        
        # for q in zero_qubits:
        #     gs.x(q)

        # controls = list(zero_qubits)
        # if len(controls) == 0:
        #     gs.z(ancilla)
        # elif len(controls) == 1:
        #     gs.cx(controls[0], ancilla)
        # else:
        #     gs.mcx(controls, ancilla)

        # for q in zero_qubits:
        #     gs.x(q)

        self._unprepare_kickback_ancilla_minus(gs, ancilla)

    def _build_diffuser(self, gs: Circuit, U: Circuit, data_qubits: List[int], ancilla: int) -> None:
        """Reflection about |psi> = U|0..0>"""
        gs.append(U.dagger(), data_qubits)
        self._build_oracle(gs,target_qubits_index=list(data_qubits), target_qubits_value = None, ancilla=ancilla)
        gs.append(U, data_qubits)

    def _get_optimal_iterations(self, p: float) -> int:
        """Calculate optimal Grover iteration count based on initial probability p"""
        theta = math.asin(math.sqrt(p))
        # Use round() instead of math.floor() to solve the issue of floating-point precision causing 0.9999 to become 0
        r = int(round((math.pi / (4.0 * theta)) - 0.5))
        return max(0, r)
    

def test(n=3, target='101'):
    """
    Test the Grover Algorithm main workflow, supporting configurable number of qubits and target state.
    Modifiable input parameters:
            - n: Number of qubits in the data register (integer)
            - target: Target state as a binary string (e.g., '101' for 3 qubits)

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    if isinstance(target, int):
         target = str(target)
    if not isinstance(n, int):
        n = int(n)

    algo = GroverAlgorithm(text_mode="legacy")
    result = algo.run(n=n, target=target)
    return result


if __name__ == "__main__":
    n = 3         # [PARAM]
    target = '101' # [PARAM]
    test(n=n, target=target)