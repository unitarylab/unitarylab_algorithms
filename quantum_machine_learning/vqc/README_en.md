# Variational Quantum Classifier (VQC)

## Parameter Settings

- `layers`: Number of variational layers. (default is `5`).
- `epochs`: Full-dataset passes. (default is `20`).
- `lr`: Adam optimizer learning rate. (default is `0.05`).
- `batch_size`: Mini-batch size. (default is `16`).

> **Summary**: This algorithm uses a variational quantum classifier to perform three-class classification on the Iris dataset. It first standardizes the 4-dimensional features and maps them into an angle range, then builds logits from a 4-qubit parameterized circuit and several Pauli-Z observables, and finally trains the parameters with the parameter-shift rule and Adam. The final calculated result includes the final loss, the final test accuracy, the quantum-computation time, and the generated circuit and training-metrics plots.

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

1. **Data Loading and Parameter Initialization**: Load the Iris dataset, standardize the features, map them to `[-pi/2, pi/2]`, and initialize the trainable parameters and the Adam optimizer.
2. **Quantum Circuit and Observable Construction**: Build the 4-qubit encoding-plus-variational circuit and construct 3 Pauli-Z observables used to form classification logits.
3. **Parameter-Shift Training Loop**: Compute cross-entropy loss on mini-batches and update each trainable parameter using gradients estimated by the parameter-shift rule.
4. **Test-Set Evaluation**: Evaluate the trained parameters on the held-out test set and record the classification accuracy.
5. **Result Export**: Save the circuit diagram together with the training loss and accuracy plot.

---

## Core Idea

The core idea of VQC is to encode classical features into a quantum circuit, transform them through trainable variational gates, and then use measurement outcomes as classification logits. In this view, the quantum circuit acts as a trainable feature extractor, while the classical loss function and optimizer align those quantum features with the supervised classification task.

---

## Mathematical Principles
Variational quantum classifiers are hybrid quantum-classical supervised models. In the current implementation, 4 qubits are used to match the 4 features of the Iris dataset. Each feature is first encoded as a `RY` rotation angle, after which every variational layer applies trainable `RY` gates and, except for the last layer, a ring of `CX` entangling gates.

To realize three-class classification, the code constructs 3 Pauli-Z observables acting on different target qubits and combines their expectation values into 3-dimensional logits. The loss function is cross entropy. Because the circuit parameters are not updated through direct backpropagation through the simulator, the implementation estimates gradients by shifting each parameter by `+pi/2` and `-pi/2`, applying the parameter-shift rule, and then passing the resulting gradients to Adam.

---

## Algorithm Steps

1. Load and preprocess the Iris data, mapping its 4 features into quantum encoding angles.
2. Construct the 4-qubit parameterized circuit and the multi-observable output structure.
3. Train the parameters with parameter-shift gradients and Adam.
4. Evaluate the classification accuracy on the test set.
5. Export the training-metrics plot and the circuit diagram.

---

## Quantum Advantage

| Task | Classical Classification Model | VQC Advantage |
|---|---|---|
| Multi-class supervised classification | Usually relies on classical neural networks or kernel models to learn feature boundaries | Builds trainable quantum feature representations through state evolution and multi-observable measurements |

---

## Complexity Analysis

The main cost of this implementation is determined by three factors: the number of epochs `epochs`, the batch size `batch_size`, and the total number of trainable parameters `4 * layers`. Since every parameter requires one positive-shift and one negative-shift circuit evaluation for each batch during training, parameter-shift learning introduces substantially more circuit calls than a single forward pass. For this reason, the current implementation is best understood as a small-scale demonstration of quantum classification and parameter-shift optimization.

---

## Applications and Impact

- It is useful for demonstrating how variational quantum classifiers operate on supervised learning tasks.
- It is a representative example of quantum feature encoding, multi-observable logit construction, and parameter-shift training.
- It can be extended to larger datasets or more expressive quantum-classification architectures.
