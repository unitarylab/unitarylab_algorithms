import time
import os
import numpy as np
import torch
import torch.nn as nn
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


class CVSimulator:
    """Continuous variable optical quantum simulator core based on truncated Fock space."""
    def __init__(self, cutoff_dim=6, device='cpu'):
        self.cutoff = cutoff_dim
        self.device = device
        a_data = np.zeros((cutoff_dim, cutoff_dim))
        for n in range(1, cutoff_dim):
            a_data[n-1, n] = np.sqrt(n)
        self.a = torch.tensor(a_data, dtype=torch.complex128).to(device)
        self.adag = self.a.T.conj()
        self.x_op = (self.a + self.adag) / np.sqrt(2)
        self.n_op = self.adag @ self.a
        self.vacuum = torch.zeros((cutoff_dim, 1), dtype=torch.complex128).to(device)
        self.vacuum[0, 0] = 1.0 + 0j

    def displacement(self, alpha):
        return torch.matrix_exp(alpha * self.adag - torch.conj(torch.as_tensor(alpha)) * self.a)

    def squeezing(self, z):
        return torch.matrix_exp(0.5 * (torch.conj(torch.as_tensor(z)) * (self.a @ self.a) - torch.as_tensor(z) * (self.adag @ self.adag)))

    def rotation(self, theta):
        return torch.matrix_exp(-1j * torch.as_tensor(theta) * self.n_op)

    def kerr(self, kappa):
        return torch.matrix_exp(1j * torch.as_tensor(kappa) * (self.n_op @ self.n_op))

class CVClassifier(nn.Module):
    """CV quantum classifier model."""
    def __init__(self, n_layers=2, cutoff=6):
        super().__init__()
        self.sim = CVSimulator(cutoff_dim=cutoff)
        self.n_layers = n_layers
        self.cutoff = cutoff
        self.sq_r = nn.Parameter(torch.randn(n_layers, 2) * 0.1)
        self.disp_r = nn.Parameter(torch.randn(n_layers, 2) * 0.1)
        self.rot_theta = nn.Parameter(torch.rand(n_layers, 2) * 2 * np.pi)
        self.kerr_k = nn.Parameter(torch.randn(n_layers, 2) * 0.05)
        self.bs_theta = nn.Parameter(torch.rand(n_layers) * np.pi)

    def forward(self, x_batch):
        outputs = []
        I = torch.eye(self.cutoff, dtype=torch.complex128)
        for i in range(x_batch.shape[0]):
            features = x_batch[i]
            st0 = self.sim.displacement(features[0]) @ self.sim.vacuum
            st1 = self.sim.displacement(features[1]) @ self.sim.vacuum
            curr_state = torch.kron(st0, st1)
            for L in range(self.n_layers):
                a0 = torch.kron(self.sim.a, I); adag0 = a0.conj().T
                a1 = torch.kron(I, self.sim.a); adag1 = a1.conj().T
                U_bs = torch.matrix_exp(self.bs_theta[L] * (adag0 @ a1 - a0 @ adag1))
                U0 = (self.sim.kerr(self.kerr_k[L,0]) @ self.sim.displacement(self.disp_r[L,0]) @ 
                      self.sim.squeezing(self.sq_r[L,0]) @ self.sim.rotation(self.rot_theta[L,0]))
                U1 = (self.sim.kerr(self.kerr_k[L,1]) @ self.sim.displacement(self.disp_r[L,1]) @ 
                      self.sim.squeezing(self.sq_r[L,1]) @ self.sim.rotation(self.rot_theta[L,1]))
                curr_state = torch.kron(U0, U1) @ U_bs @ curr_state
            x_exp = curr_state.conj().T @ torch.kron(self.sim.x_op, I) @ curr_state
            outputs.append(x_exp.real.squeeze())
        return torch.stack(outputs).view(-1, 1)

