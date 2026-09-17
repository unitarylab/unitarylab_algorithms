"""UnitaryLab coupled-oscillator implementation of the Glued Trees walk."""

# The public run/test signatures intentionally mirror parameters.json.
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=too-many-branches,redefined-outer-name,invalid-name,duplicate-code

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import os
import random
from time import perf_counter
from typing import Any, Dict, Iterable, Optional

import networkx as nx
import numpy as np
from unitarylab import Circuit, ClassicalRegister, Register
from unitarylab.library.pauli_operator import (
    pauli_string_decomposition,
    pauli_string_evolution,
)

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


@dataclass
class GluedTreesModel:
    """Graph and oscillator Hamiltonian in integer vertex order."""

    qubits: int
    graph: nx.Graph
    adjacency: np.ndarray
    stiffness: np.ndarray
    factor: np.ndarray
    hamiltonian: np.ndarray

    @property
    def columns_per_tree(self) -> int:
        """Return the source example's column parameter."""
        return self.qubits - 2

    @property
    def node_count(self) -> int:
        """Return the total number of graph vertices."""
        return self.graph.number_of_nodes()

    @property
    def exit_state(self) -> int:
        """Return the velocity-block exit-state index."""
        return self.node_count - 1


def build_glued_trees(qubits: int = 6, seed: int = 0) -> GluedTreesModel:
    """Build two binary trees, random leaf glue, and H=-[[0,B],[B†,0]]."""
    if not 4 <= qubits <= 8:
        raise ValueError("dense demonstration requires 4 <= qubits <= 8")
    if seed < 0:
        raise ValueError("seed must be non-negative")
    columns = qubits - 2
    nodes = 2 ** (columns + 1) - 2
    left = nx.balanced_tree(2, columns - 1)
    right = nx.relabel_nodes(left, lambda vertex: nodes - 1 - vertex)
    graph = nx.union(left, right)
    leaf_count = 2 ** (columns - 1)
    left_leaves = range(leaf_count - 1, 2 * leaf_count - 1)
    right_leaves = range(2 * leaf_count - 1, 3 * leaf_count - 1)
    degrees = dict.fromkeys(right_leaves, 0)
    rng = random.Random(seed)
    for vertex in left_leaves:
        candidates = [other for other in right_leaves if degrees[other] == 0]
        if not candidates:
            candidates = [other for other in right_leaves if degrees[other] < 2]
        for other in rng.sample(candidates, 2):
            graph.add_edge(vertex, other)
            degrees[other] += 1
    adjacency = nx.to_numpy_array(graph, nodelist=range(nodes), dtype=float)
    stiffness = 3 * np.eye(nodes) - adjacency
    factor = np.pad(np.linalg.cholesky(stiffness), ((0, 0), (0, 4)))
    hamiltonian = np.zeros((2**qubits, 2**qubits))
    hamiltonian[:nodes, nodes:] = -factor
    hamiltonian[nodes:, :nodes] = -factor.T
    return GluedTreesModel(qubits, graph, adjacency, stiffness, factor, hamiltonian)


def decompose_hamiltonian(model: GluedTreesModel) -> list[tuple[str, float]]:
    """Return the real Pauli terms sorted by decreasing coefficient magnitude."""
    terms = pauli_string_decomposition(
        model.hamiltonian, partition_commuting=False, real_symmetric_hint=True
    )
    real_terms = [(word, float(np.real(coefficient))) for word, coefficient in terms]
    return sorted(real_terms, key=lambda term: (-abs(term[1]), term[0]))


def crop_pauli_list(
    terms: Iterable[tuple[str, float]], size: Optional[int] = None
) -> list[tuple[str, float]]:
    """Apply the source algorithm's 60% diversity plus 40% magnitude crop."""
    terms = list(terms)
    if size is not None and size <= 0:
        raise ValueError("max_terms must be positive or None")
    if size is None or len(terms) <= size:
        return terms
    selected, used = [], set()
    quota, cursor = round(size * 0.6), 0
    while len(selected) < quota:
        previous_size = len(selected)
        for _ in range(4):
            for qubit in range(len(terms[0][0])):
                letter = "IXYZ"[cursor % 4]
                cursor += 1
                for index, (word, _) in enumerate(terms):
                    if index not in used and word[qubit] == letter:
                        selected.append(terms[index])
                        used.add(index)
                        break
                if len(selected) >= quota:
                    break
            if len(selected) >= quota:
                break
        if len(selected) == previous_size:
            break
    for index, term in enumerate(terms):
        if len(selected) >= size:
            break
        if index not in used:
            selected.append(term)
    return selected


