# 二维横场 Ising 动力学算法详解

## 参数设置

- `rows`：二维开放边界方格晶格的行数，默认值为 `6`。
- `cols`：二维开放边界方格晶格的列数，默认值为 `6`。`rows=1` 且 `cols=1` 时没有最近邻边，因此不支持 `1×1` 晶格。
- `coupling_J`：最近邻 Ising 耦合强度 $J$，默认值为 `1.0`。
- `field_h`：横场强度 $h$，默认值为 `3.0`。
- `time_step`：单个 Trotter 时间步长度 $\Delta t$，默认值为 `0.025`。
- `trotter_steps`：时间演化步数，默认值为 `8`；设为 `0` 时只计算初态观测量。
- `trotter_order`：Trotter–Suzuki 分解阶数，支持 `1`、`2` 和 `4`，默认值为 `2`。
- `max_bond`：TensorNet 后端允许的最大 bond dimension，默认值为 `32`。
- `cutoff`：TensorNet 奇异值截断阈值，默认值为 `1e-12`。
- `routing`：TensorNet 路由策略，默认值为 `auto`。
- `seed`：执行和采样使用的随机种子，默认值为 `7`。
- `sample_shots`：终态采样次数，默认值为 `0`，表示不执行采样。
- `local_configuration_mode`：局域磁构型输出模式，支持 `none`、`final`、`all` 和 `gif`，默认值为 `gif`。

> **摘要**：该算法模拟开放边界二维横场 Ising 模型的实时动力学。实现按晶格最近邻关系构造局域 $ZZ$ 相互作用与横场 $X$ 演化，使用一阶、二阶或四阶 Trotter–Suzuki 公式生成单步量子线路，并通过 UnitaryLab TensorNet 后端逐步续算。默认配置为 6×6 晶格、二阶分解、8 个时间步，并将每个时间步的局域磁构型合成为 GIF。

---

## 目录

