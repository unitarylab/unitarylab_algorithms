# algorithms 目录说明

本目录用于集中维护可独立调用的量子算法实现。目前共整理出 28 个算法，按主题划分为 6 个类别：密码学、基础算法、哈密顿量模拟、线性代数、量子机器学习、Schrodingerization 方程求解。

## 当前算法清单

### 1. cryptology

- `discrete_log`: Discrete Log Algorithm
- `shor`: Shor Algorithm
- `simon`: Simon Algorithm

### 2. fundamental_algorithm

- `hadamard_transform`: Hadamard Transform Algorithm
- `hadamard_test`: Hadamard Test Algorithm
- `amplitude_amplification`: Amplitude Amplification Algorithm
- `amplitude_estimation`: Amplitude Estimation Algorithm
- `grover`: Grover Algorithm
- `qpe`: Quantum Phase Estimation Algorithm

### 3. hamiltonian_simulation

- `trotter`: Trotter Algorithm
- `qdrift`: QDrift Algorithm
- `taylor`: Taylor Algorithm
- `qsp`: Quantum Signal Processing for Hamiltonian Simulation
- `cartan`: Cartan Decomposition Algorithm

### 4. linear_algebra

- `hhl`: HHL Algorithm
- `lcu`: LCU Algorithm
- `qft`: Quantum Fourier Transform Algorithm
- `qsp`: Quantum Signal Processing Algorithm
- `qsvt_qlsa`: QSVT Linear Solver Algorithm
- `vqls`: VQLS Algorithm

### 5. quantum_machine_learning

- `vqe`: Variational Quantum Eigensolver
- `qaoa`: Quantum Approximate Optimization Algorithm
- `qcbm`: Quantum Circuit Born Machine
- `vqc`: Variational Quantum Classifier
- `cvqnn`: Continuous-Variable Quantum Neural Network

### 6. schrodingerization

- `equation_heat`: Heat Equation Algorithm
- `equation_heat2d`: Heat2D Equation Algorithm
- `equation_advection`: Advection Equation Algorithm

## 目录规范

常规算法建议保持如下结构：

```text
unitarylab_algorithms/
  category_name/
    algorithm_name/
      __init__.py
      algorithm.py
      parameters.json
      README_en.md
      README_zh.md
```

其中各文件职责如下：

- `algorithm.py`: 算法主体实现，通常包含算法类、`run()` 方法、`test()` 方法和 `__main__` 入口。
- `parameters.json`: 前端或调度层读取的参数描述文件，定义参数名、默认值、校验规则、帮助信息。
- `README_en.md` / `README_zh.md`: 算法原理、输入输出、示例说明。
- `__init__.py`: 导出算法类，供上层模块统一导入。

补充说明：

- 当前大多数算法都继承 `unitarylab_algorithms/algo_base.py` 中的 `BaseAlgorithm`。
- `schrodingerization` 子目录使用了自己的 `base.py`，实现风格相近，但基类不完全相同。- `schrodingerization` 子目录使用 `setup.json` 替代 `parameters.json`，且当前均未包含 `README_en.md` 和 `README_zh.md`。- 结果文件通常输出到 `results/<category>/<algorithm>/`，包括 `.txt`、`.svg`、`.png` 或 `.npz` 等。

## 算法实现规范

### 1. 类命名规范

- **可以直接复制 `template.py` 进行修改**。
- 类名建议以 `Algorithm` 结尾，例如 `GroverAlgorithm`、`QAOAAlgorithm`。
- 文件夹名使用小写加下划线，例如 `amplitude_estimation`。

### 2. 继承规范

新算法优先继承 `BaseAlgorithm`：

```python
from ...algo_base import BaseAlgorithm

class ExampleAlgorithm(BaseAlgorithm):
    ...
```

建议保留当前仓库已使用的兜底导入写法，兼容单文件调试：

```python
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    import os
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm
```

### 3. `__init__` 规范

