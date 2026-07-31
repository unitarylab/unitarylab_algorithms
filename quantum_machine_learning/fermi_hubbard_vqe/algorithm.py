"""Fermi-Hubbard VQE algorithm workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
import json
import math
import os
import tempfile
import time

import matplotlib.pyplot as plt
import numpy as np

from unitarylab import Circuit

try:
    from ...algo_base import BaseAlgorithm
except ImportError:  # pragma: no cover - supports direct script execution
    import sys

    _algorithms_dir = Path(__file__).resolve().parents[2]
    if str(_algorithms_dir) not in sys.path:
        sys.path.insert(0, str(_algorithms_dir))
    from algo_base import BaseAlgorithm

from unitarylab.library.fermi_hubbard.fermi_hubbard_pauli import (
    fermi_hubbard_hamiltonian,
    fermi_hubbard_pauli,
    qubit_site_spin_mapping,
)
from unitarylab.library.fermi_hubbard.pauli_ground_state import pauli_ground_state
from unitarylab.library.fermi_hubbard.pauli_ground_state import (
    parse_pauli_expression,
    pauli_string_to_matrix,
)

try:
    from ..vqe.algorithm import VQEAlgorithm
except ImportError:  # pragma: no cover - supports direct script execution
    from unitarylab_algorithms.quantum_machine_learning.vqe.algorithm import VQEAlgorithm


_ENERGY_TOLERANCE = 1e-8
_SPECTRUM_TOLERANCE = 1e-10
_ENDIAN_TOLERANCE = 1e-12
_ENVIRONMENT_CHECKED = False
_UNITARYLAB_ENDIANNESS = "q0 is the least-significant bit"


@dataclass(frozen=True)
class PauliVQEResult:
    """Core VQE result for a Pauli Hamiltonian."""

    energy: float
    exact_energy: float
    absolute_error: float
    circuit_energy: float
    parameters: np.ndarray
    circuit: Circuit
    convergence: tuple[float, ...]
    layers: int
    max_iter: int
    evaluations: int
    optimizer_converged: bool
    optimizer_message: str
    number_of_qubits: int
    unitarylab_endianness: str
    bit_reversal_applied: bool


class _TrackingVQEAlgorithm(VQEAlgorithm):
    """Record best objective evaluations while using the project VQE class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.best_energy = math.inf
        self.best_parameters: np.ndarray | None = None
        self.evaluations = 0
        self.history: list[float] = []

    def _expectation(
        self,
        parameters_flat: np.ndarray,
        hamiltonian: np.ndarray,
        num_qubits: int,
        layers: int,
        history: list[float] | None = None,
    ) -> float:
        energy = super()._expectation(
            parameters_flat,
            hamiltonian,
            num_qubits,
            layers,
            history,
        )
        self.evaluations += 1
        self.history.append(float(energy))
        if math.isfinite(energy) and energy < self.best_energy:
            self.best_energy = float(energy)
            self.best_parameters = np.asarray(parameters_flat, dtype=float).copy()
        return float(energy)