def make_trotter_step(qubits: int, terms, dt: float, order: int = 1) -> Circuit:
    """Build one fixed first- or second-order Suzuki step."""
    if order not in (1, 2):
        raise ValueError("order must be 1 or 2")
    if not np.isfinite(dt):
        raise ValueError("dt must be finite")
    step = Circuit(qubits, name=f"Suzuki order {order}, dt={dt:g}")
    if dt == 0:
        return step
    terms = list(terms)
    if any(len(word) != qubits for word, _ in terms):
        raise ValueError("Pauli word length must equal qubits")
    sequence = terms
    if order == 2 and terms:
        half = [(word, coefficient / 2) for word, coefficient in terms[:-1]]
        sequence = half + terms[-1:] + list(reversed(half))
    blocks = {}
    for word, coefficient in sequence:
        key = (word, coefficient * dt)
        if key not in blocks:
            blocks[key] = pauli_string_evolution(*key)
        step.append(blocks[key], target=list(range(qubits)))
    return step


def make_glued_trees_circuit(
    qubits: int,
    terms,
    time: float,
    *,
    repetitions: int = 10,
    order: int = 1,
) -> Circuit:
    """Prepare the entrance state and evolve for the requested time."""
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    quantum = Register("state", qubits)
    classical = ClassicalRegister("result", qubits)
    circuit = Circuit(quantum, classical, name=f"Glued Trees t={time:g}")
    step = make_trotter_step(qubits, terms, time / repetitions, order)
    if time != 0:
        for _ in range(repetitions):
            circuit.append(step, target=quantum[:])
    return circuit


def parse_times(times, model: GluedTreesModel) -> np.ndarray:
    """Normalize None, CSV text, scalar, or a sequence to a time array."""
    if times is None or (isinstance(times, str) and not times.strip()):
        values = 2 * model.columns_per_tree + np.arange(-12, 13, 2)
    elif isinstance(times, str):
        values = [float(value.strip()) for value in times.split(",") if value.strip()]
    elif np.isscalar(times):
        values = [float(times)]
    else:
        values = times
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not array.size or not np.all(np.isfinite(array)):
        raise ValueError("times must be a non-empty finite one-dimensional sequence")
    return array


def plot_results(report, filepath: str) -> None:
    """Save exit-state probability versus evolution time."""
    import matplotlib  # pylint: disable=import-outside-toplevel

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel

    rows = report["rows"]
    figure, axis = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    axis.plot(
        [row["time"] for row in rows],
        [row["sampled_probability"] for row in rows],
        "o-",
    )
    axis.set(xlabel="Evolution time", ylabel="Exit-state probability (sampled)")
    axis.set_title(
        f"Glued Trees: {report['qubits']} qubits, exit |{report['exit_bits']}>"
    )
    figure.savefig(filepath, dpi=160)
    plt.close(figure)


