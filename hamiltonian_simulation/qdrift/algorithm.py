import time
import os
import math
import numpy as np
from scipy.linalg import expm, norm
from typing import Dict, Any, List

# 导入项目核心组件
from unitarylab import Register, Circuit
from unitarylab.library.pauli_operator import pauli_string_decomposition, pauli_string_evolution
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QDriftAlgorithm(BaseAlgorithm):
    """
    QDrift random product formula for Hamiltonian simulation.

    The QDrift method approximates the time evolution operator exp(-iHt) by
    randomly sampling Pauli terms according to their coefficient magnitudes,
    then applying them with appropriately scaled angles. This yields a
    stochastic approximation that converges to the exact evolution in the
    limit of many repetitions.

    """

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="QDrift Algorithm", prefix="QDRIFT", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, H: np.ndarray, t: float, error: float, steps: int = 5000):
        """
        Initialize the QDrift simulator.

        Parameters:
            H : numpy.ndarray
                Hamiltonian matrix (square Hermitian).
            t : float
                Total evolution time.
            error : float
                Desired approximation error (currently unused, reserved for future
                adaptive implementations).
            steps : int, optional
                Number of random samples (repetitions). Larger values improve accuracy
                but increase circuit depth. Default is 5000.
                
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Hamiltonian": H, "Evolution time": t, "error": error, "steps": steps}
        self.update_input(input)

        # Stage 1: Format and validate input
        self.log("Stage 1: Format and validate input.")
        dim, H, n = self._format_system(H, t, error)
        self.log(f"    Formatted Hamiltonian dimension: {dim} (n={n} qubits)")

        # Stage 2: Decompose Hamiltonian into Pauli terms (H is multiplied by t to incorporate time)
        self.log("Stage 2: Decompose Hamiltonian into Pauli terms.")
        decomposition = pauli_string_decomposition(H)
        self.log(f"    Decomposed Hamiltonian into {len(decomposition)} Pauli terms.")

        # Stage 3: Construct the QDrift circuit
        self.log("Stage 3: Construct the QDrift circuit.")
        reg = Register('K', n)
        qc = Circuit(reg, name='QDrift Decomposition')

        # Get the QDrift sequence (passing total time t)
        sequence = self._expand(decomposition, t, steps)

        # Append each Pauli evolution gate to the circuit
        for pauli_str, angle in sequence:
            gate = pauli_string_evolution(pauli_str, angle)
            qc.append(gate, range(n))
        self.log(f"    Constructed QDrift circuit with {len(sequence)} gates.")

        # Stage 4: Compute exact and approximate evolution matrices for error estimation.
        self.log("Stage 4: Compute exact and approximate evolution matrices for error estimation.")
        U_approx = qc.get_matrix()
        U_exact = expm(-1j * H * t)  # Exact evolution for comparison
        U_error = norm(U_approx - U_exact, ord='fro')  # Frobenius norm of the difference
        output = {"Approximate evolution matrix": U_approx, "Exact evolution matrix": U_exact, "Frobenius norm of error": U_error}
        self.update_output(output)
        self.status = "success"
        self.summary = f"QDrift simulation completed with Frobenius norm error: {U_error:.2e}"

        # Save results and circuit diagram
        circuit_path = self.save_circuit(qc)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, qc)

    def _format_system(self, H: np.ndarray, t: float, error: float = 1e-8):
        # Specialized input fields for QDrift
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

    def _expand(self, decomposition, t: float, steps: int = 5000):
        """
        Generate the QDrift random sequence of Pauli terms.

        This method samples `steps` Pauli strings according to probabilities
        proportional to the absolute values of their coefficients. Each sampled
        term is assigned an angle = sign(c) * λ * t / N, where λ = Σ|c| and N = steps.

        Parameters:
            decomposition : list of (str, complex)
                List of Pauli strings and their coefficients from the Hamiltonian.
            t : float
                Total evolution time (used to scale the angles).

        Returns:
            list of (str, float)
                A list of (pauli_string, angle) pairs, one for each step in the
                random sequence. The order is random and the list length equals `steps`.
        """
        # Extract Pauli strings and coefficients
        pauli_strings = [p for p, _ in decomposition]
        coeffs = np.array([c.real for _, c in decomposition], dtype=float)  # QDrift assumes real coefficients
        # print(decomposition)  # DEBUG: print decomposed Pauli terms

        # Compute λ = Σ|c|
        lam = np.sum(np.abs(coeffs))
        # Probabilities proportional to |c|
        probs = np.abs(coeffs) / lam

        # Randomly sample indices according to probabilities
        # np.random.seed(666)  # for reproducibility (optional)
        indices = np.random.choice(len(decomposition), size=steps, p=probs)

        # Build sequence: each step has angle = sign(c) * λ * t / N
        sequence = []
        for idx in indices:
            pauli_str = pauli_strings[idx]
            sign = np.sign(coeffs[idx])   # sign of coefficient
            angle = sign * lam * t / steps
            sequence.append((pauli_str, angle))

        return sequence

def test(H=[[2, 1], [1, 3]], t=1.0, error=1e-8, steps=5000):
    """
    Initialize the QDrift simulator.

    Parameters:
        H : numpy.ndarray
            Hamiltonian matrix (square Hermitian).
        t : float
            Total evolution time.
        error : float
            Desired approximation error (currently unused, reserved for future
            adaptive implementations).
        steps : int, optional
            Number of random samples (repetitions). Larger values improve accuracy
            but increase circuit depth. Default is 5000.
            
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    H = np.array(H)

    algo = QDriftAlgorithm(text_mode="legacy")
    result = algo.run(H, t, error, steps=steps)
    return result

if __name__ == "__main__":
    H = [[2, 1], [1, 3]] # [PARAM]
    t = 1.0 # [PARAM]
    steps = 5000 # [PARAM]

    error = 1e-8
    test(H, t, error, steps)