def run_pauli_vqe(
    pauli_expression: str,
    *,
    layers: int = 5,
    max_iter: int = 150,
    seed: int = 7,
    algo_dir: str | None = None,
    backend: str = "torch",
    device: str = "cpu",
    dtype=np.complex128,
) -> PauliVQEResult:
    """Run VQE for a Pauli Hamiltonian expression and return core results."""
    _validate_positive_integer("layers", layers)
    _validate_positive_integer("max_iter", max_iter)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    _check_unitarylab_environment()

    terms = parse_pauli_expression(pauli_expression)
    number_of_qubits = len(next(iter(terms)))
    pauli_hamiltonian = pauli_string_to_matrix(pauli_expression)
    expected_shape = (2**number_of_qubits, 2**number_of_qubits)
    if pauli_hamiltonian.shape != expected_shape:
        raise ValueError(
            "Pauli Hamiltonian dimension is inconsistent with its qubit count"
        )

    unitarylab_hamiltonian = _bit_reverse_hamiltonian(
        pauli_hamiltonian,
        number_of_qubits,
    )

    roundtrip = _bit_reverse_hamiltonian(
        unitarylab_hamiltonian, number_of_qubits
    )
    roundtrip_error = float(np.max(np.abs(roundtrip - pauli_hamiltonian)))
    if roundtrip_error >= _ENDIAN_TOLERANCE:
        raise ValueError(
            f"Hamiltonian bit-reversal roundtrip failed: error={roundtrip_error}"
        )

    pauli_spectrum = np.linalg.eigvalsh(pauli_hamiltonian)
    unitarylab_spectrum = np.linalg.eigvalsh(unitarylab_hamiltonian)
    spectrum_error = float(
        np.max(np.abs(pauli_spectrum - unitarylab_spectrum))
    )
    if spectrum_error >= _SPECTRUM_TOLERANCE:
        raise ValueError(
            "Hamiltonian spectrum changed during format adaptation: "
            f"error={spectrum_error}"
        )
    exact_energy = float(pauli_spectrum[0])

    with tempfile.TemporaryDirectory(prefix="fermi_hubbard_vqe_") as temporary:
        algorithm = _TrackingVQEAlgorithm(algo_dir=temporary)
        official_result = _run_vqe_algorithm(
            algorithm,
            number_of_qubits=number_of_qubits,
            layers=layers,
            max_iter=max_iter,
            seed=seed,
            hamiltonian=np.asarray(
                unitarylab_hamiltonian, dtype=np.complex128
            ),
        )
        if official_result.get("status") != "ok":
            raise RuntimeError("VQEAlgorithm.run() did not report success")

    if algorithm.evaluations <= 0:
        raise RuntimeError("VQE performed no objective-function evaluations")
    if algorithm.best_parameters is None or not math.isfinite(
        algorithm.best_energy
    ):
        raise RuntimeError("could not obtain lowest-energy parameters from VQE")

    official_exact_energy = float(official_result["Exact Energy"])
    if abs(official_exact_energy - exact_energy) >= _SPECTRUM_TOLERANCE:
        raise ValueError(
            "VQE exact reference energy does not match the Pauli Hamiltonian"
        )

    optimized_circuit = algorithm._build_circuit(
        algorithm.best_parameters,
        number_of_qubits,
        layers,
    )
    optimized_state = np.asarray(
        optimized_circuit.execute(
            backend=backend,
            device=device,
            dtype=dtype,
        ).state
    )
    circuit_energy = expectation_value(optimized_state, unitarylab_hamiltonian)
    if abs(circuit_energy - algorithm.best_energy) >= _ENERGY_TOLERANCE:
        raise RuntimeError(
            "optimized circuit energy does not match the lowest VQE energy"
        )
    if algorithm.best_energy < exact_energy - _ENERGY_TOLERANCE:
        raise ValueError(
            "VQE energy violates the variational upper bound; "
            "check Hamiltonian endianness"
        )

    optimizer_message = str(official_result.get("Optimizer Message", ""))
    return PauliVQEResult(
        energy=float(algorithm.best_energy),
        exact_energy=exact_energy,
        absolute_error=abs(float(algorithm.best_energy) - exact_energy),
        circuit_energy=circuit_energy,
        parameters=algorithm.best_parameters.copy(),
        circuit=optimized_circuit,
        convergence=tuple(algorithm.history),
        layers=layers,
        max_iter=max_iter,
        evaluations=algorithm.evaluations,
        optimizer_converged=_optimizer_converged(optimizer_message),
        optimizer_message=optimizer_message,
        number_of_qubits=number_of_qubits,
        unitarylab_endianness=_UNITARYLAB_ENDIANNESS,
        bit_reversal_applied=True,
    )


def expectation_value(state: np.ndarray, hamiltonian: np.ndarray) -> float:
    """Return a checked real expectation value."""
    value = np.vdot(state, np.dot(hamiltonian, state))
    if abs(float(value.imag)) > 1e-10:
        raise ValueError(
            "circuit expectation value has a significant imaginary part"
        )
    result = float(value.real)
    if not math.isfinite(result):
        raise ValueError("circuit expectation value is not finite")
    return result


def _validate_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be a positive integer")
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _check_unitarylab_environment() -> None:
    global _ENVIRONMENT_CHECKED
    if _ENVIRONMENT_CHECKED:
        return
    circuit = Circuit(1)
    circuit.x(0)
    state = circuit.execute().state
    if state.shape != (2,) or abs(state[1] - 1.0) >= 1e-6:
        raise RuntimeError(
            "UnitaryLab default simulator returned an unexpected state"
        )
    two_qubit = Circuit(2)
    two_qubit.x(0)
    two_qubit_state = np.asarray(two_qubit.execute().state)
    index = int(np.argmax(np.abs(two_qubit_state)))
    if index != 1:
        raise RuntimeError(
            "Fermi-Hubbard VQE assumes UnitaryLab q0 is the least-significant "
            f"bit, but Circuit(2).x(0) peaked at state index {index}"
        )
    _ENVIRONMENT_CHECKED = True


