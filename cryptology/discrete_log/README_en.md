# Discrete Logarithm Algorithm Explained

## Parameter Settings

- `g`: Base, default value is `3`.
- `y`: Target value, default value is `13`.
- `P`: Modulus (typically a prime number), default value is `17`.

> **Summary**: The discrete logarithm algorithm is used to find the unknown $x$ in $g^x \equiv y \pmod P$ in polynomial time. Given the inputs $g$, $y$, and $P$, it encodes the period information using Quantum Phase Estimation, combines classical continued fractions with modular arithmetic techniques, and ultimately outputs the computed discrete logarithm $x$.

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
   - Verify that $g$ and $y$ must be coprime with $P$.
   - Based on the bit length of $P$, calculate the count register size $n_{\text{count}}$ and work register size $n_{\text{work}}$ (a total of $2n_{\text{count}} + n_{\text{work}}$ qubits).
2. **Quantum Circuit Construction**:
   - Initialize two control (count) registers (corresponding to the powers of $g$ and $y^{-1}$) and one work register.
   - Apply a Hadamard layer to the control registers to prepare a uniform superposition state.
   - Initialize the work register to $|1\rangle$.
   - For the first control register, apply controlled modular multiplication operators with multipliers $g^{2^i}$ (simulated by matrices).
   - For the second control register, apply controlled modular multiplication operators with multipliers $(y^{-1})^{2^j}$ where $y^{-1}$ is the inverse in $\pmod P$ (simulated by matrices).
   - Apply the **Inverse Quantum Fourier Transform (IQFT)** to both control registers.
3. **Quantum Simulation and Measurement**:
   - Execute the quantum circuit simulation.
   - Extract the probability distribution of the respective quantum state components for further analysis.
4. **Classical Post-processing (Continued Fractions & Congruences)**:
   - Extract the most probable sets of observational values $(c_1, c_2)$ from the measured probability spectrum.
   - Use classical continued fraction algorithms to analyze the ratio $c_1/N$ and extract the possible group order (period) $r$.
   - Based on the extracted results for $x_1/r$ and $x_2/r$, formulate the linear modular equation $x \cdot x_1 + x_2 \equiv 0 \pmod r$ and solve for $x$.
   - Verify if the result satisfies $g^x \equiv y \pmod P$.
5. **Result Output**: Export the SVG chart of the quantum circuit, output the computation time, the detected period $r$, and the found result $x$.

---

## Core Idea

To solve the discrete logarithm problem $g^x \equiv y \pmod P$ over a finite cyclic group, Peter Shor demonstrated that it could be reduced to a Hidden Subgroup Problem (a 2D period-finding problem).
Define a function:
$$f(a,b) = g^a y^{-b} \bmod P$$
Evidently, if a pair $(a,b)$ is found such that $f(a,b) = 1$, since $y = g^x$, this implies:
$$g^a (g^x)^{-b} = g^{a - bx} \equiv 1 \pmod P$$
This equality holds when $a - bx \equiv 0 \pmod r$ (where $r$ is the multiplicative order of $g$). The unknown $x$ can then be classically computed using the modular inverse: $x = ab^{-1} \bmod r$. Thus, by locating the group's order and the function's implicit 2-dimensional period via quantum superposition and phase estimation, the variable $x$ can be successfully resolved.

---

## Mathematical Principles

### Controlled Group Operations and Joint State
Using two registers each of size $N$ to represent the superposition state $(a,b)$, the joint state represents:
$$\frac{1}{N}\sum_{a=0}^{N-1}\sum_{b=0}^{N-1}|a\rangle|b\rangle|g^ay^{-b}\bmod P\rangle$$
This implicitly computes and encapsulates the periodic information across a 2D grid defined by $x$.

### Two-Dimensional Quantum Fourier Transform
After applying two independent Quantum Fourier Transforms, the system's amplitudes will constructively interfere (forming peaks) around specific coordinate pairs $(c_1, c_2)$ satisfying:
$$\frac{c_1}{N} \approx \frac{k}{r} \quad \text{and} \quad \frac{c_2}{N} \approx \frac{kx}{r}$$
where $r$ is the period (the order of $g$ modulo $P$). By doing so, $r$ can be extracted from $c_1$, and subsequently $x$ can be derived by calculating $c_2/c_1 \approx x \pmod r$.

---

## Algorithm Steps

1. **Classical Pre-check**: Check the coprime conditions and calculate the required sizes for the control and work registers.
2. **State Preparation**: Prepare $|0\rangle^{\otimes 2n} |1\rangle$, then apply a Hadamard layer to obtain $|+\rangle^{\otimes 2n} |1\rangle$.
3. **Quantum Period Mapping**: Apply the two-dimensional black-box controlled operator $U|a\rangle|b\rangle|z\rangle = |a\rangle|b\rangle|z \cdot g^a y^{-b} \bmod P\rangle$.
4. **IQFT Phase Extraction**: Apply IQFT to the first two registers to concentrate the amplitudes toward $c_1, c_2$.
5. **Classical Measurement and Parsing**: Extract the period and $x$ using the continued fractions theorem. Verify the answer via back substitution over the original congruence until success.

---

## Quantum Advantage

| Task | Classical Complexity | Quantum Complexity (Shor DLP) |
|------|-----------|----------------|
| Solving Discrete Logarithm | Sub-exponential time (e.g., General Number Field Sieve) | $O((\log P)^3)$ |

Note: Just as with prime factorization, Shor's treatment of the discrete logarithm problem achieved an exponential quantum speedup. This effectively undermines the foundation of traditional cryptographic systems like Diffie-Hellman and Elliptic Curves.

---

## Complexity Analysis

- **Quantum Part**: $O(\log P)$ qubit footprint; polynomial grade $O((\log P)^3)$ quantum gate operations are required to establish the grid of controlled modular multiplications and IQFTs.
- **Overall Computation Time**: Stemming from the high likelihood of sampling correct states and the efficiency of classical post-processing (finding large inverse numbers and continued fractions), the overall time complexity is $O((\log P)^3)$.

---

## Applications and Impact

- **Breaking Public-Key Cryptography Foundations**: Beyond RSA (based on integer factorization), the security of modern cryptographic architectures—such as the Diffie-Hellman (DH) key exchange protocol, Digital Signature Algorithm (DSA), ElGamal, and Elliptic Curve Cryptography (ECC) variations—is constructed entirely on the intractability of the classical discrete logarithm problem, all of which fall to this algorithm model.
- **Driving the Next-Generation Security Formats**: Because quantum algorithms can crack these protocols in polynomial time, this algorithm serves as a forceful catalyst, pushing the global computer industry toward Post-Quantum Cryptography (PQC), such as lattice-based and hash-based cryptography.
