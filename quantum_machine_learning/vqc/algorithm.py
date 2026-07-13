import time
import os
import numpy as np
import torch
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, TensorDataset
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


class VQCAlgorithm(BaseAlgorithm):
    """VQC Algorithm Module.

    This module implements Variational Quantum Classifier for Iris dataset classification.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="VQC Algorithm", prefix="VQC", text_mode=text_mode, algo_dir=algo_dir)

        self.backend = 'torch'
        self.device = 'cpu'
        self.dtype = np.complex128

        torch.manual_seed(42)
        np.random.seed(42)
        torch.set_default_dtype(torch.float64)

    def run(self, layers: int = 3, epochs: int = 20, lr: float = 0.05, 
            batch_size: int = 16, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute the VQC training and evaluation workflow.

        Parameters:
            layers: Variational layer depth
            epochs: Number of training iterations
            lr: Adam optimizer learning rate
            batch_size: Training batch size
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """
        self.backend = backend
        self.device = device
        self.dtype = dtype
        
        input = {"Variational Layers": layers, "Epochs": epochs, "Learning Rate": lr, "Batch Size": batch_size}
        self.update_input(input)

        self.log(f"Stage 1: Loading Iris dataset and initializing variational parameters")
        x_train, y_train, x_test, y_test = self._load_iris_data()
        train_loader = DataLoader(TensorDataset(x_train, y_train), batch_size=batch_size, shuffle=True)
        
        n_qubits = 4
        theta = torch.nn.Parameter(torch.rand((n_qubits, layers)) * 2 * np.pi)
        optimizer = torch.optim.Adam([theta], lr=lr)
        criterion = torch.nn.CrossEntropyLoss()
        shift = np.pi / 2
        self.log(f"  Dataset size: {len(x_train)} training samples | {len(x_test)} test samples")

        self.log(f"Stage 2: Mapping quantum observables and logits logic")
        observables = [self._get_observable(i, n_qubits) for i in range(1, 4)]
        qc_draw = self._build_circuit(x_train[0], theta.detach())

        self.log(f"Stage 3: Starting variational parameter training loop")
        loss_history = []
        acc_history = []
        
        q_comp_start = time.time()
        
        for ep in range(1, epochs + 1):
            epoch_loss = 0.0
            for xb, yb in train_loader:
                theta_base = theta.detach().clone()
                grad_theta = torch.zeros_like(theta_base)
                for i in range(theta_base.shape[0]):
                    for j in range(theta_base.shape[1]):
                        th_p, th_m = theta_base.clone(), theta_base.clone()
                        th_p[i, j] += shift; th_m[i, j] -= shift
                        
                        loss_p = criterion(10 * self._get_batch_logits(xb, th_p, observables), yb)
                        loss_m = criterion(10 * self._get_batch_logits(xb, th_m, observables), yb)
                        grad_theta[i, j] = (loss_p - loss_m) * 0.5
                
                optimizer.zero_grad()
                theta.grad = grad_theta
                optimizer.step()
                
                with torch.no_grad():
                    logits = self._get_batch_logits(xb, theta, observables)
                    epoch_loss += criterion(10 * logits, yb).item() * xb.size(0)
            
            avg_loss = epoch_loss / len(x_train)
            loss_history.append(avg_loss)
            acc_history.append(self._evaluate(x_test, y_test, theta, observables))
            
            if ep % 5 == 0 or ep == 1:
                self.log(f"  Epoch {ep:02d}/{epochs} | Loss: {avg_loss:.4f} | Test Acc: {acc_history[-1]:.2%}")
        
        q_comp_time = time.time() - q_comp_start
        self.log(f"  Core quantum computation time: {q_comp_time:.4f} seconds")

        self.log(f"Stage 4: Final model performance statistics")
        final_acc = acc_history[-1]

        self.log(f"Stage 5: Exporting analysis plots and circuit diagrams")

        output = {"Final Loss": loss_history[-1], "Final Accuracy": final_acc, "Quantal Computation Time (s)": q_comp_time}
        self.update_output(output)
        self.status = "success"
        self.summary = f"Trained VQC with {layers} layers for {epochs} epochs. Final Loss: {loss_history[-1]:.4f}, Final Accuracy: {final_acc:.2%}, Quantum Comp Time: {q_comp_time:.4f}s"

        circuit_path = self.save_circuit(qc_draw)

        filename = self._generate_all_plots(loss_history, acc_history, self.algo_dir)
        self.log(f"  Results saved to: {filename}")
        return self._build_return_dict(True, circuit_path, filename, qc_draw)

    def _load_iris_data(self):
        try:
            from sklearn.datasets import load_iris
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            iris = load_iris()
            X = StandardScaler().fit_transform(iris["data"])
            # Feature mapping to [-pi/2, pi/2]
            X = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0) + 1e-12) * np.pi - np.pi/2
            xt, xv, yt, yv = train_test_split(X, iris["target"], test_size=0.2, stratify=iris["target"])
        except ImportError:
            xt, xv, yt, yv = dataset_xt, dataset_xv, dataset_yt, dataset_yv
        return torch.tensor(xt), torch.tensor(yt), torch.tensor(xv), torch.tensor(yv)

    def _get_observable(self, target, total):
        I = torch.eye(2, dtype=torch.complex128)
        Z = torch.tensor([[1, 0], [0, -1]], dtype=torch.complex128)
        op = Z if target == 0 else I
        for i in range(1, total):
            op = torch.kron(op, Z if i == target else I)
        return op

    def _build_circuit(self, x, theta) -> Circuit:
        qc = Circuit(4)
        for q in range(4): qc.ry(float(x[q]), q) # Encoding
        for l in range(theta.shape[1]):
            for q in range(4): qc.ry(float(theta[q, l]), q) # Variational
            if l < theta.shape[1] - 1:
                for q in range(4): qc.cx(q, (q + 1) % 4) # Entanglement
        return qc

    def _get_batch_logits(self, x_batch, theta, observables):
        all_logits = []
        for x in x_batch:
            qc = self._build_circuit(x, theta)
            psi_out = qc.execute(backend=self.backend, device=self.device, dtype=self.dtype).state
            psi = torch.as_tensor(psi_out).to(torch.complex128)
            bra = psi.conj().t()
            logits = [ (bra @ op @ psi).real.squeeze() for op in observables ]
            all_logits.append(torch.stack(logits))
        return torch.stack(all_logits)

    @torch.no_grad()
    def _evaluate(self, x, y, theta, obs):
        logits = self._get_batch_logits(x, theta, obs)
        return (torch.argmax(logits, dim=1) == y).float().mean().item()

    def _generate_all_plots(self, loss_h, acc_h, algo_dir):
        p_metrics = os.path.abspath(os.path.join(algo_dir, "VQC_Metrics.svg"))
        fig, ax1 = plt.subplots(figsize=(8, 5))
        ax1.plot(loss_h, color='#e74c3c', lw=2, label='Loss')
        ax1.set_ylabel('CrossEntropy Loss', color='#e74c3c')
        ax2 = ax1.twinx()
        ax2.plot(acc_h, color='#2ecc71', lw=2, label='Accuracy')
        ax2.set_ylabel('Test Accuracy', color='#2ecc71')
        plt.title("VQC Training Progress"); fig.tight_layout()
        fig.savefig(p_metrics); plt.close(fig); 
        return p_metrics

    
