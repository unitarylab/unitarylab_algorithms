"""General multi-marked continuous-time quantum-walk search with UnitaryLab."""

# The self-contained research implementation intentionally uses delayed imports,
# rich result objects, and parameter-heavy public APIs.
# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
# pylint: disable=too-many-instance-attributes,import-outside-toplevel
# pylint: disable=wrong-import-position,multiple-imports,redefined-outer-name
# pylint: disable=invalid-name,duplicate-code

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json, math, os
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence
import warnings

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_name, "1")

import numpy as np

DEFAULT_NUM_VERTICES = 8
DEFAULT_MARKED = (2, 5)
DEFAULT_SHOTS = 128
DEFAULT_TARGET_ERROR = 1e-4
DEFAULT_SIMULATION_STEPS = 8
SAFE_VERTEX_LIMIT = 32
Adjacency = Sequence[Sequence[float]] | np.ndarray
Marked = int | Sequence[int]


def _next_power_of_two(value: int) -> int:
    return 1 << max(0, (int(value) - 1).bit_length())


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _normalise_marked(marked: Marked, size: int) -> tuple[int, ...]:
    values = (
        (int(marked),)
        if isinstance(marked, (int, np.integer))
        else tuple(map(int, marked))
    )
    _require(bool(values), "at least one marked vertex is required")
    _require(len(set(values)) == len(values), "marked vertices must be unique")
    _require(
        all(0 <= vertex < size for vertex in values),
        "a marked vertex is outside the graph",
    )
    return tuple(sorted(values))


def validate_adjacency(adjacency: Adjacency) -> np.ndarray:
    matrix = np.asarray(adjacency, dtype=float)
    _require(
        matrix.ndim == 2 and matrix.shape[0] == matrix.shape[1],
        "adjacency must be a square matrix",
    )
    _require(matrix.shape[0] >= 2, "the graph must contain at least two vertices")
    _require(bool(np.all(np.isfinite(matrix))), "adjacency contains a non-finite value")
    _require(
        bool(np.allclose(matrix, matrix.T, atol=1e-12)),
        "continuous-time search currently requires an undirected graph",
    )
    _require(
        bool(np.allclose(np.diag(matrix), 0.0, atol=1e-12)),
        "self-loops are not supported; adjacency diagonal must be zero",
    )
    _require(not bool(np.any(matrix < -1e-12)), "edge weights must be non-negative")
    return matrix


def built_in_graph(num_vertices: int, graph_type: str = "complete") -> np.ndarray:
    _require(num_vertices >= 2, "num_vertices must be at least 2")
    kind = str(graph_type).lower()
    if kind == "complete":
        return np.ones((num_vertices, num_vertices)) - np.eye(num_vertices)
    adjacency = np.zeros((num_vertices, num_vertices), dtype=float)
    if kind in {"cycle", "path"}:
        indices = np.arange(num_vertices - 1)
        adjacency[indices, indices + 1] = adjacency[indices + 1, indices] = 1.0
        if kind == "cycle" and num_vertices > 2:
            adjacency[0, -1] = adjacency[-1, 0] = 1.0
    elif kind == "star":
        adjacency[0, 1:] = adjacency[1:, 0] = 1.0
    else:
        _require(False, "graph_type must be complete, cycle, path, or star")
    return adjacency


def adjacency_from_edges(
    num_vertices: int, edges: Sequence[Sequence[float | int]]
) -> np.ndarray:
    _require(num_vertices >= 2, "num_vertices must be at least 2")
    adjacency = np.zeros((num_vertices, num_vertices), dtype=float)
    for edge in edges:
        _require(len(edge) in (2, 3), "each edge must be [u, v] or [u, v, weight]")
        left, right = map(int, edge[:2])
        weight = 1.0 if len(edge) == 2 else float(edge[2])
        _require(
            0 <= left < num_vertices and 0 <= right < num_vertices,
            f"edge {(left, right)} is outside the graph",
        )
        _require(left != right, "self-loops are not supported")
        _require(
            math.isfinite(weight) and weight >= 0,
            "edge weights must be finite and non-negative",
        )
        adjacency[left, right] += weight
        adjacency[right, left] += weight
    return validate_adjacency(adjacency)


