# unitarylab_algorithms

本 [算法库](https://github.com/unitarylab/unitarylab_algorithms) 由 [Unitarylab](https://unitarylab.com/) 整理开发实现，包含可独立调用的量子算法实现。目前共整理出 28 个算法，按主题划分为 6 个类别：密码学、基础算法、哈密顿量模拟、线性代数、量子机器学习、Schrodingerization 方程求解。

## 下载

本算法库运行依赖于 UnitaryLab 量子模拟器软件包，可通过pip下载
```bash
pip install unitarylab
```

通过pip下载本算法库
```bash
pip install unitarylab-algorithms
```

## 当前算法清单

### 1. cryptology

- `discrete_log`: Discrete Log Algorithm
- `shor`: Shor Algorithm
- `simon`: Simon Algorithm

### 2. fundamental_algorithm

- `hadamard_transform`: Hadamard Transform Algorithm
- `hadamard_test`: Hadamard Test Algorithm
- `amplitude_amplification`: Amplitude Amplification Algorithm
- `amplitude_estimation`: Amplitude Estimation Algorithm
- `grover`: Grover Algorithm
- `qpe`: Quantum Phase Estimation Algorithm

### 3. hamiltonian_simulation

- `trotter`: Trotter Algorithm
- `qdrift`: QDrift Algorithm
- `taylor`: Taylor Algorithm
- `qsp`: Quantum Signal Processing for Hamiltonian Simulation
- `cartan`: Cartan Decomposition Algorithm

### 4. linear_algebra

- `hhl`: HHL Algorithm
- `lcu`: LCU Algorithm
- `qft`: Quantum Fourier Transform Algorithm
- `qsp`: Quantum Signal Processing Algorithm
- `qsvt_qlsa`: QSVT Linear Solver Algorithm
- `vqls`: VQLS Algorithm

### 5. quantum_machine_learning

- `vqe`: Variational Quantum Eigensolver
- `qaoa`: Quantum Approximate Optimization Algorithm
- `qcbm`: Quantum Circuit Born Machine
- `vqc`: Variational Quantum Classifier
- `cvqnn`: Continuous-Variable Quantum Neural Network

### 6. schrodingerization

- `equation_heat`: Heat Equation Algorithm
- `equation_heat2d`: Heat2D Equation Algorithm
- `equation_advection`: Advection Equation Algorithm