- [运行方式](#运行方式)
- [执行流程](#执行流程)
- [核心思想](#核心思想)
- [数学原理](#数学原理)
- [算法步骤](#算法步骤)
- [输出结果](#输出结果)
- [量子优势](#量子优势)
- [复杂度分析](#复杂度分析)
- [应用与意义](#应用与意义)
- [结果解释边界](#结果解释边界)

---

## 运行方式

在仓库根目录运行默认 6×6、GIF 输出配置：

```bash
PYTHONPATH=. python new/ising/algorithm.py
```

通过 Python 接口调用：

```python
from new.ising.algorithm import IsingAlgorithm

algorithm = IsingAlgorithm(text_mode="plain")
result = algorithm.run(
    rows=6,
    cols=6,
    coupling_J=1.0,
    field_h=3.0,
    time_step=0.025,
    trotter_steps=8,
    trotter_order=2,
    max_bond=32,
    cutoff=1e-12,
    routing="auto",
    seed=7,
    sample_shots=0,
    local_configuration_mode="gif",
)

print(result["status"])
print(result["final_observables"])
```

如需快速检查接口，可以显式使用较小晶格：

```python
result = algorithm.run(
    rows=2,
    cols=2,
    trotter_steps=2,
    local_configuration_mode="none",
)
```

默认输出目录为：

```text
results/new/ising/
```

也可以在构造算法对象时通过 `algo_dir` 指定其他目录：

```python
algorithm = IsingAlgorithm(algo_dir="/path/to/results")
```

---

## 执行流程

1. **输入校验**：检查晶格尺寸、物理参数、Trotter 阶数、TensorNet 参数和局域磁构型输出模式。
2. **晶格映射**：按行优先顺序把二维格点映射为量子比特，并列出开放边界下的水平和竖直最近邻边。
3. **线路构造**：将边分成四组互不冲突的匹配，构造横场 $X$ 演化和最近邻 $ZZ$ 演化，再组合为指定阶数的单步 Trotter 线路。
4. **TensorNet 续算**：从默认初态 $|0\rangle^{\otimes N}$ 开始执行空线路，每一步把上一结果的 `backend_state` 作为下一步的 `initial_state`。
5. **观测量计算**：在初态和每个演化步后计算纵向磁化、横向磁化、平均最近邻关联、畴壁密度和单位格点能量。
6. **局域磁构型处理**：根据 `local_configuration_mode` 决定是否计算每个格点的 $\langle X_i\rangle$ 和 $\langle Z_i\rangle$，以及是否生成终态图片或时间演化 GIF。
7. **结果导出**：保存单步线路图、全局观测量曲线、文本摘要，并返回完整的结构化结果。

---

## 核心思想

二维横场 Ising 模型包含两部分不对易的 Hamiltonian：最近邻自旋耦合 $H_{ZZ}$ 和横场项 $H_X$。算法不构造 $2^N\times2^N$ 的稠密 Hamiltonian 或态矢量，而是直接将两部分演化分解成局域量子门。

最近邻 $ZZ$ 项通过 `CNOT-RZ-CNOT` 实现，横场项通过每个量子比特上的 `RX` 门实现。二维晶格边被划分为横向偶边、横向奇边、纵向偶边和纵向奇边四组；同一组中的两比特门没有公共量子比特，可以位于同一线路层。

每完成一个 Trotter 时间步，算法复用 TensorNet 后端状态继续演化，并通过公开的 `result.expectation()` 接口计算物理观测量，不访问或手工收缩后端 MPS 张量。

---

## 数学原理

开放边界二维横场 Ising Hamiltonian 为

$$
H=-J\sum_{\langle i,j\rangle}Z_iZ_j-h\sum_iX_i
=H_{ZZ}+H_X.
$$

其中每个晶格格点对应一个量子比特，$\langle i,j\rangle$ 表示水平或竖直方向的最近邻格点对。

一阶 Lie–Trotter 公式为

$$
S_1(\Delta t)
=e^{-iH_{ZZ}\Delta t}e^{-iH_X\Delta t}.
$$

二阶 Strang 公式为

$$
S_2(\Delta t)
=e^{-iH_X\Delta t/2}
 e^{-iH_{ZZ}\Delta t}
 e^{-iH_X\Delta t/2}.
$$

四阶 Suzuki–Yoshida 公式为

$$
S_4(\Delta t)
=S_2(p\Delta t)^2
 S_2((1-4p)\Delta t)
 S_2(p\Delta t)^2,
$$

其中

$$
p=\frac{1}{4-4^{1/3}}.
$$

四阶公式中的 $1-4p$ 为负数，对应一个负时间演化块，这是对称高阶组合的正常组成部分。

算法计算的主要观测量为

$$
M_z=\frac{1}{N}\sum_i\langle Z_i\rangle,
\qquad
M_x=\frac{1}{N}\sum_i\langle X_i\rangle,
$$

$$
\overline{ZZ}
=\frac{1}{N_e}\sum_{\langle i,j\rangle}\langle Z_iZ_j\rangle,
$$

$$
D=\frac{1-\overline{ZZ}}{2},
$$

以及单位格点能量

$$
\frac{E}{N}
=\frac{-JN_e\overline{ZZ}-hNM_x}{N}.
$$

---

## 算法步骤

1. 创建 `IsingModel`，确定量子比特数 $N=\text{rows}\times\text{cols}$。
2. 枚举开放边界晶格的最近邻边，并将边分成四个互不冲突的门组。
3. 根据 `trotter_order` 构造一个一阶、二阶或四阶 Trotter 时间步线路。
4. 在默认初态 $|0\rangle^{\otimes N}$ 上创建 TensorNet 后端状态。
5. 在每个时间点计算全局观测量，并根据输出模式决定是否计算局域磁构型。
6. 使用上一时间步的 `backend_state` 执行下一时间步线路，直至完成 `trotter_steps`。
7. 可选地对终态执行 `sample_shots` 次采样。
8. 保存线路图、观测量曲线、局域构型图片或 GIF，并返回轨迹数据。

---

## 输出结果

统一返回字典包含：

| 字段 | 含义 |
| --- | --- |
| `status` | 执行状态，成功时为 `ok` |
| `circuit_path` | 单个 Trotter 时间步线路的 SVG 路径 |
| `plot` | 观测量图、磁构型图/GIF 和文本摘要的文件信息 |
| `circuit` | 单个 Trotter 时间步的 `Circuit` 对象 |
| `records` | 从第 0 步到终态的全局观测量轨迹 |
| `final_observables` | 最后一个时间点的观测量 |
| `local_configuration` | `final`、`all` 或 `gif` 模式下的终态 `z_map/x_map` |
| `samples` | `sample_shots > 0` 时的终态采样结果 |
| `wall_seconds` | 单条演化轨迹的实际执行时间 |
| `step_circuit_summary` | 单步线路的 UnitaryLab 分析摘要 |

`local_configuration_mode` 的行为如下：

| 模式 | 行为 |
| --- | --- |
| `none` | 不计算局域 $\langle X_i\rangle/\langle Z_i\rangle$ |
| `final` | 只计算终态局域构型，并生成 `magnetic_configuration.png` |
| `all` | 每个 `records` 条目都包含对应时间步的 `x_map/z_map` |
| `gif` | 计算每一步局域构型，生成 `magnetic_configuration.gif`，并返回终态构型 |

默认生成的文件包括：

```text
ising_trotter_step.svg
ising_observables.svg
magnetic_configuration.gif
2d_transverse-field_ising_dynamics_algorithm_result.txt
```

---

## 量子优势

| 任务 | 稠密经典模拟 | 当前局域线路与 TensorNet 方法 |
| --- | --- | --- |
| 状态表示 | 需要存储 $2^N$ 个复振幅 | 以截断 bond dimension 的张量网络表示状态 |
| 时间演化 | 对大规模 Hamiltonian 求矩阵指数或更新稠密态矢量 | 将演化分解为局域量子门并逐步执行 |
| 观测量 | 通常需要对完整态矢量进行运算 | 通过 TensorNet 结果对象直接计算 Pauli 和期望值 |

这里的“优势”是避免显式物化 36 或 121 比特的稠密态矢量，并不意味着计算成本会随系统规模保持多项式增长。强纠缠动力学可能要求更大的 bond dimension。

---

## 复杂度分析

对于 `rows × cols` 开放边界晶格，量子比特数为

$$
N=\text{rows}\times\text{cols},
$$

最近邻边数为

$$
N_e=\text{rows}(\text{cols}-1)+(\text{rows}-1)\text{cols}.
$$

一阶和二阶时间步的门数与 $N+N_e$ 同阶；四阶公式由五个二阶块组成，因此单步门数显著增加。总线路执行次数随 `trotter_steps` 线性增长。

TensorNet 的实际时间和内存消耗还取决于：

- `max_bond`；
- `cutoff`；
- `routing`；
- 演化过程中产生的纠缠；
- Trotter 阶数和时间步数。

`all` 和 `gif` 模式在每个时间点额外计算每个格点的 $X/Z$ 局域期望值，因此会比 `none` 和 `final` 更慢。参考复现实验中，6×6、二阶、8 步、$\chi=32$ 的基础轨迹约需 6–7 分钟；默认 GIF 模式还包含逐时间步局域观测和动画生成，实际耗时会更长，并随硬件和 UnitaryLab 版本变化。

---

## 应用与意义

- 研究量子磁性和横场驱动下的自旋动力学。
- 观察纵向/横向磁化与畴壁密度随时间的变化。
- 比较不同 Trotter 阶数带来的离散误差。
- 研究有限 TensorNet bond dimension 带来的截断效应。
- 生成二维晶格局域磁构型的静态图或动态 GIF。
- 作为大规模局域 Hamiltonian 模拟和张量网络执行的示例。

---

## 结果解释边界

- 时间无关 Hamiltonian 的精确演化应保持能量不变；结果中的能量漂移可用于诊断 Trotter 误差和有限 bond dimension 截断误差。
- 更高 Trotter 阶数或更大 `max_bond` 通常能改善某类误差，但不能单独证明结果已经收敛。
- 36 比特及更大模型没有通过稠密态矢量进行精确对照。
- TensorNet 的近似质量取决于演化产生的纠缠和所选截断参数。
- 当前结果给出磁化强度 $M_z(t)$ 和 $M_x(t)$；动态磁化率需要额外执行 $h\pm\delta h$ 的响应实验，不能由单一外场轨迹直接替代。