def load_graph_problem(path: str | Path) -> tuple[np.ndarray, tuple[int, ...], str]:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if "adjacency" in data:
        adjacency = validate_adjacency(data["adjacency"])
    elif "edges" in data:
        adjacency = adjacency_from_edges(int(data["num_vertices"]), data["edges"])
    else:
        _require(False, "graph JSON requires either adjacency or edges")
        raise AssertionError
    return (
        adjacency,
        _normalise_marked(data["marked"], len(adjacency)),
        str(data.get("name", source.stem)),
    )


def default_coupling(adjacency: np.ndarray) -> float:
    if np.allclose(
        adjacency, np.ones_like(adjacency) - np.eye(len(adjacency)), atol=1e-12
    ):
        return 1.0 / len(adjacency)
    radius = float(np.max(np.abs(np.linalg.eigvalsh(adjacency))))
    return 1.0 / radius if radius > 1e-12 else 1.0


def graph_search_hamiltonian(
    adjacency: Adjacency, marked: Marked, gamma: float | None = None
) -> np.ndarray:
    matrix = validate_adjacency(adjacency)
    targets = _normalise_marked(marked, len(matrix))
    coupling = default_coupling(matrix) if gamma is None else float(gamma)
    _require(
        math.isfinite(coupling) and coupling > 0,
        "gamma must be a positive finite number",
    )
    dimension = _next_power_of_two(len(matrix))
    padded = np.zeros((dimension, dimension), dtype=float)
    padded[: len(matrix), : len(matrix)] = matrix
    padded[targets, targets] += 1.0 / coupling
    return -coupling * padded


def complete_graph_search_hamiltonian(
    num_vertices: int, marked: Marked, gamma: float | None = None
) -> np.ndarray:
    return graph_search_hamiltonian(built_in_graph(num_vertices), marked, gamma)


def _uniform_graph_state(size: int, dimension: int) -> np.ndarray:
    return np.pad(
        np.full(size, 1.0 / math.sqrt(size), dtype=complex), (0, dimension - size)
    )


def _exact_probability_series(
    hamiltonian: np.ndarray,
    initial: np.ndarray,
    marked: Sequence[int],
    times: np.ndarray,
) -> np.ndarray:
    values, vectors = np.linalg.eigh(hamiltonian)
    states = vectors @ (
        (vectors.conj().T @ initial)[:, None] * np.exp(-1j * np.outer(values, times))
    )
    return np.sum(np.abs(states[list(marked)]) ** 2, axis=0).real


def estimate_search_time(
    hamiltonian: np.ndarray,
    initial_state: np.ndarray,
    marked: Sequence[int],
    num_vertices: int,
    *,
    grid_points: int = 129,
) -> tuple[float, float]:
    horizon = 2.0 * math.pi * math.sqrt(num_vertices / len(marked))
    coarse = np.linspace(0.0, horizon, grid_points)
    probabilities = _exact_probability_series(
        hamiltonian, initial_state, marked, coarse
    )
    center, spacing = float(coarse[int(np.argmax(probabilities))]), float(coarse[1])
    fine_times = np.linspace(
        max(0.0, center - spacing), min(horizon, center + spacing), 65
    )
    fine = _exact_probability_series(hamiltonian, initial_state, marked, fine_times)
    best = int(np.argmax(fine))
    return float(fine_times[best]), float(fine[best])


def _circuit_summary(circuit: Any) -> dict[str, Any]:
    summary = circuit.analyze(show=False).get_summary()
    return {
        **{key: int(summary[key]) for key in ("num_qubits", "size", "depth")},
        "gate_counts": {
            str(key): int(value) for key, value in summary["gate_counts"].items()
        },
    }


