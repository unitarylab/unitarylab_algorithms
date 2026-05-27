import time
import os
import numpy as np
from typing import Dict, Any, List, Optional

# Import core project components
from unitarylab.core import Circuit, Register
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class HadamardTestAlgorithm(BaseAlgorithm):
    """Hadamard Test Algorithm Module.

    This module implements the Hadamard test algorithm, which can be used to estimate the expectation
    value of unitary operators, test state superposition, and perform single-qubit phase estimation.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Hadamard Test Algorithm", prefix="HTEST", text_mode=text_mode, algo_dir=algo_dir)


    def run(self, mode: str = "expectation", 
            U: Optional[Circuit] = None, 
            prepare_psi: Optional[Circuit] = None, 
            prepare_phi: Optional[Circuit] = None,
            imag: bool = False, 
            shots: int = 20000, backend='torch', device='cpu', dtype=np.complex128
            ) -> Dict[str, Any]:
        """
        Execute the Hadamard Test main workflow, supporting expectation value estimation, state overlap test, and single-qubit phase estimation.
        
        Configurable input parameters:
             - mode: Run mode ('expectation', 'swap_test', 'phase_estimation')
             - U: Unitary operator circuit to be measured (leave None in swap_test mode)
             - prepare_psi: Circuit for preparing quantum state |psi>
             - prepare_phi: Circuit for preparing quantum state |phi> (only required in swap_test mode)
             - imag: Whether to extract the imaginary part (only valid in expectation mode)
             - shots: Number of measurement shots for statistical sampling (default: 20000)

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Mode": mode, "Unitary U": U, "Prepare |psi>": prepare_psi, "Prepare |phi>": prepare_phi, "Imaginary part": imag, "Shots": shots}
        self.update_input(input)

        start_time = time.time()

        # Stage 1: Parameter parsing and validation
        self.log(f"Stage 1/5: Parsing and validating parameters...")
        
        if mode not in ["expectation", "swap_test", "phase_estimation"]:
            raise ValueError("mode must be 'expectation', 'swap_test', or 'phase_estimation'")

        if mode == "swap_test" and (prepare_phi is None or prepare_psi is None):
            raise ValueError("swap_test mode requires both prepare_phi and prepare_psi")
        if mode in ["expectation", "phase_estimation"] and U is None:
            raise ValueError(f"Unitary operator U is required in {mode} mode")

        self.log(f"  - Run mode: {mode}")
        self.log(f"  - Shot count: {shots}")
        self.log(f"Stage 1/5 complete ✓")

        # Stage 2: Quantum circuit construction
        self.log(f"Stage 2/5: Building quantum circuit...")
        
        circuits = {}
        
        if mode == "swap_test":
            # Build U_swap and joint state for SWAP Test
            n = prepare_phi.get_num_qubits()
            U_swap = Circuit(2 * n, name="swap ")
            for i in range(n):
                U_swap.swap(i, i + n)
                
            prepare_joint = Circuit(2 * n, name="Prep(|phi>⊗|psi>)")
            prepare_joint.append(prepare_phi, target=list(range(n)))
            prepare_joint.append(prepare_psi, target=list(range(n, 2 * n)))
            
            gs_real = self._build_hadamard_test_circuit(U_swap, prepare_joint, imag=False)
            circuits["real"] = gs_real
            self.log(f"  - SWAP Test circuit built (target system: {2*n} Qubits)")
            
        elif mode == "phase_estimation":
            # Phase estimation requires running both real and imaginary circuits
            gs_real = self._build_hadamard_test_circuit(U, prepare_psi, imag=False)
            gs_imag = self._build_hadamard_test_circuit(U, prepare_psi, imag=True)
            circuits["real"] = gs_real
            circuits["imag"] = gs_imag
            self.log(f"  - Built Real & Imag circuits for phase estimation")
            
        else:
            # Basic Expectation mode
            gs = self._build_hadamard_test_circuit(U, prepare_psi, imag=imag)
            circuits["main"] = gs
            self.log(f"  - Base Hadamard Test circuit built (Imag={imag})")

        self.log(f"Stage 2/5 complete ✓")

        # Stage 3: Quantum simulation and measurement
        self.log(f"Stage 3/5: Running quantum simulation and statistical sampling...")
        
        measurements = {}
        for name, circ in circuits.items():
            state = circ.execute(backend=backend, device=device, dtype=dtype)
            
            # Read ancilla qubit (qubit 0) measurement probabilities
            anc_probs = state._phase_probabilities_from_state([0], endian="little", threshold=0.0)
            p0_exact = float(anc_probs.get("0", 0.0))
            
            # Add shot noise simulation
            if shots is not None and shots > 0:
                rng = np.random.default_rng()
                c0 = int(rng.binomial(int(shots), p0_exact))
                p0 = c0 / float(shots)
            else:
                p0 = p0_exact
                
            p1 = 1.0 - p0
            exp_val = p0 - p1  # <Z> = p(0) - p(1)
            measurements[name] = exp_val
            self.log(f"  - [{name.upper()}] Measured branch <Z> expectation: {exp_val:.6f}")

        self.log(f"Stage 3/5 complete ✓")

        # Stage 4: Classical post-processing and estimate extraction
        self.log(f"Stage 4/5: Classical post-processing and estimate extraction...")
        
        est_val = None
        msg = ""

        if mode == "expectation":
            est_val = measurements["main"]
            val_type = "Im" if imag else "Re"
            msg = f"Estimated {val_type}(<psi|U|psi>) = {est_val:.6f}"
            
        elif mode == "swap_test":
            overlap_sq = float(np.clip(measurements["real"], 0.0, 1.0))
            est_val = overlap_sq
            msg = f"Estimated state overlap |<phi|psi>|^2 = {overlap_sq:.6f}"
            
        elif mode == "phase_estimation":
            re_est = measurements["real"]
            im_est = measurements["imag"]
            est_val = self._estimate_phi_from_real_imag(re_est, im_est)
            msg = f"Estimated eigenphase phi = {est_val:.6f} from real/imag components"

        self.log(f"  - Final processing result: {msg}")
        self.log(f"Stage 4/5 complete ✓")
        
        # Stage 5: Exporting quantum circuit diagrams
        self.log(f"Stage 5/5: Exporting quantum circuit diagrams...")

        output = {"Estimated Value": est_val, "Computation Time (s)": time.time() - start_time}
        self.update_output(output)
        self.status = "success"
        self.summary = msg
        
        # save circuits and results
        saved_paths = []
        for name, circ in circuits.items():
            circuit_filename = f"HadamardTest_{mode}_{name}.svg"
            circuit_path = self.save_circuit(circ, circuit_filename)
            saved_paths.append(circuit_path)
            
        filename = self.save_txt()       

        # Return a representative circuit object valid for all modes.
        primary_circuit = next(iter(circuits.values()))
        return self._build_return_dict(True, saved_paths, filename, primary_circuit)

    def _as_statevector(self, result) -> np.ndarray:
        """Convert computation result to state vector."""
        return np.asarray(result, dtype=complex).reshape(-1)

    def _build_hadamard_test_circuit(self, U: Circuit, prepare_psi: Optional[Circuit] = None, imag: bool = False) -> Circuit:
        """Build Hadamard test circuit."""
        n = U.get_num_qubits()
        qc = Circuit(1 + n, name="HadamardTest")
        anc = 0
        tgt = list(range(1, 1 + n))

        qc.h(anc)
        if imag:
            qc.sdag(anc)

        if prepare_psi is not None:
            if prepare_psi.get_num_qubits() != n:
                raise ValueError("prepare_psi qubit count must match U.")
            qc.append(prepare_psi, target=tgt)

        qc.append(U, target=tgt, control=[anc], control_state="1")
        qc.h(anc)
        return qc

    def _estimate_phi_from_real_imag(self, cos_est: float, sin_est: float) -> float:
        """Estimate phase based on real and imaginary parts."""
        angle = float(np.arctan2(sin_est, cos_est))
        phi = float((angle / (2.0 * np.pi)) % 1.0)
        return phi

