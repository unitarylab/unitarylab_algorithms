# 分子 DMRG 算法

该示例调用 `unitarylab.library.chemistry.MolecularDMRGWorkflow`，依次完成：

1. PySCF/OpenFermion 电子结构与活性空间 Hamiltonian；
2. physics-tenpy DMRG 基态求解；
3. SciPy L-BFGS-B 经典变分解纠缠；
4. UnitaryLab 线路求值、QWC 分组采样和测量 QASM 导出。

算法示例不提供阶段 `target`，每次执行完整流程。默认输入是内置
`H2.xyz` 和 `sto-3g` 基组。内置分子下拉选项包括 H2、LiH、H2O、
CH4、CO、CO2、C6H6、HF、N2、NH3 和 O2。传入 `LiH` 等名称时从
`molecules/` 查找，传入 `.xyz` 文件名或路径时直接读取相应文件。

原实现中的四个 demo 对应以下算法参数：

| 原 demo | `xyz_file` | `basis` | `active_occupied_orbitals` | `active_virtual_orbitals` |
| --- | --- | --- | ---: | ---: |
| `h2` | `H2` | `sto-3g` | 1 | 1 |
| `lih` | `LiH` | `sto-3g` | 2 | 2 |
| `h2o-small` | `H2O` | `sto-3g` | 2 | 2 |
| `h2o` | `H2O` | `6-31g` | 3 | 4 |

其中 `h2o-small` 只是较小的 H2O 参数预设，并不是另一份 XYZ 几何。

```python
from unitarylab_algorithms import MolecularDMRGAlgorithm

result = MolecularDMRGAlgorithm().run(
    xyz_file="H2",
    basis="sto-3g",
    active_occupied_orbitals=1,
    active_virtual_orbitals=1,
    backend="torch",
    device="cpu",
    dtype="complex128",
)
```

结果目录包含 BaseAlgorithm 结果文本、线路 SVG，以及 `output/` 下的
PySCF 数据和每个 QWC 测量组的 OpenQASM 2.0 文件。

本实现保留活性空间 FCI 参考值，但不提供旧版的 MP2、CISD、CCSD、
完整 post-SCF FCI 开关或 Julia DMRG 输出文件。