@dataclass
class QuantumWalkResult:
    graph_name: str
    num_vertices: int
    hilbert_dimension: int
    marked_vertices: list[int]
    gamma: float
    evolution_time: float
    time_selection: str
    exact_scan_probability: float | None
    exact_probability_at_time: float
    success_probability: float
    simulation_probability_error: float
    measured_marked_count: int
    sampled_success_probability: float
    shots: int
    counts: dict[str, int]
    probabilities: list[float]
    padded_probability: float
    method: str
    target_error: float
    simulation_steps: int | None
    circuit_summary: dict[str, Any]
    artifacts: dict[str, str] = field(default_factory=dict)
    simulation: Any = field(default=None, repr=False)
    final_state: np.ndarray = field(default_factory=lambda: np.empty(0), repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if key not in {"simulation", "final_state"}
        }


def _write_visuals(
    simulation: Any,
    initial: np.ndarray,
    probabilities: np.ndarray,
    samples: np.ndarray,
    marked: Sequence[int],
    graph_name: str,
    output: Path,
    full: bool,
) -> dict[str, str]:
    from unitarylab import Circuit, ClassicalRegister, Register
    import matplotlib

    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str((output / ".matplotlib").resolve()))
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    qubit_count = int(math.log2(len(initial)))
    qubits = list(range(qubit_count))
    quantum = Register("q", qubit_count)
    classical = ClassicalRegister("vertex", qubit_count)
    overview = Circuit(quantum, classical, name=f"CTQW search: {graph_name}")
    direction = np.eye(1, len(initial), dtype=complex)[0] - initial
    direction /= np.linalg.norm(direction)
    prepare = Circuit(qubit_count, name="Prepare |s_G>")
    prepare.unitary(
        np.eye(len(initial)) - 2.0 * np.outer(direction, direction.conj()),
        target=qubits,
    )
    evolve = Circuit(qubit_count, name="U_H(t) = exp(-iHt)")
    evolve.append(simulation.circuit, target=qubits)
    overview.append(prepare, target=qubits)
    overview.append(evolve, target=qubits)
    overview.measure(quantum[:], classical[:])
    circuit_path = output / "quantum_walk_circuit.png"
    overview.draw(filename=str(circuit_path), title=f"CTQW search: {graph_name}")
    artifacts = {"circuit_diagram": str(circuit_path.resolve())}
    if full:
        expanded = output / "quantum_walk_circuit_expanded.png"
        simulation.circuit.decompose(n=1).draw(
            filename=str(expanded),
            title=f"CTQW Hamiltonian simulation gates: {graph_name}",
        )
        artifacts["expanded_circuit_diagram"] = str(expanded.resolve())

    vertices = np.arange(len(probabilities))
    mask = np.isin(vertices, marked)
    sampled = np.bincount(samples, minlength=len(probabilities))[
        : len(probabilities)
    ] / len(samples)
    figure, axis = plt.subplots(figsize=(9.0, 4.8))
    axis.bar(
        vertices[~mask],
        probabilities[~mask],
        color="#2563eb",
        alpha=0.82,
        label="unmarked vertex",
    )
    axis.bar(
        vertices[mask],
        probabilities[mask],
        color="#ef4444",
        alpha=0.82,
        label="marked vertex",
    )
    axis.plot(
        vertices,
        sampled,
        color="#111827",
        marker="o",
        linestyle="none",
        label="sampled frequency",
    )
    axis.set(
        title=f"Vertex measurement evidence: {graph_name}",
        xlabel="Vertex",
        ylabel="Probability",
        xticks=vertices,
        ylim=(0.0, min(1.0, max(0.05, float(np.max(probabilities)) * 1.18))),
    )
    axis.legend()
    figure.tight_layout()
    chart = output / "measurement_distribution.png"
    figure.savefig(chart, dpi=160)
    plt.close(figure)
    artifacts["measurement_chart"] = str(chart.resolve())
    return artifacts


