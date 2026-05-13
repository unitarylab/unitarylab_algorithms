import time
import os
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

# Import project core components
from unitarylab.core import Circuit
from unitarylab.library import QPE
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class HHLAlgorithm(BaseAlgorithm):
    """HHL Algorithm Module.

    This module implements the Harrow-Hassidim-Lloyd (HHL) algorithm for solving linear systems Ax = b.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="HHL Algorithm", prefix="HHL", text_mode=text_mode, algo_dir=algo_dir)
    
    def run(self, A: np.ndarray, b: np.ndarray, d: int) -> Dict[str, Any]:
        """Execute the HHL algorithm.

        Args:
            A: Hermitian matrix to be solved, dimension must be a power of 2
            b: Input vector
            d: Number of qubits in phase register
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Matrix": A, "Right-hand side": b, "Phase bits": d}
        self.update_input(input)

        start_time = time.time()

        self.log(f"Stage 1: Matrix preprocessing and adaptive parameter analysis")
        
        A = np.asarray(A, dtype=complex)
        b = np.asarray(b, dtype=complex).reshape(-1)
        N = A.shape[0]
        
        if A.shape != (N, N): raise ValueError("A must be a square matrix.")
        if not np.allclose(A, A.conj().T): raise ValueError("Current version requires A to be a Hermitian matrix.")
        if (N & (N - 1)) != 0: raise ValueError("Dimension N must be a power of 2.")
        if b.size != N: raise ValueError("Dimension of b does not match A.")
        
        n_sys = int(np.log2(N))
        norm_b = np.linalg.norm(b)
        if norm_b == 0: raise ValueError("Vector b cannot be all zeros.")
        b_state = b / norm_b
        
        # Extract eigenvalues to dynamically determine evolution time t and scaling factor
        lam = np.real(np.linalg.eigvalsh(A)).astype(float)
        lam_abs = np.abs(lam)
        nonzero = lam_abs[lam_abs > 1e-12]
        if nonzero.size == 0: raise ValueError("Eigenvalues of A are approximately zero, cannot invert.")

        lam_min, lam_max = float(np.min(nonzero)), float(np.max(nonzero))

        # If spectrum contains negative eigenvalues, use signed phase mode:
        # By constraining |lambda|*t < 1/2, separate positive and negative phases into [0,1/2) and (1/2,1).
        has_negative = bool(np.any(lam < -1e-12))
        signed_phase_mode = has_negative
        if signed_phase_mode:
            target_phi_max = 0.5 - 1.0 / (2 ** d)
            if target_phi_max <= 0:
                raise ValueError(f"Phase bits d={d} too small, cannot enable signed phase mode.")
        else:
            target_phi_max = 1.0 - 1.0 / (2 ** d)
        
        t = target_phi_max / lam_max
        grid = 2 ** d
        phi_min = lam_min * t 
        k_start = int(np.floor(phi_min * grid)) - 10
        if int(np.floor(phi_min * grid)) < 1:
            raise ValueError(f"Phase bits d={d} insufficient to resolve minimum phase, please increase d.")
        if signed_phase_mode:
            signed_cap = max(1, grid // 2 - 1)
            k_start = max(1, min(k_start, signed_cap))
        else:
            k_start = max(1, min(k_start, grid - 1))
        
        scale_factor = norm_b * t * grid / k_start
        
        self.log(f"  System dimension (N): {N} ({n_sys} System Qubits)")
        self.log(f"  Auto evolution time (t): {t:.6f}")
        self.log(f"  Phase grid starting point (k_start): {k_start}")
        self.log(f"  Phase decoding mode: {'signed (preserve eigenvalue sign)' if signed_phase_mode else 'unsigned'}")

        self.log(f"Stage 2: Building HHL quantum circuit")
        
        total_qubits = 1 + d + n_sys
        anc = 0
        phase_qubits = list(range(1, d + 1))
        system_qubits = list(range(d + 1, total_qubits))
        
        gs = Circuit(total_qubits, name="HHL_Algorithm")
        
        gs.initialize(b_state, system_qubits)
        self.log("  State preparation module mounted: Initialize |b>")
        
        U_mat, _ = self._expi_hermitian(A, t)
        U_circ = self._unitary_circuit_from_matrix(U_mat)
        
        qpe_circ = QPE(U_circ, d, return_circuit=True)
        gs.append(qpe_circ, phase_qubits + system_qubits)
        self.log("  QPE module mounted: Extract eigenphases")
        
        rot_circ = self._controlled_reciprocal_rotation(
            d, t, k_start, signed_phase=signed_phase_mode
        )
        gs.append(rot_circ, [anc] + phase_qubits)
        self.log("  Controlled reciprocal rotation module mounted: Nonlinear mapping 1/lambda")
        
        gs.append(qpe_circ.dagger(), phase_qubits + system_qubits)
        self.log("  Inverse QPE (iQPE) module mounted: System disentanglement")

        self.log(f"Stage 3: Executing quantum simulation")
        
        sim_start = time.time()
        final_state = gs.execute().state
        state_arr = np.asarray(final_state, dtype=complex).reshape(-1)
        sim_time = time.time() - sim_start
        
        self.log(f"  Low-level simulation time: {sim_time:.4f} seconds")

        self.log(f"Stage 4: Classical post-processing (post-selection to extract solution)")
        
        psi_sys, p_succ, x_q = self._postselect_solution_state(state_arr, scale_factor, d, n_sys)
        
        x_classical = np.linalg.solve(A, b)
        diff_norm = np.linalg.norm(x_q - x_classical)
        
        self.log(f"  Post-selection success probability P(anc=1, phase=|0>): {p_succ:.6f}")
        self.log(f"  Error between quantum approximation and classical exact solution (L2 Norm): {diff_norm:.6e}")

        self.log(f"Stage 5: Exporting quantum circuit diagram")
        
        output = {"Estimated solution (quantum)": x_q, "Exact solution (classical)": x_classical, "L2 error": diff_norm, "Post-selection probability": p_succ, "Computation time (s)": sim_time}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Execution successful. L2 error: {diff_norm:.6e}, Post-selection probability: {p_succ:.6f}"

        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, gs)

    def _decode_signed_phase_index(self, k: int, d: int) -> int:
        """Convert QPE phase index to signed index."""
        grid = 2 ** d
        half = grid // 2
        return k if k <= half else k - grid

    def _controlled_reciprocal_rotation(self, d: int, t: float, k_start: int,
                                        signed_phase: bool = False) -> Circuit:
        """Controlled rotation for eigenvalue reciprocal."""
        grid = 2 ** d
        gs = Circuit(d + 1, name=f"cond_Recip_Rot")
        controls = list(range(1, d + 1))
        target = 0 
        C = k_start

        if signed_phase:
            k_iter = range(1, grid)  # k=0 corresponds to zero eigenvalue component, skip to avoid division by zero
        else:
            k_iter = range(k_start, grid)

        for k in k_iter:
            if signed_phase:
                signed_k = self._decode_signed_phase_index(k, d)
                if signed_k == 0 or abs(signed_k) < k_start:
                    continue
                # Preserve sign: C / signed_k, yields positive and negative rotation angles.
                val = float(np.clip(C / signed_k, -1.0, 1.0))
            else:
                val = float(np.clip(C / k, -1.0, 1.0))
            
            flipped = []
            for i in range(d):
                if ((k >> i) & 1) == 0:
                    gs.x(i + 1)
                    flipped.append(i + 1)

            theta = 2.0 * np.arcsin(val)
            gs.mcry(theta, controls, target)

            for q in flipped:
                gs.x(q)

        return gs

    def _expi_hermitian(self, A: np.ndarray, t: float) -> Tuple[np.ndarray, np.ndarray]:
        """Compute U = exp(i A t)."""
        w, V = np.linalg.eigh(A)
        phases = np.exp(1j * 2.0 * np.pi * w * t)
        U = V @ np.diag(phases) @ V.conj().T
        return U, w

    def _unitary_circuit_from_matrix(self, U: np.ndarray) -> Circuit:
        """Package unitary matrix as a circuit."""
        n = int(np.log2(U.shape[0]))
        gs = Circuit(n, name="U")
        gs.unitary(U, list(range(n)))
        return gs

    def _postselect_solution_state(self, state: np.ndarray, scale: float, d: int, n: int) -> Tuple[np.ndarray, float, np.ndarray]:
        """Post-select ancilla=1 and phase=|0...0> and extract solution vector."""
        # 1. Extract slice where ancilla=1 (qubit 0 is the least significant bit)
        vec_anc1 = state[1::2] 
        
        # 2. Extract slice where phase=|0...0> (stride is 2^d)
        stride = 2 ** d
        vec_sys = vec_anc1[0::stride]
        
        x_q = np.array(vec_sys) * scale
        p = float(np.vdot(vec_sys, vec_sys).real)
        print(p)
        
        if p <= 0:
            raise ValueError("Post-selection probability is zero (ancilla=1 and phase=0 state did not occur).")
            
        psi_sys = vec_sys / np.sqrt(p)
        return psi_sys, p, x_q


def test(A = [[0.8, 0], [0, 0.4]], b = [1, 2], d = 11):
    """Execute the HHL algorithm.

    Args:
        A: Hermitian matrix to be solved, dimension must be a power of 2
        b: Input vector
        d: Number of qubits in phase register
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    A = np.array(A)
    b = np.array(b)
    d = int(d)

    # Run algorithm (using 11 phase bits)
    algo = HHLAlgorithm(text_mode="legacy")
    result = algo.run(A=A, b=b, d=d)
    return result


if __name__ == "__main__":
    A = [[0.8, 0], [0, 0.4]] # [PARAM]
    A = np.array(A)
    N = A.shape[0]
    if A is None or A.shape != (N, N):
        raise ValueError("A must be an N x N matrix")
    
    b = [1, 2] # [PARAM]
    b = np.array(b)
    if b is None or b.shape != (N,):
        raise ValueError("b must be a vector of size N")
    
    d = 12 # [PARAM]
    test(A=A, b=b, d=d)