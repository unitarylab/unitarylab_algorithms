# 变分量子线性求解器 (VQLS)

变分量子线性求解器 (Variational Quantum Linear Solver, VQLS) 是一种混合量子-经典算法，用于在近期量子设备 (NISQ) 上求解线性方程组 Ax = b。

---

## 目录

- [算法背景](#算法背景)
- [算法原理](#算法原理)
- [数学基础](#数学基础)
- [算法步骤](#算法步骤)
- [使用示例](#使用示例)
- [应用场景](#应用场景)
- [参考文献](#参考文献)

---

## 算法背景

### 问题描述

线性方程组求解是科学计算中的基础问题，广泛应用于物理模拟、机器学习、优化等领域。给定矩阵 A 和向量 b，求解满足 Ax = b 的向量 x。

在量子计算中，HHL 算法提供了指数级加速，但需要量子相位估计和受控幺正门，对量子硬件要求较高。VQLS 算法通过变分方法，在浅层量子电路上实现线性方程组求解，更适合 NISQ 设备。

### 算法提出

- **提出时间**: 2019年
- **论文**: *Variational Quantum Linear Solver* (arXiv:1909.05820)
- **作者**: Carlos Bravo-Prieto 等
- **应用领域**: 量子机器学习、量子化学、组合优化

---

## 算法原理

### 核心思想

VQLS 将线性方程组求解问题转化为变分优化问题：

1. **变分态准备**: 使用参数化量子电路 V(θ) 准备变分态 |x(θ)⟩
2. **成本函数构造**: 定义成本函数 C(θ)，当 A|x⟩ ∝ |b⟩ 时成本函数最小
3. **经典优化**: 使用经典优化器调整参数 θ，最小化成本函数
4. **解的提取**: 优化后的变分态即为方程的近似解

### 量子优势

与经典方法相比：
- **浅层电路**: 不需要量子相位估计，电路深度可控
- **灵活性**: 可以处理非 Hermitian 矩阵
- **适应性**: 适合 NISQ 设备，噪声容忍度较高

与 HHL 算法相比：
- **硬件要求低**: 不需要精确的相位估计
- **电路深度小**: 更适合当前量子设备
- **权衡**: 需要多次电路执行和经典优化

---

## 数学基础

### 问题形式

考虑线性方程组:
```
Ax = b
```

其中 A 可以表示为线性组合:
```
A = Σᵢ cᵢ Aᵢ
```

这里 Aᵢ 是酉算子或可实现为酉算子的组合。

### 变分态

使用参数化量子电路准备变分态:
```
|x(θ)⟩ = V(θ)|0⟩
```

其中 V(θ) 是由参数 θ 控制的幺正变换。

### 成本函数

#### 全局成本函数

基本形式:
```
C_G(θ) = 1 - |⟨b|A|x(θ)⟩|² / (⟨x(θ)|A†A|x(θ)⟩ ⟨b|b⟩)
```

当 A|x⟩ = λ|b⟩ 时，C_G(θ) = 0。

#### 局部成本函数

为减少电路复杂度，使用局部成本函数:
```
C_L(θ) = Σⱼ (1 - μⱼ(θ))
```

其中:
```
μⱼ(θ) = |⟨ψ|Zⱼ|ψ⟩| / ⟨ψ|ψ⟩
```

这里 |ψ⟩ = A|x(θ)⟩，Zⱼ 是作用在第 j 个量子比特上的 Pauli-Z 算子。

### Hadamard 测试

使用 Hadamard 测试电路测量局部期望值:

```
      ┌───┐     ┌─────────┐     ┌───┐
anc: ─┤ H ├─────┤ Control ├─────┤ H ├─  测量 Z
      └───┘     └─────────┘     └───┘
                     │
sys: ────────────────┴──────────────────
```

通过测量辅助比特上的 Pauli-Z 期望值，可以提取所需的重叠项。

---

## 算法步骤

### 步骤 1: 初始化

- 确定系统量子比特数 n
- 准备矩阵 A = c₀A₀ + c₁A₁ + c₂A₂
- 构建 |b⟩ 态的准备电路 Uᵦ

在本实现中：
- A₀ = I (单位矩阵)
- A₁ = X ⊗ Z (n_qubits=2 时)
- A₂ = X ⊗ I (n_qubits=2 时)
- |b⟩ = Uᵦ|0⟩，其中 Uᵦ 由 Hadamard 门组成

### 步骤 2: 构建变分电路

参数化量子电路 V(θ)：

```
     ┌───┐┌────────┐
q_0: ┤ H ├┤ Ry(θ₀) ├
     ├───┤├────────┤
q_1: ┤ H ├┤ Ry(θ₁) ├
     └───┘└────────┘
```

这是一个简单的 ansatz，包含：
1. Hadamard 层：创建均匀叠加态
2. 旋转层：可变参数 Ry 门

### 步骤 3: 构建局部 Hadamard 测试电路

对于每对 (l, l')，构建测试电路：

```
1. 辅助比特 H 门
2. (可选) S† 门用于虚部测量
3. 应用 V(θ)
4. 受控应用 Aₗ
5. 应用 Uᵦ†
6. (可选) 受控 Zⱼ
7. 应用 Uᵦ
8. 受控应用 Aₗ'†
9. 辅助比特 H 门
10. 测量辅助比特的 Z 期望值
```

### 步骤 4: 计算成本函数

```python
def cost(θ):
    μ_sum = 0
    for l in range(len(c)):
        for l' in range(len(c)):
            for j in range(n_qubits):
                μⱼ = measure_hadamard_test(θ, l, l', j)
                μ_sum += c[l] * c*[l'] * μⱼ
    
    ψ_norm = compute_psi_norm(θ)
    return 0.5 - 0.5 * |μ_sum| / (n_qubits * ψ_norm)
```

### 步骤 5: 经典优化

使用 COBYLA 或其他无梯度优化算法最小化成本函数：

```
θ_opt = argmin_θ C_L(θ)
```

### 步骤 6: 解的提取

优化后的参数 θ_opt 对应的变分态即为近似解：

```
|x⟩ ≈ V(θ_opt)|0⟩
```

---

## 使用示例

### 基础用法

```python
from unitarylab.algorithms import VQLSAlgorithm
import numpy as np

# 创建算法实例
algo = VQLSAlgorithm(seed=42)

# 设置输出模式（可选）
algo.set_output_mode("plain")

# 运行算法
result = algo.run(
    n_qubits=2,           # 系统量子比特数
    max_iterations=100,   # 最大优化迭代次数
    tolerance=1e-6        # 收敛容差
)

# 查看结果
print(result['plot'])
print(f"保真度: {result['fidelity']:.6f}")
print(f"相对误差: {result['relative_error']:.6e}")
print(f"最优参数: {result['optimal_params']}")
```

### 自定义矩阵系数

```python
# 自定义线性组合系数
coefficients = [1.0, 0.3, 0.3]  # A = 1.0*I + 0.3*A₁ + 0.3*A₂

result = algo.run(
    n_qubits=2,
    coefficients=coefficients,
    max_iterations=150
)
```

### 输出结果解释

```python
# 算法返回的结果字典包含：
result = {
    "status": "success",           # 优化状态
    "fidelity": 0.946676,          # 解的保真度
    "relative_error": 3.017e-01,   # 相对误差
    "optimal_params": [...],       # 最优变分参数
    "final_cost": 1.66e-13,        # 最终成本函数值
    "iterations": 59,              # 实际迭代次数
    "circuit_path": "path/to/circuit.svg",  # 电路图路径
    "message": "...",              # 执行备注
    "plot": "..."                  # ASCII 格式报告
}
```

### 完整示例

```python
from unitarylab.algorithms import VQLSAlgorithm

# 创建算法实例
algo = VQLSAlgorithm(seed=42)
algo.set_output_mode("plain")

# 运行算法求解 2 量子比特系统
result = algo.run(
    n_qubits=2,
    coefficients=[1.0, 0.2, 0.2],
    max_iterations=100,
    tolerance=1e-6,
    initial_spread=0.5
)

# 打印详细报告
print(result['plot'])

# 访问关键指标
print(f"\n核心指标:")
print(f"  保真度: {result['fidelity']:.6f}")
print(f"  相对误差: {result['relative_error']:.6e}")
print(f"  迭代次数: {result['iterations']}")

# 查看电路图
print(f"\n电路图已保存: {result['circuit_path']}")
```

---

## 应用场景

### 1. 量子机器学习

- **特征映射**: 求解量子核方法中的线性系统
- **数据分类**: 支持向量机的量子加速
- **参数估计**: 最小二乘问题求解

### 2. 量子化学

- **分子模拟**: 薛定谔方程的离散化求解
- **能量计算**: 哈密顿量本征值问题
- **电子结构**: 配置相互作用方法

### 3. 优化问题

- **线性规划**: 约束优化问题
- **投资组合**: 风险收益平衡
- **资源分配**: 网络流问题

### 4. 偏微分方程

- **数值求解**: 有限元或有限差分离散化后的线性系统
- **边值问题**: 泊松方程、热方程
- **流体力学**: 不可压缩流动模拟

### 局限性

1. **问题规模**: 当前实现适合小到中等规模问题（2-4 量子比特）
2. **电路深度**: 随量子比特数增加，电路复杂度上升
3. **优化难度**: 成本函数可能存在多个局部最优解
4. **精度权衡**: 变分方法给出近似解，精度取决于 ansatz 和优化器
5. **矩阵形式**: 需要将矩阵 A 表示为酉算子的线性组合

---

## 参考文献

1. **原始论文**:
   - Bravo-Prieto, C, et al. (2019). *Variational Quantum Linear Solver*. arXiv:1909.05820.
   - https://arxiv.org/abs/1909.05820

2. **相关工作**:
   - Harrow, A. W, Hassidim, A, & Lloyd, S. (2009). *Quantum algorithm for linear systems of equations*. Physical Review Letters, 103(15), 150502.
   - Cerezo, M, et al. (2021). *Variational quantum algorithms*. Nature Reviews Physics, 3(9), 625-644.

3. **实现参考**:
   - Qiskit Textbook: Variational Quantum Linear Solver
   - PennyLane Demos: VQLS Tutorial

4. **理论基础**:
   - Preskill, J. (2018). *Quantum Computing in the NISQ era and beyond*. Quantum, 2, 79.
   - Bharti, K, et al. (2022). *Noisy intermediate-scale quantum algorithms*. Reviews of Modern Physics, 94(1), 015004.

---

## 技术细节

### 电路资源

- **量子比特数**: n_qubits + 1（系统量子比特 + 1 个辅助比特）
- **电路深度**: O(n_qubits × iterations)
- **门数量**: 与 ansatz 选择和矩阵分解有关

### 性能分析

- **时间复杂度**: O(iterations × measurements)
- **测量次数**: O(n_qubits² × |c|²) 每次迭代
- **收敛速度**: 依赖于问题条件数和 ansatz 表达能力

### 参数选择建议

| 参数 | 建议值 | 说明 |
|------|--------|------|
| n_qubits | 2-4 | 量子比特数，取决于问题规模 |
| max_iterations | 50-200 | 最大迭代次数，复杂问题需要更多 |
| tolerance | 1e-6 | 收敛容差，影响优化精度 |
| initial_spread | 0.3-0.8 | 初始参数范围，影响收敛速度 |
| seed | 任意整数 | 随机种子，保证结果可重复 |

---

**最后更新**: 2026-04-29  
**版本**: 1.0  
**维护者**: unitarylab 算法团队
