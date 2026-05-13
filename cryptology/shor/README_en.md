# Shor Algorithm Explained

## Parameter Settings

- `N`: The composite number to be factored (e.g., 15, 21).
- `method`: The method for solving controlled modular exponentiation. Options are `"matrix"` (unitary matrix) or `"operator"` (elementary logic gates). Default is `"matrix"`.

> **Summary**: The Shor algorithm factors a composite number into the product of prime factors. Given an input composite number $N$, it calculates the non-trivial factors of $N$.

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

1. **Classical Pre-check**: The algorithm first checks whether $N$ is even.
2. **Random Base Selection and Verification**:
   - Randomly select an integer $a \in [2, N-1]$.
   - Check $\gcd(a, N)$. If it is greater than 1, the factors are directly obtained through classical calculation.
3. **Quantum Circuit Construction**:
   - Determine the number of auxiliary qubits based on the selected `method` (`"matrix"` mode requires $\log N$; `"operator"` mode requires approximately $2\log N + 2$).
   - Initialize the counting qubit register ($2\log N$ qubits).
   - Apply the Hadamard layer to prepare the superposition state.
   - Execute the **Controlled Modular Exponentiation** circuit to encode the period information.
   - Apply the **Inverse Quantum Fourier Transform (IQFT)**.
4. **Quantum Simulation and Measurement**:
   - Execute the quantum circuit simulation.
   - Measure the counting register to obtain the observation value.
5. **Classical Post-processing (Continued Fractions)**:
   - Use the continued fraction algorithm to extract the possible period $r$ from the measured value.
   - Verify whether $r$ can derive the non-trivial factors of $N$.
6. **Result Output**: If successful, output the factor pair; if it fails and the maximum number of attempts has not been reached, jump back to Step 2.

---

## Core Idea

The key insight of Shor's algorithm is: **reducing the integer factorization problem to a period-finding problem**.

For a random integer $a$ ($1 < a < N$, and $\gcd(a,N)=1$), consider the function:
$$f(x) = a^x \bmod N$$

This function is periodic, and its period $r$ satisfies $a^r \equiv 1 \pmod{N}$. If $r$ is even and $a^{r/2} \not\equiv -1 \pmod{N}$, the non-trivial factors of $N$ can be calculated by:
$$\gcd(a^{r/2}-1,\;N) \quad \text{or} \quad \gcd(a^{r/2}+1,\;N)$$

---

## Mathematical Principles

### Modular Arithmetic Basics

For $N = p \times q$, Euler's theorem guarantees:
$$a^{\phi(N)} \equiv 1 \pmod{N}$$
Therefore, a period $r$ that divides $\phi(N)=(p-1)(q-1)$ must exist.

### Quantum Fourier Transform (QFT)

QFT is the quantum analog of classical DFT:
$$\text{QFT}|j\rangle = \frac{1}{\sqrt{2^n}}\sum_{k=0}^{2^n-1}e^{2\pi ijk/2^n}|k\rangle$$

### Period Finding and Quantum Phase Estimation

By preparing the superposition state $\frac{1}{\sqrt{r}}\sum_{x=0}^{r-1}|x\rangle$ and applying QFT, peaks appear at integer multiples of $2^n/r$, allowing the period $r$ to be extracted.

---

## Algorithm Steps

1. **Classical Pre-check**: If $N$ is even, factor it directly.
2. **Random Selection**: Randomly select $a$ such that $1 < a < N$. If $\gcd(a,1) > 1$, output the result directly.
3. **Quantum Period Finding**: Perform phase estimation/IQFT on the unitary operator $U_f|x\rangle = |a^x \bmod N\rangle$ to find the period $r$.
4. **Classical Post-processing**: If $r$ satisfies the conditions, compute the factors $p = \gcd(a^{r/2}-1, N)$ and $q = \gcd(a^{r/2}+1, N)$.

---

## Quantum Advantage

| Task | Classical Complexity | Shor Quantum Complexity |
|------|-----------|----------------|
| Integer Factorization | Sub-exponential (GNFS) | $O((\log N)^3)$ |
| Period Finding | $O(\sqrt{N})$ (Pollard rho) | $O((\log N)^2)$ |

---

## Complexity Analysis

- **Quantum Part** (QPE Period Finding): $O(\log^2 N)$ gate operations; $O(\log N)$ qubits.
- **Overall Algorithm**: Combined with Schönhage–Strassen multiplication, the total complexity is $O((\log N)^3)$, which is polynomial relative to $N$.

---

## Applications and Impact

- **Cryptography**: Breaks RSA and ECC, driving the development of Post-Quantum Cryptography (PQC).
- **Quantum Supremacy**: The first quantum algorithm proven to have exponential speedup on a practically useful problem.
- **Standardization**: Prompted the rollout of the NIST Post-Quantum Cryptography Standardization Project.