def _reverse_bits(index: int, number_of_qubits: int) -> int:
    reversed_index = 0
    for _ in range(number_of_qubits):
        reversed_index = (reversed_index << 1) | (index & 1)
        index >>= 1
    return reversed_index


def _bit_reverse_hamiltonian(
    hamiltonian: np.ndarray,
    number_of_qubits: int,
) -> np.ndarray:
    permutation = np.array(
        [
            _reverse_bits(index, number_of_qubits)
            for index in range(2**number_of_qubits)
        ],
        dtype=int,
    )
    return np.asarray(hamiltonian)[np.ix_(permutation, permutation)]


def _optimizer_converged(message: str) -> bool:
    lowered = message.lower()
    nonconvergence_markers = (
        "maxfun",
        "max iterations",
        "maximum number of function evaluations",
        "maximum number of iterations",
        "iteration limit",
        "not converged",
    )
    return bool(message.strip()) and not any(
        marker in lowered for marker in nonconvergence_markers
    )


def _run_vqe_algorithm(
    algorithm: _TrackingVQEAlgorithm,
    *,
    number_of_qubits: int,
    layers: int,
    max_iter: int,
    seed: int,
    hamiltonian: np.ndarray,
):
    try:
        return algorithm.run(
            n=number_of_qubits,
            layers=layers,
            max_iter=max_iter,
            seed=seed,
            hamiltonian=hamiltonian,
            normalize=False,
            device="cpu",
            dtype=np.complex128,
        )
    except TypeError as error:
        message = str(error)
        if (
            "device" not in message
            and "dtype" not in message
            and "unexpected" not in message
        ):
            raise
        return algorithm.run(
            n=number_of_qubits,
            layers=layers,
            max_iter=max_iter,
            seed=seed,
            hamiltonian=hamiltonian,
            normalize=False,
        )


