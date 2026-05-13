import time
import os
import math
import numpy as np
from scipy.linalg import expm, norm
from typing import Dict, Any, List, Tuple
from scipy.special import jn

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


class TrotterAlgorithm(BaseAlgorithm):
    """
    Hamiltonian simulation with Trotterization.

    The Trotter method approximates the time evolution operator exp(-iHt) by decomposing the Hamiltonian into a sum of local terms and applying a sequence of exponentials of these terms. This approach is straightforward to implement but may require many steps for high precision, especially for long evolution times.

    """

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Trotter Hamiltonian Simulation Algorithm", prefix="TROTTER_HS", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, H: np.ndarray, t: float, error: float, order: int = 1, steps: int = 1000):
        """
        Initialize the Trotterization for Hamiltonian simulation.

        Parameters:
            H : numpy.ndarray
                Hamiltonian matrix (square Hermitian).
            t : float
                Total evolution time.
            error : float
                Desired approximation error (currently unused, reserved for future
                adaptive implementations).
            order : int, optional
                Order of the Trotter formula. Default is 1 (first-order).
            steps : int, optional
                Number of time steps for the simulation. Default is 1000.

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Hamiltonian": H, "Evolution time": t, "error": error, "order of Trotter formula": order, "steps of Trotter formula": steps}
        self.update_input(input)

        # Stage 1: Format and validate input
        self.log("Stage 1: Formatting and validating input.")
        dim, H, n = self._format_system(H, t, error)
        alpha = np.linalg.norm(H, 2)
        steps = int(min(5**order * np.power(t * n * alpha, 1 + 1.0 / order) * np.power(error, -1.0 / order) * 1.5, steps))
        self.log(f"    Hamiltonian dimension: {dim}, number of qubits: {n}, spectral norm: {alpha:.4f}.")
        self.log(f"    Chosen Trotter order: {order}, number of simulation steps: {steps}.")

        self.log("Stage 2: Decomposing Hamiltonian into Pauli terms.")
        # Decompose Hamiltonian into Pauli terms (H is multiplied by t to incorporate time)
        decomposition = pauli_string_decomposition(H * t)
        self.log(f"    Decomposed Hamiltonian into {len(decomposition)} Pauli terms.")
        
        # Create a register and an empty circuit.
        self.log("Stage 3: Building Trotter circuit for one time slice.")
        reg = Register('K', n)
        trotter = Circuit(reg, name='Trotter')

        # Get the full Trotter sequence.
        sequence = self._expand(decomposition, order, steps)
        
        # Append each Pauli evolution gate to the circuit.
        for pauli_str, angle in sequence:
            gate = pauli_string_evolution(pauli_str, angle)
            trotter.append(gate, range(n))
        
        qc = Circuit(reg, name='Trotter Decomposition')
        qc.append(trotter.repeat(steps), range(n))
        U_approx = qc.get_matrix()

        U_exact = expm(-1j * H * t)  # Exact evolution for comparison
        U_error = norm(U_approx - U_exact, ord='fro')  # Frobenius norm of the difference
        output = {"Approximate evolution matrix": U_approx, "Exact evolution matrix": U_exact, "Frobenius norm of error": U_error}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Trotter simulation completed with Frobenius norm error: {U_error:.2e}"

        # Save results and circuit diagram
        circuit_path_1 = self.save_circuit(qc, name="trotter_full")
        circuit_path_2 = self.save_circuit(trotter, name="trotter_slice")
        circuit_path = [circuit_path_1, circuit_path_2]

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

    def _recurse(self, order: int, decomposition: List[Tuple[str, complex]]) -> List[Tuple[str, complex]]:
        """
        Recursively construct the higher‑order Trotter-Suzuki decomposition.
    
        This method implements the Suzuki recursive formula for even orders.
        For order 1 it returns the decomposition unchanged; for order 2 it applies
        the symmetric composition; for higher orders it recursively builds the
        nested product.
    
        Parameters:
            order : int
                Current order of the decomposition. Must be 1 or an even integer.
            decomposition : List[Tuple[str, complex]]
                A flat list of Pauli strings and their coefficients (the Hamiltonian
                decomposed into Pauli terms).
    
        Returns:
            List[Tuple[str, complex]]
                A list (with possibly modified coefficients) that, when multiplied
                in order, approximates the time evolution for the given order.
        """
        if order == 1:
            return decomposition
        elif order == 2:
            # Second‑order Suzuki: halves of all but the last term, then full last, then reversed halves.
            halves = [(p, c / 2) for p, c in decomposition[:-1]]
            full = [decomposition[-1]]
            return halves + full + list(reversed(halves))
        else:
            # Higher even orders: recursive composition.
            reduction = 1 / (4 - 4 ** (1 / (order - 1)))
            # Outer terms: apply recursion of order-2 with scaled coefficients.
            outer = 2 * self._recurse(order - 2, [(p, c * reduction) for p, c in decomposition])
            # Inner term: apply recursion with a different scaling.
            inner = self._recurse(order - 2, [(p, c * (1 - 4 * reduction)) for p, c in decomposition])
            return outer + inner + outer
    
    def _expand(self, decomposition: List[Tuple[str, complex]], order: int, steps: int) -> List[Tuple[str, complex]]:
        """
        Expand the Trotter-Suzuki sequence for a given total time.
    
        The method scales the coefficients by t / steps, builds a single time slice
        using recursion, and then repeats the slice `steps` times.
    
        Parameters:
            decomposition : List[Tuple[str, complex]]
                A flat list of Pauli strings and their coefficients (the Hamiltonian
                decomposed into Pauli terms).
            order : int
                Order of the Trotter-Suzuki decomposition.
            steps : int
                Number of time steps for the simulation.

        Returns:
            List[Tuple[str, complex]]
                The full Trotter sequence repeated `steps` times. Each element is a
                (pauli_string, coefficient) for one slice.
        """
        scaled_decomposition = [(p, c / steps) for p, c in decomposition]
        one_slice = self._recurse(order, scaled_decomposition)
        return one_slice


def test(H=[[2, 1], [1, 3]], t=1.0, error=1e-8, order=1, steps=1000):
    """
    Initialize the Trotter simulator.

    Parameters:
        H : numpy.ndarray
            Hamiltonian matrix (square Hermitian).
        t : float
            Total evolution time.
        error : float
            Desired approximation error (currently unused, reserved for future
            adaptive implementations).
        order : int, optional
            Order of the Trotter-Suzuki decomposition. Default is 1.
        steps : int, optional
            Number of time steps for the simulation. Default is 1000.

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    H = np.array(H)

    algo = TrotterAlgorithm(text_mode="legacy")
    result = algo.run(H, t, error, order=order, steps=steps)
    return result

if __name__ == "__main__":
    H = [[2, 1], [1, 3]] # [PARAM]
    t = 1.0 # [PARAM]
    order = 1 # [PARAM]
    steps = 1000 # [PARAM]

    error = 1e-8
    test(H, t, error, order=order, steps=steps)