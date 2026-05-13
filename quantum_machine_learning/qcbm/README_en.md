# Quantum Circuit Born Machine (QCBM)

## Parameter Settings

- `n`: Number of qubits. The default value is `4`.
- `layers`: Variational circuit depth. The default value is `4`.
- `epochs`: Number of training epochs. The default value is `40`.
- `lr`: Adam optimizer learning rate. The default value is `0.1`.

> **Summary**: This algorithm uses a Quantum Circuit Born Machine to learn a discrete target distribution. The code takes a 4-qubit BAS distribution as the target, builds a parameterized circuit from `Ry` rotations and ring-like `CX` entanglers, and updates the parameters with Adam using the parameter-shift rule. The final calculated result includes the final KL loss, the core quantum-computation time, and the generated circuit, loss, distribution-comparison, and sampling-visualization files.

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

1. **Target Distribution and Parameter Preparation**: Build the BAS target distribution and its valid states, then initialize the parameter tensor `theta`, the Adam optimizer, and the parameter-shift step size.
2. **Variational Circuit Construction**: Construct a parameterized circuit with layered `Ry` rotations and ring-style `CX` entanglement.
3. **Parameter-Shift Training Loop**: At each epoch, compute the current distribution, evaluate the KL-divergence loss, and estimate gradients explicitly through parameter-shift evaluations before updating the parameters.
4. **Post-training Distribution Evaluation**: Recompute the final learned distribution from the optimized parameters and compare it with the target distribution.
5. **Result Export**: Save the circuit diagram, KL-loss convergence curve, target-vs-learned distribution plot, and sampling visualization.

---

## Core Idea

The core idea of QCBM is to treat the measurement probabilities of a parameterized quantum circuit as a learnable discrete probability model. By adjusting the circuit parameters so that the generated distribution approaches a target distribution, the quantum circuit acts as a generative model over bitstrings.

---

## Mathematical Principles
QCBM uses the Born rule
$$
p_\theta(z) = |\langle z | \psi(\theta) \rangle|^2
$$
to turn the output state of a parameterized quantum circuit into a discrete bitstring distribution. In the current implementation, the target distribution is the BAS (Bars and Stripes) distribution, whose valid states are fixed to
$$
\{0, 3, 5, 10, 12, 15\}.
$$
The code assigns uniform probability to these states and zero probability to all others.

During training, the algorithm builds a variational circuit from `Ry` rotations and inter-layer ring `CX` entanglers, and uses the KL divergence
$$
D_{KL}(p_{\text{target}} || p_\theta)
$$
as the loss function. Instead of relying on direct automatic differentiation through the circuit, the gradients are estimated with the parameter-shift rule by evaluating the output distribution at positive and negative shifted parameter values. This yields an explicit gradient estimate for each variational angle while keeping the circuit structure transparent.

---

## Algorithm Steps

1. Build the BAS target distribution and initialize the variational parameters.
2. Construct the multi-layer parameterized circuit from `Ry` and `CX` gates.
3. Minimize the KL loss with parameter-shift gradient estimates.
4. Obtain the final learned quantum distribution.
5. Export the loss curve, distribution comparison, and sample plots.

---

## Quantum Advantage

| Task | Classical Generative Model | QCBM Advantage |
|---|---|---|
| Discrete distribution modeling | Often uses explicit probabilistic models or neural generative models | Directly generates probabilities from squared quantum amplitudes and naturally captures interference-induced correlations |

---

## Complexity Analysis

The cost of this implementation is mainly determined by the number of qubits `n`, the variational depth `layers`, the training length `epochs`, and the number of parameter-shift gradient evaluations. Since every parameter requires both a positive and a negative circuit evaluation per training step, the total number of circuit executions is significantly larger than a simple forward pass. This makes the current implementation best suited as a small-scale demonstration of QCBM training and parameter-shift optimization.

---

## Applications and Impact

- It is useful for demonstrating how quantum generative models can learn target probability distributions.
- It is an important example for understanding parameter-shift training, Born sampling, and quantum generative modeling.
- It can be extended to more general discrete data modeling and small-scale quantum sampling tasks.