def solve_graph_search(
    adjacency: Adjacency,
    marked: Marked,
    *,
    graph_name: str = "custom-graph",
    gamma: float | None = None,
    evolution_time: float | None = None,
    method: str = "trotter",
    target_error: float = DEFAULT_TARGET_ERROR,
    simulation_steps: int = DEFAULT_SIMULATION_STEPS,
    shots: int = DEFAULT_SHOTS,
    seed: int = 7,
    output_dir: str | Path | None = None,
    diagrams: bool = False,
    full_artifacts: bool = False,
    allow_large: bool = False,
    backend: str = "numpy",
    device: str = "cpu",
    dtype=np.complex128,
) -> QuantumWalkResult:
    from unitarylab.library import hamiltonian_simulation

    matrix = validate_adjacency(adjacency)
    size = len(matrix)
    _require(
        size <= SAFE_VERTEX_LIMIT or allow_large,
        f"graphs above {SAFE_VERTEX_LIMIT} vertices require allow_large=True",
    )
    targets = _normalise_marked(marked, size)
    _require(shots >= 1, "shots must be positive")
    _require(
        math.isfinite(target_error) and target_error > 0,
        "target_error must be positive",
    )
    _require(simulation_steps >= 1, "simulation_steps must be positive")
    coupling = default_coupling(matrix) if gamma is None else float(gamma)
    hamiltonian = graph_search_hamiltonian(matrix, targets, coupling)
    initial = _uniform_graph_state(size, len(hamiltonian))
    if evolution_time is None:
        selected_time, scan_probability = estimate_search_time(
            hamiltonian, initial, targets, size
        )
        time_selection = "small-instance exact spectral scan"
    else:
        selected_time, scan_probability = float(evolution_time), None
        _require(
            math.isfinite(selected_time) and selected_time >= 0,
            "evolution_time must be finite and non-negative",
        )
        time_selection = "user supplied"
    options = {"steps": simulation_steps} if method in {"trotter", "qdrift"} else {}
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Casting complex values to real discards the imaginary part",
            category=np.exceptions.ComplexWarning,
        )
        simulation = hamiltonian_simulation(
            hamiltonian,
            selected_time,
            method=method,
            target_error=target_error,
            backend=backend,
            device=device,
            dtype=dtype,
            **options,
        )
    final_state = np.asarray(
        simulation.circuit.execute(
            initial_state=initial.copy(), backend=backend, device=device, dtype=dtype
        ).state
    )
    full_probabilities = np.abs(final_state) ** 2
    success = float(np.sum(full_probabilities[list(targets)]))
    exact = float(
        _exact_probability_series(
            hamiltonian, initial, targets, np.asarray([selected_time])
        )[0]
    )
    samples = np.random.default_rng(seed).choice(
        len(hamiltonian), size=shots, p=full_probabilities / full_probabilities.sum()
    )
    histogram = np.bincount(samples, minlength=len(hamiltonian))
    values = np.flatnonzero(histogram)
    frequencies = histogram[values]
    width = int(math.log2(len(hamiltonian)))
    counts = {
        format(int(value), f"0{width}b"): int(count)
        for value, count in sorted(
            zip(values, frequencies), key=lambda item: int(item[1]), reverse=True
        )
    }
    marked_count = sum(int(histogram[vertex]) for vertex in targets)
    destination = Path(output_dir) if output_dir is not None else None
    if destination is not None:
        destination.mkdir(parents=True, exist_ok=True)
    artifacts = (
        _write_visuals(
            simulation,
            initial,
            full_probabilities[:size],
            samples,
            targets,
            graph_name,
            destination,
            full_artifacts,
        )
        if diagrams and destination
        else {}
    )
    result = QuantumWalkResult(
        graph_name,
        size,
        len(hamiltonian),
        list(targets),
        coupling,
        selected_time,
        time_selection,
        scan_probability,
        exact,
        success,
        abs(success - exact),
        marked_count,
        marked_count / shots,
        shots,
        counts,
        [float(value) for value in full_probabilities[:size]],
        float(np.sum(full_probabilities[size:])),
        method,
        target_error,
        simulation_steps if method in {"trotter", "qdrift"} else None,
        _circuit_summary(simulation.circuit),
        artifacts,
        simulation,
        final_state,
    )
    if destination is not None:
        (destination / "result.json").write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return result


