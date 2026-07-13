# Fermi–Hubbard VQE

## Parameter Settings

- `L`: Number of lattice sites in the open chain. The default value is `2`.
- `t`: Nearest-neighbor hopping coefficient. The default value is `1.0`.
- `U`: On-site interaction strength. The default value is `4.0`.
- `B`: Zeeman magnetic-field coefficient. The default value is `1.5`.
- `layers`: Number of VQE variational circuit layers. The default value is `5`.
- `max_iter`: Maximum number of COBYLA optimization iterations. The default value is `1000`.
- `seed`: Random seed for the initial VQE parameters. The default value is `7`.
- `measure_shots`: Number of shots for total-spin magnetic-moment measurement. The default value is `10000`; set it to `0` to skip measurement.

> **Summary**: This algorithm maps the open one-dimensional Fermi–Hubbard Hamiltonian to a Jordan–Wigner Pauli Hamiltonian, obtains an exact ground-state energy reference through dense diagonalization, and then optimizes a variational circuit with UnitaryLab VQE. The final result includes exact energy, VQE energy, absolute error, optimizer information, circuit and convergence plots, optimized parameters, and finite-shot total-spin magnetic-moment estimates.

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

1. **Model Construction and Pauli Mapping**: Build the Fermi–Hubbard Hamiltonian and convert it to a Jordan–Wigner Pauli expression.
2. **Exact Diagonalization**: Construct a dense matrix in the full Fock/Hilbert space and compute the lowest eigenvalue.
3. **VQE Optimization**: Use the official `VQEAlgorithm` with an Ry-Rz rotation ansatz and ring-connected CNOT entanglement.
4. **Result Export**: Save the optimized circuit, energy-convergence plot, and optimized parameters.
5. **Magnetic-Moment Measurement**: When `measure_shots > 0`, estimate the total-spin magnetic moment using X/Y/Z basis measurements.

## Core Idea

The Fermi–Hubbard model describes spinful fermions on a lattice. Each spin-site mode is encoded into a qubit, and a parameterized quantum state is optimized so that its energy expectation approaches the ground-state energy. For small systems, exact diagonalization provides a reference for measuring the VQE absolute error.

## Mathematical Principles

For an open chain of length `L`,

$$
H=-t\sum_{j=1}^{L-1}\sum_{\sigma}(c_{j\sigma}^{\dagger}c_{j+1,\sigma}+c_{j+1,\sigma}^{\dagger}c_{j\sigma})+U\sum_{j=1}^{L}n_{j\uparrow}n_{j\downarrow}-B\sum_{j=1}^{L}(n_{j\uparrow}-n_{j\downarrow}).
$$

The mode order is fixed as `(1↑, 1↓, 2↑, 2↓, ...)`. The project library generates the Pauli expression through the Jordan–Wigner mapping. Because NumPy and UnitaryLab use different qubit-endianness conventions, the adapter applies bit reversal and verifies that the Hamiltonian spectrum is unchanged.

VQE minimizes

$$
E(\theta)=\langle\psi(\theta)|H|\psi(\theta)\rangle.
$$

Each layer applies `Ry` and `Rz` rotations to every qubit, a nearest-neighbor CNOT chain, and a ring-closing CNOT. The number of trainable parameters is `2 × (2L) × layers`.

## Algorithm Steps

1. Construct the fermionic and Pauli Hamiltonians from `L`, `t`, `U`, and `B`.
2. Convert the Pauli Hamiltonian to a dense matrix and compute the exact ground-state energy.
3. Initialize the Ry-Rz ring-entangling ansatz and the COBYLA optimizer.
4. Evaluate the energy iteratively and retain the parameters producing the lowest observed energy.
5. Export the circuit diagram, convergence plot, and parameter file, then return VQE and exact-diagonalization results.
6. Optionally perform five full-register X/Y/Z-basis measurement settings to estimate `(Mx, My, Mz)`.

## Quantum Advantage

| Task | Classical Method | Role of VQE |
|---|---|---|
| Small-system ground-state energy | Dense exact diagonalization grows rapidly with system size | Represents a candidate ground state with a parameterized circuit and optimizes it through energy measurements |
| Interacting fermion modeling | Direct Fock-space treatment has exponential dimension | Maps fermionic modes to qubits and Pauli terms suitable for quantum execution |

## Complexity Analysis

The system contains `2L` qubits, and the dense Hamiltonian has dimension `2^(2L) × 2^(2L)`, so exact diagonalization is intended only for small-system validation. VQE cost is mainly determined by `layers`, `max_iter`, and the state-simulation or measurement cost of each energy evaluation. Increasing circuit depth can improve expressivity but also increases optimization and simulation cost.

## Applications and Impact

- Demonstrates Jordan–Wigner mapping and VQE ground-state search for interacting fermion systems.
- Validates variational quantum results against exact diagonalization.
- Provides an introductory workflow for Hubbard models, quantum magnetism, and quantum simulation of chemistry and materials.
