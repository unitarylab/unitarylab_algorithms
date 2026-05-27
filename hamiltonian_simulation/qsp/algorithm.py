import time
import os
import math
import numpy as np
from scipy.linalg import expm, norm
from typing import Dict, Any, List
from scipy.special import jn

# 导入项目核心组件
from unitarylab import Register, Circuit
from unitarylab.library import block_encode
from unitarylab.library._qsp import QSP
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QSPHSAlgorithm(BaseAlgorithm):
    """
    Hamiltonian simulation with Quantum Signal Processing.

    The QSP method constructs a quantum circuit that approximates the time evolution operator exp(-iHt) by encoding the Hamiltonian's eigenvalues into a signal and applying a sequence of controlled unitaries and single-qubit rotations. This approach can achieve high precision with fewer gates compared to Trotterization, especially for long evolution times.

    """

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="QSP Hamiltonian Simulation Algorithm", prefix="QSP_HS", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, H: np.ndarray, t: float, error: float, degree: int = 15, beta: float = 0.7, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """
        Initialize the QSP simulator.

        Parameters:
            H : numpy.ndarray
                Hamiltonian matrix (square Hermitian).
            t : float
                Total evolution time.
            error : float
                Desired approximation error (currently unused, reserved for future
                adaptive implementations).
            degree : int, optional
                Degree of the QSP polynomial. Larger values improve accuracy
                but increase circuit depth. Default is 15.
            beta : float, optional
                Preconditioning factor (0 < beta < 1) to ensure numerical stability.
                Default is 0.7.

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Hamiltonian": H, "Evolution time": t, "error": error, "degree": degree, "beta": beta}
        self.update_input(input)

        # Stage 1: Format and validate input
        self.log("Stage 1: Formatting and validating input.")
        dim, H, n = self._format_system(H, t, error)
        encoded_H = block_encode(H, method="nagy")      # obtain block-encoding of H
        UH = encoded_H.circuit                     # circuit that block-encodes H/α
        alpha = encoded_H.alpha                    # scaling factor α
        m = encoded_H.total_qubits - n                # total qubits used in block-encoding (incl. ancillas)
        self.log(f"    Block-encoded Hamiltonian with α={alpha:.4f} using {m} qubits.")

        self.log("Stage 2: Estimating required QSP degree and time slicing.")
        time_slices = 1
        max_time_slices = max(1, int(os.environ.get('QSP_MAX_TIME_SLICES', '4096')))
        while time_slices < max_time_slices:
            cand_slice_time = t / time_slices
            cand_slice_degree = self._estimate_required_degree(alpha, cand_slice_time, error)
            if cand_slice_degree <= degree:
                break
            time_slices *= 2

        slice_time = t / time_slices
        slice_degree_target = self._estimate_required_degree(alpha, slice_time, error)
        degree = min(max(int(degree), slice_degree_target), degree)
        self.log(f"    Chosen time slices: {time_slices}, slice time: {slice_time:.4f}, target degree per slice: {slice_degree_target}.")   

        self.log("Stage 3: Constructing QSP circuit for one time slice and composing by matrix power.")
        factor = 2 / beta                      # factor to recover exp(-iHt) from (cos - i sin) / (β/2)
        if beta <= 0 or beta >= 1:
            raise ValueError("beta must be between 0 and 1, strictly speaking (0, 1)!")
        t = alpha * slice_time       # dimensionless parameter x = (H/α)·(α * slice_time) for each slice

        self.log(f"    Approximating the real component (cos) for t = {t:.4f}")

        # Generate Chebyshev coefficients of β·cos(tx) using Bessel functions
        d = int(degree)
        coef_cos = np.zeros(d + 1)
        coef_cos[0] = jn(0, t) * beta
        for i in range(1, d + 1):
            if i % 2 == 0:
                coef_cos[i] = jn(i, t) * 2 * (-1) ** (i / 2) * beta
        cos_Ht = QSP(UH, n, m, coef_cos.copy(), 0, is_coef_cheby=True)  # block-encoding of β·cos(t H)
        cos_Ht.update_name("cos(tH)")

        self.log(f"    Approximating the imaginary component (sin) for t = {t:.4f}")
        coef_sin = np.zeros(d + 1)
        for i in range(d + 1):
            if i % 2 != 0:
                coef_sin[i] = jn(i, t) * 2 * (-1) ** ((i - 1) / 2) * beta
        sin_Ht = QSP(UH, n, m, coef_sin.copy(), 1, is_coef_cheby=True)
        sin_Ht.update_name("sin(tH)")

        self.log("    Combining cos and sin components via LCU to construct the final QSP circuit for one slice.")
        qc = Circuit(n + m + 2)           # add one extra qubit for LCU selection
        qc.h(n + m + 1)                        # prepare |+⟩ on selection qubit
        qc.s(n + m + 1)                        # S gate to obtain |+i⟩
        qc.z(n + m + 1)                        # Z to adjust phase (together with S gives phase for imaginary part)
        qc.append(cos_Ht, list(range(n + m + 1)), [n + m + 1], [0])   # cos part when control=0
        qc.append(sin_Ht, list(range(n + m + 1)), [n + m + 1], [1])   # sin part when control=1
        qc.h(n + m + 1)                        # final Hadamard to complete LCU

        self.log(f"Stage 4: Computing exact and approximate evolution matrices for error estimation.")
        u_slice = qc.get_matrix(n, backend=backend, device=device, dtype=dtype) * factor

        if time_slices > 1:
            U_approx = np.linalg.matrix_power(u_slice, time_slices)
        else:
            U_approx = u_slice
        U_exact = expm(-1j * H * slice_time * time_slices)  # Exact evolution for comparison
        U_error = norm(U_approx - U_exact, ord='fro')  # Frobenius norm of the difference
        output = {"Approximate evolution matrix": U_approx, "Exact evolution matrix": U_exact, "Frobenius norm of error": U_error}
        self.update_output(output)
        self.status = "success"
        self.summary = f"QSP simulation completed with Frobenius norm error: {U_error:.2e}"

        # Save results and circuit diagram
        circuit_path = self.save_circuit(qc)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, qc)

    def _format_system(self, H: np.ndarray, t: float, error: float = 1e-8):
        # Specialized input fields for QSPHS
        tol: float = 1e-12

        if not np.isfinite(t):
            raise ValueError("Evolution time t must be finite.")
        if error <= 0:
            raise ValueError("target_error must be positive.")
        if tol <= 0:
            raise ValueError("tol must be positive.")

        # Normalize to contiguous complex ndarray for faster numerical kernels.
        H = np.asarray(H, dtype=np.complex128)
        if H.ndim != 2 or H.shape[0] != H.shape[1]:
            raise ValueError("Matrix must be square.")

        # Verify Hermiticity (within numerical tolerance)
        if not np.allclose(H, H.conj().T, atol=tol, rtol=tol):
            raise ValueError("Matrix must be Hermitian.")

        # If the dimension is not a power of 2, pad with zeros to the next power of 2
        dim = int(H.shape[0])
        if dim <= 0:
            raise ValueError("Matrix dimension must be positive.")

        if (dim & (dim - 1)) != 0:
            padded_dim = 1 << (dim - 1).bit_length()
            padded_H = np.zeros((padded_dim, padded_dim), dtype=np.complex128)
            padded_H[:dim, :dim] = H
            self.log(
                f"Hamiltonian dimension {dim} is not a power of 2; padded to {padded_dim}.")
        else:
            padded_dim = dim
            padded_H = H

        padded_H = np.ascontiguousarray(padded_H)

        # Number of qubits needed = log2(padded dimension)
        n = padded_dim.bit_length() - 1
        return padded_dim, padded_H, n

    @staticmethod
    def _estimate_required_degree(alpha: float, t: float, target_error: float) -> int:
        """Estimate required polynomial degree for exp(-i * alpha * t * x)."""
        t_scaled = abs(alpha * t)
        return max(1, int(np.ceil(1.4 * t_scaled + np.log(1.0 / target_error))))

def test(H=[[2, 1], [1, 3]], t=1.0, error=1e-8, d=15, beta=0.7):
    """
    Initialize the QSP simulator.

    Parameters:
        H : numpy.ndarray
            Hamiltonian matrix (square Hermitian).
        t : float
            Total evolution time.
        error : float
            Desired approximation error (currently unused, reserved for future
            adaptive implementations).
        d : int, optional
            Degree of the approximating polynomial. Larger values improve accuracy
            but increase circuit depth. Default is 15.

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    H = np.array(H)

    algo = QSPHSAlgorithm(text_mode="legacy")
    result = algo.run(H, t, error, degree=d, beta=beta)
    return result

if __name__ == "__main__":
    H = [[2, 1], [1, 3]] # [PARAM]
    t = 1.0 # [PARAM]
    d = 15 # [PARAM]

    error = 1e-8
    test(H, t, error, d=d)