dataset_xt = [[-8.72664626e-02,  2.61799388e-01,  2.92860332e-01,
    3.92699082e-01],
[ 1.39626340e+00,  7.85398163e-01,  1.46430166e+00,
    1.17809725e+00],
[-3.49065850e-01, -3.92699082e-01,  1.33118333e-01,
-4.97157870e-13],
[ 1.74532925e-01, -3.92699082e-01,  8.78580996e-01,
    6.54498469e-01],
[-2.61799388e-01, -6.54498469e-01,  6.12344331e-01,
    7.85398163e-01],
[-1.13446401e+00, -2.61799388e-01, -1.35780699e+00,
-1.30899694e+00],
[ 5.23598776e-01,  1.30899694e-01,  9.31828329e-01,
    1.57079633e+00],
[-1.48352986e+00, -2.84217094e-13, -1.41105433e+00,
-1.43989663e+00],
[ 5.23598776e-01, -1.30899694e-01,  3.99354998e-01,
    2.61799388e-01],
[-9.59931089e-01,  5.23598776e-01, -1.35780699e+00,
-1.43989663e+00],
[ 3.49065850e-01, -2.61799388e-01,  9.85075663e-01,
    1.17809725e+00],
[-8.72664626e-02, -6.54498469e-01,  6.12344331e-01,
    3.92699082e-01],
[ 2.61799388e-01, -5.23598776e-01,  8.78580996e-01,
    1.04719755e+00],
[ 6.10865238e-01, -2.84217094e-13,  1.03832300e+00,
    1.30899694e+00],
[-7.85398163e-01,  1.17809725e+00, -1.30455966e+00,
-1.57079633e+00],
[-9.59931089e-01,  3.92699082e-01, -1.25131233e+00,
-9.16297857e-01],
[ 1.74532925e-01, -5.23598776e-01,  6.12344331e-01,
    2.61799388e-01],
[-1.04719755e+00, -1.04719755e+00, -3.46107665e-01,
-3.92699082e-01],
[-7.85398163e-01, -6.54498469e-01, -2.66236666e-02,
    1.30899694e-01],
[ 5.23598776e-01, -1.30899694e-01,  8.78580996e-01,
    1.43989663e+00],
[-8.72664626e-01,  3.92699082e-01, -1.35780699e+00,
-1.43989663e+00],
[-6.10865238e-01, -2.61799388e-01,  2.92860332e-01,
    2.61799388e-01],
[-9.59931089e-01,  3.92699082e-01, -1.41105433e+00,
-1.30899694e+00],
[ 5.23598776e-01, -9.16297857e-01,  9.85075663e-01,
    6.54498469e-01],
[ 5.23598776e-01, -2.61799388e-01,  5.59096998e-01,
    5.23598776e-01],
[ 8.72664626e-02, -3.92699082e-01,  1.86365666e-01,
-4.97157870e-13],
[ 2.61799388e-01, -2.84217094e-13,  2.92860332e-01,
    2.61799388e-01],
[-8.72664626e-01,  1.30899694e-01, -1.19806500e+00,
-1.04719755e+00],
[-4.36332313e-01, -5.23598776e-01,  5.05849665e-01,
    9.16297857e-01],
[-1.13446401e+00, -1.30899694e-01, -1.25131233e+00,
-1.43989663e+00],
[-1.22173048e+00, -2.84217094e-13, -1.41105433e+00,
-1.43989663e+00],
[ 3.49065850e-01, -5.23598776e-01,  3.46107665e-01,
    2.61799388e-01],
[-8.72664626e-01,  6.54498469e-01, -1.30455966e+00,
-1.17809725e+00],
[-1.04719755e+00, -2.61799388e-01, -1.35780699e+00,
-1.43989663e+00],
[ 9.59931089e-01, -2.61799388e-01,  9.85075663e-01,
    3.92699082e-01],
[-4.36332313e-01, -2.61799388e-01,  2.92860332e-01,
    2.61799388e-01],
[-5.23598776e-01, -7.85398163e-01,  2.39612999e-01,
-1.30899694e-01],
[-3.49065850e-01, -5.23598776e-01,  7.98709997e-02,
-4.97157870e-13],
[ 8.72664626e-02, -5.23598776e-01,  4.52602331e-01,
    6.54498469e-01],
[ 1.57079633e+00,  7.85398163e-01,  1.30455966e+00,
    9.16297857e-01],
[-3.60378394e-13, -3.92699082e-01,  3.99354998e-01,
    1.30899694e-01],
[ 5.23598776e-01,  1.30899694e-01,  9.31828329e-01,
    1.04719755e+00],
[ 1.74532925e-01, -6.54498469e-01,  5.05849665e-01,
    6.54498469e-01],
[ 4.36332313e-01, -2.61799388e-01,  2.39612999e-01,
    1.30899694e-01],
[-1.04719755e+00, -1.30899694e-01, -1.30455966e+00,
-1.43989663e+00],
[-6.10865238e-01,  2.61799388e-01, -1.19806500e+00,
-1.43989663e+00],
[-2.61799388e-01, -6.54498469e-01,  7.98709997e-02,
-3.92699082e-01],
[-4.36332313e-01, -3.92699082e-01, -1.86365666e-01,
-4.97157870e-13],
[-2.61799388e-01,  1.04719755e+00, -1.46430166e+00,
-1.43989663e+00],
[ 1.74532925e-01,  1.30899694e-01,  1.09157033e+00,
    1.57079633e+00],
[-5.23598776e-01, -1.04719755e+00, -1.33118333e-01,
-3.92699082e-01],
[-1.13446401e+00,  2.61799388e-01, -1.25131233e+00,
-1.43989663e+00],
[-9.59931089e-01, -2.61799388e-01, -1.25131233e+00,
-1.43989663e+00],
[-8.72664626e-01,  7.85398163e-01, -1.25131233e+00,
-1.43989663e+00],
[ 2.61799388e-01, -1.30899694e-01,  8.25333663e-01,
    6.54498469e-01],
[ 5.23598776e-01, -2.61799388e-01,  6.65591664e-01,
    1.30899694e+00],
[-5.23598776e-01, -1.17809725e+00,  2.66236666e-02,
-4.97157870e-13],
[-1.13446401e+00, -2.61799388e-01, -1.35780699e+00,
-1.57079633e+00],
[ 2.61799388e-01, -3.92699082e-01,  1.86365666e-01,
-4.97157870e-13],
[-6.10865238e-01,  6.54498469e-01, -1.30455966e+00,
-1.43989663e+00],
[ 2.61799388e-01, -5.23598776e-01,  8.78580996e-01,
    1.17809725e+00],
[-2.61799388e-01, -6.54498469e-01, -2.66236666e-02,
-1.30899694e-01],
[ 5.23598776e-01, -1.30899694e-01,  2.39612999e-01,
    1.30899694e-01],
[-6.10865238e-01,  9.16297857e-01, -1.41105433e+00,
-1.17809725e+00],
[-8.72664626e-02, -1.30899694e+00,  5.59096998e-01,
    2.61799388e-01],
[-7.85398163e-01,  2.61799388e-01, -1.35780699e+00,
-1.43989663e+00],
[-8.72664626e-01,  3.92699082e-01, -1.35780699e+00,
-1.30899694e+00],
[-6.98131701e-01,  6.54498469e-01, -1.30455966e+00,
-1.43989663e+00],
[ 6.98131701e-01, -2.84217094e-13,  9.31828329e-01,
    1.30899694e+00],
[ 3.49065850e-01, -2.61799388e-01,  8.25333663e-01,
    6.54498469e-01],
[ 1.13446401e+00, -5.23598776e-01,  1.14481766e+00,
    7.85398163e-01],
[-4.36332313e-01, -6.54498469e-01,  1.33118333e-01,
-4.97157870e-13],
[ 9.59931089e-01, -2.84217094e-13,  1.09157033e+00,
    6.54498469e-01],
[-9.59931089e-01,  2.61799388e-01, -1.30455966e+00,
-1.43989663e+00],
[-8.72664626e-02, -2.61799388e-01,  4.52602331e-01,
    6.54498469e-01],
[ 2.61799388e-01, -2.84217094e-13,  7.18838997e-01,
    1.30899694e+00],
[ 4.36332313e-01, -3.92699082e-01,  3.46107665e-01,
-4.97157870e-13],
[-1.04719755e+00,  5.23598776e-01, -1.35780699e+00,
-1.57079633e+00],
[-5.23598776e-01,  3.92699082e-01, -1.41105433e+00,
-1.43989663e+00],
[-4.36332313e-01, -2.61799388e-01,  7.98709997e-02,
-4.97157870e-13],
[ 6.98131701e-01, -1.30899694e-01,  6.12344331e-01,
    1.30899694e+00],
[-6.10865238e-01,  2.61799388e-01, -1.30455966e+00,
-1.17809725e+00],
[-9.59931089e-01, -1.57079633e+00, -2.39612999e-01,
-3.92699082e-01],
[ 8.72664626e-02,  2.61799388e-01,  7.72086330e-01,
    1.30899694e+00],
[ 2.61799388e-01, -6.54498469e-01,  7.18838997e-01,
    7.85398163e-01],
[-8.72664626e-01,  7.85398163e-01, -1.09157033e+00,
-1.17809725e+00],
[-3.49065850e-01, -2.61799388e-01,  1.33118333e-01,
-1.30899694e-01],
[-1.74532925e-01, -2.61799388e-01,  6.12344331e-01,
    6.54498469e-01],
[ 1.74532925e-01, -9.16297857e-01,  5.59096998e-01,
    7.85398163e-01],
[-3.60378394e-13, -7.85398163e-01,  8.78580996e-01,
    1.30899694e-01],
[ 1.74532925e-01, -1.17809725e+00,  2.39612999e-01,
-4.97157870e-13],
[-3.60378394e-13, -5.23598776e-01,  2.66236666e-02,
-4.97157870e-13],
[-6.10865238e-01,  9.16297857e-01, -1.19806500e+00,
-1.17809725e+00],
[-1.57079633e+00, -2.61799388e-01, -1.51754899e+00,
-1.57079633e+00],
[-1.04719755e+00, -1.30899694e-01, -1.30455966e+00,
-1.57079633e+00],
[-3.49065850e-01,  7.85398163e-01, -1.19806500e+00,
-1.30899694e+00],
[-5.23598776e-01, -9.16297857e-01,  2.66236666e-02,
-4.97157870e-13],
[ 1.74532925e-01, -9.16297857e-01,  5.05849665e-01,
    2.61799388e-01],
[ 1.74532925e-01,  1.30899694e-01,  3.99354998e-01,
    3.92699082e-01],
[-9.59931089e-01,  1.30899694e-01, -1.35780699e+00,
-1.43989663e+00],
[ 3.49065850e-01, -2.61799388e-01,  6.65591664e-01,
    9.16297857e-01],
[-3.60378394e-13, -2.61799388e-01,  3.46107665e-01,
    1.30899694e-01],
[-1.48352986e+00, -3.92699082e-01, -1.35780699e+00,
-1.43989663e+00],
[ 1.39626340e+00, -7.85398163e-01,  1.57079633e+00,
    1.30899694e+00],
[-7.85398163e-01,  3.92699082e-01, -1.30455966e+00,
-1.43989663e+00],
[-3.49065850e-01, -5.23598776e-01,  2.92860332e-01,
-4.97157870e-13],
[-1.30899694e+00, -1.30899694e-01, -1.30455966e+00,
-1.43989663e+00],
[-1.30899694e+00, -2.84217094e-13, -1.35780699e+00,
-1.43989663e+00],
[ 8.72664626e-01, -2.61799388e-01,  1.03832300e+00,
    1.04719755e+00],
[-9.59931089e-01, -1.17809725e+00, -3.46107665e-01,
-3.92699082e-01],
[ 6.98131701e-01, -1.30899694e-01,  5.05849665e-01,
    2.61799388e-01],
[-2.61799388e-01, -6.54498469e-01,  6.12344331e-01,
    7.85398163e-01],
[-1.39626340e+00, -1.17809725e+00, -1.41105433e+00,
-1.30899694e+00],
[-1.13446401e+00,  2.61799388e-01, -1.09157033e+00,
-1.43989663e+00],
[ 1.74532925e-01,  2.61799388e-01,  8.78580996e-01,
    1.43989663e+00],
[ 3.49065850e-01, -2.84217094e-13,  6.12344331e-01,
    9.16297857e-01],
[-1.04719755e+00, -9.16297857e-01,  2.92860332e-01,
    5.23598776e-01],
[-1.74532925e-01, -2.61799388e-01,  1.33118333e-01,
    2.61799388e-01],
[-4.36332313e-01, -9.16297857e-01, -2.66236666e-02,
-2.61799388e-01],
[-8.72664626e-01, -9.16297857e-01, -5.05849665e-01,
-2.61799388e-01]]

