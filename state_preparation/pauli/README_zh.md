# Pauli-Word 态制备算法详解

## 参数设置

- `Psi`: 目标量子态向量，必须是非零一维向量，长度不超过 $2^{\text{target\_qubits}}$。
- `target_qubits`: 用于制备目标态的量子比特数。
- `target_error`: 期望达到的近似误差。

> **总结**：Pauli-word 态制备是一种变分态制备方法。算法固定一组有序 Pauli words，构造 PauliRot 乘积线路，并通过经典优化寻找旋转参数，使制备态与目标态的 fidelity 尽可能高。

---

## 目录

- [运行流程](#运行流程)
- [核心思想](#核心思想)
- [数学原理](#数学原理)
- [算法步骤](#算法步骤)
- [量子优势](#量子优势)
- [复杂度分析](#复杂度分析)
- [应用与影响](#应用与影响)

---

## 运行流程

1. **参数准备**：
   - 将 `Psi` 归一化并补齐。
   - 根据目标量子比特数生成固定 Pauli-word 序列。
2. **参数化线路构造**：
   - 为每个 Pauli word 分配一个实参数。
   - 构造 Pauli rotation 门的乘积。
3. **目标函数评估**：
   - 将参数化线路作用在 $|0^n\rangle$ 上。
   - 计算候选态与目标态的 fidelity。
4. **经典优化**：
   - 通过多个确定性初值最小化 $1-F(\theta)$。
   - 在可用时使用 parameter-shift 梯度。
5. **结果输出**：
   - 输出优化后的权重、Pauli words、线路、稠密矩阵和最终误差。

---

## 核心思想

算法假设目标态可以由如下形式近似：
$$
U(\theta)|0^n\rangle\approx|\psi\rangle,
$$
其中
$$
U(\theta)=\prod_{\ell=1}^{M}\exp\left(-\frac{i\theta_\ell}{2}P_\ell\right).
$$
$P_\ell$ 是 Pauli word，例如 $XIZ$ 或 $YZX$，$\theta_\ell$ 是待训练的实参数。

---

## 数学原理

### Pauli Rotation

任意 Pauli word 都满足
$$
P^2=I.
$$
因此
$$
\exp\left(-\frac{i\theta}{2}P\right)
=
\cos\frac{\theta}{2}I-i\sin\frac{\theta}{2}P.
$$
这使得算法可以不用通用矩阵指数，直接构造稠密 Pauli rotation 矩阵。

### Fidelity 目标函数

候选态为
$$
|\psi(\theta)\rangle=U(\theta)|0^n\rangle.
$$
其 fidelity 为
$$
F(\theta)=|\langle\psi_{\text{target}}|\psi(\theta)\rangle|^2.
$$
优化器最小化
$$
L(\theta)=1-F(\theta).
$$

### Parameter-Shift 梯度

由于 Pauli rotation 只有两个本征值分支，导数可以通过
$$
\frac{\partial F}{\partial\theta_i}
=\frac{1}{2}\left[
F(\theta_i+\pi/2)-F(\theta_i-\pi/2)
\right]
$$
计算。

---

## 算法步骤

1. 归一化并补齐目标向量。
2. 为指定量子比特数生成 Pauli-word 列表。
3. 缓存稠密 Pauli 矩阵。
4. 定义参数化酉矩阵乘积 $U(\theta)$。
5. 定义 fidelity 和 loss 函数。
6. 从多个初值运行经典优化。
7. 选择忽略全局相位后误差最小的参数。
8. 构建最终 PauliRot 线路和矩阵。

---

## 量子优势

| 任务 | 解析态制备 | Pauli-Word 态制备 |
|------|------------|-------------------|
| 线路结构 | 由目标振幅直接决定 | 固定可训练 ansatz |
| 硬件友好性 | 可能需要复杂受控门 | 使用 Pauli rotations |
| 精确性 | 通常确定性 | 近似且依赖优化器 |

当希望使用可训练 PauliRot ansatz，而不是完全解析分解时，该方法很有价值。

---

## 复杂度分析

- **参数数量**：由选定 Pauli-word 序列决定。
- **优化成本**：取决于参数数量、重启次数和优化器收敛情况。
- **可扩展性**：随着量子比特数增加，Pauli-word 列表增长会带来较高成本。
- **精度**：由于依赖数值优化，不保证所有目标态都能达到给定误差。

---

## 应用与影响

- 变分态制备实验。
- 量子机器学习中的可训练数据加载层。
- 比较解析态制备与优化型态制备。
- 研究 Pauli-word 顺序和 ansatz 表达能力。
- 测试 parameter-shift 梯度和优化器行为。