class FermiHubbardVQEAlgorithm(BaseAlgorithm):
    """Run VQE for the open one-dimensional Fermi-Hubbard model."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = Path(__file__).resolve()
            algo_dir = os.path.join(
                os.getcwd(),
                "results",
                _this.parents[1].name,
                _this.parent.name,
            )
        os.makedirs(algo_dir, exist_ok=True)
        super().__init__(
            name="Fermi-Hubbard VQE Algorithm",
            prefix="FH-VQE",
            text_mode=text_mode,
            algo_dir=algo_dir,
        )

    def run(
        self,
        params: Dict[str, Any] | str | None = None,
        *,
        L: int = 2,
        t: float = 1.0,
        U: float = 4.0,
        B: float = 1.5,
        layers: int = 5,
        max_iter: int = 1000,
        seed: int = 7,
        measure_shots: int = 10000,
        backend: str = "torch",
        device: str = "cpu",
        dtype = np.complex128,
    ) -> Dict[str, Any]:
        """Execute the standard Fermi-Hubbard VQE workflow."""
        parsed = _load_params(params)
        if parsed:
            L = int(parsed.get("L", L))
            t = float(parsed.get("t", t))
            U = float(parsed.get("U", U))
            B = float(parsed.get("B", B))
            layers = int(parsed.get("layers", parsed.get("vqe_layers", layers)))
            max_iter = int(parsed.get("max_iter", parsed.get("vqe_max_iter", max_iter)))
            seed = int(parsed.get("seed", seed))
            measure_shots = int(
                parsed.get(
                    "measure_shots",
                    parsed.get("measurement_shots", measure_shots),
                )
            )

        input_data = {
            "Lattice Sites": L,
            "Hopping t": t,
            "Interaction U": U,
            "Magnetic Field B": B,
            "VQE Layers": layers,
            "Max Iterations": max_iter,
            "Seed": seed,
            "Measurement Shots": measure_shots,
        }
        self.update_input(input_data)
        total_start = time.time()

        self.log("Stage 1: Building Fermi-Hubbard Pauli Hamiltonian")
        mapping = qubit_site_spin_mapping(L)
        fermionic_hamiltonian = fermi_hubbard_hamiltonian(L, t, U, B)
        pauli_expression = fermi_hubbard_pauli(L, t, U, B)

        self.log("Stage 2: Running dense exact diagonalization")
        exact = pauli_ground_state(pauli_expression)

        self.log("Stage 3: Running VQE optimization")
        vqe_start = time.time()
        vqe_result = run_pauli_vqe(
            pauli_expression,
            layers=layers,
            max_iter=max_iter,
            seed=seed,
            algo_dir=self.algo_dir,
            backend=backend,
            device=device,
            dtype=dtype,
        )
        vqe_time = time.time() - vqe_start

        self.log("Stage 4: Exporting standard algorithm outputs")
        circuit_path, plot_paths = self._generate_outputs(vqe_result)

        measurement = None
        if measure_shots > 0:
            self.log("Stage 5: Measuring total spin magnetic moment")
            from unitarylab.library.fermi_hubbard.measure import (
                measure_circuit_magnetic_moment,
            )

            measurement = measure_circuit_magnetic_moment(
                vqe_result.circuit,
                shots=measure_shots,
            )

        total_time = time.time() - total_start
        output = {
            "Exact Energy": exact.energy,
            "VQE Energy": vqe_result.energy,
            "Absolute Error": vqe_result.absolute_error,
            "Circuit Energy": vqe_result.circuit_energy,
            "Number of Qubits": vqe_result.number_of_qubits,
            "Optimizer Evaluations": vqe_result.evaluations,
            "Optimizer Converged": vqe_result.optimizer_converged,
            "Optimizer Message": vqe_result.optimizer_message,
            "VQE Runtime": vqe_time,
            "Total Runtime": total_time,
            "Qubit Mapping": mapping,
            "Fermionic Hamiltonian": fermionic_hamiltonian,
            "Pauli Hamiltonian": pauli_expression,
        }
        if measurement is not None:
            output.update(
                {
                    "Measured Magnetic Moment": measurement.magnetic_moment,
                    "Magnetic Moment Standard Errors": measurement.standard_errors,
                    "Measurement Total Shots": measurement.total_shots,
                }
            )

        self.update_output(output)
        self.status = "success"
        self.summary = (
            f"Fermi-Hubbard VQE completed with energy {vqe_result.energy:.6f}; "
            f"exact energy {exact.energy:.6f}; absolute error "
            f"{vqe_result.absolute_error:.6e}."
        )
        self.save_txt()
        return self._build_return_dict(True, circuit_path, plot_paths, vqe_result.circuit)

    def _generate_outputs(self, vqe_result):
        circuit_path = os.path.abspath(
            os.path.join(self.algo_dir, "Fermi_Hubbard_VQE_Circuit.svg")
        )
        vqe_result.circuit.draw(filename=circuit_path)

        convergence_path = os.path.abspath(
            os.path.join(self.algo_dir, "Fermi_Hubbard_VQE_Convergence.svg")
        )
        plt.figure(figsize=(6, 4))
        plt.plot(vqe_result.convergence, color="#3498db", lw=2)
        plt.xlabel("Evaluation")
        plt.ylabel("Energy")
        plt.title("Fermi-Hubbard VQE Energy Convergence")
        plt.tight_layout()
        plt.savefig(convergence_path)
        plt.close()

        parameters_path = os.path.abspath(
            os.path.join(self.algo_dir, "Fermi_Hubbard_VQE_Parameters.npy")
        )
        np.save(parameters_path, vqe_result.parameters)
        return circuit_path, [convergence_path, parameters_path]


def _load_params(params: Dict[str, Any] | str | None) -> Dict[str, Any]:
    if params is None:
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        return json.loads(params)
    raise TypeError("params must be a dict, JSON string, or None")


def test(
    L: int = 2,
    t: float = 1.0,
    U: float = 4.0,
    B: float = 1.5,
    layers: int = 5,
    max_iter: int = 1000,
    seed: int = 7,
    measurement_shots: int = 10000,
):
    """Execute the Fermi-Hubbard VQE workflow."""
    algo = FermiHubbardVQEAlgorithm(text_mode="legacy")
    return algo.run(
        L=L,
        t=t,
        U=U,
        B=B,
        layers=layers,
        max_iter=max_iter,
        seed=seed,
        measure_shots=measurement_shots,
    )


if __name__ == "__main__":
    test()
