# Simon Algorithm Explained

## Parameter Settings

- `s`: The target hidden mask string $s$ (must be a binary string and cannot be all zeros). Default value is `"1101"`.

> **Summary**: Simon's algorithm finds the hidden periodic mask $s$ of a black-box function in polynomial time. Given this black box, it obtains linear equations through quantum superposition evaluation and coherent measurement, and finally computes the mask $s$ using classical Gaussian elimination.

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

1. **Parameter Preparation**: Check if the hidden mask $s$ is all zeros and calculate the relevant register size $n$ (requiring $2n$ qubits in total).
2. **Quantum Circuit Construction**:
   - Initialize the input register and output register.
   - Apply a Hadamard layer to the input register to prepare a uniform superposition state.
   - Apply the specific black-box function (Oracle) that encodes Simon's problem.
   - Measure the output register, and then apply a Hadamard layer to the input register again.
3. **Quantum Simulation and Execution**:
   - Execute the quantum circuit simulation.
   - Parse the resulting quantum state to extract all measured valid basis states (which correspond to the coefficients of the equations).
4. **Classical Post-processing (Solving Linear Equations)**:
   - Extract a finite number of linearly independent vectors from the obtained basis states.
   - Perform Gaussian elimination / back substitution in the $\mathbb{F}_2$ field to find $s$.
   - Verify whether the computed $s$ matches the target.
5. **Result Output**: Export the circuit diagram and output the computed mask $s$, the number of basis states, and the computation time report.

---

## Core Idea

Simon's algorithm solves **Simon's Problem**: Given a black-box function $f:\{0,1\}^n \to \{0,1\}^n$, find a non-zero hidden string $s$ such that:
$$f(x)=f(y) \iff x=y \quad \text{or} \quad y=x\oplus s$$

Classical methods require an exponential number of queries to find $s$ (using collisions via the birthday paradox). However, by causing "self-coherent cancellation," the quantum algorithm only needs to collect a small number of mutually orthogonal basis vectors, reducing the problem to classical linear equation solving.

---

## Mathematical Principles

### Black-Box Function and Measurement

Applying the prepared state to the Oracle yields the state:
$$\frac{1}{\sqrt{2^n}}\sum_{x\in \{0,1\}^n} |x\rangle|f(x)\rangle$$
When the second register is measured, the state of the first register collapses to $\frac{1}{\sqrt{2}}(|x\rangle + |x \oplus s\rangle)$.

### Interference Effect

Applying the Hadamard transform to the first register again causes interference that cancels out all quantum states satisfying $y \cdot s = 1 \pmod{2}$, so only states $|y\rangle$ satisfying:
$$y \cdot s = 0 \pmod{2}$$
have a non-zero probability of being measured.

---

## Algorithm Steps

1. **State Preparation**: Apply $H^{\otimes n}$ to the input register to create a uniform superposition state.
2. **Oracle Query**: Apply the black-box function Oracle $U_f$.
3. **Interference Extraction**: Apply $H^{\otimes n}$ to the input register again.
4. **Measurement**: Measure the states to obtain vectors $y$ that satisfy $y \cdot s = 0 \pmod{2}$.
5. **Repeated Collection**: Run multiple times or extract enough quantum state data to collect $n-1$ linearly independent vectors $y$.
6. **Classical Elimination**: Execute Gaussian elimination in the $\mathbb{F}_2$ domain to solve the linear equations for $s$.

---

## Quantum Advantage

| Method | Query Complexity |
|------|-----------|
| Classical Algorithm | $\Omega(2^{n/2})$ |
| Simon (Quantum Algorithm) | $O(n)$ |

Note: Simon's algorithm is one of the earliest models to clearly demonstrate an **exponential speedup** of quantum computing over classical computing (leaping directly from exponential to polynomial complexity).

---

## Complexity Analysis

- **Quantum Query Complexity**: Requires running the quantum circuit and querying the Oracle approximately $O(n)$ times to guarantee finding $n-1$ linearly independent terms.
- **Classical Post-processing Complexity**: Mainly involves solving a system of $n$ linear equations, with a complexity of $O(n^3)$.
- **Overall Time Complexity**: Polynomial grade, $O(n^3)$.

---

## Applications and Impact

- **Cryptanalysis and System Evaluation**: The core collision detection design of this algorithm was later used in cryptographic analysis, including breaking specific classical symmetric cryptographic design structures, such as particular Feistel networks or variants with Even-Mansour structures.
- **Algorithm Inspiration**: Simon's algorithm proved that quantum computers can exponentially accelerate hidden period problems, directly inspiring Peter Shor to extend the problem structure beyond the $\mathbb{F}_2$ domain, ultimately giving birth to Shor's algorithm for breaking RSA.
