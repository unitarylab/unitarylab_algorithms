import os
import time
from typing import Any, Dict, List
import numpy as np
from unitarylab import Circuit, Register, ClassicalRegister

try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm



class SimonAlgorithm(BaseAlgorithm):
    """Simon algorithm for finding hidden mask s in f(x)=f(x xor s)."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Simon Algorithm", prefix="SIMON", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, s: str = "1010", backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """
        Run Simon algorithm to find hidden mask s in f(x)=f(x xor s).
        
        Args:
            s: The hidden mask string (binary) to be found.

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """
        input = {"Hidden mask": s}
        self.update_input(input)

        self.log("Stage 1: Parameter preparation")

        n = len(s)
        if s.find('1') == -1:
            raise ValueError("Secret string s cannot be all zeros")
            
        self.log(f"  Secret string s: {s}")
        self.log(f"  Register size: n = {n} (total {2*n} qubits)")

        # Stage 2: Quantum circuit construction
        self.log(f"Stage 2: Building quantum circuit")
        
        rx = Register('x', n)
        ry = Register('y', n)
        cqr= ClassicalRegister('cr',n)
        gs = Circuit(rx, ry, cqr, name=f'Simon_{s}')

        gs.h(rx[:]) 
        self._build_simon_oracle(gs, s)
        gs.measure(ry[:], cqr[:])
        gs.h(rx[:])

        # Stage 3: Quantum simulation
        self.log(f"Stage 3: Executing quantum simulation")
        
        start_time = time.time()
        re_state = gs.execute(backend=backend, device=device, dtype=dtype)
        state_basis_dict = re_state.calculate_state(range(n))
        end_time = time.time()
        comp_time = end_time - start_time

        self.log(f"  Computation time: {comp_time:.4f} seconds")
        self.log(f"  Number of valid basis states measured: {len(state_basis_dict)}")

        # Stage 4: Classical post-processing
        self.log(f"Stage 4: Classical post-processing (solving linear equations)")
        
        basis = self._get_basis_simple(list(state_basis_dict.keys()), n)
        found_s = self._solve_simon_general(basis, n)
        is_success = (found_s == s)
        
        self.log(f"  Extracted linearly independent equations: {len(basis)}")
        self.log(f"  Computed result s: {found_s}")
        self.log(f"  Verification: {'Success' if is_success else 'Failed'}")

        # Stage 5: Export circuit diagram
        self.log(f"Stage 5: Exporting circuit diagram")
        
        output = {"Computed s": found_s, "Valid states": len(state_basis_dict), "computation time (s)": comp_time, "Register size": n, "Equations": len(basis)}
        self.update_output(output)
        self.status = "success" if is_success else "failed"
        self.summary = f"Algorithm executed successfully with result s={found_s}" if is_success else "Algorithm failed to solve"

        # Save results
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        
        return self._build_return_dict(is_success, circuit_path, filename, gs)

    def _build_simon_oracle(self, gs: Circuit, s: str) -> None:
        """Build U_f oracle for Simon problem."""
        n = len(s)
        for i in range(n - 1, -1, -1):
            gs.cx(i, i + n)

        pivot_idx = s.find("1")
        for i in range(n):
            if s[i] == "1":
                gs.cx(n - 1 - pivot_idx, n - 1 - i + n)

    def _get_basis_simple(self, state_list: List[str], n_qubits: int) -> List[str]:
        """Select linearly independent vectors from measured states."""
        basis_list: List[str] = []
        seen_pivots = set()
        for bitstring in state_list:
            pivot = bitstring.find("1")
            if pivot != -1 and pivot not in seen_pivots:
                seen_pivots.add(pivot)
                basis_list.append(bitstring)
            if len(basis_list) == n_qubits - 1:
                break
        return basis_list

    def _solve_simon_general(self, basis_list: List[str], n: int) -> str:
        """Solve linear equations over GF(2) by back substitution."""
        s_vec = [0] * n
        pivot_map = {row.find("1"): row for row in basis_list if row.find("1") != -1}
        free_idx = next((i for i in range(n) if i not in pivot_map), -1)

        if free_idx == -1:
            return "Error"

        s_vec[free_idx] = 1
        for p in sorted(pivot_map.keys(), reverse=True):
            row = pivot_map[p]
            dot_sum = 0
            for j in range(p + 1, n):
                if row[j] == "1":
                    dot_sum ^= s_vec[j]
            s_vec[p] = dot_sum

        return "".join(map(str, s_vec))


def test(s = "1101") -> Dict[str, Any]:
    """
    Run Simon algorithm to find hidden mask s in f(x)=f(x xor s).
    
    Args:
        s: The hidden mask string (binary) to be found.

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    if not isinstance(s, str):
        s = str(s)

    algo = SimonAlgorithm(text_mode="legacy")
    return algo.run(s=s)


if __name__ == "__main__":
    s = "1101" # [PARAM]
    test(s)