class GluedTreesAlgorithm(BaseAlgorithm):
    """Search a glued-trees graph using coupled-oscillator quantum evolution."""

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
        super().__init__("Glued Trees", "GT", text_mode, algo_dir)

    def run(
        self,
        qubits: int = 6,
        seed: int = 0,
        shots: int = 8192,
        repetitions: int = 10,
        order: int = 1,
        max_terms=None,
        backend: str = "numpy",
        times=None,
    ) -> Dict[str, Any]:
        """Run the Glued Trees time scan and return standardized artifacts."""
        qubits, seed = int(qubits), int(seed)
        shots, repetitions, order = int(shots), int(repetitions), int(order)
        max_terms = None if max_terms in (None, "", "None") else int(max_terms)
        backend = str(backend)
        if shots <= 0 or repetitions <= 0 or seed < 0:
            raise ValueError("shots/repetitions must be positive; seed non-negative")
        if backend not in ("numpy", "torch"):
            raise ValueError("backend must be 'numpy' or 'torch'")
        self.update_input(
            {
                "Qubits": qubits,
                "Seed": seed,
                "Shots": shots,
                "Trotter repetitions": repetitions,
                "Suzuki order": order,
                "Maximum Pauli terms": max_terms or "all",
                "Backend": backend,
                "Times": times or "default scan",
            }
        )
        started = perf_counter()
        self.log("Stage 1/4: Building the glued-trees oscillator model...")
        model = build_glued_trees(qubits, seed)
        model_end = perf_counter()
        scan_times = parse_times(times, model)
        self.log("Stage 2/4: Decomposing the Hamiltonian into Pauli terms...")
        full_terms = decompose_hamiltonian(model)
        terms = crop_pauli_list(full_terms, max_terms)
        decomposition_end = perf_counter()
        self.log("Stage 3/4: Evolving and sampling each time point...")
        exit_bits = format(model.exit_state, f"0{qubits}b")
        rows, representative = [], None
        for index, time_value in enumerate(scan_times):
            build_start = perf_counter()
            circuit = make_glued_trees_circuit(
                qubits,
                terms,
                float(time_value),
                repetitions=repetitions,
                order=order,
            )
            built = perf_counter()
            result = circuit.execute(backend=backend, device="cpu", seed=seed + index)
            executed = perf_counter()
            counts = Counter(result.sample(shots=shots, seed=seed + index))
            sampled = perf_counter()
            row = {
                "time": float(time_value),
                "sampled_probability": counts.get(exit_bits, 0) / shots,
                "exit_count": counts.get(exit_bits, 0),
                "build_seconds": built - build_start,
                "execute_seconds": executed - built,
                "sample_seconds": sampled - executed,
            }
            rows.append(row)
            if representative is None or row["sampled_probability"] > max(
                item["sampled_probability"] for item in rows[:-1]
            ):
                representative = circuit
        report = {
            "qubits": qubits,
            "nodes": model.node_count,
            "exit_state": model.exit_state,
            "exit_bits": exit_bits,
            "terms": len(terms),
            "full_terms": len(full_terms),
            "order": order,
            "repetitions": repetitions,
            "shots": shots,
            "backend": backend,
            "rows": rows,
        }
        self.log(
            "Stage 4/4: Exporting the representative circuit and probability plot..."
        )
        peak = max(rows, key=lambda row: row["sampled_probability"])
        total = perf_counter() - started
        self.status = "success"
        self.summary = (
            f"Peak sampled exit probability {peak['sampled_probability']:.6f} "
            f"at t={peak['time']:g}."
        )
        self.update_output(
            {
                "Nodes": model.node_count,
                "Exit state": exit_bits,
                "Pauli terms": f"{len(terms)}/{len(full_terms)}",
                "Peak exit probability": peak["sampled_probability"],
                "Peak time": peak["time"],
                "Rows": rows,
                "Model construction (s)": model_end - started,
                "Pauli decomposition (s)": decomposition_end - model_end,
                "Total time (s)": total,
            }
        )
        circuit_path = self.save_circuit(representative)
        plot_name = "glued_trees_exit_probability.png"
        plot_results(report, os.path.join(self.algo_dir, plot_name))
        filename = self.save_txt()
        return self._build_return_dict(
            True, circuit_path, [filename, plot_name], representative
        )


def test(
    qubits=6,
    seed=0,
    shots=8192,
    repetitions=10,
    order=1,
    max_terms=None,
    backend="numpy",
    times=None,
):
    """Standard test entry point."""
    algorithm = GluedTreesAlgorithm(text_mode="legacy")
    return algorithm.run(
        qubits, seed, shots, repetitions, order, max_terms, backend, times
    )


if __name__ == "__main__":
    qubits = 6  # [PARAM]
    seed = 0  # [PARAM]
    shots = 8192  # [PARAM]
    repetitions = 10  # [PARAM]
    order = 1  # [PARAM]
    max_terms = None  # [PARAM]
    backend = "numpy"  # [PARAM]
    times = ""  # [PARAM]
    test(qubits, seed, shots, repetitions, order, max_terms, backend, times)
