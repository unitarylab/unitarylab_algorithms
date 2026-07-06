"""VQE adapter for Pauli Hamiltonians used by the Fermi-Hubbard workflow."""

from __future__ import annotations

from dataclasses import dataclass
import math
import tempfile
from typing import Any

import numpy as np

from unitarylab import Circuit

try:
    from ..vqe.algorithm import VQEAlgorithm
except ImportError:  # pragma: no cover - supports direct script execution
    from algorithms.quantum_machine_learning.vqe.algorithm import VQEAlgorithm

from unitarylab.library.fermi_hubbard.pauli_ground_state import (
    parse_pauli_expression,
    pauli_string_to_matrix,
)


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
            "Pauli Hamiltonian dimension is inconsistent with its qubit count")

    unitarylab_hamiltonian = _bit_reverse_hamiltonian(
        pauli_hamiltonian,
        number_of_qubits,
    )

    roundtrip = _bit_reverse_hamiltonian(unitarylab_hamiltonian, number_of_qubits)
    roundtrip_error = float(np.max(np.abs(roundtrip - pauli_hamiltonian)))
    if roundtrip_error >= _ENDIAN_TOLERANCE:
        raise ValueError(
            f"Hamiltonian bit-reversal roundtrip failed: error={roundtrip_error}"
        )

    pauli_spectrum = np.linalg.eigvalsh(pauli_hamiltonian)
    unitarylab_spectrum = np.linalg.eigvalsh(unitarylab_hamiltonian)
    spectrum_error = float(
        np.max(np.abs(pauli_spectrum - unitarylab_spectrum)))
    if spectrum_error >= _SPECTRUM_TOLERANCE:
        raise ValueError(
            f"Hamiltonian spectrum changed during format adaptation: error={spectrum_error}"
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
            hamiltonian=np.asarray(unitarylab_hamiltonian, dtype=np.complex128),
        )
        if official_result.get("status") != "ok":
            raise RuntimeError("VQEAlgorithm.run() did not report success")

    if algorithm.evaluations <= 0:
        raise RuntimeError("VQE performed no objective-function evaluations")
    if algorithm.best_parameters is None or not math.isfinite(algorithm.best_energy):
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
            device="cpu",
            dtype=np.complex128,
        ).state
    )
    circuit_energy = expectation_value(optimized_state, unitarylab_hamiltonian)
    if abs(circuit_energy - algorithm.best_energy) >= _ENERGY_TOLERANCE:
        raise RuntimeError(
            "optimized circuit energy does not match the lowest VQE energy"
        )
    if algorithm.best_energy < exact_energy - _ENERGY_TOLERANCE:
        raise ValueError(
            "VQE energy violates the variational upper bound; check Hamiltonian endianness"
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
            "circuit expectation value has a significant imaginary part")
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
            "UnitaryLab default simulator returned an unexpected state")
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
        [_reverse_bits(index, number_of_qubits)
         for index in range(2**number_of_qubits)],
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
        if "device" not in message and "dtype" not in message and "unexpected" not in message:
            raise
        return algorithm.run(
            n=number_of_qubits,
            layers=layers,
            max_iter=max_iter,
            seed=seed,
            hamiltonian=hamiltonian,
            normalize=False,
        )