- 支持 `text_mode`，常见取值为 `plain` 或 `legacy`。
- 支持 `algo_dir`，默认自动创建结果目录。
- 在 `super().__init__()` 中传入清晰的 `name` 和 `prefix`。

建议模式：

```python
def __init__(self, text_mode: str = "plain", algo_dir: str = None):
    if algo_dir is None:
        _this = os.path.abspath(__file__)
        _directory = os.path.dirname(_this)
        algo_dir = os.path.join(
            os.getcwd(),
            "results",
            os.path.basename(os.path.dirname(_directory)),
            os.path.basename(_directory),
        )
    os.makedirs(algo_dir, exist_ok=True)
    super().__init__(name="Example Algorithm", prefix="EXM", text_mode=text_mode, algo_dir=algo_dir)
```

### 4. `run()` 规范

- `run()` 是核心入口，参数要明确、可读、可校验。
- 一开始调用 `self.update_input(...)` 记录输入。
- 关键阶段调用 `self.log(...)` 输出进度。
- 算法结束后调用 `self.update_output(...)` 更新输出。
- 设置 `self.status` 和 `self.summary`。
- 如有电路图，调用 `self.save_circuit(...)`。
- 最后调用 `self.save_txt()` 并返回 `_build_return_dict(...)`。

推荐执行顺序：

1. 参数检查
2. 输入记录
3. 电路构建或数值计算
4. 运行模拟
5. 后处理与结果分析
6. 保存电路/文本/图像
7. 返回标准字典

### 5. 返回值规范

建议返回 `BaseAlgorithm._build_return_dict()` 生成的标准字典，包含：

- `status`: 算法执行状态，True/False
- `circuit_path`
- `result_path`
- `circuit`

### 6. 参数文件规范

`parameters.json` 建议包含以下字段：

```json
{
  "title": "Algorithm Name",
  "description": "Short description of the algorithm.",
  "tags": ["tag1", "tag2"],
  "tab": "Category",
  "params": [
    {
      "name": "n",
      "value": "3",
      "description": "Number of qubits",
      "help": "The number of qubits in the register.",
      "pattern": "^[1-9]\\d*$",
      "min": 1,
      "max": 10
    }
  ]
}
```

要求：

- `name` 与 `test()` `__main__` 参数名保持一致。
- `value` 使用可直接传入前端表单的默认值。
- `pattern` 尽量提供，便于前端校验。
- `description` 面向展示，`help` 面向解释。

### 7. 文档规范

每个算法目录建议至少维护以下文档：

- `README_zh.md`: 中文说明
- `README_en.md`: 英文说明

文档内容建议包括：

1. 算法有哪些参数，怎么设置，一句话介绍算法做了什么
2. 算法简介/背景
3. 算法思想、原理说明
4. 复杂度分析
5. 算法应用
6. 参考文献

### 8. 导出规范

新增算法后，需要同步修改两层导出：

1. 对应分类目录下的 `__init__.py`
2. `algorithms/__init__.py`

否则上层无法统一导入。

## 新增一个算法的推荐流程

1. 在对应分类下新建算法目录，例如 `algorithms/fundamental_algorithm/my_algorithm/`。
2. 拷贝 `algorithms/template.py` 作为初始模板。
3. 将类名、算法名、参数、日志、输出字段替换为实际内容。
4. 编写 `parameters.json`。
5. 补充 `README_zh.md` 和 `README_en.md`。
6. 更新分类 `__init__.py` 和总入口 `algorithms/__init__.py`。
7. 运行最小测试，确认可以独立执行。

## 最小检查清单

提交前建议至少确认：

- 算法类名与导出名一致。
- `run()` 能独立运行。
- 输入参数已记录到 `self.input`。
- 输出结果已记录到 `self.output`。
- `self.status` 和 `self.summary` 已设置。
- 结果目录会自动创建。
- `parameters.json` 中参数名与代码一致。
- 中英文 README 已补齐。

## 模板文件

通用模板已新增到当前目录：`algorithms/template.py`。

如果后续要统一整个仓库的算法风格，建议优先让新增算法遵循这个模板，再逐步回收历史实现差异。