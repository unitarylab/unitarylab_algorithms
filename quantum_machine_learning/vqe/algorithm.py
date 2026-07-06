import time
import os
import numpy as np
import torch
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from typing import Dict, Any, List, Optional

from unitarylab import Circuit
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class VQEAlgorithm(BaseAlgorithm):
    """VQE for estimating the ground-state energy of a Hermitian Hamiltonian."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="VQE Algorithm", prefix="VQE", text_mode=text_mode, algo_dir=algo_dir)
        self.backend = 'torch'
        self.device = 'cpu'
        self.dtype = np.complex128
        
    def _validate_hamiltonian(self, hamiltonian: np.ndarray) -> tuple[np.ndarray, int]:
        h = np.asarray(hamiltonian, dtype=np.complex128)
        if h.ndim != 2 or h.shape[0] != h.shape[1]:
            raise ValueError("Hamiltonian must be a square matrix.")

        dim = h.shape[0]
        if dim == 0 or (dim & (dim - 1)) != 0:
            raise ValueError("Hamiltonian dimension must be a power of 2.")

        if not np.allclose(h, h.conj().T):
            raise ValueError("Hamiltonian must be Hermitian.")

        return h, dim.bit_length() - 1

    def _random_hermitian(
        self, num_qubits: int, seed: Optional[int] = None, normalize: bool = True
    ) -> np.ndarray:
        dim = 2**num_qubits
        rng = np.random.default_rng(seed)
        a = rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))
        h = (a + a.conj().T) / 2.0

        if normalize:
            spec_norm = np.linalg.norm(h, ord=2)
            if spec_norm > 0:
                h = h / spec_norm
        return h

    def _build_ansatz(self, layer_parameters: np.ndarray, num_qubits: int) -> Circuit:
        ansatz = Circuit(num_qubits)

        for q in range(num_qubits):
            ansatz.ry(float(layer_parameters[q, 0]), q)
            ansatz.rz(float(layer_parameters[q, 1]), q)

        for q in range(num_qubits - 1):
            ansatz.cx(q, q + 1)
        if num_qubits > 1:
            ansatz.cx(num_qubits - 1, 0)

        return ansatz

    def _build_circuit(self, parameters_flat: np.ndarray, num_qubits: int, layers: int) -> Circuit:
        parameters = np.asarray(parameters_flat, dtype=float).reshape(layers, num_qubits, 2)
        qc = Circuit(num_qubits)

        for layer in range(layers):
            layer_qc = self._build_ansatz(parameters[layer], num_qubits)
            qc.append(layer_qc, range(num_qubits))

        return qc

    def _expectation(
        self,
        parameters_flat: np.ndarray,
        hamiltonian: np.ndarray,
        num_qubits: int,
        layers: int,
        history: Optional[list[float]] = None,
    ) -> float:
        state = self._build_circuit(parameters_flat, num_qubits, layers).execute(backend=self.backend, device=self.device, dtype=self.dtype).state
        energy = (state.conj().T @ hamiltonian @ state).item()
        energy_real = float(np.real(energy))

        if history is not None:
            history.append(energy_real)
        return energy_real

    def _exact_ground_energy(self, hamiltonian: np.ndarray) -> float:
        evals = np.linalg.eigvalsh(hamiltonian)
        return float(np.min(np.real(evals)))

    def run(
        self,
        n: int = 2,
        layers: int = 2,
        max_iter: int = 150,
        seed: int = 7,
        hamiltonian: Optional[np.ndarray] = None,
        normalize: bool = True, backend='torch', device='cpu', dtype=np.complex128
    ) -> Dict[str, Any]:
        """Run VQE on a user-provided Hermitian Hamiltonian or a random Hermitian example."""
        self.backend = backend
        self.device = device
        self.dtype = dtype

        if hamiltonian is None:
            hamiltonian = self._random_hermitian(n, seed=seed, normalize=normalize)
            hamiltonian_source = "random Hermitian"
        else:
            hamiltonian_source = "user provided"

        hamiltonian, num_qubits = self._validate_hamiltonian(hamiltonian)
        if hamiltonian_source == "user provided":
            n = num_qubits

        input_data = {
            "Hamiltonian Source": hamiltonian_source,
            "Number of Qubits": num_qubits,
            "Number of Layers": layers,
            "Max Iterations": max_iter,
            "Seed": seed,
            "Normalize": normalize,
        }
        self.update_input(input_data)

        self.log("Stage 1: Validating Hamiltonian and preparing initial parameters")
        rng = np.random.default_rng(seed)
        initial_theta = rng.uniform(-np.pi, np.pi, size=2 * num_qubits * layers)
        exact_energy = self._exact_ground_energy(hamiltonian)

        self.log("Stage 2: Building Ry-Rz ring-entangling ansatz")
        qc_draw = self._build_circuit(initial_theta, num_qubits, layers)

        self.log("Stage 3: Running COBYLA energy minimization")
        history: list[float] = []
        q_comp_start = time.time()
        opt_res = minimize(
            fun=self._expectation,
            x0=initial_theta,
            args=(hamiltonian, num_qubits, layers, history),
            method="COBYLA",
            options={"maxiter": max_iter},
        )
        q_comp_time = time.time() - q_comp_start

        vqe_energy = float(opt_res.fun)
        abs_error = abs(vqe_energy - exact_energy)

        self.log("Stage 4: Exporting circuit and convergence plot")
        output = {
            "Exact Energy": exact_energy,
            "VQE Energy": vqe_energy,
            "Absolute Error": abs_error,
            "Optimizer Message": str(opt_res.message),
            "Quantum Comp Time": q_comp_time,
        }
        self.update_output(output)
        self.status = "success"
        self.summary = (
            f"VQE completed with energy {vqe_energy:.6f}; "
            f"exact energy {exact_energy:.6f}; absolute error {abs_error:.6e}."
        )

        circuit_path = self.save_circuit(qc_draw, "VQE_Circuit.svg")
        filename = os.path.abspath(os.path.join(self.algo_dir, "VQE_Convergence.svg"))

        plt.figure(figsize=(6, 4)); plt.plot(history, color='#9b59b6', lw=2)
        plt.title("Energy Convergence")
        plt.savefig(filename); plt.close()
        self.log(f"    Result plot saved to: {filename}")

        return self._build_return_dict(True, circuit_path, filename, qc_draw)


def test(n=2, layers=2, max_iter=150):
    """Execute the VQE training workflow.

    Parameters:
        n: Number of qubits
        layers: Number of variational layers
        max_iter: Maximum number of optimizer iterations

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    algo = VQEAlgorithm(text_mode="legacy")
    return algo.run(
        n=n,
        layers=layers,
        max_iter=max_iter,
    )


if __name__ == "__main__":
    n = 2  # [PARAM]
    layers = 2  # [PARAM]
    max_iter = 150  # [PARAM]
    test(n=n, layers=layers, max_iter=max_iter)