class CVQNNAlgorithm(BaseAlgorithm):
    """CVQNN Algorithm Module.

    This module implements continuous variable quantum neural network classification tasks.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="CVQNN Algorithm", prefix="CVQNN", text_mode=text_mode, algo_dir=algo_dir)

        torch.manual_seed(42)
        np.random.seed(42)
        torch.set_default_dtype(torch.float64)

    def _build_circuit(self, n_layers: int, n_modes: int = 2) -> Circuit:
        """Construct quantum circuit topology."""
        qc = Circuit(n_modes) 
        for m in range(n_modes):
            qc.ry(0.0, m) # Encoding layer
        for l in range(n_layers):
            qc.cx(0, 1) # Entanglement layer (BS)
            for m in range(n_modes):
                qc.rx(0.0, m) 
                qc.ry(0.0, m) 
                qc.rz(0.0, m) # Variational layer evolution combination
        return qc

    def run(self, x_train: np.ndarray, y_train: np.ndarray, 
            n_layers: int = 2, cutoff: int = 6, epochs: int = 40, 
            lr: float = 0.05) -> Dict[str, Any]:
        """Execute CVQNN training and evaluation process.

        Parameters:
            x_train: Input features
            y_train: Labels
            n_layers: Variational layer depth
            cutoff: Fock truncation dimension
            epochs: Training epochs
            lr: Learning rate
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Dimension of training data": x_train.shape, "Number of layers": n_layers, "Cutoff dimension": cutoff, "Epochs": epochs, "Learning rate": lr}
        self.update_input(input)

        total_start = time.time()

        self.log(f"Stage 1: Data preprocessing and model initialization")
        x_mean, x_std = x_train.mean(axis=0), x_train.std(axis=0)
        X_norm = (x_train - x_mean) / x_std
        x_tensor = torch.tensor(X_norm, dtype=torch.float64)
        y_tensor = torch.tensor(y_train, dtype=torch.float64).view(-1, 1)
        y_target = torch.where(y_tensor > 0.5, 1.0, -1.0) 

        model = CVClassifier(n_layers=n_layers, cutoff=cutoff)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        criterion = nn.MSELoss()

        self.log(f"Stage 2: Construct quantum phase space architecture")
        qc = self._build_circuit(n_layers)

        self.log(f"Stage 3: Variational gradient parameter optimization loop")
        loss_history = []
        
        q_comp_start = time.time()
        for e in range(1, epochs + 1):
            optimizer.zero_grad()
            preds = model(x_tensor)
            loss = criterion(preds, y_target)
            loss.backward()
            optimizer.step()
            loss_history.append(loss.item())
            if e % 10 == 0 or e == 1:
                self.log(f"  Epoch {e:03d}/{epochs} | Loss: {loss.item():.6f}")
        
        q_comp_time = time.time() - q_comp_start
        self.log(f"  Core quantum computation time: {q_comp_time:.4f} seconds")

        self.log(f"Stage 4: Classification decision boundary evaluation")
        with torch.no_grad():
            final_preds = model(x_tensor)
            final_acc = ((torch.where(final_preds > 0, 1.0, 0.0)) == y_tensor).float().mean().item()
        self.log(f"  Final accuracy (Acc): {final_acc:.2%}")

        self.log(f"Stage 5: Export analysis plots and circuit diagrams")

        output = {"Final Loss": loss_history[-1], "Final Accuracy": final_acc, "Total Computation Time (s)": time.time() - total_start}
        self.update_output(output)
        self.status = "success"
        self.summary = f"CVQNN completed with final loss {loss_history[-1]:.6f} and accuracy {final_acc:.2%} in {time.time() - total_start:.2f} seconds."

        circuit_path = self.save_circuit(qc)
        filename = self._generate_metrics_plots(X_norm, y_train, model, loss_history, final_acc, self.algo_dir)
        self.log(f"  Metrics plots saved to: {filename}")
        return self._build_return_dict(True, circuit_path, filename, qc)

    def _generate_metrics_plots(self, X_norm, y_train, model, history, acc, algo_dir):
        p_metrics = os.path.abspath(os.path.join(algo_dir, "CVQNN_Metrics.svg"))
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        ax1.plot(history, color='#e74c3c', lw=2); ax1.set_title("Training Loss"); ax1.set_xlabel("Epochs")
        grid_res = 15
        x_min, x_max = X_norm[:, 0].min()-0.5, X_norm[:, 0].max()+0.5
        y_min, y_max = X_norm[:, 1].min()-0.5, X_norm[:, 1].max()+0.5
        xx, yy = np.meshgrid(np.linspace(x_min, x_max, grid_res), np.linspace(y_min, y_max, grid_res))
        with torch.no_grad():
            pts = torch.tensor(np.c_[xx.ravel(), yy.ravel()], dtype=torch.float64)
            zz = model(pts).view(xx.shape).numpy()
        ax2.contourf(xx, yy, zz, levels=20, cmap="RdBu", alpha=0.8)
        ax2.scatter(X_norm[:, 0], X_norm[:, 1], c=y_train, cmap="RdBu_r", edgecolors='k')
        ax2.set_title(f"Decision Boundary (Acc: {acc:.2%})")
        plt.tight_layout(); fig.savefig(p_metrics); plt.close(fig)
        return p_metrics


