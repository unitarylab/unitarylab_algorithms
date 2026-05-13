# Continuous Variable Quantum Neural Network (CVQNN)

## Parameter Settings

- `layers`: Number of variational layers. The default value is `2`.
- `cutoff`: Fock-space truncation dimension. The default value is `6`.
- `epochs`: Number of training epochs. The default value is `40`.
- `lr`: Adam optimizer learning rate. The default value is `0.05`.

> **Summary**: This algorithm uses a continuous-variable quantum neural network to perform binary classification on 2D training data. It first standardizes the features, then builds a CV model in truncated Fock space with displacement, squeezing, rotation, Kerr nonlinearity, and beam-splitter-like coupling, and finally optimizes the parameters with Adam. The final calculated result includes the final training loss, the final classification accuracy, the total runtime, and the generated circuit and metric-plot files.

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

1. **Data Preprocessing and Model Initialization**: Standardize the input features, convert the labels into training targets, and initialize the CVClassifier, Adam optimizer, and mean-squared-error loss.
2. **Quantum Phase-Space Architecture Construction**: Build a topology circuit for visualization according to `layers` and initialize the trainable continuous-variable model parameters.
3. **Variational Training Loop**: Perform forward propagation, loss evaluation, backpropagation, and parameter updates at each epoch while recording the loss history.
4. **Classification Evaluation**: Recompute predictions with the trained model and evaluate the final classification accuracy.
5. **Result Export**: Save the quantum circuit diagram, the training-loss and decision-boundary plot, and the final metrics.

---

## Core Idea

The core idea of CVQNN is to encode classical continuous features into quantum states through displacement operations and then transform those states through trainable Gaussian and non-Gaussian continuous-variable gates. The classification output is extracted from the expectation value of an observable, so the model learns a decision boundary directly in quantum phase space rather than in a qubit-based computational basis.

---

## Mathematical Principles
Continuous-variable quantum neural networks operate in the Fock-space representation of quantum harmonic oscillators. In the code, `CVSimulator` constructs the annihilation operator `a`, the creation operator `adag`, the position operator `x_op`, and the number operator `n_op`, while the vacuum state is used as the initial reference state. The two input features of each sample are encoded as displacement operations on two modes, creating a two-mode input state.

At each variational layer, the model applies rotation, squeezing, displacement, and Kerr-nonlinearity operations to each mode, followed by a beam-splitter-like two-mode coupling transformation. After `layers` layers, the algorithm measures the expectation value of the position operator of the first mode,
$$
\langle x \rangle,
$$
and uses it as the classification output. During training, the labels are mapped from `{0,1}` to `{-1,1}`, and the model parameters are optimized by minimizing the mean-squared error with Adam.

---

## Algorithm Steps

1. Standardize the training features and convert the labels into training targets.
2. Encode each 2D sample into a two-mode continuous-variable quantum state through displacement gates.
3. Evolve the state through multiple trainable single-mode gates and two-mode coupling layers.
4. Use the position-operator expectation value as the model output and train with MSE loss.
5. Report the final accuracy and export the loss curve and decision-boundary plot.

---

## Quantum Advantage

| Task | Classical Model | CVQNN Advantage |
|---|---|---|
| Continuous-feature classification | Classical neural networks learn decision boundaries in Euclidean feature space | Directly encodes continuous inputs into CV quantum states and uses Gaussian plus non-Gaussian phase-space transformations for richer expressive dynamics |

---

## Complexity Analysis

The computational cost of this implementation is mainly determined by the Fock cutoff `cutoff`, the variational depth `layers`, and the training length `epochs`. A larger cutoff increases the matrix dimension per mode, deeper circuits require more matrix exponentials and Kronecker-structured operations, and more epochs increase the total number of gradient updates. For this reason, the current implementation is best understood as a demonstrative prototype of the CVQNN training workflow and phase-space modeling strategy.

---

## Applications and Impact

- It is useful for demonstrating continuous-variable quantum machine learning on low-dimensional continuous data.
- It highlights how displacement, squeezing, Kerr nonlinearity, and inter-mode coupling combine inside a CV model.
- It provides a starting point for further study of optical quantum neural networks and continuous-variable variational learning.
