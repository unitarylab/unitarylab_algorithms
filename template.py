import os
import time
from typing import Any, Dict

import numpy as np
from unitarylab.core import Circuit

try:
    from .algo_base import BaseAlgorithm
except ImportError:
    import sys

    _algorithms_dir = os.path.dirname(os.path.abspath(__file__))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class ExampleAlgorithm(BaseAlgorithm):
    """Minimal template for adding a new algorithm under algorithms/."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        # 设置算法名称、前缀
        super().__init__(name="Example Algorithm", prefix="EXP", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, n: int = 2) -> Dict[str, Any]:
        """
        Run the Example algorithm.

        Parameters:
            n: Number of qubits

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """
        
        # 首先记录 input 参数信息，然后进行更新，会自动打印参数
        input = {"Number of qubits (n)": n}
        self.update_input(input)

        # 正常的算法执行流程，期间可以通过 self.log 输出日志信息
        self.log("Stage 1/4: Building circuit...")

        qc = Circuit(n)

        # 记录 output 信息，然后进行更新，会自动打印结果
        output = {"Result": "Example result", "Elapsed time (s)": 0}
        self.update_output(output)

        # 记录算法执行状态和总结信息
        self.status = "success"
        self.summary = f"Execution successful. Example result is {output['Result']}."

        # 保存线路图和结果文本
        circuit_path = self.save_circuit(qc)
        filename = self.save_txt()

        # 如果有多个线路图，可以通过 self.save_circuit(qc, name="another") 来保存
        circuit_path_1 = self.save_circuit(qc, name="example_1")
        circuit_path_2 = self.save_circuit(qc, name="example_2")
        circuit_path = [circuit_path_1, circuit_path_2]

        # 最后构建返回字典，包含算法执行状态(True/False)、线路图路径、保存的文件路径、量子线路本身
        return self._build_return_dict(True, circuit_path, filename, qc)


def test(n: int = 2) -> Dict[str, Any]:
    # test 函数用于在本地测试算法，参数 n 需要设置默认值
    # legacy 模式下使用富文本，plain 模式下使用纯文本
    algo = ExampleAlgorithm(text_mode="legacy")
    return algo.run(n=n)


if __name__ == "__main__":
    # test 中输入的参数后加上 `# [PARAM]` 注释，和 parameters.json 中的参数名称一致，网页端运行时会自动替换为用户输入的参数值
    # 不需要修改的参数就不用加 `# [PARAM]` 注释，保持默认值即可
    n = 2  # [PARAM]
    test(n=n)