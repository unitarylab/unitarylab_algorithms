import time
import os
import numpy as np
import torch
import matplotlib.pyplot as plt
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


class QCBMAlgorithm(BaseAlgorithm):
    """QCBM Algorithm Module.

    This module implements Quantum Circuit Born Machine for learning and modeling discrete probability distributions.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="QCBM Algorithm", prefix="QCBM", text_mode=text_mode, algo_dir=algo_dir)

        torch.manual_seed(42)
        np.random.seed(42)
        torch.set_default_dtype(torch.float64)

    def run(self, n: int = 4, layers: int = 4, epochs: int = 40, 
            lr: float = 0.1) -> Dict[str, Any]:
        """Execute the QCBM training workflow.

        Parameters:
            n: Number of qubits
            layers: Variational layer depth
            epochs: Number of training iterations
            lr: Adam optimizer learning rate
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Number of qubits": n, "Variational layer depth": layers, "Training epochs": epochs, "Learning rate": lr}
        self.update_input(input)

        total_start = time.time()
        self.log(f"Stage 1: Preparing BAS target distribution and parameter space")
        target_probs, valid_states = self._get_bas_dist(n)
        theta = torch.nn.Parameter(torch.rand((layers, n)) * 2 * np.pi)
        optimizer = torch.optim.Adam([theta], lr=lr)
        shift = np.pi / 2
        self.log(f"  State space dimension: 2^{n} = {2**n}")

        self.log(f"Stage 2: Mapping variational quantum operator sequence")
        qc_draw = self._build_circuit(theta.detach(), n)

        self.log(f"Stage 3: Parameter Shift gradient optimization loop")
        loss_history = []
        
        q_comp_start = time.time()
        for ep in range(1, epochs + 1):
            curr_probs = self._get_probs(theta.detach(), n)
            eps = 1e-12
            loss_val = torch.sum(target_probs * torch.log((target_probs + eps) / (curr_probs + eps)))
            loss_history.append(loss_val.item())

            grad_theta = torch.zeros_like(theta)
            for l in range(layers):
                for q in range(n):
                    th_p = theta.detach().clone(); th_p[l, q] += shift
                    th_m = theta.detach().clone(); th_m[l, q] -= shift
                    p_p = self._get_probs(th_p, n)
                    p_m = self._get_probs(th_m, n)
                    grad_p = 0.5 * (p_p - p_m)
                    grad_theta[l, q] = torch.sum(-(target_probs / (curr_probs + eps)) * grad_p)

            optimizer.zero_grad()
            theta.grad = grad_theta
            optimizer.step()
            
            if ep % 10 == 0 or ep == 1:
                self.log(f"  Epoch [{ep:03d}/{epochs}] | KL Loss: {loss_val.item():.6f}")
        
        q_comp_time = time.time() - q_comp_start
        self.log(f"  Core quantum computation time: {q_comp_time:.4f} seconds")

        self.log(f"Stage 4: Evaluating probability fidelity under optimal parameters")
        with torch.no_grad():
            final_probs = self._get_probs(theta, n).cpu().numpy()

        self.log(f"Stage 5: Exporting analysis plots")

        output = {"Final KL Loss": loss_history[-1], "Quantum Computation Time": q_comp_time}
        self.update_output(output)
        self.status = "success"
        self.summary = f"QCBM trained for {epochs} epochs with final KL Loss {loss_history[-1]:.6f} in {q_comp_time:.4f} seconds."

        circuit_path = self.save_circuit(qc_draw)

        paths = self._generate_all_outputs(n, target_probs.numpy(), final_probs, loss_history, self.algo_dir)
        self.log(f"  Results saved to: {paths}")
        return self._build_return_dict(True, circuit_path, paths, qc_draw)

    def _generate_all_outputs(self, n, target, final, history, algo_dir):
        """Generate and save convergence, distribution, and sampling plots."""
        paths = []
        # 1. Loss curve
        p_loss = os.path.abspath(os.path.join(algo_dir, "QCBM_Loss.svg"))
        plt.figure(figsize=(6, 4)); plt.plot(history, color='#e67e22', lw=2)
        plt.title("QCBM KL Loss Convergence"); plt.savefig(p_loss); plt.close()
        paths.append(p_loss)

        # 2. Distribution comparison
        p_dist = os.path.abspath(os.path.join(algo_dir, "QCBM_Distribution.svg"))
        plt.figure(figsize=(10, 5)); x = np.arange(len(target))
        plt.bar(x - 0.2, target, 0.4, label='Target', alpha=0.4)
        plt.bar(x + 0.2, final, 0.4, label='QCBM Learned', color='#3498db')
        plt.legend(); plt.savefig(p_dist); plt.close()
        paths.append(p_dist)

        # 3. Sampling patterns (structured grid)
        p_samples = os.path.abspath(os.path.join(algo_dir, "QCBM_Samples.svg"))
        samples = np.random.choice(np.arange(len(final)), size=12, p=final/final.sum())
        fig = plt.figure(figsize=(15, 5))
        for i, s in enumerate(samples):
            ax = fig.add_subplot(3, 4, i+1)
            grid = np.array([int(b) for b in f"{int(s):0{n}b}"]).reshape(int(np.sqrt(n)), -1)
            ax.imshow(grid, cmap='binary', vmin=0, vmax=1, interpolation='nearest')
            ax.set_xticks(np.arange(-.5, 2, 1), minor=True); ax.set_yticks(np.arange(-.5, 2, 1), minor=True)
            ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5)
            ax.set_xticks([]); ax.set_yticks([]); ax.set_title(f"State: {s}")
        plt.tight_layout(); plt.savefig(p_samples); plt.close()
        paths.append(p_samples)
        return paths

    def _get_bas_dist(self, n):
        valid = [0, 3, 5, 10, 12, 15]
        probs = np.zeros(2**n)
        probs[valid] = 1.0 / len(valid)
        return torch.from_numpy(probs), valid

    def _build_circuit(self, theta, n) -> Circuit:
        qc = Circuit(n)
        for l in range(theta.shape[0]):
            for q in range(n): qc.ry(float(theta[l, q]), q)
            if l < theta.shape[0] - 1:
                for q in range(n): qc.cx(q, (q + 1) % n)
        return qc

    def _get_probs(self, theta, n):
        qc = self._build_circuit(theta, n)
        state0 = np.zeros((2**n, 1), dtype=np.complex128); state0[0,0] = 1.0
        final_state = qc.execute(initial_state=state0).state
        return torch.as_tensor(np.abs(np.asarray(final_state).flatten())**2)

def test(n=4, layers=4, epochs=40, lr=0.1):
    """Execute the QCBM training workflow.

    Parameters:
        n: Number of qubits
        layers: Variational layer depth
        epochs: Number of training iterations
        lr: Adam optimizer learning rate
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    algo = QCBMAlgorithm(text_mode="legacy")
    result = algo.run(n=n, layers=layers, epochs=epochs, lr=lr)
    return result


if __name__ == "__main__":
    n = 4  # [PARAM]
    layers = 4  # [PARAM]
    epochs = 40   # [PARAM]
    lr = 0.1      # [PARAM]
    test(n=n, layers=layers, epochs=epochs, lr=lr)