import time
import os
import math
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


class AmplitudeEstimationAlgorithm(BaseAlgorithm):
    """Amplitude Estimation Algorithm Module.

    This module implements the Quantum Amplitude Estimation (QAE) algorithm, which estimates
    the amplitude of target states by combining Grover iterations with Quantum Phase Estimation (QPE).
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Amplitude Estimation Algorithm", prefix="QAE", text_mode=text_mode, algo_dir=algo_dir)


    def run(self, U: Circuit, good_zero_qubits: List[int], d: int = 6, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute amplitude estimation algorithm.

        Parameters:
            U: State preparation unitary operator
            good_zero_qubits: List of bit indices defining the target state
            d: Number of phase register qubits (determines estimation precision)
        
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {
            "State preparation unitary": "Given as input circuit object",
            "Target state where all qubits are |0>": good_zero_qubits,
            "Number of phase register qubits": d
        }
        self.update_input(input)

        self.log(f"Stage 1: Parsing and configuring system parameters")
        
        n_data = U.get_num_qubits()
        total_qubits = d + n_data + 1
        
        self.log(f"  Phase register: {d} Qubits")
        self.log(f"  Data register: {n_data} Qubits")
        self.log(f"  Grover ancilla qubit: 1 Qubit")
        self.log(f"  Target state condition: Qubits {good_zero_qubits} must all be |0>")

        self.log(f"Stage 2: Building QPE + Grover circuit")
        
        prepare = Circuit(n_data + 1, name="prepare")
        data_indices = list(range(n_data))
        prepare.append(U, data_indices)
        
        G = self._grover_operator_from_zero_oracle(U, good_zero_qubits)
        
        qpe_circ = self._qpe_circuit(G, d=d, prepare_target=prepare)
        
        self.log(f"  Built Grover iteration operator G")
        self.log(f"  Completed {d}-qubit QPE expansion and iQFT")

        self.log(f"Stage 3: Executing quantum simulation")
        
        sim_start = time.time()
        state = qpe_circ.execute(backend=backend, device=device, dtype=dtype).state
        statevector = np.asarray(state, dtype=complex).reshape(-1)
        sim_time = time.time() - sim_start
        
        histogram = self._phase_histogram(statevector, d=d)
        
        self.log(f"  Underlying computation time: {sim_time:.4f} seconds")
        self.log(f"  Phase histogram non-zero entries: {len(histogram)}")

        self.log(f"Stage 4: Executing classical post-processing")
        
        best_bits = next(iter(histogram))
        phi_raw = int(best_bits, 2) / (2 ** d)
        
        phi = min(phi_raw, 1.0 - phi_raw)
        
        est_amp = float(np.sin(np.pi * phi) ** 2)
        
        self.log(f"  Most likely phase peak: {best_bits}")
        self.log(f"  Equivalent decimal phase phi: {phi:.6f}")
        self.log(f"  Derived amplitude: {est_amp:.6f}")

        self.log(f"Stage 5: Exporting circuit diagram")
        
        output = {
            "Target amplitude": est_amp,
            "Most likely phase (bits)": best_bits,
            "Phase": phi,
            "Computation time (s)": sim_time,
            "Total qubits": total_qubits
        }
        self.update_output(output)
        self.status = 'success'
        self.summary = f"Algorithm execution successful with amplitude: {est_amp:.6f}"

        # Save results
        circuit_path = self.save_circuit(qpe_circ)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, qpe_circ)

    def _iqft_circuit(self, n: int, do_swaps: bool = True) -> Circuit:
        """Build inverse quantum Fourier transform (iQFT) circuit."""
        gs = Circuit(n, name=f"iQFT_{n}")
        if do_swaps:
            for i in range(n // 2):
                gs.swap(i, n - 1 - i)
        for j in range(n):
            for k in range(0, j):
                angle = -np.pi / (2 ** (j - k))
                gs.mcp(angle, k, j)
            gs.h(j)
        return gs

    def _qpe_circuit(self, U: Circuit, d: int, prepare_target: Optional[Circuit] = None) -> Circuit:
        """Build quantum phase estimation (QPE) core circuit."""
        n_target = U.get_num_qubits()
        gs = Circuit(d + n_target, name=f"QPE_d{d}")
        
        phase = list(range(d))
        target = list(range(d, d + n_target))

        if prepare_target is not None:
            gs.append(prepare_target, target)

        for q in phase:
            gs.h(q)

        for k in range(d):
            gs.append(U.repeat(2 ** k), target=target, control=phase[k], control_state='1')

        iqft = self._iqft_circuit(d, do_swaps=True)
        gs.append(iqft, phase)
        return gs

    def _prepare_kickback_ancilla_minus(self, gs: Circuit, ancilla: int) -> None:
        """Prepare ancilla qubit in |-> = H X |0> state."""
        gs.x(ancilla)
        gs.h(ancilla)

    def _unprepare_kickback_ancilla_minus(self, gs: Circuit, ancilla: int) -> None:
        """Restore ancilla qubit to |0> state."""
        gs.h(ancilla)
        gs.x(ancilla)

    def _phase_oracle_all_zeros(self, gs: Circuit, zero_qubits: list[int], ancilla: int) -> None:
        """Apply phase flip to states where all specified qubits are |0>."""
        self._prepare_kickback_ancilla_minus(gs, ancilla)
        for q in zero_qubits:
            gs.x(q)

        controls = list(zero_qubits)
        if len(controls) == 0:
            gs.x(ancilla)
        elif len(controls) == 1:
            gs.cx(controls[0], ancilla)
        else:
            gs.mcx(controls, ancilla)

        for q in zero_qubits:
            gs.x(q)
        self._unprepare_kickback_ancilla_minus(gs, ancilla)

    def _diffusion_about_prepared_state(self, gs: Circuit, U: Circuit, data_qubits: list[int], ancilla: int) -> None:
        """Perform diffusion operation on prepared state."""
        gs.append(U.dagger(), data_qubits)
        self._phase_oracle_all_zeros(gs, zero_qubits=list(data_qubits), ancilla=ancilla)
        gs.append(U, data_qubits)

    def _grover_operator_from_zero_oracle(self, U: Circuit, good_zero_qubits: list[int]) -> Circuit:
        """Build single Grover iteration (including global phase correction)."""
        n_data = U.get_num_qubits()
        data = list(range(n_data))
        ancilla = n_data

        gs = Circuit(n_data + 1, name="G")
        self._phase_oracle_all_zeros(gs, zero_qubits=good_zero_qubits, ancilla=ancilla)
        self._diffusion_about_prepared_state(gs, U=U, data_qubits=data, ancilla=ancilla)

        self._prepare_kickback_ancilla_minus(gs, ancilla)
        gs.x(ancilla)
        self._unprepare_kickback_ancilla_minus(gs, ancilla)

        return gs

    def _phase_histogram(self, statevector: np.ndarray, d: int) -> dict[str, float]:
        """Extract phase register histogram from quantum state vector."""
        probs = np.abs(statevector) ** 2
        counts: dict[str, float] = {}
        modulus = 2 ** d
        for idx, p in enumerate(probs):
            if p < 1e-12: continue
            k = idx % modulus 
            bits = format(k, f'0{d}b')
            counts[bits] = counts.get(bits, 0.0) + float(p)
        return dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))

def test(p = 0.36, d = 6) -> Dict[str, Any]:
    """Test amplitude estimation algorithm.

    Parameters:
        p: Target success probability to encode in the state preparation unitary
        d: Number of phase register qubits (determines estimation precision)
    
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    
    if not isinstance(p, float):
        p = float(p)
    if not isinstance(d, int):
        d = int(d)
        
    algo = AmplitudeEstimationAlgorithm(text_mode="legacy")

    theta = math.acos(math.sqrt(p))
    U_single = Circuit(1)
    U_single.ry(2 * theta, 0)

    result = algo.run(U=U_single, good_zero_qubits=[0], d=d)
    return result

if __name__ == "__main__":
    p = 0.36 # [PARAM]
    d = 6 # [PARAM]
    test(p=p, d=d)