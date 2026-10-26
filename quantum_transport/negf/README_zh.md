# NEGF 算法

该模块使用 UnitaryLab SDK 内置 QSVT 求解器，计算连接左右半无限引线的矩形
正方晶格器件。Kwant 提供 Hamiltonian 和引线自能，QSVT 求解引线注入方程，
再由注入响应计算透射率、局域态密度和键电流。

## 参数与调用

| 参数 | 默认值 | 含义 |
| --- | ---: | --- |
| `L` | `4` | 散射区 x 方向格点数，至少为 2 的整数 |
| `W` | `4` | y 方向格点数，也是两侧引线宽度，至少为 2 的整数 |
| `a` | `1.0` | 晶格常数，该物理模型建议使用正值 |
| `t` | `1.0` | 跃迁能标，单位 eV，该物理模型建议使用正值 |
| `inverse_tolerance` | `2e-3` | 倒数多项式相对误差容限，严格位于 0 与 1 之间 |

格点 onsite 为 `4 * t`，最近邻 hopping 为 `-t`。`ENERGY` 保持按横向前两个
子带阈值的中点自动计算：

```text
E_FIRST = 2 * t * (1 - cos(pi / (W + 1)))
E_SECOND = 2 * t * (1 - cos(2 * pi / (W + 1)))
ENERGY = (E_FIRST + E_SECOND) / 2
```

不提供单独的能量参数。`a`、`t` 保持源 Python 行为，上述正值建议不增加新的
参数校验规则。

默认 `4 × 4` 器件位于当前 SDK 的 QASM2 导出尺寸支持范围内。

```python
from unitarylab_algorithms import NEGFAlgorithm

result = NEGFAlgorithm(text_mode="plain").run(
    L=4,
    W=4,
    a=1.0,
    t=1.0,
    inverse_tolerance=2e-3,
)
print(result["transmission"])
print(result["injection_residuals"])
print(result["qasm_paths"])
```

构造函数还接受 `algo_dir`，用于指定结果目录。`test(...)` 入口提供相同的五个
算法参数。

## 计算流程

1. 使用 Kwant 构建正方晶格散射区 Hamiltonian 和左右引线。
2. 取得引线自能 `Sigma_L`、`Sigma_R` 及展宽 `Gamma_L`、`Gamma_R`，将界面块
   嵌入散射区，组装 `A = ENERGY * I - H_C - Sigma_L - Sigma_R`。
3. 从展宽分解得到引线注入向量 `C_L`、`C_R`，求解
   `A @ injection_responses = [C_L, C_R]`。使用基向量 `e0` 构建一次 SDK QSVT
   主体线路，各右端向量复用该主体，不构造散射区的完整逆矩阵。
4. 为每个注入通道构建实际执行的 `Circuit`：将右端向量归一化并补零，用
   `initialize` 在低位系统量子位制备输入，再接入共用 QSVT 主体。调用无外部
   初态参数的 `execute()`，从全零态执行包含输入态制备的整条线路。
5. 读取所有辅助位为 0 的分块，取前 `L * W` 个复幅值，乘以该右端向量原始
   范数及 SDK 返回的缩放因子，恢复注入响应。
6. 将响应拆分为 `X_L`、`X_R`，计算方程残差，再经典计算透射率、局域态密度和
   键电流。

保留的源表达式为：

```text
transmission = ||C_R.conj().T @ X_L||_F**2
ldos = (sum(abs(X_L)**2, axis=1) + sum(abs(X_R)**2, axis=1)) / (2*pi)
current_on_bond(i, j) = 2 * imag(H_C[i, j] * vdot(X_L[i], X_L[j]))
```

`bond_current` 严格采用 `fsyst.graph` 的有向键顺序，电流方向、符号和单位约定
沿用源表达式。它不是以 SI 安培表示的有限偏压电流：本流程没有增加偏压窗口
积分、占据权重或 SI 电流前因子。

## 返回结果与文件

默认结果目录为 `results/quantum_transport/negf/`。