def run_search(
    num_vertices: int = DEFAULT_NUM_VERTICES,
    marked: Marked = DEFAULT_MARKED,
    method: str = "trotter",
    *,
    adjacency: Adjacency | None = None,
    graph_type: str = "complete",
    gamma: float | None = None,
    evolution_time: float | None = None,
    target_error: float = DEFAULT_TARGET_ERROR,
    simulation_steps: int = DEFAULT_SIMULATION_STEPS,
    backend: str = "numpy",
    device: str = "cpu",
    dtype=np.complex128,
) -> tuple[float, np.ndarray, object]:
    matrix = (
        built_in_graph(num_vertices, graph_type)
        if adjacency is None
        else validate_adjacency(adjacency)
    )
    result = solve_graph_search(
        matrix,
        marked,
        graph_name=graph_type if adjacency is None else "custom-graph",
        gamma=gamma,
        evolution_time=evolution_time,
        method=method,
        target_error=target_error,
        simulation_steps=simulation_steps,
        backend=backend,
        device=device,
        dtype=dtype,
    )
    return result.success_probability, result.final_state, result.simulation


def _print_summary(result: QuantumWalkResult, elapsed: float, output: Path) -> None:
    top = ", ".join(f"{key}:{value}" for key, value in list(result.counts.items())[:6])
    circuit = result.circuit_summary
    print(f"""Quantum Walk Search
Graph: {result.graph_name}; vertices: {result.num_vertices}; marked: {result.marked_vertices}
Backend: numpy (CPU); method: {result.method}; steps: {result.simulation_steps}
Success probability: simulated={result.success_probability:.4%}; sampled={result.sampled_success_probability:.4%} ({result.measured_marked_count}/{result.shots})
Exact reference: {result.exact_probability_at_time:.4%}; simulation error: {result.simulation_probability_error:.4%}
Most frequent outcomes: {top}
Circuit: {circuit['num_qubits']} qubits; depth={circuit['depth']}; size={circuit['size']}
Total runtime (excluding imports): {elapsed:.6f} s
Result JSON: {(output / 'result.json').resolve()}""")
    for label, path in result.artifacts.items():
        print(f"{label}: {path}")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    add = parser.add_argument
    add("--graph-json", type=Path, help="custom graph JSON file")
    add(
        "--graph-type",
        choices=("complete", "cycle", "path", "star"),
        default="complete",
    )
    add("--marked", type=int, nargs="+", default=list(DEFAULT_MARKED))
    add("--gamma", type=float)
    add("--time", type=float, dest="evolution_time")
    add("--method", default="trotter")
    add(
        "--target-error",
        type=float,
        default=DEFAULT_TARGET_ERROR,
        help="metadata only; use --steps to control approximation",
    )
    for flag, default in (
        ("--num-vertices", DEFAULT_NUM_VERTICES),
        ("--steps", DEFAULT_SIMULATION_STEPS),
        ("--shots", DEFAULT_SHOTS),
        ("--seed", 7),
    ):
        add(flag, type=int, default=default)
    add("--output-dir", type=Path, default=script_dir / "walk_run")
    diagrams = parser.add_mutually_exclusive_group()
    diagrams.add_argument("--diagrams", dest="diagrams", action="store_true")
    diagrams.add_argument("--skip-diagrams", dest="diagrams", action="store_false")
    parser.set_defaults(diagrams=True)
    for flag in ("--full-artifacts", "--print-json", "--allow-large"):
        add(flag, action="store_true")
    args = parser.parse_args()
    if args.graph_json:
        adjacency, marked, name = load_graph_problem(args.graph_json)
    else:
        adjacency, marked, name = (
            built_in_graph(args.num_vertices, args.graph_type),
            tuple(args.marked),
            f"{args.graph_type}-{args.num_vertices}",
        )
    started = perf_counter()
    result = solve_graph_search(
        adjacency,
        marked,
        graph_name=name,
        gamma=args.gamma,
        evolution_time=args.evolution_time,
        method=args.method,
        target_error=args.target_error,
        simulation_steps=args.steps,
        shots=args.shots,
        seed=args.seed,
        output_dir=args.output_dir,
        diagrams=args.diagrams or args.full_artifacts,
        full_artifacts=args.full_artifacts,
        allow_large=args.allow_large,
    )
    _print_summary(result, perf_counter() - started, args.output_dir)
    if args.print_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    import sys

    _algorithms_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    _repository_dir = os.path.dirname(_algorithms_dir)
    for _path in (_repository_dir, _algorithms_dir):
        if _path not in sys.path:
            sys.path.insert(0, _path)
    from algo_base import BaseAlgorithm