def test(U=[[1, 0], [0, 1]], psi=[1,2], shots=0):
    """
    Test the Hadamard Test main workflow with expectation value estimation.
    
    Configurable input parameters:
        - U: Unitary operator as a 2D list or numpy array (default: identity)
        - psi: Initial state vector as a list or numpy array (default: [1, 2])
        - shots: Number of measurement shots for statistical sampling (default: 0 for exact probabilities

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    U = np.array(U)
    Psi_1 = np.array(psi)
    Psi_normolized_1 = Psi_1 / np.linalg.norm(Psi_1)
    I_test= U @ U.transpose()
    I = np.eye(U.shape[0])

    if U.shape[0] != U.shape[1]:
        raise ValueError("U must be a square matrix.")
    if U.shape[0] != len(Psi_1):
        raise ValueError("Dimension of U must match length of Psi.")
    if np.linalg.norm(I - I_test) > 1e-6:
        raise ValueError("U is not unitary.")
    
    n_qubit = int(round(np.log2(U.shape[0])))
    gs1 = Circuit(n_qubit, name="U")
    gs1.unitary(U, list(range(n_qubit)))

    gs2 = Circuit(n_qubit, name="Psi")
    gs2.initialize(Psi_normolized_1, list(range(n_qubit)))
    
    algo = HadamardTestAlgorithm(text_mode="legacy")
    result = algo.run(U=gs1, prepare_psi=gs2, shots=shots)
    return result


if __name__ == "__main__":
    U = [[1, 0], [0, -1]] # [PARAM]
    Psi = [1, 2] # [PARAM]
    shots = 0 # [PARAM]
    test(U, Psi, shots)