dataset_xv = [[-3.60378394e-13, -5.23598776e-01,  3.99354998e-01,
-1.30899694e-01],
[ 8.72664626e-02, -1.30899694e+00,  2.92860332e-01,
    2.61799388e-01],
[ 9.59931089e-01,  5.23598776e-01,  1.14481766e+00,
    1.57079633e+00],
[ 6.10865238e-01, -2.61799388e-01,  8.25333663e-01,
    1.04719755e+00],
[-3.60378394e-13, -2.61799388e-01,  5.05849665e-01,
    6.54498469e-01],
[-8.72664626e-02, -3.92699082e-01,  2.92860332e-01,
    2.61799388e-01],
[ 6.98131701e-01, -1.30899694e-01,  7.72086330e-01,
    1.04719755e+00],
[ 1.30899694e+00, -2.61799388e-01,  1.41105433e+00,
    1.04719755e+00],
[-2.61799388e-01, -5.23598776e-01,  6.12344331e-01,
    1.43989663e+00],
[ 6.10865238e-01, -5.23598776e-01,  4.52602331e-01,
    1.30899694e-01],
[-8.72664626e-01,  2.61799388e-01, -1.30455966e+00,
-1.43989663e+00],
[-3.49065850e-01, -7.85398163e-01, -2.39612999e-01,
-3.92699082e-01],
[-1.30899694e+00,  5.23598776e-01, -1.57079633e+00,
-1.43989663e+00],
[ 7.85398163e-01, -2.84217094e-13,  3.99354998e-01,
    1.30899694e-01],
[-1.22173048e+00, -2.84217094e-13, -1.25131233e+00,
-1.43989663e+00],
[-1.74532925e-01, -2.84217094e-13,  4.52602331e-01,
    6.54498469e-01],
[-5.23598776e-01, -1.04719755e+00, -7.98709997e-02,
-2.61799388e-01],
[-9.59931089e-01, -2.84217094e-13, -1.46430166e+00,
-1.43989663e+00],
[-5.23598776e-01,  1.30899694e+00, -1.35780699e+00,
-1.43989663e+00],
[-8.72664626e-01,  7.85398163e-01, -1.30455966e+00,
-1.30899694e+00],
[ 1.39626340e+00, -5.23598776e-01,  1.46430166e+00,
    9.16297857e-01],
[-3.49065850e-01,  1.57079633e+00, -1.30455966e+00,
-1.17809725e+00],
[-2.61799388e-01, -7.85398163e-01,  2.66236666e-02,
-1.30899694e-01],
[ 1.04719755e+00, -3.92699082e-01,  1.25131233e+00,
    6.54498469e-01],
[-1.48352986e+00, -2.61799388e-01, -1.41105433e+00,
-1.43989663e+00],
[-8.72664626e-02, -1.30899694e+00,  2.66236666e-02,
-3.92699082e-01],
[-9.59931089e-01,  2.61799388e-01, -1.25131233e+00,
-1.17809725e+00],
[-1.30899694e+00,  2.61799388e-01, -1.35780699e+00,
-1.30899694e+00],
[-3.49065850e-01, -9.16297857e-01,  5.59096998e-01,
    9.16297857e-01],
[ 1.39626340e+00, -2.61799388e-01,  1.14481766e+00,
    1.30899694e+00]]

