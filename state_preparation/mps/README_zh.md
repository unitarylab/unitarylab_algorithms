# MPS 态制备算法详解

## 参数设置

- `Psi`: 目标量子态向量，必须是非零一维向量，长度不超过 $2^{\text{target\_qubits}}$。
- `target_qubits`: 目标态的系统量子比特数。
- `target_error`: 允许的数值制备误差。
- `mps`: 可选的预先给定 Matrix Product State 张量。
- `work_wires`: 可选辅助量子比特，用于编码 bond index。
- `mps_max_bond_dim`: 从态向量转成 MPS 时可选的最大 bond dimension。

> **总结**：MPS 态制备算法利用 Matrix Product State 表示来合成量子线路。算法将每个 MPS 张量通过 QR completion 嵌入为局部酉矩阵，并用辅助 work qubits 在相邻 site 之间传递 bond index 信息。

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
   - 使用外部传入的 MPS，或从态向量分解得到 MPS 张量。
2. **MPS 校验**：
   - 检查张量形状和相邻 bond dimension。
   - 确保 work qubits 足够编码最大 bond dimension。
3. **正则化与局部酉构造**：
   - 可选地将 MPS 转成右正则形式。
   - 把每个张量嵌入为等距映射。
   - 用 QR 分解将等距映射补全为完整酉矩阵。
4. **线路构造**：
   - 在当前系统比特和共享 work register 上依次施加 site unitaries。
   - 从 work-zero 子空间提取系统态。
5. **结果输出**：
   - 输出线路、完整演化矩阵、提取后的系统酉矩阵和制备误差。

---

## 核心思想

一个 $n$ 量子比特态可以写成
$$
\psi_{s_0s_1\cdots s_{n-1}}
=
\sum_{\alpha_0,\ldots,\alpha_{n-2}}
A^{(0)}_{s_0,\alpha_0}
A^{(1)}_{\alpha_0,s_1,\alpha_1}
\cdots
A^{(n-1)}_{\alpha_{n-2},s_{n-1}}.
$$
算法不直接从全部 $2^n$ 个振幅合成线路，而是把每个局部张量 $A^{(j)}$ 转化为局部酉门。work register 用于存储中间 bond index $\alpha_j$。

---

## 数学原理

### Bond Dimension 与 Work Qubits

如果最大 bond dimension 为 $\chi_{\max}$，work register 需要满足
$$
2^{n_{\text{work}}}\ge \chi_{\max}.
$$
因此至少需要 $\lceil\log_2\chi_{\max}\rceil$ 个 work qubits。

### 右正则等距映射

对右正则 MPS 张量，有
$$
\sum_{s,r}A_{\ell,s,r}A^*_{\ell',s,r}
=\delta_{\ell,\ell'}.
$$
这说明固定左 bond index 后得到的向量是正交归一列：
$$
|v_\ell\rangle=\sum_{s,r}A_{\ell,s,r}|s\rangle|r\rangle.
$$

### QR Completion

这些正交列构成一个等距映射。QR completion 将该等距映射补全为作用在一个系统比特和 work register 上的完整酉矩阵：
$$
U_j\in\mathbb{C}^{2^{1+n_{\text{work}}}\times 2^{1+n_{\text{work}}}}.
$$

---

## 算法步骤

1. 归一化目标态并确定系统量子比特数。
2. 如果未提供 MPS，则将态向量转换为 MPS 张量。
3. 校验张量形状和 bond dimension。
4. 计算所需 work qubits 数量。
5. 可选地将 MPS 转成右正则形式。
6. 通过 QR completion 将每个张量转成局部酉矩阵。
7. 按 site 顺序施加局部酉矩阵。
8. 从 work-zero 子空间提取制备出的系统态。
9. 忽略全局相位后计算制备误差。

---

## 量子优势

| 任务 | 通用态制备 | MPS 态制备 |
|------|------------|------------|
| 低纠缠态 | 通常需要指数级门数 | 可利用小 bond dimension |
| 张量网络态 | 展平成 $2^n$ 个振幅 | 直接使用局部张量结构 |

该方法最适合具有紧凑 MPS 结构的目标态。对于高度纠缠的任意态，bond dimension 仍可能指数增长。

---

## 复杂度分析

- **系统量子比特数**：$n$。
- **辅助量子比特数**：$\lceil\log_2\chi_{\max}\rceil$。
- **局部酉矩阵大小**：每个 site 为 $2^{1+n_{\text{work}}}\times 2^{1+n_{\text{work}}}$。
- **最好情况**：bond dimension 较小时较高效。
- **最坏情况**：若 $\chi_{\max}$ 随系统规模指数增长，整体复杂度也会指数增长。

---

## 应用与影响

- 低纠缠量子态制备。
- 将张量网络态加载为量子线路。
- 与通用任意态制备方法做比较。
- 研究有限 bond dimension 带来的截断误差。
- 为量子模拟和量子机器学习构建结构化态制备模块。
