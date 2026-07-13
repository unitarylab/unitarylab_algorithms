# Mottönen State Preparation Explained

## Parameter Settings

- `Psi`: Target quantum state vector. It must be non-zero and one-dimensional, with length no larger than $2^{\text{target\_qubits}}$.
- `target_qubits`: Number of target qubits used to prepare the state.
- `target_error`: Allowed numerical preparation error.

> **Summary**: The Mottönen state-preparation algorithm prepares an arbitrary quantum state by separating amplitude and phase synthesis. It uses uniformly controlled $R_Y$ rotations for probability amplitudes, uniformly controlled $R_Z$ rotations for phases, and Gray-code decompositions to express the controlled rotations with elementary gates.

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

1. **Parameter Preparation**:
   - Normalize and pad `Psi` to dimension $2^n$.
   - Validate that `target_qubits` is compatible with the input state length.
2. **Amplitude and Phase Extraction**:
   - Write each amplitude as $a_j=r_je^{i\phi_j}$.
   - Use $r_j$ for amplitude synthesis and $\phi_j$ for phase synthesis.
3. **Uniformly Controlled Rotation Construction**:
   - Compute $R_Y$ rotation angles from recursive probability splits.
   - Compute $R_Z$ rotation angles from blockwise phase differences.
4. **Gray-Code Decomposition**:
   - Convert each uniformly controlled rotation into a Gray-code ladder of single-qubit rotations and CNOT gates.
5. **Result Output**:
   - Return the circuit, the dense evolution matrix, and the phase-invariant preparation error.

---

## Core Idea

For a target state
$$
|\psi\rangle=\sum_{j=0}^{2^n-1}a_j|j\rangle
=\sum_{j=0}^{2^n-1}r_je^{i\phi_j}|j\rangle,
$$
the algorithm constructs
$$
U_{\text{Mottonen}}=U_Z(\phi)U_Y(r)
$$
so that
$$
U_{\text{Mottonen}}|0^n\rangle=|\psi\rangle.
$$
The $U_Y$ stage prepares the absolute values of amplitudes, while the $U_Z$ stage writes the relative phases. Both stages are implemented with uniformly controlled rotations.

---

## Mathematical Principles

### Recursive Probability Splitting

For a probability block divided into left and right halves,
$$
P_L=\sum_{j\in L}r_j^2,\qquad P_R=\sum_{j\in R}r_j^2.
$$
The required rotation angle is
$$
\alpha_y=2\arcsin\sqrt{\frac{P_R}{P_L+P_R}}.
$$
This follows from
$$
R_Y(\alpha)|0\rangle=\cos(\alpha/2)|0\rangle+\sin(\alpha/2)|1\rangle.
$$

### Phase Recovery

After amplitude preparation, uniformly controlled $R_Z$ rotations restore the relative phase structure by comparing the average phase difference between paired left and right blocks.

### Gray-Code Ladder

A uniformly controlled rotation with $m$ controls is converted into $2^m$ single-qubit rotations interleaved with CNOT gates. Gray-code ordering ensures that adjacent control patterns differ by only one bit.

---

## Algorithm Steps

1. Normalize and pad the target vector.
2. Split the target amplitudes into magnitudes and phases.
3. Recursively compute uniformly controlled $R_Y$ angles.
4. Recursively compute uniformly controlled $R_Z$ angles.
5. Decompose every uniformly controlled rotation with a Gray-code ladder.
6. Build the final circuit and compute the resulting matrix.
7. Compare the prepared state with the target state up to global phase.

---

## Quantum Advantage

| Task | Direct Classical Description | Mottönen Circuit Construction |
|------|------------------------------|-------------------------------|
| Arbitrary state loading | Store $2^n$ complex amplitudes | Deterministic circuit from amplitudes |
| Exact small-scale preparation | Dense matrix construction | Structured rotations and CNOT ladders |

Mottönen preparation is not an exponential speedup algorithm by itself; its value is that it gives a deterministic and systematic circuit synthesis method for arbitrary state loading.

---

## Complexity Analysis

- **Qubit Cost**: $n$ target qubits.
- **Gate Cost**: Exponential in $n$ for arbitrary states, because a generic state has $O(2^n)$ independent amplitudes.
- **Classical Preprocessing**: $O(2^n)$ angle computation plus decomposition overhead.

---

## Applications and Impact

- General-purpose arbitrary quantum state preparation.
- Baseline for comparing state-loading methods such as multiplexer and MPS preparation.
- Data loading for small quantum machine-learning demonstrations.
- Exact test-state generation for validating simulators and circuit compilers.
