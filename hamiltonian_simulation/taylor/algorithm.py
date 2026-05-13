import time
import os
import cmath
import numpy as np
from scipy.linalg import expm, norm
from typing import Dict, Any, List
from collections import defaultdict
from scipy.special import jn

# 导入项目核心组件
from unitarylab import Register, Circuit
from unitarylab.library import LCU
from unitarylab.library.pauli_operator import pauli_string_decomposition, pauli_string_circuit, pauli_string_multiply, pauli_string_to_matrix, pauli_string_power
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class TaylorAlgorithm(BaseAlgorithm):
    """
    Hamiltonian simulation with Taylor expansion.

    The Taylor method approximates the time evolution operator exp(-iHt) by expanding it as a Taylor series and truncating the expansion at a specified degree. This approach can achieve high precision with fewer gates compared to Trotterization, especially for short evolution times.

    """

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Taylor Hamiltonian Simulation Algorithm", prefix="TAYLOR_HS", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, H: np.ndarray, t: float, error: float, degree: int = 15):
        """
        Initialize the Taylor simulator.

        Parameters:
            H : numpy.ndarray
                Hamiltonian matrix (square Hermitian).
            t : float
                Total evolution time.
            error : float
                Desired approximation error (currently unused, reserved for future
                adaptive implementations).
            degree : int, optional
                Degree of the Taylor expansion. Larger values improve accuracy
                but increase circuit depth. Default is 15.

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Hamiltonian": H, "Evolution time": t, "error": error, "degree": degree}
        self.update_input(input)

        self.log(f"Stage 1: Formatting and validating input.")
        dim, H, n = self._format_system(H, t, error)
        alpha = np.linalg.norm(H, 2)
        lam = alpha * t
        time_split = 0.5
        degree = min(max(degree, int(np.ceil(lam * 1.5 + np.log(1/error) * 1.5))), 15)
        self.log(f"    Formatted Hamiltonian dimension: {dim} (n={n} qubits)")
        self.log(f"    Spectral norm (alpha): {alpha:.4f}")
        self.log(f"    Degree of expansion: {degree}")

        self.log(f"Stage 2: Decomposing Hamiltonian into Pauli strings.")
        # Split total time into r slices to reduce the required Taylor order
        r = int(lam / time_split) + 1

        # Decompose the Hamiltonian for a single slice: (H * t / r) into Pauli strings
        ans_decomposition = pauli_string_decomposition(H * t / r)
        L = len(ans_decomposition)
        self.log(f"    Decomposed Hamiltonian into {L} Pauli strings.")

        self.log(f"Stage 3: Building Taylor series expansion for one time slice and converting to LCU format.")
        # term_map[k] will store coefficients for (Ht/r)^k (k-th order term)
        ans_term_map = dict()
        for k in range(degree + 1):
            ans_term_map[k] = defaultdict(complex)
        # Zero‑th order term: identity
        ans_term_map[0]["I" * n] = 1.0

        # Build the Taylor series for a single slice using dynamic programming
        for k in range(1, degree + 1):
            for str_prev in ans_term_map[k-1]:
                for i in range(L):
                    # Multiply the previous product with one Pauli term
                    ans_str, ans_val = pauli_string_multiply(str_prev, ans_decomposition[i][0])
                    # Accumulate coefficient: previous * Pauli factor * original coeff * (-i/k)
                    ans_term_map[k][ans_str] += (ans_term_map[k-1][str_prev] * ans_val * ans_decomposition[i][1] * -1j / k)

        # Combine all orders to get the single‑slice evolution operator
        ans_term_list = defaultdict(complex)
        for k in range(degree + 1):
            for str_ in ans_term_map[k]:
                ans_term_list[str_] += ans_term_map[k][str_]
        ans_term_list = [(key, val) for key, val in ans_term_list.items()]

        self.log(f"    Constructed Taylor series with {len(ans_term_list)} unique Pauli string terms for one slice.")
        
        self.log(f"Stage 4: Raising the single-slice operator to the power r to approximate exp(-iHt) and converting to LCU format.")
        term_list = pauli_string_power(ans_term_list, r)
        
        # Optional: reconstruct matrix from Pauli terms (for verification)
        # equ_H1 = np.zeros_like(H, dtype = complex)
        # for key, val in term_list:
        #     equ_H1 += pauli_string_to_matrix(key) * val

        # Convert each term into an LCU building block: unitary + weight
        LCU_terms = list()
        for key, coef in term_list:
            magnitude = abs(coef)                      # weight for LCU
            phase = cmath.phase(coef)                  # global phase to absorb the complex argument
            # Create the Pauli circuit and add the global phase
            U_rotation = self._make_U_rotation(pauli_string_circuit(key), phase, n)
            LCU_terms.append((U_rotation, magnitude))

        # Optional: verify that the weighted sum of unitaries matches the target matrix
        # equ_H2 = np.zeros_like(H, dtype = complex)
        # for key, val in LCU_terms:
        #     equ_H2 += key.get_matrix() * val
        self.log(f"    Constructed LCU terms with {len(LCU_terms)} components.")

        self.log(f"Stage 5: Building the LCU circuit and extracting the approximate evolution operator.")
        # Build the LCU circuit
        circuit = LCU(LCU_terms)
        
        # Extract the system block from the full LCU matrix
        m = len(LCU_terms)                             # number of ancilla states
        lcu_matrix = circuit.get_matrix()              # full (N*m) × (N*m) matrix
        U_approx = np.zeros_like(H, dtype=complex)
        for i in range(len(U_approx)):
            for j in range(len(U_approx)):
                # Take the top‑left block where ancilla is in |0⟩
                U_approx[i, j] = lcu_matrix[i*m, j*m]
        s = sum(alpha for _, alpha in LCU_terms)       # normalization factor (sum of weights)
        U_approx = U_approx * s                        # remove the 1/s factor from LCU output

        self.log(f"Stage 5: Computing exact evolution and error estimation.")
        U_exact = expm(-1j * H * t)  # Exact evolution for comparison
        U_error = norm(U_approx - U_exact, ord='fro')  # Frobenius norm of the difference
        output = {"Approximate evolution matrix": U_approx, "Exact evolution matrix": U_exact, "Frobenius norm of error": U_error}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Taylor series simulation completed with Frobenius norm error: {U_error:.2e}"

        # Save results and circuit diagram
        circuit_path = self.save_circuit(circuit.decompose())
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, circuit)

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

    def _make_U_rotation(self, qc: Circuit, phase_angle: float, target_qubits: int) -> Circuit:
        """
        Apply a global phase rotation to a copy of the given gate sequence.

        This method creates a copy of the input circuit and appends a global phase
        gate with the specified angle. It is used to incorporate the complex phases
        arising from the Taylor coefficients into the LCU building blocks.

        Parameters:
            qc : Circuit
                Input quantum circuit (typically a Pauli string circuit).
            phase_angle : float
                Angle (in radians) for the global phase gate.
            target_qubits : int
                Number of qubits in the system (used to create the copy).

        Returns:
            Circuit
                A new circuit with the same gates as `qc` plus an appended global phase.
        """
        qc_copy = qc.copy()
        # if abs(phase_angle) > 1e-12:
        qc_copy.gp(phase_angle)
        return qc_copy


def test(H=[[2, 1], [1, 3]], t=1.0, error=1e-8, d=15):
    """
    Initialize the Taylor simulator.

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

    algo = TaylorAlgorithm(text_mode="legacy")
    result = algo.run(H, t, error, degree=d)
    return result

if __name__ == "__main__":
    H = [[2, 1], [1, 3]] # [PARAM]
    t = 1.0 # [PARAM]
    d = 10 # [PARAM]

    error = 1e-8
    test(H, t, error, d=d)