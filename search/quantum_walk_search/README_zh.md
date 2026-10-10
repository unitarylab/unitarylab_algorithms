# 连续时间量子游走搜索算法详解

## 参数设置

- `num_vertices`：内置图的顶点数，默认 8。
- `marked`：逗号分隔的目标顶点，默认 `2,5`。
- `graph_type`：`complete`、`cycle`、`path` 或 `star`。
- `graph_json`：可选自定义邻接矩阵或边列表 JSON，填写后覆盖内置图。
- `gamma`：游走耦合强度；留空时根据图谱自动选择。
- `evolution_time`：演化时间；留空时执行小规模精确谱扫描。
- `method`、`target_error`、`simulation_steps`：哈密顿量模拟设置。
- `shots`、`seed`：采样次数和随机种子。

> **总结**：算法以图邻接矩阵和标记顶点构造搜索哈密顿量，从图上的均匀叠加态连续演化，并通过测量获得标记顶点。

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

1. 构造或解析无向加权图并验证标记顶点。
2. 选择耦合系数和演化时间。
3. 构造搜索哈密顿量并调用 UnitaryLab 哈密顿量模拟。
4. 从图顶点均匀叠加态执行演化。
5. 采样末态，统计标记顶点总概率并与精确谱演化比较。
6. 导出电路图和标准结果。

---

## 核心思想

连续时间量子游走把图结构编码到哈密顿量中。标记项改变目标顶点能量，相干演化使振幅在图上传播并向标记子空间集中。算法支持多个标记顶点以及完全图、环、路径、星图和自定义图。

---

## 数学原理

对邻接矩阵 $A$、标记集合 $M$ 和耦合强度 $\gamma>0$，构造

$$H=-\gamma A-\sum_{w\in M}|w\rangle\langle w|.$$

初态为有效顶点的均匀叠加态

$$|s_G\rangle=\frac{1}{\sqrt{N}}\sum_{v=0}^{N-1}|v\rangle,$$

演化后标记成功概率为

$$P_M(t)=\sum_{w\in M}|\langle w|e^{-iHt}|s_G\rangle|^2.$$

非二次幂顶点数会补零到最近的 $2^q$ 维度，并单独报告落入填充空间的概率。

---

## 算法步骤

1. 验证邻接矩阵对称、有限、非负且无自环。
2. 计算默认 $\gamma$ 或采用用户值。
3. 自动扫描或采用指定时间。
4. 使用选定方法近似 $e^{-iHt}$。
5. 执行状态向量模拟并采样。
6. 输出精确概率、模拟误差、计数和电路资源。

---

## 量子优势

在完全图等具有适当谱结构的图上，连续时间量子游走可在 $O(\sqrt{N/M})$ 量级时间内放大 $M$ 个标记顶点。优势依赖图结构和参数选择；本实现运行在经典模拟器上，不代表经典硬件上的实际加速。

---

## 复杂度分析

需要 $q=\lceil\log_2N\rceil$ 个量子比特。经典稠密哈密顿量和精确谱扫描分别涉及 $O(4^q)$ 存储与立方量级对角化；量子线路复杂度取决于模拟方法、步数和目标误差。

---

## 应用与影响

适用于图搜索、网络分析、空间搜索、哈密顿量模拟教学以及不同图谱结构对量子搜索行为的研究。

## 接口与运行限制

`QuantumWalkSearchAlgorithm(text_mode="plain", algo_dir=None).run()` 默认参数：
`num_vertices=8, marked="2,5", graph_type="complete", graph_json="",
gamma=None, evolution_time=None, method="trotter", target_error=1e-4,
simulation_steps=8, shots=128, seed=7, backend="numpy", device="cpu",
dtype=np.complex128`。标准 `test()` 和 Web 输入使用字符串
`"complex128"`，调用 run 前转为 NumPy 类型。

graph_json 接受内联邻接矩阵数组、含 adjacency 的对象，或含 num_vertices 和
edges 的对象，不接受文件路径；边格式为 [u,v] 或 [u,v,weight]，重复边累加。
自定义图覆盖内置图，标记仍来自独立 marked 参数，run 不读取 JSON 中的 marked。
研究辅助函数 load_graph_problem(path) 才读取文件中的标记。
图必须至少有2个顶点，有限、按原容差近似对称、非负且无自环；标记须非空、不重复、在范围内。
标准 run 最多32顶点；只有 solve_graph_search(allow_large=True) 能放开该限制。

backend/device/dtype 同时透传至 hamiltonian_simulation 构造和最终 execute；
最终执行默认仍为 numpy/cpu/complex128。原实现的模拟器构造隐式使用 torch，
现在统一使用传入配置，这是必要接口差异，数值影响尚待对照。谱扫描和经典参照的
NumPy 精度保持原实现。后端支持依赖已安装 UnitaryLab；numpy 仅支持 cpu。
没有静默回退或自动降精度。seed 只控制顶点采样，不为下层模拟器构造设种子。

返回包含 status、circuit_path、plot、circuit、QuantumWalkResult.to_dict() 的业务字段，
以及 Elapsed time (s)。status=ok 仅代表运行完成，不代表概率或误差达标。
probabilities 长度为有效顶点数N，padded_probability 单列D-N个填充态；
counts 使用宽度log2(D)的常规二进制顶点编号，按频次降序，频次相同时保持顶点升序。
标准返回不包含原始量子态；solve_graph_search 的对象仍包含 final_state、simulation，
run_search 保留原三元组返回。

默认目录为 <cwd>/results/search/quantum_walk_search，标准运行导出带测量的概览SVG及TXT。
构造参数 algo_dir 可以覆盖目录。研究函数的JSON/PNG导出仍可选，
标准 run 没有请求这些导出，因此 artifacts 通常为空。保留的研究 argparse main()
不会由标准 __main__ 自动调用，且未开放三个执行参数。

依用户确认保留原限制：Taylor等带辅助寄存器的方法可能返回比D维初态更大的线路，
直接 execute 可能维度不匹配；本次未增加辅助初始化、后选择或概率重新解释。
target_error 不保证实际误差达标，simulation_steps 只向 trotter/qdrift 透传，
实际步骤可能被底层调整。显式零时间保留原模拟器行为，部分实现可能遇到零步数边界。

选定版本仅将采样计数改为整数直方图；随机调用、浮点表达式及排序规则保持不变。
静态检查完成，运行验证待完成；未运行算法、CLI、Web、测试或性能测量，不宣称实测提升。
