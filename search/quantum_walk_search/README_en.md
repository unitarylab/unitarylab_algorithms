# Continuous-Time Quantum Walk Search Explained

## Parameter Settings

The parameters select a built-in or JSON graph, comma-separated marked vertices, optional coupling and evolution time, Hamiltonian-simulation method, step count, shots, and seed. Empty `gamma` and `evolution_time` enable automatic selection.

> **Summary**: The algorithm encodes graph connectivity and marked vertices in a Hamiltonian, evolves a uniform graph state, and measures the marked subspace.

---

## Table of Contents

- [Execution Flow](#execution-flow)
- [Core Idea](#core-idea)
- [Mathematical Principles](#mathematical-principles)
- [Algorithm Steps](#algorithm-steps)
- [Quantum Advantage](#quantum-advantage)
- [Complexity Analysis](#complexity-analysis)
- [Applications and Impact](#applications-and-impact)

---

## Execution Flow

Validate the graph, select coupling and time, construct the search Hamiltonian, simulate its evolution from the uniform graph state, sample vertices, compare against exact spectral evolution, and export the circuit and report.

---

## Core Idea

Continuous-time quantum walks encode graph structure in a Hamiltonian. Marking changes target-vertex energies so coherent interference can concentrate amplitude in the marked subspace.

---

## Mathematical Principles

For adjacency $A$ and marked set $M$,

$$H=-\gamma A-\sum_{w\in M}|w\rangle\langle w|,$$

and

$$P_M(t)=\sum_{w\in M}|\langle w|e^{-iHt}|s_G\rangle|^2.$$

Non-power-of-two graphs are zero-padded and the padded probability is reported.

---

## Algorithm Steps

Validate input, choose $\gamma$ and $t$, simulate $e^{-iHt}$, execute from the uniform state, sample, and report probabilities, error, counts, and resources.

---

## Quantum Advantage

On suitable graphs such as the complete graph, marked amplitude can be amplified in $O(\sqrt{N/M})$-scale time. Advantage depends on graph spectrum and parameters; classical state-vector execution is a demonstration, not wall-clock speedup.

---

## Complexity Analysis

The register uses $\lceil\log_2N\rceil$ qubits. Classical dense matrices require $O(4^q)$ storage, while circuit cost depends on the Hamiltonian-simulation method, steps, and target error.

---

## Applications and Impact

Applications include spatial and network search, graph algorithms, Hamiltonian-simulation studies, and teaching spectral effects in quantum walks.

## Implementation Interface And Limits

`QuantumWalkSearchAlgorithm(text_mode="plain", algo_dir=None).run()` defaults to
`num_vertices=8, marked="2,5", graph_type="complete", graph_json="",
gamma=None, evolution_time=None, method="trotter", target_error=1e-4,
simulation_steps=8, shots=128, seed=7, backend="numpy", device="cpu",
dtype=np.complex128`. The standard `test()` and Web entry use the dtype string
`"complex128"`, converted before calling `run()`.

`graph_json` is inline JSON, not a path. It accepts a square adjacency array,
an object with `adjacency`, or an object with `num_vertices` and `edges`.
Each edge is `[u,v]` or `[u,v,weight]`; repeated edges accumulate.
Custom input overrides the built-in graph, but `marked` remains a separate
argument: a `marked` field in inline JSON is not used by `run()`.
The research helper `load_graph_problem(path)` instead reads a file with
its own marked vertices. Graphs require at least two vertices, finite,
approximately symmetric, non-negative weights and a zero diagonal under
the original tolerances. Marked vertices must be nonempty, unique and in range.
The standard run has a 32-vertex limit; only `solve_graph_search(allow_large=True)`
can override it.

`backend/device/dtype` are forwarded to Hamiltonian-simulation construction
and final circuit execution. The final default remains NumPy CPU complex128.
The original helper implicitly used Torch for simulator construction;
making both stages follow the supplied settings is a necessary interface
difference and still requires numerical comparison. Spectral scans and
classical reference calculations retain their original NumPy precision.
Backend/device support depends on the installed UnitaryLab version;
NumPy is CPU only. There is no automatic fallback or precision change.
The vertex sampling seed does not seed simulator construction.

The returned dictionary includes `status`, `circuit_path`, `plot`, `circuit`,
and the fields from `QuantumWalkResult.to_dict()`, plus `Elapsed time (s)`.
`status="ok"` means execution completed, not that a probability or error
threshold was achieved. `probabilities` has N entries; `padded_probability`
reports the remaining D-N states. `counts` keys are conventional
zero-padded binary vertex indices of width log2(D); frequency ties preserve
ascending vertex order. The dictionary does not return a statevector.
`solve_graph_search()` returns the richer result with `final_state` and
`simulation`; `run_search()` returns their historical tuple.

Standard output is `<cwd>/results/search/quantum_walk_search`: a measured
overview circuit SVG and a text report. `algo_dir` overrides that directory.
The research helper's JSON/PNG export remains optional; the standard run
does not request those exports, so its `artifacts` mapping is normally empty.
The retained research argparse `main()` is not called by the standard
`__main__` block and does not expose the three execution settings.

Known original limitations are preserved by user choice. Taylor and other
auxiliary-register methods may return a circuit larger than the D-dimensional
initial state accepted by the direct execution path. No auxiliary initialization,
postselection or probability reinterpretation has been added.
`target_error` is not a guaranteed achieved error, and steps are passed only
for `trotter/qdrift`; the underlying simulator may adjust the actual count.
Explicit zero time retains the original simulator behavior, which may encounter
zero-step edge cases depending on the installed implementation.

The selected version uses an integer histogram for sample frequencies and
marked counts. Floating-point expressions, random calls and result sorting are
unchanged. Static review is complete; algorithm, CLI, Web, tests and performance
measurements have not run. No measured speed or peak-memory improvement is claimed.
