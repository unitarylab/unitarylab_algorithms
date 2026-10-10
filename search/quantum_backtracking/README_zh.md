# 量子回溯搜索算法详解

## 参数设置

- `problem_json`：问题 JSON；留空使用内置深度 2 的前缀约束示例。支持 `binary_cnf` 和 `prefix_constraints`。
- `phase_bits`：QPE 相位寄存器比特数，默认 3。
- `shots`：每次子树检测的相位采样次数，默认 128。
- `seed`：采样随机种子，默认 7。
- `threshold`：零相位频率判定阈值，默认 $3/8$。
- `backend/device/dtype`：每次谓词和 QPE 执行均透传，默认 `numpy/cpu/complex128`，保持原算法配置；CLI/Web 的 dtype 为字符串，`test()` 转换为 NumPy dtype。其他后端/精度未运行验证。

## 实际接口与限制

```python
from unitarylab_algorithms import QuantumBacktrackingAlgorithm

algorithm = QuantumBacktrackingAlgorithm(algo_dir="results/search/quantum_backtracking")
result = algorithm.run()  # 内置深度2示例；此示例本次未执行
print(result["exists"], result["solution_path"])
```

`status='ok'` 表示正常完成，是否检测到解读取 `exists`；有限相位精度和采样可能漏检，`exists=False` 不是无解证明。输入可为 JSON 字符串或 dict，不修改调用方输入。CNF 子句用从1开始的有符号变量序号，路径按变量顺序编码；相位寄存器在低位。接受路径可提前终止，因此赋值可能仅含部分变量。

返回保留 `problem/exists/solution_path/solution_assignment/evidence/resource_report/artifacts`，加 `Elapsed time (s)` 和基类 `status/circuit_path/plot/circuit`。标准 run 保存 SVG 和结果 TXT，`artifacts` 保持空字典；不会调用研究入口的 PNG/直方图/QASM 导出。原 `main()`/Solver.solve(output_dir, full_artifacts=...) 仍保留，属于不同入口；`main()` 未自动调用且其默认 example_problem.json 原目录未提供，使用时须显式给问题文件。

深度 d、拒绝工作位 r、相位位 p：walk 为 `2d+3+r` 位，QPE 为 `2d+3+r+p` 位，child oracle 为 `3d+7+r` 位。CNF 的 r 为子句数，前缀问题的 r 为拒绝前缀数；资源报告也构造 child oracle。经典状态向量模拟成本呈指数增长。本次只做静态检查，无性能结论。

> **总结**：算法将经典回溯树分成奇偶层反射，构造离散量子游走 $W=R_BR_A$，再用 QPE 判断子树是否包含解，并逐层恢复一条可接受路径。

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

1. 解析 CNF 或前缀约束，构造可逆接受/拒绝 oracle。
2. 以路径比特和 one-hot 深度寄存器编码回溯树节点。
3. 构造偶数层反射 $R_A$、奇数层反射 $R_B$ 和游走 $W$。
4. 对当前子树根执行 controlled-$W$ QPE。
5. 根据零相位频率与阈值判断子树是否含解。
6. 依次检测左右子节点，直到找到接受路径或未检测到解。
7. 导出 QPE 代表线路、资源报告和结果文本。

---

## 核心思想

经典回溯逐节点扩展搜索树。量子回溯把局部父子星图上的扩散写成反射，并把交替层反射组合成量子游走。若某棵子树含有接受节点，子树根态在游走算子的零相位子空间上具有可检测权重；QPE 因而可作为“这棵子树是否含解”的量子检测器。

---

## 数学原理

对偶数层和奇数层局部扩散算子分别构造反射：

$$R_A=\bigoplus_{x\in A}D_x,\qquad R_B=\bigoplus_{x\in B}D_x,$$

并定义离散游走：

$$W=R_BR_A.$$

若谱分解为

$$W=\sum_j e^{i\theta_j}|u_j\rangle\langle u_j|,$$

则从子树根态执行 QPE 后，测得全零相位寄存器的概率近似其在 $\theta_j=0$ 谱子空间上的投影权重。实现用有限 shots 得到零相位频率，并与 `threshold` 比较。

---

## 算法步骤

1. 验证问题约束并创建寄存器布局。
2. 对每个深度构造接受和拒绝标志。
3. 以可逆 Givens 旋转和受控相位实现局部反射。
4. 组合 $R_A$ 与 $R_B$。
5. 对根子树进行 QPE 检测。
6. 若存在解，递归选择检测为真的子节点。
7. 使用接受/拒绝量子 oracle 查询确认路径，并生成变量赋值。

---

## 量子优势

Montanaro 量子回溯框架在合适条件下可把大小为 $T$、深度为 $n$ 的回溯树搜索从经典 $O(T)$ 节点级工作改善到近似 $\widetilde O(\sqrt{Tn})$ 的量子检测规模。实际优势依赖 oracle 成本、谱隙、精度和错误概率。

---

## 复杂度分析

相位精度为 $2^{-p}$ 时，QPE 需要约 $2^p-1$ 次 controlled-$W$ 应用。路径深度、约束工作比特和 `phase_bits` 都会迅速增加经典状态向量模拟成本，因此默认示例刻意保持很小。

---

## 应用与影响

可用于 SAT/CSP、小规模组合搜索、调度和路径约束问题，也是研究量子游走、相位估计与经典回溯结合方式的门级示例。
