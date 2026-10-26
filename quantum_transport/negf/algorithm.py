"""NEGF transport using the built-in UnitaryLab QSVT linear solver."""

import os
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np
from scipy import sparse
from unitarylab import Circuit
from unitarylab.library import solve

try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class KwantSolvers:
    """引线注入方程的共用代码；内置 QSVT 构建一次后复用。"""

    @staticmethod
    def lead_injection_vectors(gamma, interface, *, self_energy=None, system_size=None):
        """分解界面 Gamma，返回 b，使 Gamma ≈ b b†（舍入误差范围内）。

        可传入生成 Gamma=i(Sigma-Sigma†) 的同维 self_energy。带边附近
        Gamma 可能远小于 Sigma，误差尺度必须包含 Sigma；正负的近零
        特征值使用同一阈值，避免把舍入噪声误判为负展宽或传播通道。
        指定 system_size 时 gamma/self_energy 是界面局部块，返回嵌入
        system_size 维空间的注入向量；省略时保留原来的全矩阵接口。
        """
        gamma = np.asarray(gamma)
        interface = np.asarray(interface, dtype=int)
        if system_size is None:
            local = gamma[np.ix_(interface, interface)]
            size = len(gamma)
        else:
            if (isinstance(system_size, (bool, np.bool_))
                    or not isinstance(system_size, (int, np.integer)) or system_size < 0
                    or interface.ndim != 1 or np.any(interface < 0)
                    or np.any(interface >= system_size)
                    or len(np.unique(interface)) != len(interface)
                    or gamma.shape != (len(interface), len(interface))):
                raise ValueError("局部 Gamma 维数、interface 和 system_size 必须一致")
            local, size = gamma, system_size
        if not np.all(np.isfinite(local)):
            raise ValueError("引线 Gamma 必须包含有限数值")
        values, vectors = np.linalg.eigh((local + local.conj().T) / 2)
        scale = np.max(np.abs(values), initial=0.)
        if self_energy is not None:
            self_energy = np.asarray(self_energy)
            if self_energy.shape != gamma.shape:
                raise ValueError("self_energy 必须与 Gamma 具有相同维数")
            local_sigma = (self_energy if system_size is not None
                           else self_energy[np.ix_(interface, interface)])
            if not np.all(np.isfinite(local_sigma)):
                raise ValueError("引线 self_energy 必须包含有限数值")
            if len(interface):
                # 两个自能项相减的误差按其原始尺度估计，保持对能量单位的缩放不变性。
                scale = max(scale, 2 * np.linalg.norm(local_sigma, 2))
        tolerance = 100 * np.finfo(float).eps * max(1, len(interface)) * scale
        if np.any(values < -tolerance):
            raise ValueError("引线 Gamma 不是半正定矩阵，请检查推迟自能的符号"
                             f"（最小特征值 {values.min():.3e}，数值容差 {tolerance:.3e}）")
        nonzero = values > tolerance
        sources = np.zeros((size, np.count_nonzero(nonzero)), dtype=complex)
        sources[interface] = vectors[:, nonzero] * np.sqrt(values[nonzero])
        return sources

    @staticmethod
    def _solve_input_states(rhs, evolve, state_size, scaling_factor):
        """共用 QSVT 输入/输出：辅助位为 0，恢复 ||b||、缩放及复相位。"""
        rhs = np.asarray(rhs, dtype=complex)
        if rhs.ndim != 2 or rhs.shape[0] > state_size or not np.all(np.isfinite(rhs)):
            raise ValueError("rhs 必须是线路空间可容纳的有限数值列向量矩阵")
        responses = np.zeros_like(rhs)
        for j, vector in enumerate(rhs.T):
            norm = np.linalg.norm(vector)
            if norm == 0:
                continue
            state = np.zeros(state_size, dtype=complex)
            state[:len(vector)] = vector / norm
            print(f"\nQSVT 实际注入态 [{j+1}/{rhs.shape[1]}]：开始模拟完整线路……",
                  flush=True)
            started = perf_counter()
            out = evolve(state)  # 复用 QSVT 主体，为该输入构建完整态制备线路。
            elapsed = perf_counter() - started
            print(f"QSVT 实际注入态 [{j+1}/{rhs.shape[1]}]：模拟完成，耗时 {elapsed:.3f} s",
                  flush=True)
            responses[:, j] = norm * scaling_factor * out[:len(vector)]
        if not np.all(np.isfinite(responses)):
            raise RuntimeError("QSVT 引线注入响应出现非有限数值")
        return responses

    @staticmethod
    def solve_unitarylab(A, rhs, *, inverse_tolerance=2e-3):
        """构建内置 QSVT，并为各注入态补齐实际执行的态制备线路。"""
        A = A.toarray() if sparse.issparse(A) else np.asarray(A)
        size = 1 << (len(A) - 1).bit_length()
        padded = np.linalg.norm(A, 2) * np.eye(size, dtype=complex)
        padded[:len(A), :len(A)] = A
        e0 = np.zeros(size, dtype=complex)
        e0[0] = 1
        epsilon, error = KwantSolvers._unitarylab_epsilon(padded, inverse_tolerance)
        result = solve(padded, e0, method="qsvt", epsilon=epsilon,
                       backend="numpy", dtype=np.complex128, logging=False)
        circuit = result.circuit
        system_qubits = list(range(size.bit_length() - 1))
        circuits = []

        def evolve(state):
            # 系统位在低位，两个辅助位从全零态开始；保留复数输入的相位。
            display_circuit = Circuit(circuit.get_num_qubits(),
                                      name=f"NEGF injection {len(circuits) + 1}")
            display_circuit.initialize(state[:size], system_qubits)
            display_circuit.append(circuit, list(range(circuit.get_num_qubits())))
            circuits.append(display_circuit)
            return display_circuit.execute(backend="numpy", dtype=np.complex128).state

        responses = KwantSolvers._solve_input_states(
            rhs, evolve, 1 << circuit.get_num_qubits(), result.scaling_factor)
        return responses, circuits, result.scaling_factor, epsilon, error

    @staticmethod
    def _unitarylab_epsilon(matrix, tolerance):
        """按 SDK 的谱归一化流程校准 epsilon，返回实际多项式误差。"""
        from unitarylab.library.block_encoding.tools import normalize_matrix
        from unitarylab.library.linear_solver.qsvt import _indicator

        if not np.isfinite(tolerance) or not 0 < tolerance < 1:
            raise ValueError("inverse_tolerance 必须在 (0, 1) 内")
        singular_values = np.linalg.svd(matrix, compute_uv=False)
        if singular_values[-1] <= np.finfo(float).eps * len(matrix) * singular_values[0]:
            raise ValueError("A 在当前数值精度下必须可逆")

        # 与 QSVTSolver 一致：先除以谱范数，再计算 Nagy 的 alpha。
        # 仅校准局部矩阵，solve() 仍接收原始 padded。
        matrix = matrix / np.linalg.norm(matrix, 2)
        singular_values = np.linalg.svd(matrix, compute_uv=False)
        kappa = np.linalg.cond(matrix)
        _, alpha = normalize_matrix(matrix, norm_type="spectral")
        sigma = singular_values / alpha
        grid = np.unique(np.r_[np.linspace(sigma[-1], sigma[0], 20001), sigma])
        # 仅用未截断公式估计初值；最终验收 _indicator 返回的实际系数。
        log_ratio = -np.log(tolerance) / singular_values[0]**2
        for _ in range(32):
            epsilon = float(kappa * alpha * np.exp(-log_ratio))
            if not np.isfinite(epsilon) or not 0 < epsilon < kappa * alpha:
                raise RuntimeError("unitarylab epsilon 超出浮点数范围")
            b_order = np.ceil((kappa * alpha)**2 * log_ratio)
            if not np.isfinite(b_order):
                raise RuntimeError("unitarylab 多项式截断参数超出浮点数范围")
            if 4 * b_order > epsilon:
                odd, beta = _indicator(kappa, alpha, epsilon, 2.)
                coefficients = np.zeros(2 * len(odd))
                coefficients[1::2] = odd
                values = np.polynomial.chebyshev.chebval(grid, coefficients)
                error = np.max(np.abs(grid * values * beta * kappa * alpha - 1))
                if np.isfinite(error) and error <= tolerance:
                    print(f"unitarylab epsilon={epsilon:.6g}；次数={len(coefficients)-1}；"
                          f"逆函数相对误差={error:.3e} <= {tolerance:g}")
                    return epsilon, float(error)
            log_ratio *= 2
        raise RuntimeError("unitarylab 多项式未满足 inverse_tolerance")