dataset_yt = [1, 2, 1, 2, 2, 0, 2, 0, 1, 0, 2, 1, 2, 2, 0, 0, 2, 1, 1, 2, 0, 1,
0, 2, 1, 1, 1, 0, 2, 0, 0, 1, 0, 0, 2, 1, 1, 1, 2, 2, 1, 2, 2, 1,
0, 0, 1, 1, 0, 2, 1, 0, 0, 0, 2, 2, 1, 0, 1, 0, 2, 1, 1, 0, 2, 0,
0, 0, 2, 2, 2, 1, 2, 0, 2, 2, 1, 0, 0, 1, 2, 0, 1, 2, 2, 0, 1, 2,
2, 2, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 2, 1, 0, 2, 0, 1, 0, 0, 2, 1,
1, 2, 0, 0, 2, 2, 2, 1, 1, 1]

dataset_yv = [1, 1, 2, 2, 2, 1, 2, 2, 2, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 2, 0,
1, 2, 0, 1, 0, 0, 2, 2]

def test(layers=3, epochs=20, lr=0.05, batch_size=16):
    """Execute the VQC training and evaluation workflow.

    Parameters:
        layers: Variational layer depth
        epochs: Number of training iterations
        lr: Adam optimizer learning rate
        batch_size: Training batch size
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    algo = VQCAlgorithm(text_mode="legacy")
    result = algo.run(layers=layers, epochs=epochs, lr=lr, batch_size=batch_size)
    return result


if __name__ == "__main__":
    layers = 5     # [PARAM]
    epochs = 20      # [PARAM]
    lr = 0.05        # [PARAM]
    batch_size = 16  # [PARAM]
    test(layers=layers, epochs=epochs, lr=lr, batch_size=batch_size)