def _optional_float(value):
    if value in (None, "", "None", "null"):
        return None
    return float(value)


def _marked_vertices(value) -> tuple[int, ...]:
    if isinstance(value, str):
        values = [part.strip() for part in value.split(",") if part.strip()]
        return tuple(int(part) for part in values)
    if isinstance(value, int):
        return (value,)
    return tuple(map(int, value))


def _custom_adjacency(value, num_vertices: int):
    if value in (None, "", "None", "null"):
        return None
    data = json.loads(value) if isinstance(value, str) else value
    if isinstance(data, dict):
        if "adjacency" in data:
            return validate_adjacency(data["adjacency"])
        if "edges" in data:
            return adjacency_from_edges(
                int(data.get("num_vertices", num_vertices)), data["edges"]
            )
        raise ValueError("graph_json requires 'adjacency' or 'edges'")
    return validate_adjacency(data)


def _build_overview_circuit(adjacency, simulation):
    """Build the complete prepare-evolve-measure search circuit."""
    from unitarylab import Circuit, ClassicalRegister, Register

    dimension = simulation.circuit.get_num_qubits()
    hilbert_dimension = 1 << dimension
    initial = _uniform_graph_state(len(adjacency), hilbert_dimension)
    basis_zero = np.zeros(hilbert_dimension, dtype=complex)
    basis_zero[0] = 1.0
    direction = basis_zero - initial
    direction /= np.linalg.norm(direction)
    prepare = Circuit(dimension, name="Prepare |s_G>")
    prepare.unitary(
        np.eye(hilbert_dimension) - 2.0 * np.outer(direction, direction.conj()),
        target=list(range(dimension)),
    )
    quantum = Register("vertex", dimension)
    classical = ClassicalRegister("result", dimension)
    overview = Circuit(quantum, classical, name="Quantum Walk Search")
    overview.append(prepare, target=quantum[:])
    overview.append(simulation.circuit, target=quantum[:])
    overview.measure(quantum[:], classical[:])
    return overview


