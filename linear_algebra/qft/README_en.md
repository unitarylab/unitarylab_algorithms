# Quantum Fourier Transform (QFT) Explained

## Parameter Settings

- `n`: The number of qubits on which the QFT acts.
- `state`: The input state vector. The default value is `[1, 0, 0, ..., 0]`. If omitted, the code uses the basis state $|0\cdots0\rangle$; if provided, the state is normalized before being initialized on the quantum register.
- `inverse`: Whether to execute the inverse quantum Fourier transform. The default value is `False`. When set to `True`, the code takes the dagger of the constructed QFT circuit to obtain IQFT.

> **Summary**: This algorithm constructs a QFT or IQFT circuit for `n` qubits and applies it either to a user-provided input state or to the default zero state. The final calculated result includes the simulated final quantum state, the reference state computed with NumPy FFT/iFFT, the verification error between them, and the generated circuit files.

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

1. **QFT Circuit Construction**: Build the circuit from the most significant qubit down to the least significant one by applying a Hadamard gate and the required controlled-phase gates, then perform the final swaps that reverse the qubit order; if `inverse=True`, take the dagger of the whole circuit to obtain IQFT.
2. **Input-State Loading**: If `state` is provided, normalize and initialize it on the quantum register; otherwise use the default basis state $|0\cdots0\rangle$.
3. **Quantum Simulation**: Append the QFT or IQFT circuit to the register and execute the quantum simulation to obtain the final state vector.
4. **Classical FFT Verification**: Use NumPy `ifft` or `fft` to compute the reference result and compare it with the simulated final state through a vector-norm error.
5. **Result Output**: Save the final state, the reference state, the verification error, the runtime, and the decomposed circuit diagram together with the text result file.

---

## Core Idea

QFT is the unitary quantum analogue of the classical discrete Fourier transform. It re-encodes amplitudes from the computational basis into a frequency-domain basis so that phase structure can be extracted and exploited by interference. In this implementation, layered Hadamard and controlled-phase gates accumulate the Fourier phases, and the final swaps restore the standard output ordering of the transform.

---

## Mathematical Principles

For an $n$-qubit register, the QFT is defined on a computational basis state $|x\rangle$ by
$$
\mathrm{QFT}|x\rangle = \frac{1}{\sqrt{2^n}} \sum_{y=0}^{2^n-1} e^{2\pi ixy/2^n}|y\rangle.
$$
Its inverse satisfies
$$
\mathrm{QFT}^{-1}|y\rangle = \frac{1}{\sqrt{2^n}} \sum_{x=0}^{2^n-1} e^{-2\pi ixy/2^n}|x\rangle.
$$
In the code, the QFT is synthesized by applying a Hadamard gate to each qubit and then adding controlled-phase rotations with angle
$$
\frac{\pi}{2^{i-j}}
$$
between qubits `j` and `i`. A final layer of swaps reverses the qubit order to match the standard QFT convention. To verify correctness, the program compares the simulated quantum output with the NumPy Fourier-transform result, where forward QFT is checked against `ifft(state) * sqrt(2^n)` and inverse QFT is checked against `fft(state) / sqrt(2^n)`.

---

## Algorithm Steps

1. Construct the standard QFT circuit for `n` qubits, or take its dagger to obtain IQFT when requested.
2. Normalize and load the input state vector, or use the default zero state.
3. Execute the QFT circuit and obtain the simulated final quantum state.
4. Compute the classical reference result with FFT or iFFT.
5. Report the quantum output, the reference output, and the verification error.

---

## Quantum Advantage

| Task | Classical Realization | QFT Quantum Advantage |
|------|-----------------------|-----------------------|
| Embedding Fourier structure inside quantum algorithms | Classical FFT acts on classical arrays only | QFT directly encodes frequency-domain phase structure on quantum superposition states, enabling phase estimation, period finding, and interference-based subroutines |

---

## Complexity Analysis

The standard QFT circuit on `n` qubits typically uses $O(n^2)$ controlled-phase and swap operations. This implementation builds the exact gate sequence explicitly, so the circuit depth is mainly determined by the number of controlled-phase gates. An approximate QFT could reduce the number of small-angle rotations, but the current implementation keeps the full exact version so that it can be compared directly with the NumPy reference transform.

---

## Applications and Impact

- It is a core subroutine in quantum phase estimation, Shor's algorithm, and period-finding algorithms.
- It is widely used to extract phase information from eigenstates and periodic structures.
- It is also one of the foundational algorithms for understanding quantum interference and frequency-domain encoding.
