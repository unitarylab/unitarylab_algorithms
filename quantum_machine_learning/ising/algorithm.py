"""Directly callable 2D transverse-field Ising dynamics algorithm.

This module is self-contained with respect to the original Ising reproduction
implementation.  It only depends on the repository-level ``algo_base.py`` and
the public UnitaryLab API.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

# Matplotlib needs a writable cache directory on macOS/Linux.
_MPL_CACHE = Path(tempfile.gettempdir()) / "ising-unitarylab-algorithm-mpl"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.font_manager import FontProperties
from unitarylab import Circuit

try:
    from unitarylab_algorithms.algo_base import BaseAlgorithm
except ImportError:
    _algorithms_dir = Path(__file__).resolve().parents[3]
    if str(_algorithms_dir) not in sys.path:
        sys.path.insert(0, str(_algorithms_dir))
    from algo_base import BaseAlgorithm


@dataclass(frozen=True)
class IsingModel:
    """二维开放边界横场 Ising 模型。

    Hamiltonian 为

        H = -J Σ_<i,j> Z_i Z_j - h Σ_i X_i,

    其中每个晶格格点对应一个量子比特，初态默认为 |0>^N。
    """

    rows: int
    cols: int
    coupling_J: float
    field_h: float

    @property
    def num_qubits(self) -> int:
        """晶格总格点数，也就是线路的量子比特数。"""
        return self.rows * self.cols

    @classmethod
    def from_config(
        cls,
        model_config: dict[str, object],
        experiment_config: dict[str, object],
    ) -> "IsingModel":
        """从模型条目和公共物理参数创建一个晶格模型。"""
        return cls(
            rows=int(model_config["rows"]),
            cols=int(model_config["cols"]),
            coupling_J=float(experiment_config["coupling_J"]),
            field_h=float(experiment_config["field_h"]),
        )


@dataclass(frozen=True)
class SimulationSettings:
    """所有模型和对比组合共用的数值模拟参数。"""

    time_step: float
    trotter_steps: int
    cutoff: float
    routing: str
    seed: int
    sample_shots: int = 0

    @classmethod
    def from_config(cls, config: dict[str, object]) -> "SimulationSettings":
        """从 JSON 配置创建数值模拟参数。"""
        return cls(
            time_step=float(config["time_step"]),
            trotter_steps=int(config["trotter_steps"]),
            cutoff=float(config["cutoff"]),
            routing=str(config["routing"]),
            seed=int(config["seed"]),
            sample_shots=int(config.get("sample_shots", 0)),
        )


def qubit_id(row: int, col: int, cols: int) -> int:
    """按行优先顺序把二维坐标 (row, col) 映射为一维量子比特编号。"""
    return row * cols + col


def lattice_edges(rows: int, cols: int) -> list[tuple[int, int]]:
    """列出开放边界方格晶格的全部最近邻边 <i,j>。"""
    horizontal = [
        (qubit_id(row, col, cols), qubit_id(row, col + 1, cols))
        for row in range(rows)
        for col in range(cols - 1)
    ]
    vertical = [
        (qubit_id(row, col, cols), qubit_id(row + 1, col, cols))
        for row in range(rows - 1)
        for col in range(cols)
    ]
    return horizontal + vertical


def edge_groups(rows: int, cols: int) -> list[list[tuple[int, int]]]:
    """把最近邻边分成四组互不冲突的匹配。"""
    groups: list[list[tuple[int, int]]] = [[], [], [], []]
    for row in range(rows):
        for col in range(cols - 1):
            first = qubit_id(row, col, cols)
            groups[col % 2].append((first, first + 1))
    for row in range(rows - 1):
        for col in range(cols):
            first = qubit_id(row, col, cols)
            groups[2 + row % 2].append((first, first + cols))
    return groups


def observable_sums(model: IsingModel) -> dict[str, list[tuple[float, str, list[int]]]]:
    """把全局观测量写成 UnitaryLab 可直接计算的 Pauli 项之和。"""
    edges = lattice_edges(model.rows, model.cols)
    return {
        "magnetization_z": [
            (1.0 / model.num_qubits, "Z", [qubit])
            for qubit in range(model.num_qubits)
        ],
        "magnetization_x": [
            (1.0 / model.num_qubits, "X", [qubit])
            for qubit in range(model.num_qubits)
        ],
        "mean_zz": [
            (1.0 / len(edges), "ZZ", [first, second])
            for first, second in edges
        ],
    }


def append_zz(circuit: Circuit, first: int, second: int, angle: float) -> None:
    """用 CNOT-RZ-CNOT 实现 exp(-i angle Z⊗Z/2)。"""
    circuit.cx(first, second)
    circuit.rz(angle, second)
    circuit.cx(first, second)


def append_x_evolution(circuit: Circuit, model: IsingModel, duration: float) -> None:
    """添加 exp(-i H_X duration)，其中 H_X=-h Σ_i X_i。"""
    for qubit in range(model.num_qubits):
        circuit.rx(-2.0 * model.field_h * duration, qubit)


def append_zz_evolution(circuit: Circuit, model: IsingModel, duration: float) -> None:
    """添加 exp(-i H_ZZ duration)，其中 H_ZZ=-J Σ_<i,j> Z_iZ_j。"""
    for group in edge_groups(model.rows, model.cols):
        for first, second in group:
            append_zz(circuit, first, second, -2.0 * model.coupling_J * duration)


def append_second_order_block(
    circuit: Circuit,
    model: IsingModel,
    duration: float,
) -> None:
    """向已有线路追加一个二阶对称 Strang 时间块。"""
    append_x_evolution(circuit, model, duration / 2.0)
    append_zz_evolution(circuit, model, duration)
    append_x_evolution(circuit, model, duration / 2.0)


def build_trotter_step(model: IsingModel, time_step: float, order: int) -> Circuit:
    """构造一阶、二阶或四阶 Trotter–Suzuki 时间步。"""
    if order not in (1, 2, 4):
        raise ValueError(f"trotter order must be 1, 2, or 4; got {order}")

    circuit = Circuit(model.num_qubits)
    if order == 1:
        # 线路先执行 X，再执行 ZZ，所以总酉矩阵是 U_ZZ U_X。
        append_x_evolution(circuit, model, time_step)
        append_zz_evolution(circuit, model, time_step)
    elif order == 2:
        append_second_order_block(circuit, model, time_step)
    else:
        coefficient = 1.0 / (4.0 - 4.0 ** (1.0 / 3.0))
        for weight in (
            coefficient,
            coefficient,
            1.0 - 4.0 * coefficient,
            coefficient,
            coefficient,
        ):
            append_second_order_block(circuit, model, weight * time_step)
    return circuit


def real_expectation(
    result: object,
    observable: object,
    qubits: list[int] | None = None,
) -> float:
    """通过 UnitaryLab 结果对象读取归一化 Pauli 期望值。"""
    value = (
        result.expectation(observable, qubits)
        if qubits is not None
        else result.expectation(observable)
    )
    if abs(complex(value).imag) > 1e-10:
        raise RuntimeError(f"Expectation is not real: {value}")
    return float(complex(value).real)


def observe(result: object, model: IsingModel) -> dict[str, float]:
    """通过三个 Pauli 和计算全局磁化、畴壁密度和能量。"""
    terms = observable_sums(model)
    magnetization_z = real_expectation(result, terms["magnetization_z"])
    magnetization_x = real_expectation(result, terms["magnetization_x"])
    mean_zz = real_expectation(result, terms["mean_zz"])
    edge_count = len(lattice_edges(model.rows, model.cols))
    energy = (
        -model.coupling_J * edge_count * mean_zz
        -model.field_h * model.num_qubits * magnetization_x
    )
    return {
        "magnetization_z": magnetization_z,
        "magnetization_x": magnetization_x,
        "mean_zz": mean_zz,
        "domain_wall_density": (1.0 - mean_zz) / 2.0,
        "energy_per_site": energy / model.num_qubits,
    }


def observe_local_configuration(result: object, model: IsingModel) -> dict[str, object]:
    """只在需要保存磁构型时计算每个格点的局域 <Xi> 和 <Zi>。"""
    z_values = np.asarray([
        real_expectation(result, "Z", [qubit])
        for qubit in range(model.num_qubits)
    ])
    x_values = np.asarray([
        real_expectation(result, "X", [qubit])
        for qubit in range(model.num_qubits)
    ])
    return {
        "z_map": z_values.reshape(model.rows, model.cols).tolist(),
        "x_map": x_values.reshape(model.rows, model.cols).tolist(),
    }


def execute_options(
    settings: SimulationSettings,
    max_bond: int,
) -> dict[str, object]:
    """生成直接传给 Circuit.execute() 的参数。"""
    return {
        "backend": "tensornet",
        "device": "cpu",
        "seed": settings.seed,
        "backend_options": {
            "max_bond": max_bond,
            "cutoff": settings.cutoff,
            "routing": settings.routing,
        },
    }


def run_key(
    model_name: str,
    trotter_order: int,
    max_bond: int,
    time_step: float,
    trotter_steps: int,
) -> str:
    """生成可用于标识运行参数的唯一组合标识。"""
    return (
        f"{model_name}|order={trotter_order}|chi={max_bond}"
        f"|dt={time_step:g}|steps={trotter_steps}"
    )


def run_trajectory(
    model_name: str,
    model: IsingModel,
    settings: SimulationSettings,
    trotter_order: int,
    max_bond: int,
    save_local_configuration: bool,
    local_configuration_mode: str = "final",
) -> dict[str, object]:
    """执行一个指定尺寸、Trotter 阶数和键维的完整轨迹。"""
    options = execute_options(settings, max_bond)
    step_circuit = build_trotter_step(
        model,
        settings.time_step,
        trotter_order,
    )

    started = time.perf_counter()

    # 空线路在默认 |0>^N 初态上执行，获得 UnitaryLab TensorNet 结果对象。
    result = Circuit(model.num_qubits).execute(**options)
    records = []
    local_configuration_records = []

    for step in range(settings.trotter_steps + 1):
        # 先记录当前时刻，再在循环末尾推进一个 Trotter 时间步。
        values = observe(result, model)
        current_time = step * settings.time_step
        record = {"step": step, "time": current_time, **values}
        if save_local_configuration and local_configuration_mode in ("all", "gif"):
            local = observe_local_configuration(result, model)
            if local_configuration_mode == "all":
                record.update(local)
            else:
                local_configuration_records.append({**record, **local})
        records.append(record)
        print(
            f"{model_name} p={trotter_order} χ={max_bond} "
            f"step={step:>3d}/{settings.trotter_steps} tJ={current_time:.5f} "
            f"Mz={values['magnetization_z']:+.8f} "
            f"D={values['domain_wall_density']:.8f} "
            f"E/N={values['energy_per_site']:+.8f}",
            flush=True,
        )

        if step < settings.trotter_steps:
            # 使用公开续算接口：把上一步的 backend_state 交给下一次 execute。
            # 代码不读取 backend_state 内部的 MPS 张量。
            result = step_circuit.execute(
                initial_state=result.backend_state,
                **options,
            )

    # 如配置了 sample_shots，采样同样交给 UnitaryLab 的公开 result.sample()。
    samples = (
        result.sample(shots=settings.sample_shots, seed=settings.seed)
        if settings.sample_shots
        else []
    )
    run = {
        "key": run_key(
            model_name,
            trotter_order,
            max_bond,
            settings.time_step,
            settings.trotter_steps,
        ),
        "model": model_name,
        "rows": model.rows,
        "cols": model.cols,
        "num_qubits": model.num_qubits,
        "max_bond": max_bond,
        "trotter_order": trotter_order,
        "time_step": settings.time_step,
        "trotter_steps": settings.trotter_steps,
        "wall_seconds": time.perf_counter() - started,
        "step_circuit_summary": step_circuit.analyze(show=False).get_summary(),
        "samples": samples,
        "records": records,
        "step_circuit": step_circuit,
    }
    if save_local_configuration:
        if local_configuration_mode == "all":
            run["local_configuration"] = {
                "z_map": records[-1]["z_map"],
                "x_map": records[-1]["x_map"],
            }
        elif local_configuration_mode == "gif":
            run["local_configuration_records"] = local_configuration_records
            run["local_configuration"] = {
                "z_map": local_configuration_records[-1]["z_map"],
                "x_map": local_configuration_records[-1]["x_map"],
            }
        else:
            run["local_configuration"] = observe_local_configuration(result, model)
    return run


def plot_observables(records: list[dict[str, object]], path: Path) -> None:
    """保存全局 Ising 观测量随时间变化的曲线。"""
    times = [float(record["time"]) for record in records]
    figure, axes = plt.subplots(2, 2, figsize=(10, 7.2))
    series = (
        ("magnetization_z", "Magnetization Z", "Mz"),
        ("magnetization_x", "Magnetization X", "Mx"),
        ("domain_wall_density", "Domain-wall density", "D"),
        ("energy_per_site", "Energy per site", "E/N"),
    )
    for axis, (field, title, ylabel) in zip(axes.flat, series):
        axis.plot(times, [float(record[field]) for record in records], "o-")
        axis.set_title(title)
        axis.set_xlabel("Time")
        axis.set_ylabel(ylabel)
        axis.grid(alpha=0.3)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def plot_magnetic_configuration(
    run: dict[str, object],
    output_path: Path,
    font: FontProperties | None,
) -> None:
    """绘制一个终态的局域 (〈Xi〉,〈Zi〉) 磁构型。"""
    local = run["local_configuration"]
    z_map = np.asarray(local["z_map"], dtype=float)
    x_map = np.asarray(local["x_map"], dtype=float)
    row_grid, col_grid = np.indices(z_map.shape)
    length = np.hypot(x_map, z_map)
    length = np.where(length > 1e-12, length, 1.0)

    figure, axis = plt.subplots(figsize=(6.5, 6.0))
    image = axis.imshow(z_map, vmin=-1.0, vmax=1.0, cmap="RdBu", origin="upper")
    axis.quiver(
        col_grid,
        row_grid,
        0.58 * x_map / length,
        -0.58 * z_map / length,
        angles="xy",
        scale_units="xy",
        scale=1.0,
        color="#142b4a",
        pivot="middle",
    )
    final = run["records"][-1]
    axis.set_title(
        f"{run['model']} 终态磁构型：p={run['trotter_order']}，χ={run['max_bond']}\n"
        f"tJ={final['time']:.3f}，Mz={final['magnetization_z']:+.4f}",
        fontproperties=font,
    )
    axis.set_xticks([])
    axis.set_yticks([])
    figure.colorbar(image, ax=axis, label=r"$\langle Z_i\rangle$")
    figure.tight_layout()
    figure.savefig(output_path)
    plt.close(figure)


def plot_magnetic_evolution_gif(
    records: list[dict[str, object]],
    output_path: Path,
) -> None:
    """把每个时间步的局域磁构型合成为 GIF。"""
    figure, axis = plt.subplots(figsize=(6.5, 6.0))

    def update(frame: int) -> None:
        axis.clear()
        record = records[frame]
        z_map = np.asarray(record["z_map"], dtype=float)
        x_map = np.asarray(record["x_map"], dtype=float)
        row_grid, col_grid = np.indices(z_map.shape)
        length = np.hypot(x_map, z_map)
        length = np.where(length > 1e-12, length, 1.0)
        axis.imshow(z_map, vmin=-1.0, vmax=1.0, cmap="RdBu", origin="upper")
        axis.quiver(
            col_grid,
            row_grid,
            0.58 * x_map / length,
            -0.58 * z_map / length,
            angles="xy",
            scale_units="xy",
            scale=1.0,
            color="#142b4a",
            pivot="middle",
        )
        axis.set_title(
            f"tJ={record['time']:.3f}, Mz={record['magnetization_z']:+.4f}, "
            f"Mx={record['magnetization_x']:+.4f}, "
            f"D={record['domain_wall_density']:.4f}"
        )
        axis.set_xticks([])
        axis.set_yticks([])

    animation = FuncAnimation(
        figure,
        update,
        frames=len(records),
        interval=500,
        repeat=True,
    )
    animation.save(output_path, writer=PillowWriter(fps=2))
    plt.close(figure)


class IsingAlgorithm(BaseAlgorithm):
    """2D transverse-field Ising dynamics using TensorNet execution."""

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
        super().__init__(
            name="2D Transverse-Field Ising Dynamics Algorithm",
            prefix="ISING",
            text_mode=text_mode,
            algo_dir=algo_dir,
        )

    @staticmethod
    def _validate_inputs(
        rows: int,
        cols: int,
        coupling_J: float,
        field_h: float,
        time_step: float,
        trotter_steps: int,
        trotter_order: int,
        max_bond: int,
        cutoff: float,
        routing: str,
        seed: int,
        sample_shots: int,
        local_configuration_mode: str,
    ) -> None:
        if isinstance(rows, bool) or not isinstance(rows, int) or rows <= 0:
            raise ValueError("rows must be a positive integer.")
        if isinstance(cols, bool) or not isinstance(cols, int) or cols <= 0:
            raise ValueError("cols must be a positive integer.")
        if rows == 1 and cols == 1:
            raise ValueError("The lattice must contain at least one nearest-neighbor edge.")
        if not math.isfinite(coupling_J):
            raise ValueError("coupling_J must be finite.")
        if not math.isfinite(field_h):
            raise ValueError("field_h must be finite.")
        if not math.isfinite(time_step) or time_step <= 0:
            raise ValueError("time_step must be a positive finite number.")
        if isinstance(trotter_steps, bool) or not isinstance(trotter_steps, int) or trotter_steps < 0:
            raise ValueError("trotter_steps must be a non-negative integer.")
        if trotter_order not in (1, 2, 4):
            raise ValueError("trotter_order must be 1, 2, or 4.")
        if isinstance(max_bond, bool) or not isinstance(max_bond, int) or max_bond <= 0:
            raise ValueError("max_bond must be a positive integer.")
        if not math.isfinite(cutoff) or cutoff < 0:
            raise ValueError("cutoff must be a non-negative finite number.")
        if not isinstance(routing, str) or not routing:
            raise ValueError("routing must be a non-empty string.")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer.")
        if isinstance(sample_shots, bool) or not isinstance(sample_shots, int) or sample_shots < 0:
            raise ValueError("sample_shots must be a non-negative integer.")
        if local_configuration_mode not in ("none", "final", "all", "gif"):
            raise ValueError(
                "local_configuration_mode must be one of: none, final, all, gif."
            )

    def run(
        self,
        rows: int = 6,
        cols: int = 6,
        coupling_J: float = 1.0,
        field_h: float = 3.0,
        time_step: float = 0.025,
        trotter_steps: int = 8,
        trotter_order: int = 2,
        max_bond: int = 32,
        cutoff: float = 1e-12,
        routing: str = "auto",
        seed: int = 7,
        sample_shots: int = 0,
        local_configuration_mode: str = "gif",
    ) -> Dict[str, Any]:
        """Run one 2D transverse-field Ising evolution trajectory."""
        self._validate_inputs(
            rows,
            cols,
            coupling_J,
            field_h,
            time_step,
            trotter_steps,
            trotter_order,
            max_bond,
            cutoff,
            routing,
            seed,
            sample_shots,
            local_configuration_mode,
        )

        self.input.clear()
        self.output.clear()
        self.info.clear()
        self.status = ""
        self.summary = ""

        input_data = {
            "rows": rows,
            "cols": cols,
            "coupling_J": coupling_J,
            "field_h": field_h,
            "time_step": time_step,
            "trotter_steps": trotter_steps,
            "trotter_order": trotter_order,
            "max_bond": max_bond,
            "cutoff": cutoff,
            "routing": routing,
            "seed": seed,
            "sample_shots": sample_shots,
            "local_configuration_mode": local_configuration_mode,
        }
        self.update_input(input_data)

        model = IsingModel(
            rows=rows,
            cols=cols,
            coupling_J=coupling_J,
            field_h=field_h,
        )
        settings = SimulationSettings(
            time_step=time_step,
            trotter_steps=trotter_steps,
            cutoff=cutoff,
            routing=routing,
            seed=seed,
            sample_shots=sample_shots,
        )

        self.log("Stage 1/4: Building the Trotter step circuit.")
        model_name = f"{rows}x{cols}"
        save_local_configuration = local_configuration_mode != "none"

        self.log("Stage 2/4: Executing the Ising trajectory with TensorNet.")
        run = run_trajectory(
            model_name=model_name,
            model=model,
            settings=settings,
            trotter_order=trotter_order,
            max_bond=max_bond,
            save_local_configuration=save_local_configuration,
            local_configuration_mode=(
                "final" if local_configuration_mode == "none" else local_configuration_mode
            ),
        )
        step_circuit = run.pop("step_circuit")
        final_observables = dict(run["records"][-1])

        self.log("Stage 3/4: Saving the circuit and result visualizations.")
        circuit_path = self.save_circuit(step_circuit, name="ising_trotter_step")
        observables_path = Path(self.algo_dir) / "ising_observables.svg"
        plot_observables(run["records"], observables_path)
        plot_paths = [str(observables_path)]

        if local_configuration_mode == "final":
            configuration_path = Path(self.algo_dir) / "magnetic_configuration.png"
            plot_magnetic_configuration(
                run,
                configuration_path,
                None,
            )
            plot_paths.append(str(configuration_path))
        elif local_configuration_mode == "gif":
            gif_records = run.pop("local_configuration_records")
            gif_path = Path(self.algo_dir) / "magnetic_configuration.gif"
            plot_magnetic_evolution_gif(gif_records, gif_path)
            plot_paths.append(str(gif_path))

        output_data = {
            "final_observables": final_observables,
            "wall_seconds": run["wall_seconds"],
            "step_circuit_summary": run["step_circuit_summary"],
        }
        self.update_output(output_data)
        self.status = "success"
        self.summary = (
            f"Completed {rows}x{cols} Ising dynamics through "
            f"t={time_step * trotter_steps:g}; final Mz="
            f"{final_observables['magnetization_z']:+.6f}."
        )

        self.log("Stage 4/4: Saving the text summary.")
        result_filename = self.save_txt()
        plot_paths.append(result_filename)
        result = self._build_return_dict(
            True,
            circuit_path,
            plot_paths,
            step_circuit,
        )
        result.update(run)
        result["final_observables"] = final_observables
        return result


def test(
    rows: int = 6,
    cols: int = 6,
    coupling_J: float = 1.0,
    field_h: float = 3.0,
    time_step: float = 0.025,
    trotter_steps: int = 8,
    trotter_order: int = 2,
    max_bond: int = 32,
    cutoff: float = 1e-12,
    routing: str = "auto",
    seed: int = 7,
    sample_shots: int = 0,
    local_configuration_mode: str = "gif",
) -> Dict[str, Any]:
    """Execute the default directly callable Ising example."""
    algo = IsingAlgorithm(text_mode="legacy")
    return algo.run(
        rows=rows,
        cols=cols,
        coupling_J=coupling_J,
        field_h=field_h,
        time_step=time_step,
        trotter_steps=trotter_steps,
        trotter_order=trotter_order,
        max_bond=max_bond,
        cutoff=cutoff,
        routing=routing,
        seed=seed,
        sample_shots=sample_shots,
        local_configuration_mode=local_configuration_mode,
    )


if __name__ == "__main__":
    rows = 6  # [PARAM]
    cols = 6  # [PARAM]
    coupling_J = 1.0  # [PARAM]
    field_h = 3.0  # [PARAM]
    time_step = 0.025  # [PARAM]
    trotter_steps = 8  # [PARAM]
    trotter_order = 2  # [PARAM]
    max_bond = 32  # [PARAM]
    cutoff = 1e-12  # [PARAM]
    routing = "auto"  # [PARAM]
    seed = 7  # [PARAM]
    sample_shots = 0  # [PARAM]
    local_configuration_mode = "gif"  # [PARAM]

    test(
        rows=rows,
        cols=cols,
        coupling_J=coupling_J,
        field_h=field_h,
        time_step=time_step,
        trotter_steps=trotter_steps,
        trotter_order=trotter_order,
        max_bond=max_bond,
        cutoff=cutoff,
        routing=routing,
        seed=seed,
        sample_shots=sample_shots,
        local_configuration_mode=local_configuration_mode,
    )