class QuantumWalkSearchAlgorithm(BaseAlgorithm):
    """Search marked graph vertices by continuous-time Hamiltonian evolution."""

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
        super().__init__("Quantum Walk Search", "QWS", text_mode, algo_dir)

    # Public signature intentionally mirrors parameters.json.
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def run(
        self,
        num_vertices: int = 8,
        marked="2,5",
        graph_type: str = "complete",
        graph_json: str = "",
        gamma=None,
        evolution_time=None,
        method: str = "trotter",
        target_error: float = 1e-4,
        simulation_steps: int = 8,
        shots: int = 128,
        seed: int = 7,
        backend: str = "numpy",
        device: str = "cpu",
        dtype=np.complex128,
    ) -> dict[str, Any]:
        """Execute continuous-time quantum-walk search."""
        num_vertices, simulation_steps = int(num_vertices), int(simulation_steps)
        shots, seed = int(shots), int(seed)
        targets = _marked_vertices(marked)
        gamma, evolution_time = _optional_float(gamma), _optional_float(evolution_time)
        target_error = float(target_error)
        custom = _custom_adjacency(graph_json, num_vertices)
        adjacency = (
            built_in_graph(num_vertices, graph_type) if custom is None else custom
        )
        graph_name = graph_type if custom is None else "custom-graph"
        self.update_input(
            {
                "Number of vertices": len(adjacency),
                "Marked vertices": targets,
                "Graph": graph_name,
                "Gamma": "automatic" if gamma is None else gamma,
                "Evolution time": (
                    "automatic" if evolution_time is None else evolution_time
                ),
                "Method": method,
                "Target error": target_error,
                "Simulation steps": simulation_steps,
                "Shots": shots,
                "Seed": seed,
                "Backend": backend,
                "Device": device,
                "Dtype": str(dtype),
            }
        )
        self.log(
            "Stage 1/4: Validating the graph and constructing the search Hamiltonian..."
        )
        started = perf_counter()
        self.log(
            "Stage 2/4: Selecting the evolution time and building the simulation..."
        )
        result = solve_graph_search(
            adjacency,
            targets,
            graph_name=graph_name,
            gamma=gamma,
            evolution_time=evolution_time,
            method=str(method),
            target_error=target_error,
            simulation_steps=simulation_steps,
            shots=shots,
            seed=seed,
            backend=backend,
            device=device,
            dtype=dtype,
        )
        self.log(
            "Stage 3/4: Executing, sampling, and comparing with exact evolution..."
        )
        elapsed = perf_counter() - started
        self.status = "success"
        self.summary = (
            f"Marked-vertex probability {result.success_probability:.6f}; "
            f"sampled {result.sampled_success_probability:.6f}."
        )
        output = result.to_dict()
        output.update({"Elapsed time (s)": elapsed})
        self.update_output(output)
        self.log("Stage 4/4: Exporting circuit and result files...")
        circuit = _build_overview_circuit(adjacency, result.simulation)
        circuit_path = self.save_circuit(circuit)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, circuit)


# pylint: disable=too-many-arguments,too-many-positional-arguments
def test(
    num_vertices=8,
    marked="2,5",
    graph_type="complete",
    graph_json="",
    gamma=None,
    evolution_time=None,
    method="trotter",
    target_error=1e-4,
    simulation_steps=8,
    shots=128,
    seed=7,
    backend="numpy",
    device="cpu",
    dtype="complex128",
):
    """Standard test entry point."""
    algorithm = QuantumWalkSearchAlgorithm(text_mode="legacy")
    return algorithm.run(
        num_vertices,
        marked,
        graph_type,
        graph_json,
        gamma,
        evolution_time,
        method,
        target_error,
        simulation_steps,
        shots,
        seed,
        backend,
        device,
        np.dtype(dtype).type,
    )


if __name__ == "__main__":
    num_vertices = 8  # [PARAM]
    marked = "2,5"  # [PARAM]
    graph_type = "complete"  # [PARAM]
    graph_json = ""  # [PARAM]
    gamma = None  # [PARAM]
    evolution_time = None  # [PARAM]
    method = "trotter"  # [PARAM]
    target_error = 1e-4  # [PARAM]
    simulation_steps = 8  # [PARAM]
    shots = 128  # [PARAM]
    seed = 7  # [PARAM]
    backend = "numpy"  # [PARAM]
    device = "cpu"  # [PARAM]
    dtype = "complex128"  # [PARAM]
    test(
        num_vertices,
        marked,
        graph_type,
        graph_json,
        gamma,
        evolution_time,
        method,
        target_error,
        simulation_steps,
        shots,
        seed,
        backend,
        device,
        dtype,
    )
