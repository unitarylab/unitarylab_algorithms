<div align="center">

<h1>UnitaryLab Algorithms</h1>

<p>
  <strong>A practical quantum algorithm library built on the UnitaryLab simulator.</strong><br/>
  <strong>一个基于 UnitaryLab 模拟器的实用量子算法库。</strong>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3b82f6?style=flat-square&logo=python&logoColor=white" alt="Python 3.10, 3.11, and 3.12"/>
  <img src="https://img.shields.io/badge/UnitaryLab-required-7c3aed?style=flat-square" alt="UnitaryLab required"/>
  <img src="https://img.shields.io/badge/Quantum_Algorithms-41-f59e0b?style=flat-square" alt="41 Quantum Algorithms"/>
  <img src="https://img.shields.io/badge/Categories-9-22c55e?style=flat-square" alt="9 Categories"/>
</p>

<p>
  <a href="https://unitarylab.com/">Website / 官网</a>
  &middot;
  <a href="https://docs.unitarylab.com/en/docs/unitarylab-algorithms-user-manual/">Technical Documentation</a>
  &middot;
  <a href="https://docs.unitarylab.com/zh/docs/unitarylab-algorithms-user-manual/">技术文档</a>
  &middot;
  <a href="https://pypi.org/project/unitarylab-algorithms/">PyPI</a>
</p>

</div>

---

<a name="english"></a>

## English

### What is this?

