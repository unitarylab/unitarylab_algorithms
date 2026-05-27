import time
import os
import numpy as np
from typing import Dict, Any, List, Tuple

# Import project core components
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


class LCUAlgorithm(BaseAlgorithm):
    """LCU Algorithm Module.

    This module implements the quantum circuit representation of non-unitary operator M = ∑ α_j U_j.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="LCU Algorithm", prefix="LCU", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, alphas: List[float], unitaries: List[Circuit], 
            n_sys: int, initial_state: Circuit = None, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute the LCU algorithm.

        Args:
            alphas: List of non-negative coefficients
            unitaries: List of unitary operator circuits
            n_sys: Number of qubits in system register
            initial_state: Initial state of system register (optional)
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"LCU coefficients (alphas)": alphas, "Unitary operators": [U.name for U in unitaries], "System qubits": n_sys}
        self.update_input(input)

        self.log(f"Stage 1: Parsing and validating LCU coefficients and operators")
        
        if len(alphas) != len(unitaries):
            raise ValueError("Length of alphas must match length of unitaries.")

        m = len(alphas)
        n_anc = int(np.ceil(np.log2(m)))
        total_qubits = n_anc + n_sys
        
        s_norm = float(np.sum(alphas))
        
        self.log(f"  LCU term count (m): {m}")
        self.log(f"  Ancilla register (Ancilla): {n_anc} Qubits")
        self.log(f"  Data register (System): {n_sys} Qubits (Total {total_qubits} Qubits)")
        self.log(f"  Normalization constant (s = sum(alpha)): {s_norm:.6f}")

        self.log(f"Stage 2: Building LCU core quantum circuit")
        
        # Register definition (using list indices for convenience, 0~n_anc-1 are ancilla, rest are system)
        anc_qubits = list(range(n_anc))
        sys_qubits = list(range(n_anc, total_qubits))
        
        qc = Circuit(total_qubits, name='LCU_circuit')
        
        # 1. Prepare system initial state (if provided)
        if initial_state is not None:
            if initial_state.get_num_qubits() != n_sys:
                raise ValueError("Number of qubits in initial_state must equal n_sys")
            qc.append(initial_state, sys_qubits)
            self.log(f"  - User-provided system initial state loaded")
            
        # 2. Build and add V operator
        self.log(f"  - Building and applying V operator (coefficient state preparation)...")
        V_circ = self._build_V(alphas, s_norm, m, n_anc)
        qc.append(V_circ, anc_qubits)
        
        # 3. Build and add SELECT(U) operator
        self.log(f"  - Building and applying SELECT operator (multi-controlled multiplexer)...")
        select_circ = self._build_select(unitaries, m, n_anc, n_sys)
        qc.append(select_circ, range(total_qubits))
        
        # 4. Build and add V_dagger operator
        self.log(f"  - Building and applying V_dagger operator...")
        V_dag_circ = V_circ.dagger()
        qc.append(V_dag_circ, anc_qubits)
        
        self.log(f"Stage 2/5: Quantum circuit construction complete ✓")

        # ================= Stage 3 =================
        self.log(f"Stage 3/5: Executing quantum simulation...")
        
        sim_start = time.time()
        raw_result = qc.execute(backend=backend, device=device, dtype=dtype)
        sim_time = time.time() - sim_start
        
        self.log(f"  Low-level simulation time: {sim_time:.4f} seconds")

        self.log(f"Stage 4/5: Classical post-processing (extracting LCU success probability)")
        
        anc_probs = raw_result._phase_probabilities_from_state(anc_qubits, endian="little", threshold=0.0)
        
        zero_state_str = "0" * n_anc 
        success_prob = float(anc_probs.get(zero_state_str, 0.0))
        
        is_success = success_prob > 1e-6
        
        self.log(f"  Probability of all ancilla bits being |0> (LCU success rate): {success_prob:.6f}")
        self.log(f"  State assessment: {'Valid' if is_success else 'Very low success rate, possibly due to system operator cancellation'}")

        self.log(f"Stage 5/5: Exporting quantum circuit diagram")

        result_state = raw_result.state.reshape(-1, 2**len(anc_qubits))
        output = {"Success probability": success_prob, "Computation time (s)": sim_time, "Result state": result_state[:,0]}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Execution successful. LCU success probability: {success_prob:.6f}"        

        # Save results
        circuit_path = self.save_circuit(qc)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, qc)

    def _build_V(self, alphas: List[float], s_norm: float, m: int, n_anc: int) -> Circuit:
        """Build V operator to prepare coefficient superposition state."""
        dim = 2 ** n_anc
        state = np.zeros(dim)
        for j in range(m):
            state[j] = np.sqrt(alphas[j] / s_norm)
        
        qc = Circuit(n_anc, name="V")
        qc.initialize(state, range(n_anc))
        return qc

    def _build_select(self, unitaries: List[Circuit], m: int, n_anc: int, n_sys: int) -> Circuit:
        """Build SELECT operator to implement multi-controlled multiplexer."""
        qc = Circuit(n_anc + n_sys, name="SELECT-U")
        anc_qubits = list(range(n_anc))
        sys_qubits = list(range(n_anc, n_anc + n_sys))
        
        for j, U in enumerate(unitaries):
            ctrl_state = format(j, f"0{n_anc}b")
            if U.order == 'little':
                ctrl_state = ctrl_state[::-1]
            qc.append(U, target=sys_qubits, control=anc_qubits, control_state=ctrl_state)
            
        return qc
    
def format_pauli_list(pauli_str):
    if isinstance(pauli_str, list):
        return pauli_str
    
    # 把 ，；;等中文逗号替换成英文逗号，并分割成列表
    pauli_str = pauli_str.replace("；", ",").replace(";", ",").replace("，", ",")
    pauli_list = pauli_str.split(',')
    return [p.strip() for p in pauli_list if p.strip()]

def test(n=1, alphas = [0.6, 0.4], paulis = ['I', 'X']):
    """Execute the LCU algorithm.

    Args:
        n: Number of qubits in the system register
        alphas: List of non-negative coefficients
        paulis: List of Pauli strings representing unitary operators (e.g., 'IX', 'ZZ', etc.)
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    alphas = list(map(float, alphas))
    paulis = format_pauli_list(paulis)

    if len(alphas) != len(paulis):
        raise ValueError("alphas and paulis must have the same length")

    n_sys = n
    if any(len(p) != n_sys for p in paulis):
        raise ValueError("All Pauli strings must have the same length")

    # 根据 paulis 自动构造 Circuit 列表
    coef = []
    unitaries = []
    for i, pauli_str in enumerate(paulis):
        U = Circuit(n_sys, name=f"{pauli_str}")
        if alphas[i] == 0:
            continue
        elif alphas[i] < 0:
            coef.append(-alphas[i])
            U.gp(np.angle(-1))
        else:
            coef.append(alphas[i])

        for q, p in enumerate(pauli_str):
            if p == 'I':
                continue
            if p == 'X':
                U.x(q)
            elif p == 'Y':
                U.y(q)
            elif p == 'Z':
                U.z(q)
            else:
                raise ValueError(f"Unsupported Pauli operator: {p}")
        unitaries.append(U)


    algo = LCUAlgorithm(text_mode="legacy")
    # Run algorithm
    result = algo.run(alphas=coef, unitaries=unitaries, n_sys=n)
    return result


if __name__ == "__main__":
    n = 1 # [PARAM]
    alphas = [0.6, 0.4] # [PARAM]
    paulis = ['I', 'X'] # [PARAM]
    
    # 运行算法
    test(n=n, alphas=alphas, paulis=paulis)