"""UnitaryLab implementation of the Boolean hidden-shift algorithm."""

# The public run/test signatures intentionally mirror parameters.json.
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=redefined-outer-name,invalid-name,duplicate-code

from __future__ import annotations

from collections import Counter
import os
import random
from time import perf_counter
from typing import Any, Dict, Iterable

from unitarylab import Circuit, ClassicalRegister, Register

try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    import sys

    _algorithms_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


def bitstring(bits: Iterable[int]) -> str:
    """Return bits in q0, q1, ... order."""
    return "".join(str(int(bit)) for bit in bits)


def make_oracle_f(qubit_count: int) -> Circuit:
    """Construct U_f for f(x) = XOR_i x[2i]x[2i+1]."""
    if qubit_count <= 0 or qubit_count % 2:
        raise ValueError("qubit_count must be a positive even integer")
    oracle = Circuit(qubit_count, name="U_f")
    for qubit in range(0, qubit_count, 2):
        oracle.cz(qubit, qubit + 1)
    return oracle


def make_hs_circuit(shift: Iterable[int], *, measure: bool = False) -> Circuit:
    """Build H -> X_s U_f X_s -> H -> U_f -> H."""
    shift = tuple(shift)
    if not shift or len(shift) % 2 or any(bit not in (0, 1) for bit in shift):
        raise ValueError("shift must be a non-empty even-length binary sequence")
    qubit_count = len(shift)
    oracle_f = make_oracle_f(qubit_count)
    qubits = list(range(qubit_count))
    shifted_qubits = [index for index, value in enumerate(shift) if value]
    quantum = Register("q", qubit_count)
    classical = ClassicalRegister("result", qubit_count)
    circuit = Circuit(quantum, classical, name="Hidden Shift")
    circuit.h(qubits)
    if shifted_qubits:
        circuit.x(shifted_qubits)
    circuit.append(oracle_f, target=qubits)
    if shifted_qubits:
        circuit.x(shifted_qubits)
    circuit.h(qubits)
    circuit.append(oracle_f, target=qubits)
    circuit.h(qubits)
    if measure:
        circuit.measure(quantum[:], classical[:])
    return circuit


def sample_circuit(
    circuit: Circuit, shots: int = 100, *, backend: str = "numpy", seed: int = 42
) -> Counter:
    """Execute once and sample the final state."""
    if circuit.has_measurement:
        raise ValueError("sample_circuit requires a circuit without measurements")
    result = circuit.execute(backend=backend, device="cpu", seed=seed)
    return Counter(outcome[::-1] for outcome in result.sample(shots=shots, seed=seed))


class HiddenShiftAlgorithm(BaseAlgorithm):
    """Recover a hidden Boolean shift using the self-dual bent function oracle."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            directory = os.path.dirname(os.path.abspath(__file__))
            algo_dir = os.path.join(
                os.getcwd(),
                "results",
                os.path.basename(os.path.dirname(directory)),
                os.path.basename(directory),
            )
        os.makedirs(algo_dir, exist_ok=True)
        super().__init__("Hidden Shift", "HS", text_mode, algo_dir)

    def run(
        self,
        qubits: int = 6,
        shift: str = "",
        shots: int = 100,
        seed: int = 41,
        backend: str = "numpy",
        measurement_mode: str = "sample",
    ) -> Dict[str, Any]:
        """Run the hidden-shift circuit and return the standardized result."""
        qubits, shots, seed = int(qubits), int(shots), int(seed)
        shift = "" if shift is None else str(shift).strip()
        backend, measurement_mode = str(backend), str(measurement_mode)
        if shots <= 0 or seed < 0:
            raise ValueError("shots must be positive and seed must be non-negative")
        if backend not in ("numpy", "torch"):
            raise ValueError("backend must be 'numpy' or 'torch'")
        if measurement_mode not in ("sample", "execute"):
            raise ValueError("measurement_mode must be 'sample' or 'execute'")
        if shift:
            if any(value not in "01" for value in shift):
                raise ValueError("shift must be a binary string")
            shift_bits = [int(value) for value in shift]
            qubits = len(shift_bits)
        else:
            rng = random.Random(seed)
            shift_bits = [rng.randint(0, 1) for _ in range(qubits)]
        if qubits <= 0 or qubits % 2:
            raise ValueError("the number of qubits must be positive and even")

        self.update_input(
            {
                "Qubits": qubits,
                "Shift": shift or "random",
                "Shots": shots,
                "Seed": seed,
                "Backend": backend,
                "Measurement mode": measurement_mode,
            }
        )
        started = perf_counter()
        self.log("Stage 1/3: Building the hidden-shift circuit...")
        circuit = make_hs_circuit(shift_bits, measure=measurement_mode == "execute")
        built = perf_counter()
        self.log("Stage 2/3: Executing and sampling...")
        if measurement_mode == "sample":
            frequencies = sample_circuit(circuit, shots, backend=backend, seed=seed)
        else:
            result = circuit.execute(
                backend=backend, device="cpu", shots=shots, seed=seed
            )
            frequencies = Counter(
                {outcome[::-1]: count for outcome, count in result.counts.items()}
            )
        finished = perf_counter()
        answer = frequencies.most_common(1)[0][0]
        expected = bitstring(shift_bits)
        matched = answer == expected
        self.log("Stage 3/3: Verifying and exporting results...")
        self.status = "success" if matched else "failed"
        self.summary = f"Recovered {answer}; expected {expected}; match={matched}."
        self.update_output(
            {
                "Secret shift": expected,
                "Most common bitstring": answer,
                "Counts": dict(frequencies),
                "Matched": matched,
                "Circuit construction (s)": built - started,
                "Execution and sampling (s)": finished - built,
                "Total time (s)": finished - started,
            }
        )
        circuit_path = self.save_circuit(circuit)
        filename = self.save_txt()
        return self._build_return_dict(matched, circuit_path, filename, circuit)


def test(
    qubits=6,
    shift="",
    shots=100,
    seed=41,
    backend="numpy",
    measurement_mode="sample",
):
    """Standard test entry point."""
    algorithm = HiddenShiftAlgorithm(text_mode="legacy")
    return algorithm.run(qubits, shift, shots, seed, backend, measurement_mode)


if __name__ == "__main__":
    qubits = 6  # [PARAM]
    shift = ""  # [PARAM]
    shots = 100  # [PARAM]
    seed = 41  # [PARAM]
    backend = "numpy"  # [PARAM]
    measurement_mode = "sample"  # [PARAM]
    test(qubits, shift, shots, seed, backend, measurement_mode)