| 返回字段 | 含义 |
| --- | --- |
| `status` | 本次执行是否成功 |
| `circuit_path` | 第一个实际注入线路的 SVG 路径 |
| `plot` | 包含 `format`、`filename` 的生成文件信息 |
| `circuit` | 第一个实际注入线路，包含输入态制备和 QSVT 主体 |
| `circuits` | 按左侧、右侧注入通道顺序排列的全部实际注入线路 |
| `circuit_paths` | 各注入线路的 SVG 路径 |
| `qasm_paths` | 成功导出的注入线路 QASM2 文件路径 |
| `qasm_export_errors` | 未获 SDK 支持的 QASM2 导出记录列表，各项包含线路名 `circuit` 和 SDK 原始异常文字 `reason` |
| `ENERGY` | 自动计算的注入能量 |
| `left_channels`、`right_channels` | 左右引线保留的注入通道数 |
| `transmission` | 根据注入响应计算的透射率 |
| `injection_residuals` | 各注入方程的相对残差 `norm(A @ x - b) / norm(b)` |
| `epsilon` | 经倒数多项式误差校准后传给 SDK 的内部参数 |
| `inverse_polynomial_error` | 校准时测得的倒数多项式最大相对误差 |
| `scaling_factor` | 恢复线性响应时使用的 SDK 缩放因子 |
| `rhs_norms` | 各注入右端向量的原始范数 |
| `system_size` | 散射区矩阵原始维数 `L * W` |
| `ldos` | 按散射区格点顺序排列的局域态密度 |
| `bond_current` | 按有向键顺序排列的电流值 |

生成文件包括：

- `negf_result.txt`：BaseAlgorithm 输入、日志和结果摘要。
- `kwant_square_system.png`：器件和引线结构图。
- `kwant_square_ldos.png`：局域态密度图。
- `kwant_square_current.png`：键电流图。
- `negf_circuit.svg`：第一个实际注入线路。
- `negf_circuit_2.svg` 等：其余通道的实际注入线路。
- `negf_circuit.qasm`、`negf_circuit_2.qasm` 等：仅在对应线路成功导出 QASM2 时生成。

SVG 由 `BaseAlgorithm.save_circuit` 调用 SDK 绘图生成，QASM2 使用
`circuit.to_qasm2(transpile=True)` 导出。当前 SDK 绘图默认最多显示 25 个排版层，
SVG 可能截断较长线路，不能据此判断全部门的数量。

当前 SDK 的 Nagy 酉矩阵分解最多支持 6 个目标量子位。此 QSVT 线路要求补齐
后的系统维数 `N <= 32`，等价于 `L * W <= 32`，才能满足该 QASM2 导出限制。
默认 `4 × 4` 器件有 16 个格点，系统维数为 `N = 16`，对应的分解有 5 个目标
量子位，满足当前尺寸限制。

若 SDK 在 QASM2 导出时抛出 `NotImplementedError`，算法按通道记录
`qasm_export_errors`，例如 `{"circuit": "negf_circuit", "reason": "SDK 原始异常文字"}`，
并在日志和 `negf_result.txt` 中提示未导出及原因。该通道不生成 QASM2 文件，也不
加入 `qasm_paths`；算法继续执行，保留成功状态、数值结果、全部 SVG 和实际
`Circuit`。其他异常仍正常抛出。

QASM2 导出会省略无控制的全局相位，导出态在物理上等价；若将 QASM2 执行结果
用于逐个复幅值恢复线性响应，需要注意这一全局相位。

## 依赖与数值行为

直接依赖为 `numpy`、`scipy`、`matplotlib`、`kwant` 和 `unitarylab`。

Hamiltonian 以稀疏形式组装，SDK 内置 QSVT 路径会将求解矩阵展开为稠密数组并
补齐到 2 的幂，不能描述为全程稀疏计算。

`inverse_tolerance` 校准只在构建 QSVT 主体前执行一次。校准先在局部将矩阵除以
其谱范数，重新计算奇异值、条件数及 SDK 的归一化系数 `alpha`，再使用 SDK
倒数多项式和其实际缩放 `beta` 检查误差。误差检查覆盖 20001 个网格点及全部
实际奇异值，并返回 `epsilon` 与 `inverse_polynomial_error`。

该容限控制倒数多项式近似，不保证最终方程残差。最终残差独立保存在
`injection_residuals` 中，不以同一容限作为失败断言。
