# Hidden Shift Algorithm Explained

## Parameter Settings

- `qubits`: Positive even register size; default 6. A supplied `shift` determines it.
- `shift`: Hidden binary string, or empty to generate it from `seed`.
- `shots`: Final-state samples; default 100.
- `seed`: Seed for shift generation and sampling; default 41.
- `backend`: UnitaryLab `numpy` or `torch` backend.
- `measurement_mode`: `sample` evolves once and samples the final state; `execute` repeatedly executes a measured circuit.

> **Summary**: The algorithm exploits the phase relation between a bent Boolean function and its shifted version, using Hadamard interference to recover the hidden string.

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

1. Validate or generate an even-length hidden string $s$.
2. Build the phase oracle for $f(x)=\bigoplus_i x_{2i}x_{2i+1}$.
3. Implement $g(x)=f(x\oplus s)$ as $X_sU_fX_s$.
4. Build $H\rightarrow U_g\rightarrow H\rightarrow U_f\rightarrow H$.
5. Execute, sample, and compare the dominant bit string with $s$.
6. Save the circuit and standardized report.

---

## Core Idea

Classical point queries reveal little about a global input translation. A quantum phase oracle acts on all inputs coherently, and the Walsh–Hadamard transform converts that translation into a measurable linear phase. The selected bent function is self-dual, allowing the second $U_f$ to cancel the remaining function-dependent phase.

---

## Mathematical Principles

Define

$$f(x)=\bigoplus_{i=0}^{n/2-1}x_{2i}x_{2i+1},\qquad g(x)=f(x\oplus s),$$

with phase oracle

$$U_f|x\rangle=(-1)^{f(x)}|x\rangle,$$

and shifted oracle

$$U_g=X_sU_fX_s.$$

Hadamard interference converts the shift into the linear phase $(-1)^{s\cdot y}$. Self-duality lets the second oracle cancel the $f(y)$ phase, and the final Hadamard layer maps the linear phase to $|s\rangle$.

---

## Algorithm Steps

1. Apply $H^{\otimes n}$ to $|0\rangle^{\otimes n}$.
2. Apply $X$ on the shifted positions, execute $U_f$, and undo $X$.
3. Apply the second Hadamard layer.
4. Execute $U_f$ again to cancel the bent-function phase.
5. Apply the final Hadamard layer to obtain $|s\rangle$.
6. Sample and verify the result.

---

## Quantum Advantage

| Method | Oracle-query behavior |
|---|---|
| Classical | Infer the translation from individual values |
| Quantum Hidden Shift | Extract the global translation through phase interference |

The precise advantage depends on the function family and oracle model. This implementation demonstrates the deterministic bent-function circuit.

---

## Complexity Analysis

- $n$ qubits.
- $3n$ Hadamard gates across three layers.
- $n/2$ CZ gates per $U_f$, used twice.
- At most $2n$ X gates for the shifted oracle.
- Classical state-vector simulation still scales exponentially in $n$.

---

## Applications and Impact

Hidden-shift algorithms inform quantum query complexity, Boolean Fourier analysis, oracle learning, and cryptanalysis. They also demonstrate how phase kickback and Walsh–Hadamard interference convert hidden global structure into a classical output.