def test(n_layers=2, cutoff=6, epochs=30, lr=0.05):
    """Execute CVQNN training and evaluation process.

    Parameters:
        n_layers: Variational layer depth
        cutoff: Fock truncation dimension
        epochs: Training epochs
        lr: Learning rate
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    try:
        from sklearn.datasets import make_moons
        X, y = make_moons(n_samples=40, noise=0.1, random_state=42)
    except ImportError:
        print("Please install scikit-learn to run the test: pip install scikit-learn")
        X = [[-1.02933991, -0.00298386],
       [-0.86996117,  0.54241283],
       [-0.80316236,  0.61089337],
       [ 0.37814419, -0.41500468],
       [ 0.8840248 ,  0.77229777],
       [-0.43851252,  0.95332979],
       [ 1.82650142,  0.13439534],
       [ 0.55363043, -0.26334916],
       [ 2.03229998,  0.36065831],
       [ 0.32911473,  0.73277684],
       [ 0.3399878 , -0.20330403],
       [ 0.1571653 ,  0.81292617],
       [-0.49050173,  0.83971655],
       [ 1.29280481, -0.40348121],
       [ 1.91135621, -0.12862539],
       [ 0.25512714,  1.01131048],
       [-1.04112002,  0.21991241],
       [ 0.02329181, -0.25089093],
       [ 1.06363051, -0.09067207],
       [ 1.59455242, -0.20680035],
       [ 0.69844027,  0.79542838],
       [-0.33511901,  0.95820148],
       [ 1.13325543,  0.05220476],
       [ 1.01242119, -0.32393285],
       [ 0.0594272 ,  0.16697667],
       [ 0.97850176,  0.31658757],
       [ 1.12935882, -0.42297226],
       [ 1.80150356, -0.06033703],
       [ 0.86442037,  0.37939163],
       [ 1.80418942, -0.12555484],
       [ 0.38387907, -0.07845648],
       [ 1.32349064, -0.37337902],
       [ 0.00469116,  1.22530709],
       [ 0.21647481,  0.25767384],
       [-0.95705538,  0.25425763],
       [-0.0610322 ,  0.46838341],
       [ 0.253453  ,  0.89288858],
       [-0.58101744,  0.71475467],
       [ 0.67711022, -0.50537808],
       [ 2.05876963,  0.30982895]]
        y = [0, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0,
       0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1]
        X = np.array(X)
        y = np.array(y)


    algo = CVQNNAlgorithm(text_mode="legacy")
    result = algo.run(x_train=X, y_train=y, n_layers=n_layers, cutoff=cutoff, epochs=epochs, lr=lr)
    return result


if __name__ == "__main__":
    layers = 2    # [PARAM]
    cutoff = 6      # [PARAM]
    epochs = 40     # [PARAM]
    lr = 0.05       # [PARAM]
    test(n_layers=layers, cutoff=cutoff, epochs=epochs, lr=lr)