**UnitaryLab Algorithms** is a collection of independent quantum algorithm implementations maintained by [UnitaryLab](https://unitarylab.com/), with a companion [Quantum Skill](https://github.com/unitarylab/quantum-skills) library to guide learning and usage. It provides ready-to-run algorithm modules, parameter configurations for execution, and algorithm descriptions in both Chinese and English, making it suitable for learning, demonstrating, and integrating with the UnitaryLab quantum simulator.

The library currently contains **41 algorithms / equation-solving modules** across **9 categories**.

---

### Algorithms Covered

| Category | Algorithms |
|----------|-----------|
| **Cryptology** | Discrete Logarithm, Shor, Simon |
| **Fundamental Algorithms** | Hadamard Transform, Hadamard Test, Amplitude Amplification, Amplitude Estimation, Grover, QPE |
| **Hamiltonian Simulation** | Suzuki-Trotter, qDrift, Taylor Series, QSP-based Hamiltonian Simulation, Cartan Decomposition |
| **Linear Algebra** | AQC, HHL, LCU, QFT, QSP, QSVT Linear Solver, VQLS |
| **Quantum Chemistry** | Molecular DMRG |
| **Quantum Machine Learning** | VQE, Fermi-Hubbard VQE, QAOA, QCBM, VQC, CVQNN, Ising |
| **Schrodingerization** | 1D Heat Equation, 2D Heat Equation, 1D Advection Equation |
| **State Preparation** | MPS, Multiplexer, Mottonen, Pauli, Superposition |
| **Quantum Search** | Glued Trees, Hidden Shift, Quantum Walk Search, Quantum Backtracking |

---

### Installation

Install the UnitaryLab simulator dependency (Python 3.10–3.12):

```bash
pip install unitarylab
```

To use the quantum chemistry module, install the chemistry extra (currently supported on Linux and macOS):

```bash
pip install "unitarylab[chemistry]"
```

Install this algorithm package:

```bash
pip install unitarylab-algorithms
```

Download the source repository:

```bash
git clone https://github.com/unitarylab/unitarylab_algorithms.git
cd unitarylab_algorithms
```

For local source development, direct script examples below assume commands are run from the cloned repository root. To import modules with the `unitarylab_algorithms` package path, install the package or run Python from the parent directory of the cloned repository.

---

### Usage

Import and run an algorithm class:

```python
from unitarylab_algorithms import GroverAlgorithm

algo = GroverAlgorithm(text_mode="plain")
result = algo.run(n=3, target="101")

print(result["status"])
print(result["circuit_path"])
```

Or run an algorithm script directly from the cloned repository root:

```bash
python fundamental_algorithm/grover/algorithm.py
```

By default, generated files are written under:

```text
results/<category>/<algorithm>/
```

Typical outputs include:

| Field | Meaning |
|-------|---------|
| `status` | Execution status: `ok` on success, `failed` on failure |
| `circuit_path` | Path to the exported circuit SVG |
| `plot` | List of generated output files |
| `circuit` | The constructed quantum circuit object |
| algorithm-specific fields | Final states, probabilities, errors, solutions, or optimization results |

---

### Adding a New Algorithm

Use `template.py` and existing folders as references:

1. Create a new folder under the appropriate category.
2. Implement `algorithm.py` by extending `BaseAlgorithm`.
3. Provide a `test(...)` function for local and web-side execution.
4. In the `__main__` block, mark replaceable inputs with `# [PARAM]`; names should match `parameters.json`.
5. Add `parameters.json`, `README_en.md`, and `README_zh.md`.
6. Export the algorithm class from the category `__init__.py` and top-level `__init__.py` when needed.

---

### License

This project is licensed under the MIT license. For details, please refer to the `LICENSE` file in the repository root directory or the license description included in the distribution package.

---

<a name="chinese"></a>

## 中文

### 这是什么？

**UnitaryLab Algorithms** 是由 [UnitaryLab](https://unitarylab.com/) 维护的独立量子算法实现集合，可结合配套的 [Quantum Skill](https://github.com/unitarylab/quantum-skills) 技能库学习和使用算法。它提供可直接运行的算法模块、用于执行的参数配置，以及中英文算法说明，适合量子算法学习、演示和与 UnitaryLab 量子模拟器集成。

当前库包含 **41 个算法/方程求解模块**，覆盖 **9 个方向**。

---

### 算法覆盖范围

| 分类 | 算法 |
|------|------|
| **密码学** | 离散对数、Shor 算法、Simon 算法 |
| **基础量子算法** | Hadamard 变换、Hadamard 测试、振幅放大、振幅估计、Grover、QPE |
| **哈密顿量模拟** | Suzuki-Trotter、qDrift、Taylor 级数、基于 QSP 的哈密顿量模拟、Cartan 分解 |
| **线性代数** | AQC、HHL、LCU、QFT、QSP、QSVT 线性求解器、VQLS |
| **量子化学** | 分子 DMRG |
| **量子机器学习** | VQE、Fermi-Hubbard VQE、QAOA、QCBM、VQC、CVQNN、Ising |
| **Schrodingerization** | 一维热方程、二维热方程、一维对流方程 |
| **量子态制备** | MPS、Multiplexer、Mottonen、Pauli、Superposition |
| **量子搜索** | Glued Trees、Hidden Shift、Quantum Walk Search、Quantum Backtracking |

---

### 安装

安装 UnitaryLab 模拟器依赖（Python 3.10–3.12）：

```bash
pip install unitarylab
```

如需使用量子化学模块，请安装 chemistry 可选依赖（目前支持 Linux 和 macOS）：

```bash
pip install "unitarylab[chemistry]"
```

安装算法库：

```bash
pip install unitarylab-algorithms
```

下载源码仓库：

```bash
git clone https://github.com/unitarylab/unitarylab_algorithms.git
cd unitarylab_algorithms
```

如果在源码目录中开发或调试，下方直接运行脚本的示例默认在克隆后的仓库根目录执行。若要使用 `unitarylab_algorithms` 包路径导入模块，请先安装该包，或从克隆仓库的父目录运行 Python。

---

### 使用方法

导入并运行算法类：

```python
from unitarylab_algorithms import GroverAlgorithm

algo = GroverAlgorithm(text_mode="plain")
result = algo.run(n=3, target="101")

print(result["status"])
print(result["circuit_path"])
```

也可以在克隆后的仓库根目录直接运行单个算法脚本：

```bash
python fundamental_algorithm/grover/algorithm.py
```

默认情况下，生成文件会写入：

```text
results/<category>/<algorithm>/
```

常见输出包括：

| 字段 | 含义 |
|------|------|
| `status` | 执行状态，成功时为 `ok`，失败时为 `failed` |
| `circuit_path` | 导出的线路图 SVG 路径 |
| `plot` | 生成的输出文件列表 |
| `circuit` | 构造出的量子线路对象 |
| 算法自定义字段 | 最终态、概率、误差、求解结果或优化结果等 |

---

### 新增算法

新增算法时，建议参考 `template.py` 和现有算法目录：

1. 在对应分类下创建新的算法目录。
2. 在 `algorithm.py` 中继承 `BaseAlgorithm` 并实现算法逻辑。
3. 提供 `test(...)` 函数，便于本地和网页端统一调用。
4. 在 `__main__` 代码块中，用 `# [PARAM]` 标记可替换输入；参数名需与 `parameters.json` 保持一致。
5. 补充 `parameters.json`、`README_en.md` 和 `README_zh.md`。
6. 如需统一导出，在分类 `__init__.py` 和顶层 `__init__.py` 中加入算法类。

---

### License

本项目采用 MIT 许可证。详情请参阅仓库根目录中的 `LICENSE` 文件，或发布包中随附的许可证说明。
