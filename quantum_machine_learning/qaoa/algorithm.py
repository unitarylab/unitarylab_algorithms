import time
import os
import numpy as np
import torch
import matplotlib.pyplot as plt
import networkx as nx
from scipy.optimize import minimize
from typing import Dict, Any, List

from unitarylab import Circuit
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class QAOAAlgorithm(BaseAlgorithm):
    """QAOA Algorithm Module.

    This module implements the Quantum Approximate Optimization Algorithm for solving Max-Cut problems.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="QAOA Algorithm", prefix="QAOA", text_mode=text_mode, algo_dir=algo_dir)
        np.random.seed(42)
        torch.manual_seed(42)

    def _get_h_cost(self, edges: List, n_qubits: int):
        dim = 2**n_qubits
        h_c = np.zeros((dim, dim), dtype=np.complex128)
        z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
        i_mat = np.eye(2, dtype=np.complex128)
        for u, v in edges:
            operators = [i_mat] * n_qubits
            operators[u] = z
            operators[v] = z
            res = operators[0]
            for k in range(1, n_qubits):
                res = np.kron(res, operators[k])
            h_c += res
        return h_c

    def _build_circuit(self, params: np.ndarray, n_qubits: int, edges: List) -> Circuit:
        """Build the variational circuit."""
        p = len(params) // 2
        gammas, betas = params[:p], params[p:]
        
        qc = Circuit(n_qubits)
        for i in range(n_qubits): qc.h(i)
        for i in range(p):
            for u, v in edges:
                u, v = int(u), int(v)
                qc.cx(u, v)
                qc.rz(2 * gammas[i], v)
                qc.cx(u, v)
            for j in range(n_qubits): 
                qc.rx(2 * betas[i], j)
        return qc

    def run(self, edges: List = None, n: int = 6, layers: int = 4, 
            max_iter: int = 100) -> Dict[str, Any]:
        """Execute the QAOA training workflow.

        Parameters:
            edges: List of edges
            n: Number of qubits
            layers: Number of evolution layers
            max_iter: Maximum iterations for the optimizer

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Max-Cut Edges": len(edges), "Number of qubits": n, "Number of layers": layers, "Max Iterations": max_iter}
        self.update_input(input)

        total_start = time.time()
        
        if edges is None:
            edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 5)]

        self.log(f"Stage 1: Initializing Hamiltonian matrix and parameter space")
        h_cost = self._get_h_cost(edges, n)
        exact_energy = float(np.linalg.eigvalsh(h_cost)[0])
        initial_params = np.random.uniform(0, np.pi, 2 * layers)

        self.log(f"Stage 2: Mapping quantum circuit evolution architecture")
        qc_draw = self._build_circuit(initial_params, n, edges)

        self.log(f"Stage 3: Variational parameter optimization (COBYLA)")
        history = []
        q_comp_start = time.time()
        
        def obj_func(p_flat):
            qc = self._build_circuit(p_flat, n, edges)
            psi_out = qc.execute(initial_state=np.eye(2**n, 1, dtype=np.complex128)).state
            
            # Compatibility handling: convert backend output to numpy array for energy calculation
            psi = np.asarray(psi_out)
            energy = np.real(psi.conj().T @ h_cost @ psi).item()
            history.append(energy)
            return energy

        opt_res = minimize(obj_func, x0=initial_params, method='COBYLA', options={'maxiter': max_iter})
        
        q_comp_time = time.time() - q_comp_start
        self.log(f"  Core quantum computation time: {q_comp_time:.4f} seconds")
        self.log(f"  Final optimized energy: {opt_res.fun:.6f}")

        self.log(f"Stage 4: Optimal state measurement and bitstring decoding")
        qc_final = self._build_circuit(opt_res.x, n, edges)
        final_psi_out = qc_final.execute(initial_state=np.eye(2**n, 1, dtype=np.complex128)).state
        final_psi = np.asarray(final_psi_out)
        
        best_idx = int(np.argmax(np.abs(final_psi.flatten())**2))
        best_bits = format(best_idx, f"0{n}b")
        maxcut_val = len([(u, v) for u, v in edges if best_bits[u] != best_bits[v]])

        self.log(f"Stage 5: Exporting analysis plots")
        output = {"Optimal bitstring": best_bits, "Max-Cut Value": maxcut_val, "Optimized Energy": opt_res.fun, "Quantum Computation Time": q_comp_time}
        self.update_output(output)
        self.status = "success"
        self.summary = f"QAOA found bitstring {best_bits} with Max-Cut value {maxcut_val} (Exact: {exact_energy:.6f}, Optimized: {opt_res.fun:.6f}) in {q_comp_time:.4f} seconds."

        circuit_path, paths = self._generate_outputs(edges, best_bits, history, qc_draw, n, self.algo_dir)
        self.log(f'    Circuit diagram saved to: {circuit_path}')
        self.log(f'    Convergence plot saved to: {paths}')
        return self._build_return_dict(True, circuit_path, paths, qc_draw)

    def _generate_outputs(self, edges, best_bits, history, qc_draw, n_qubits, algo_dir):
        paths = []
        p_circ = os.path.abspath(os.path.join(algo_dir, "QAOA_Circuit.svg"))
        qc_draw.draw(filename=p_circ);
        p_loss = os.path.abspath(os.path.join(algo_dir, "QAOA_Convergence.svg"))
        plt.figure(figsize=(6, 4)); plt.plot(history, color='#3498db', lw=2)
        plt.title("Energy Convergence"); plt.savefig(p_loss); plt.close(); paths.append(p_loss)
        p_res = os.path.abspath(os.path.join(algo_dir, "MaxCut_Solution.svg"))
        g = nx.Graph(); g.add_edges_from(edges)
        colors = ["#3498db" if best_bits[i] == "0" else "#e74c3c" for i in range(n_qubits)]
        plt.figure(figsize=(8, 6)); pos = nx.spring_layout(g)
        nx.draw(g, pos, node_color=colors, with_labels=True, node_size=800, font_color='white')
        plt.savefig(p_res); plt.close(); paths.append(p_res)
        return p_circ, paths


def test(edges = [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [1, 5]], n = 6, layers = 4, max_iter = 60):
    """Execute the QAOA training workflow.

    Parameters:
        edges: List of edges
        n: Number of qubits
        layers: Number of evolution layers
        max_iter: Maximum iterations for the optimizer

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    edges = np.array(edges)

    algo = QAOAAlgorithm(text_mode="legacy")
    result = algo.run(edges=edges, n=n, layers=layers, max_iter=max_iter)

    return result


if __name__ == "__main__":
    edges = [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [1, 5]]  # [PARAM]
    n = 6    # [PARAM]
    layers = 4    # [PARAM]
    max_iter = 100  # [PARAM]
    test(edges=edges, n=n, layers=layers, max_iter=max_iter)