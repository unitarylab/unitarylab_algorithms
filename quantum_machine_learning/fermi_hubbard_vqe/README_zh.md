# 一维 Fermi–Hubbard 模型 VQE

## 参数设置

- `L`：开放链上的格点数，默认值为 `2`。
- `t`：最近邻跃迁系数，默认值为 `1.0`。
- `U`：格点内相互作用强度，默认值为 `4.0`。
- `B`：Zeeman 磁场系数，默认值为 `1.5`。
- `layers`：VQE 变分线路层数，默认值为 `5`。
- `max_iter`：COBYLA 最大优化迭代次数，默认值为 `1000`。
- `seed`：VQE 初始参数的随机种子，默认值为 `7`。
- `measure_shots`：总自旋磁矩测量的 shots 数，默认值为 `10000`；设为 `0` 可跳过测量。

> **摘要**：该算法将开放边界的一维 Fermi–Hubbard Hamiltonian 映射为 Jordan–Wigner Pauli Hamiltonian，先通过稠密矩阵严格对角化获得基态能量参考，再使用 UnitaryLab 的 VQE 优化变分线路。最终结果包括严格能量、VQE 能量、绝对误差、优化信息、线路图、收敛曲线、优化参数以及有限 shots 的总自旋磁矩测量结果。

---

## 目录

- [执行流程](#执行流程)
- [核心思想](#核心思想)
- [数学原理](#数学原理)
- [算法步骤](#算法步骤)
- [量子优势](#量子优势)
- [复杂度分析](#复杂度分析)
- [应用与意义](#应用与意义)

---

## 执行流程

1. **构造模型与 Pauli 映射**：建立 Fermi–Hubbard Hamiltonian，并使用 Jordan–Wigner 映射得到 Pauli 表达式。
2. **严格对角化**：在完整 Fock/Hilbert 空间中构造稠密矩阵，计算最低本征能量。
3. **VQE 优化**：调用官方 `VQEAlgorithm`，使用 Ry-Rz 旋转和环形 CNOT 纠缠线路搜索基态。
4. **结果导出**：保存优化线路、能量收敛图和优化参数。
5. **磁矩测量**：在 `measure_shots > 0` 时，通过 X/Y/Z 基测量估计总自旋磁矩。

## 核心思想

Fermi–Hubbard 模型用于描述晶格中具有自旋的费米子。算法将每个自旋-格点模式编码为一个量子位，在完整 Hilbert 空间中优化变分量子态，使其能量期望值尽可能接近 Hamiltonian 的基态能量。严格对角化结果作为小规模系统的精确基准，用于计算 VQE 的绝对误差。

## 数学原理

长度为 `L` 的开放链 Hamiltonian 为

$$
H=-t\sum_{j=1}^{L-1}\sum_{\sigma}(c_{j\sigma}^{\dagger}c_{j+1,\sigma}+c_{j+1,\sigma}^{\dagger}c_{j\sigma})+U\sum_{j=1}^{L}n_{j\uparrow}n_{j\downarrow}-B\sum_{j=1}^{L}(n_{j\uparrow}-n_{j\downarrow}).
$$

模式顺序固定为 `(1↑, 1↓, 2↑, 2↓, ...)`。Pauli 表达式使用项目库的 Jordan–Wigner 映射生成。由于 NumPy 基矢和 UnitaryLab 对量子位端序的约定不同，适配器会进行 bit-reversal，并检查 Hamiltonian 的谱在转换前后保持一致。

VQE 最小化

$$
E(\theta)=\langle\psi(\theta)|H|\psi(\theta)\rangle,
$$

其中每层包含每个量子位上的 `Ry`、`Rz`、相邻 CNOT 链以及首尾环形 CNOT。参数数量为 `2 × (2L) × layers`。

## 算法步骤

1. 根据 `L`、`t`、`U`、`B` 构造费米 Hamiltonian 和 Pauli Hamiltonian。
2. 将 Pauli Hamiltonian 转为稠密矩阵并计算精确最低能量。
3. 初始化 Ry-Rz 环形纠缠 ansatz 和 COBYLA 优化器。
4. 迭代计算能量期望值，保留优化过程中找到的最低能量参数。
5. 生成线路图、收敛曲线和参数文件，并返回 VQE 与严格对角化结果。
6. 可选地执行五组全量子位 X/Y/Z 基测量，估计 `(Mx, My, Mz)`。

## 量子优势

| 任务 | 经典方法 | VQE 的作用 |
| --- | --- | --- |
| 小规模基态能量 | 稠密精确对角化随系统规模快速增长 | 用参数化量子线路表示候选基态，并通过能量测量进行变分优化 |
| 费米子相互作用建模 | 直接处理指数增长的 Fock 空间 | 将费米模式映射到量子位和 Pauli 项，适配量子处理器执行 |

## 复杂度分析

系统包含 `2L` 个量子位，稠密 Hamiltonian 的矩阵维度为 `2^(2L) × 2^(2L)`，因此严格对角化只适合小规模验证。VQE 的成本主要由 `layers`、`max_iter` 和每次能量评估中的量子态模拟或测量开销决定。增加线路深度可能提升表达能力，但也会增加优化和模拟成本。

## 应用与意义

- 用于演示费米子多体系统的 Jordan–Wigner 映射与 VQE 基态搜索。
- 用严格对角化能量验证变分量子算法结果。
- 作为研究 Hubbard 模型、量子磁性和量子化学/材料模拟的入门工作流。