class NEGFAlgorithm(BaseAlgorithm):
    """Run square-lattice NEGF transport with the built-in UnitaryLab QSVT solver."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            algo_dir = os.path.join(os.getcwd(), "results", "quantum_transport", "negf")
        os.makedirs(algo_dir, exist_ok=True)
        super().__init__(name="NEGF", prefix="NEGF", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, L: int = 4, W: int = 4, a: float = 1.0, t: float = 1.0,
            inverse_tolerance: float = 2e-3) -> Dict[str, Any]:
        """Preserve the source NEGF flow and return its observables and files."""
        import kwant

        self.update_input({
            "L": L,
            "W": W,
            "a": a,
            "t": t,
            "inverse_tolerance": inverse_tolerance,
        })

        output_dir = Path(self.algo_dir)

        print("\n" + "=" * 80)
        print("step1: Import libraries")
        print("=" * 80)

        print("\n" + "=" * 80)
        print("step2: Construct the Hamitonian")
        print("=" * 80)

        # 参考：https://kwant-project.org/doc/latest/tutorial/first_steps
        # L、W 分别为中心散射区沿 x、y 方向的格点数；修改这两项即可调节长宽。
        # 后续只求引线注入响应，不构造散射区的完整逆矩阵。
        # 二维散射区的两个方向均至少取 2 个格点。
        if any(isinstance(size, (bool, np.bool_)) or not isinstance(size, (int, np.integer))
               or size < 2 for size in (L, W)):
            raise ValueError("L 和 W 必须是大于等于 2 的整数。")

        # 横向硬墙的前两个子带底；取两者之间的能量作为单通道入射能量。
        E_FIRST = 2 * t * (1 - np.cos(np.pi / (W + 1)))
        E_SECOND = 2 * t * (1 - np.cos(2 * np.pi / (W + 1)))
        ENERGY = (E_FIRST + E_SECOND) / 2    # eV，可在上述单通道区间内调整

        # 正方晶格 Hamiltonian：onsite = 4t，x、y 方向最近邻 hopping = -t。
        # 矩阵按 (x, y) 排序，与 step3 的 Kwant 站点顺序一致。
        H_X = sparse.diags([-t, 2*t, -t], [-1, 0, 1], shape=(L, L), format="csr")
        H_Y = sparse.diags([-t, 2*t, -t], [-1, 0, 1], shape=(W, W), format="csr")
        H_DEVICE = (sparse.kron(H_X, sparse.eye(W), format="csr")
                    + sparse.kron(sparse.eye(L), H_Y, format="csr"))

        print("正方晶格参数")
        print(f"  L         = {L} (x 方向格点数)")
        print(f"  W         = {W} (y 方向格点数)")
        print(f"  a         = {a:.10f}")
        print(f"  t         = {t:.10f} eV")
        print(f"  ENERGY    = {ENERGY:.10f} eV")


        print("\n" + "=" * 80)
        print("step3: 用 kwant.Builder 构建矩形正方晶格散射区及左右半无限引线")
        print("=" * 80)

        def build_square_system():
            """构造 L × W 的正方晶格散射区及宽度为 W 的左右半无限引线。"""
            lat = kwant.lattice.square(a, norbs=1)
            syst = kwant.Builder()

            # 中心散射区：0 <= x < L，0 <= y < W。
            sites = {(x, y): lat(x, y) for x in range(L) for y in range(W)}
            syst[sites.values()] = 4 * t
            syst[lat.neighbors()] = -t

            # 引线与散射区使用相同的 onsite、hopping 和宽度。
            left_lead = kwant.Builder(kwant.TranslationalSymmetry((-a, 0)))
            left_lead[(lat(0, y) for y in range(W))] = 4 * t
            left_lead[lat.neighbors()] = -t

            syst.attach_lead(left_lead)
            syst.attach_lead(left_lead.reversed())

            return syst.finalized()

        fsyst = build_square_system()

        # 导出散射区及左右引线连接结构，不在 notebook 中展示。
        # 用 Kwant 内置绘图显示每侧引线的 4 个晶胞，红色渐淡表示半无限延伸。
        fig = kwant.plot(fsyst, num_lead_cells=4, site_size=0.25,
                         hop_lw=0.08, lead_color="red", lead_site_size=0.25,
                         lead_hop_lw=0.08, colorbar=False, show=False)
        structure_path = output_dir / "kwant_square_system.png"
        fig.savefig(structure_path, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print(f"step3 图片文件导出到：{structure_path}")


        print("\n" + "=" * 80)
        print("step4: 准备 A 矩阵, A=EI-H_C-Sigma_L-Sigma_R")
        print("=" * 80)

        # Kwant 给出 L×W 个站点的散射区 Hamiltonian。
        H_C = fsyst.hamiltonian_submatrix(sparse=True).tocsr()

        # 将引线的局部表面自能嵌入散射区矩阵。
        def embedded_self_energy(sigma, lead_index):
            interface = fsyst.lead_interfaces[lead_index]
            rows, columns = np.meshgrid(interface, interface, indexing="ij")
            return sparse.csr_matrix((sigma.ravel(), (rows.ravel(), columns.ravel())),
                                     shape=H_C.shape)

        # 自能和展宽只保存 W×W 界面块；组装时以稀疏形式嵌入。
        Sigma_L = fsyst.leads[0].selfenergy(ENERGY)
        Sigma_R = fsyst.leads[1].selfenergy(ENERGY)
        Gamma_L = 1j * (Sigma_L - Sigma_L.conj().T)
        Gamma_R = 1j * (Sigma_R - Sigma_R.conj().T)

        # 图2：左右边界列已包含在 H_C 中，自能仅作用于这两侧界面。
        H_prime = H_C + embedded_self_energy(Sigma_L, 0) + embedded_self_energy(Sigma_R, 1)
        # 图3：(E I - H_prime) x_L/R = b_L/R。
        A = ENERGY * sparse.eye(H_C.shape[0], format="csr") - H_prime


        # step5 共用：图1的 Gamma = b b†，只保留引线的非零注入通道。

        C_L = KwantSolvers.lead_injection_vectors(Gamma_L, fsyst.lead_interfaces[0],
                                     self_energy=Sigma_L, system_size=A.shape[0])  # 图中的 b_L
        C_R = KwantSolvers.lead_injection_vectors(Gamma_R, fsyst.lead_interfaces[1],
                                     self_energy=Sigma_R, system_size=A.shape[0])  # 图中的 b_R
        left_channels, right_channels = C_L.shape[1], C_R.shape[1]
        injection_rhs = np.column_stack((C_L, C_R))
        if injection_rhs.shape[1] == 0:
            raise ValueError("当前能量没有传播通道，请在引线传播能带内选择 ENERGY")
        print(f"左/右注入通道数：{left_channels}/{right_channels}；"
              f"求解 {injection_rhs.shape[1]} 个右端向量，矩阵维数为 {A.shape[0]}。")


        print("step5: unitarylab QSVT 求解左右引线的注入方程")
        injection_responses, circuits, scaling_factor, epsilon, error = (
            KwantSolvers.solve_unitarylab(
                A, injection_rhs, inverse_tolerance=inverse_tolerance)
        )

        # 按左右通道拆分响应；实际线路残差独立于多项式误差报告。
        X_L = injection_responses[:, :left_channels]
        X_R = injection_responses[:, left_channels:]
        if not np.all(np.isfinite(injection_responses)):
            raise RuntimeError("引线注入响应出现非有限数值")
        injection_residuals = (np.linalg.norm(A @ injection_responses - injection_rhs, axis=0)
                               / np.linalg.norm(injection_rhs, axis=0))
        print(f"各注入方程 ||A @ x - b|| / ||b|| = {injection_residuals}")





        print("\n" + "=" * 80)
        print("step6: 显式 NEGF 计算透射率、电流和局域态密度, 并导出")
        print("=" * 80)

        transmission = np.linalg.norm(C_R.conj().T @ X_L, "fro")**2
        ldos = (np.sum(np.abs(X_L)**2, axis=1) + np.sum(np.abs(X_R)**2, axis=1)) / (2*np.pi)


        def current_on_bond(i, j):
            # (X_L X_L†)[j,i] = sum_a X_L[j,a] conj(X_L[i,a])。
            # 仅计算实际存在的键；保持原程序的电流方向、符号和单位约定。
            return 2 * np.imag(H_C[i, j] * np.vdot(X_L[i], X_L[j]))


        # 电流数组严格按照 fsyst.graph 的有向键顺序排列，可直接交给 Kwant 作图。
        bond_current = np.array([current_on_bond(i, j) for i, j in fsyst.graph])

        print(f"透射率 T = {transmission:.12f}")




        def export_ldos(fsyst, ldos, output_dir):
            """使用 Kwant 原生格点映射绘制 LDOS，返回 PNG 路径。"""
            fig = kwant.plotter.map(
                fsyst, ldos, cmap="Reds", oversampling=1,
                vmin=0, vmax=float(ldos.max()), show=False, fig_size=(5, 4.5),
            )
            fig.axes[0].set_title("LDOS")
            path = output_dir / "kwant_square_ldos.png"
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            return path


        def export_current(fsyst, bond_current, output_dir):
            """使用 Kwant 原生电流流线绘图，返回 PNG 路径。"""
            fig, ax = plt.subplots(figsize=(5, 4.5))
            kwant.plotter.current(
                fsyst, bond_current, relwidth=0.12,
                ax=ax, show=False, colorbar=False,
            )
            ax.set_title("Current")
            ax.set_aspect("equal")
            path = output_dir / "kwant_square_current.png"
            fig.savefig(path, dpi=200, bbox_inches="tight")
            plt.close(fig)
            return path




        ldos_path = export_ldos(fsyst, ldos, output_dir)
        current_path = export_current(fsyst, bond_current, output_dir)
        print(f"step6 LDOS 图片导出到：{ldos_path}")
        print(f"step6 Current 图片导出到：{current_path}")

        self.update_output({
            "ENERGY": float(ENERGY),
            "left_channels": left_channels,
            "right_channels": right_channels,
            "transmission": float(transmission),
            "injection_residuals": injection_residuals,
            "epsilon": epsilon,
            "inverse_polynomial_error": error,
            "scaling_factor": scaling_factor,
            "rhs_norms": np.linalg.norm(injection_rhs, axis=0),
            "system_size": A.shape[0],
        })
        # 保存实际执行的各注入线路；第一个通道使用框架的主线路字段。
        circuit_paths = []
        qasm_paths = []
        qasm_export_errors = []
        for j, circuit in enumerate(circuits):
            name = "negf_circuit" if j == 0 else f"negf_circuit_{j + 1}"
            circuit_path = self.save_circuit(circuit, name=name)
            circuit_paths.append(circuit_path)
            path = Path(circuit_path).with_suffix(".qasm")
            try:
                qasm = circuit.to_qasm2(transpile=True)
            except NotImplementedError as exc:
                qasm_export_errors.append({"circuit": name, "reason": str(exc)})
                self.log(f"  QASM2 未导出（{name}）：{exc}")
                continue
            path.write_text(qasm, encoding="utf-8")
            qasm_paths.append(str(path))
            self.log(f"  QASM2 circuit saved: {path}")

        self.update_output({"qasm_export_errors": qasm_export_errors})
        self.status = "success"
        self.summary = f"NEGF transport completed with transmission {transmission:.12f}."
        filename = self.save_txt()
        result = self._build_return_dict(
            True,
            circuit_paths[0],
            [filename, structure_path.name, ldos_path.name, current_path.name,
             *(Path(path).name for path in circuit_paths[1:]),
             *(Path(path).name for path in qasm_paths)],
            circuits[0],
        )
        for artifact in result["plot"]:
            if artifact["filename"].lower().endswith(".qasm"):
                artifact["format"] = "qasm"
        result.update({
            "ldos": ldos,
            "bond_current": bond_current,
            "circuits": circuits,
            "circuit_paths": circuit_paths,
            "qasm_paths": qasm_paths,
        })
        return result


def test(L: int = 4, W: int = 4, a: float = 1.0, t: float = 1.0,
         inverse_tolerance: float = 2e-3) -> Dict[str, Any]:
    algo = NEGFAlgorithm(text_mode="legacy")
    return algo.run(L=L, W=W, a=a, t=t, inverse_tolerance=inverse_tolerance)


if __name__ == "__main__":
    L = 4  # [PARAM]
    W = 4  # [PARAM]
    a = 1.0  # [PARAM]
    t = 1.0  # [PARAM]
    inverse_tolerance = 2e-3  # [PARAM]
    test(L=L, W=W, a=a, t=t, inverse_tolerance=inverse_tolerance)
