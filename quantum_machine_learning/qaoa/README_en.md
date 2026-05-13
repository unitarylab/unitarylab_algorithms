# Quantum Approximate Optimization Algorithm (QAOA)

## Parameter Settings

- `edges`: The graph edge list. The default value is `[[0,1],[1,2],[2,3],[3,0],[0,4],[1,5]]`.
- `n`: The number of qubits, which also matches the number of graph vertices. The default value is `6`.
- `layers`: The number of QAOA evolution layers. The default value is `4`.
- `max_iter`: The maximum number of COBYLA optimization iterations. The default value is `100`.

> **Summary**: This algorithm uses QAOA to solve a Max-Cut problem. It first constructs the cost Hamiltonian from the input edges, then builds a parameterized circuit with alternating cost and mixer layers, and finally optimizes the parameters with COBYLA. The final calculated result includes the optimal bitstring, the corresponding Max-Cut value, the optimized energy, the quantum-computation time, and the generated circuit, convergence, and partition-visualization files.

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

1. **Hamiltonian and Parameter-Space Initialization**: Construct the Max-Cut cost Hamiltonian from the input edge set and randomly initialize the `2 * layers` QAOA parameters.
2. **QAOA Circuit Construction**: Start from a uniform superposition and build the alternating cost-evolution and mixer-evolution layers.
3. **Variational Parameter Optimization**: Use COBYLA to minimize the expectation value of the cost Hamiltonian while recording the energy-convergence history.
4. **Optimal-State Decoding**: Re-execute the circuit with the optimized parameters, extract the most probable bitstring, and compute its Max-Cut value from the graph edges.
5. **Result Export**: Save the quantum circuit diagram, the energy-convergence plot, and the final graph partition visualization.

---

## Core Idea

The core idea of QAOA is to alternate between problem-Hamiltonian evolution and mixer-Hamiltonian evolution inside a shallow parameterized quantum circuit. For Max-Cut, low-energy states correspond to bitstrings that induce good graph cuts, so a classical optimizer only needs to update the angle parameters in order to search for better cuts through the quantum state landscape.

---

## Mathematical Principles
QAOA is a hybrid quantum-classical algorithm for combinatorial optimization. For the Max-Cut problem on a graph, the code first constructs the cost Hamiltonian
$$
H_C = \sum_{(u,v) \in E} Z_u Z_v,
$$
where each edge contributes one Pauli `Z_u Z_v` term. Although this uses the `Z_u Z_v` form directly, minimizing its expectation still favors assignments in which adjacent vertices lie on opposite sides of the cut.

The circuit starts from the uniform superposition created by Hadamard gates on all qubits. Each QAOA layer then contains a cost step associated with
$$
e^{-i \gamma_l H_C}
$$
and a mixer step associated with
$$
e^{-i \beta_l H_M}.
$$
In the implementation, the cost step is realized through a `CX-RZ-CX` pattern on every edge, while the mixer step is implemented by `RX` rotations on each qubit. The classical optimizer then searches for a parameter set that minimizes the measured energy.

---

## Algorithm Steps

1. Build the Max-Cut cost Hamiltonian from the graph edge list.
2. Initialize the angle parameters and construct the `layers`-deep QAOA circuit.
3. Optimize the parameters with COBYLA to minimize the output-state energy.
4. Extract the most probable bitstring from the optimized state.
5. Compute its Max-Cut value and export the graphical outputs.

---

## Quantum Advantage

| Task | Classical Methods | QAOA Advantage |
|---|---|---|
| Approximate combinatorial optimization | Often relies on heuristic search, integer programming, or local-improvement strategies | Encodes the optimization problem into quantum-state energy minimization and explores near-optimal solutions with shallow parameterized circuits under NISQ constraints |

---

## Complexity Analysis

The main cost of this implementation is determined by the number of qubits `n`, the number of edges `|E|`, the circuit depth `layers`, and the optimization budget `max_iter`. Every objective-function evaluation rebuilds and executes the full QAOA circuit, so larger graphs and deeper circuits increase the per-evaluation cost, while more optimizer iterations increase the total runtime. This makes the current implementation best suited as a small-scale Max-Cut and QAOA workflow prototype.

---

## Applications and Impact

- It serves as a concrete quantum approximate solver for Max-Cut.
- It is useful for understanding how optimization Hamiltonians, parameterized circuits, and hybrid optimizers work together.
- It also provides a natural starting template for extending to other Ising-type optimization problems.
