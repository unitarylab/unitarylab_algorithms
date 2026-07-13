import time
import os
import sys
import io
import numpy as np
from typing import Dict, Any

from unitarylab.core import Circuit, Register

try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


# ==========================================================
# Internal helper functions
# ==========================================================

def _uprep_b(b: np.ndarray) -> np.ndarray:
    """Construct unitary U_b such that U_b|0⟩ = |b⟩.

    Uses a Householder reflection to map the computational basis state
    |0⟩ to the normalised vector |b⟩.

    Args:
        b (np.ndarray): Normalised state vector of length N = 2^n.

    Returns:
        np.ndarray: Unitary matrix of shape (N, N).
    """
    b = b.reshape(-1, 1)
    n = len(b)
    v = np.zeros((n, 1), dtype=complex)
    v[0, 0] = np.sqrt((b[0, 0] + 1.0) / 2.0)
    for k in range(1, n):
        v[k, 0] = b[k, 0] / (2.0 * v[0, 0])
    Ub = 2.0 * (v @ v.conj().T) - np.eye(n)
    return Ub


def _bloc_enc(A: np.ndarray) -> np.ndarray:
    """Construct the block encoding unitary of A via SVD.

    The returned matrix has A in its top-left block:

        [[A,           sqrt(I - A^2)],
         [sqrt(I - A^2), -A         ]]

    Args:
        A (np.ndarray): Square matrix with ||A||_2 ≤ 1.

    Returns:
        np.ndarray: Unitary block-encoding matrix of shape (2N, 2N).
    """
    U, s, Vh = np.linalg.svd(A)
    S = np.diag(s)
    root = np.diag(np.sqrt(np.clip(1.0 - s ** 2, 0.0, None)))
    middle = np.block([[S, root], [root, -S]])
    I = np.eye(len(s))
    Z = np.zeros_like(I)
    return np.block([[U, Z], [Z, I]]) @ middle @ np.block([[Vh, Z], [Z, I]])


# ==========================================================
# AQC Algorithm Class
# ==========================================================

class AQCAlgorithm(BaseAlgorithm):
    """AQC Algorithm Module.

    This module implements the discrete adiabatic quantum linear system solver (QLSP),
    solving Ax = b via a Trotterized discrete adiabatic evolution.
    The algorithm uses n = log2(N) system qubits and 5 ancillary qubits.
    """

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(
                os.getcwd(), "results",
                os.path.basename(os.path.dirname(_directory)),
                os.path.basename(_directory),
            )
        os.makedirs(algo_dir, exist_ok=True)
        super().__init__(name="AQC Algorithm", prefix="AQC", text_mode=text_mode, algo_dir=algo_dir)

    @staticmethod
    def _add_adiabatic_step(qc, k, T_val, n_sys, sys_qubits, anl_qubits,
                            Ub_mat, Bl_A, kappa, p, _qc_mcz_template):
        """Append one discrete adiabatic evolution step (11 sub-operations) to the circuit.

        Args:
            qc: Target Circuit to append gates to.
            k: Current step index (1-based).
            T_val: Total number of adiabatic steps.
            n_sys: Number of system qubits.
            sys_qubits: System register.
            anl_qubits: Ancillary register (5 qubits).
            Ub_mat: Unitary for state preparation U_b.
            Bl_A: Block encoding unitary of A.
            kappa: Condition number of A.
            p: Adiabatic schedule parameter.
            _qc_mcz_template: Pre-computed MCZ sub-circuit template.
        """
        s = k / T_val  # normalised schedule time

        # ---- step 1: Hadamard on anl[2] ----
        qc.h(anl_qubits[2])

        # ---- step 2: CUQb1 (Ub_dagger-controlled NOT-flip on sys) ----
        qc.unitary(Ub_mat.conj().T, target=sys_qubits[:])
        for i in range(n_sys):
            qc.x(sys_qubits[i])
        qc.x(anl_qubits[4])
        qc.append(
            _qc_mcz_template,
            target=list(range(n_sys)) + [n_sys + 4],
            control=[n_sys + 1, n_sys + 2],
            control_state=[1, 1],
        )
        for i in range(n_sys):
            qc.x(sys_qubits[i])
        qc.x(anl_qubits[4])
        qc.unitary(Ub_mat, target=sys_qubits[:])

        # ---- step 3: Scheduled rotation (CZ + CRY on anl[1]-anl[3]) ----
        f_s = (
            kappa
            / (kappa - 1.0)
            * (
                1.0
                - (1.0 + s * (kappa ** (p - 1.0) - 1.0)) ** (1.0 / (1.0 - p))
            )
        )
        theta = 2.0 * np.arctan2(f_s, 1.0 - f_s)
        qc.cz(control=anl_qubits[1], target=anl_qubits[3], control_state=0)
        qc.cry(theta, control=anl_qubits[1], target=anl_qubits[3], control_state=0)

        # ---- step 4: CH on anl[1]-anl[3] ----
        qc.ch(control=anl_qubits[1], target=anl_qubits[3], control_state=1)

        # ---- step 5: Controlled block encoding of A ----
        qc.cz(target=anl_qubits[4], control=anl_qubits[3], control_state=0)
        target_A = list(range(0, 1 + n_sys))  # sys qubits + anl[0]
        qc.unitary(Bl_A, target=target_A, control=[n_sys + 3, n_sys + 4],
                   control_state=[1, 1])
        qc.unitary(Bl_A.conj().T, target=target_A, control=[n_sys + 3, n_sys + 4],
                   control_state=[1, 0])
        qc.cx(anl_qubits[3], anl_qubits[4])

        # ---- step 6: X on anl[1] ----
        qc.x(anl_qubits[1])

        # ---- step 7: CH on anl[1]-anl[3] ----
        qc.ch(control=anl_qubits[1], target=anl_qubits[3], control_state=1)

        # ---- step 8: Scheduled rotation (symmetric with step 3) ----
        qc.cz(control=anl_qubits[1], target=anl_qubits[3], control_state=0)
        qc.cry(theta, control=anl_qubits[1], target=anl_qubits[3], control_state=0)

        # ---- step 9: CUQb1 (symmetric with step 2) ----
        qc.unitary(Ub_mat.conj().T, target=sys_qubits[:])
        for i in range(n_sys):
            qc.x(sys_qubits[i])
        qc.x(anl_qubits[4])
        qc.append(
            _qc_mcz_template,
            target=list(range(n_sys)) + [n_sys + 4],
            control=[n_sys + 1, n_sys + 2],
            control_state=[1, 1],
        )
        for i in range(n_sys):
            qc.x(sys_qubits[i])
        qc.x(anl_qubits[4])
        qc.unitary(Ub_mat, target=sys_qubits[:])

        # ---- step 10: Hadamard on anl[2] ----
        qc.h(anl_qubits[2])

        # ---- step 11: Reflection ----
        qc.x(anl_qubits[3])
        qc.mcz(controls=[n_sys, n_sys + 2], target=anl_qubits[3],
               control_state=[0, 0])
        qc.x(anl_qubits[3])
        qc.gp(np.pi)

    def run(self, n: int = 2, T: int = 0, p: float = 1.4, backend='torch', device='cpu', dtype=np.complex128) -> Dict[str, Any]:
        """Execute discrete adiabatic quantum linear system solver (AQC).

        Parameters:
            n: Number of system qubits (1–6), matrix dimension N = 2^n.
            T: Number of adiabatic evolution steps (0 = auto-select based on condition number).
            p: Adiabatic schedule parameter (> 1).

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """
        T_val = None if T == 0 else T

        overall_start = time.time()

        # ================= Stage 1 =================
        self.log("Stage 1/4: Input validation and preprocessing...")

        np.random.seed(42)
        N = 2 ** n

        # Build a well-conditioned Hermitian matrix
        A = np.random.randn(N, N)
        A = (A + A.T) / 2 + 10 * np.eye(N)
        A = np.asarray(A, dtype=complex)

        # Random right-hand side
        b = np.random.randn(N)
        b = np.asarray(b, dtype=complex).reshape(-1)

        n_sys = int(np.log2(N))

        # --- auto-normalisation ---
        norm_A_orig = float(np.linalg.norm(A, ord=2))
        norm_b_orig = float(np.linalg.norm(b))
        normalisation_applied = False
        a_scale = 1.0
        b_scale = 1.0

        if abs(norm_A_orig - 1.0) > 1e-12:
            a_scale = norm_A_orig
            A = A / a_scale
            normalisation_applied = True
        if abs(norm_b_orig - 1.0) > 1e-12:
            b_scale = norm_b_orig
            b = b / b_scale
            normalisation_applied = True

        if normalisation_applied:
            self.log(f"  Note: Input was auto-normalised "
                     f"(||A||_2 = {norm_A_orig:.6f}, ||b|| = {norm_b_orig:.6f})")

        kappa = np.linalg.cond(A)

        # --- auto-set T if not provided ---
        if T_val is None:
            T_val = int(np.ceil(kappa * 10))
            if T_val % 2 == 1:
                T_val += 1  # ensure T is even for symmetry

        # --- record input (after T is determined) ---
        if T == 0:
            t_display = f"auto (10·κ ≈ {T_val})"
        else:
            t_display = str(T)
        input_data = {
            "System Qubits (n)": n,
            "Adiabatic Steps (T)": t_display,
            "Schedule Parameter (p)": p,
        }
        self.update_input(input_data)

        self.log(f"  Linear system dimension (N): {N} ({n_sys} System Qubits)")
        self.log(f"  Condition number (kappa): {kappa:.4f}")
        self.log(f"  Adiabatic steps (T): {T_val}, Schedule parameter (p): {p:.2f}")
        self.log("Stage 1/4 complete ✓")

        # ================= Stage 2 =================
        self.log("Stage 2/4: Building discrete adiabatic quantum circuit...")

        # Qubit layout (little-endian):
        #   global qubits  0 .. n_sys-1    : system register  (sys)
        #   global qubits  n_sys .. n_sys+4 : ancillary register (anl)
        sys_qubits = Register('sys', n_sys)
        anl_qubits = Register('anl', 5)
        qc = Circuit(sys_qubits, anl_qubits)

        # Pre-compute unitaries
        Ub_mat = _uprep_b(b)
        Bl_A = _bloc_enc(A)

        # Initialise |b> on the system register
        qc.unitary(Ub_mat, target=sys_qubits[:])

        self.log(f"  Total qubits: {n_sys + 5} ({n_sys} sys + 5 ancillary)")
        self.log(f"  Loading normalised state |b> on system register")

        # --- Edge case: kappa == 1 (A is a scalar multiple of identity) ---
        if abs(kappa - 1.0) < 1e-12:
            self.log(f"  Trivial system detected (kappa ≈ 1). Returning x = b directly.")
            x_final = b.copy()
            if normalisation_applied:
                x_final = x_final * (b_scale / a_scale)
            self.log("Stage 2/4 complete ✓ (trivial)")
            self.log("Stage 3/4 complete ✓ (trivial)")

            # Stage 4
            self.log("Stage 4/4: Classical post-processing (post-selection and rescaling)...")
            residual_norm = float(np.linalg.norm(A * a_scale @ x_final - b * b_scale)) if normalisation_applied else float(np.linalg.norm(A @ x_final - b))
            x_classical = np.linalg.solve(
                A * a_scale if normalisation_applied else A,
                b * b_scale if normalisation_applied else b)
            error = float(np.linalg.norm(x_final - x_classical))
            self.log(f"  Residual norm ||Ax - b||: {residual_norm:.6e}")
            self.log(f"  Error vs classical solution (L2): {error:.6e}")
            self.log("Stage 4/4 complete ✓")

            elapsed = time.time() - overall_start

            self.status = "success"
            self.summary = (
                f"AQC discrete adiabatic linear solver completed (trivial κ≈1). "
                f"Residual norm ||Ax-b|| = {residual_norm:.6e}, "
                f"Error vs classical = {error:.6e}, "
                f"Elapsed time = {elapsed:.4f} s."
            )

            output = {
                "Quantum Solution (x)": x_final,
                "Classical Solution": x_classical,
                "Residual Norm ||Ax-b||": residual_norm,
                "Error vs Classical (L2)": error,
                "Internal Scale Factor": 1.0,
                "Elapsed Time (s)": elapsed,
            }
            self.update_output(output)

            circuit_path = self.save_circuit(qc)
            filename = self.save_txt()
            return self._build_return_dict(True, circuit_path, filename, qc)

        # --- Discrete adiabatic evolution loop ---
        # Pre-compute the sub-circuit template for the CUQb1 steps (steps 2 and 9).
        # This is a circuit with n_sys + 1 qubits implementing MCZ on all controls.
        _qc_mcz_template = Circuit(n_sys + 1)
        _qc_mcz_template.mcz(
            controls=list(range(0, n_sys)),
            target=n_sys,
            control_state=[1] * n_sys,
        )

        for k in range(1, T_val + 1):
            self._add_adiabatic_step(
                qc, k, T_val, n_sys, sys_qubits, anl_qubits,
                Ub_mat, Bl_A, kappa, p, _qc_mcz_template,
            )

        self.log("Stage 2/4 complete ✓")

        # ================= Stage 3 =================
        self.log("Stage 3/4: Running quantum simulation...")

        sim_start = time.time()
        final_state = qc.execute(backend=backend, device=device, dtype=dtype).state
        state_arr = np.asarray(final_state, dtype=complex).reshape(-1)
        sim_time = time.time() - sim_start

        self.log(f"  Core simulation time: {sim_time:.4f} s")
        self.log("Stage 3/4 complete ✓")

        # ================= Stage 4 =================
        self.log("Stage 4/4: Classical post-processing (post-selection and rescaling)...")

        # Post-select on ancillary register |10000>
        # In little-endian: anl[0]..anl[3] = |0000>, anl[4] = |1>
        #   bit n_sys+4 = 1 → skip first 2**(n_sys+4) elements
        vec_anc_postselected = state_arr[2 ** (n_sys + 4):]
        x_quantum = vec_anc_postselected[:2 ** n_sys]

        # Normalise extracted quantum state
        x_quantum_norm = np.linalg.norm(x_quantum)
        if x_quantum_norm < 1e-15:
            raise RuntimeError(
                "Post-selection returned a near-zero state. "
                "The adiabatic evolution may need more steps (increase T) "
                "or the system may be too ill-conditioned."
            )
        x_normalised = x_quantum / x_quantum_norm

        # Compute internal scaling factor (on the normalised problem)
        internal_scale = 0.0
        for i in range(2 ** n_sys):
            if abs(b[i]) > 1e-12:
                internal_scale = b[i] / (A[i] @ x_normalised)
                break
        if abs(internal_scale) < 1e-15:
            internal_scale = 1.0

        # Solution for the normalised problem
        x_result_problem = internal_scale * x_normalised

        # Rescale back to the original (un-normalised) problem if needed
        if normalisation_applied:
            x_final = x_result_problem * (b_scale / a_scale)
        else:
            x_final = x_result_problem

        # Error and residual on the normalised problem
        x_classical = np.linalg.solve(A, b)
        x_classical_normalised = x_classical / np.linalg.norm(x_classical)
        error = float(np.linalg.norm(x_normalised - x_classical_normalised))

        # Residual norm on the final (rescaled) solution
        A_orig = np.asarray(A, dtype=complex) * a_scale if normalisation_applied else A
        b_orig = (np.asarray(b, dtype=complex).reshape(-1) * b_scale
                  if normalisation_applied else b)
        residual_norm = float(np.linalg.norm(A_orig @ x_final - b_orig))

        self.log(f"  Post-selection success amplitude: {x_quantum_norm:.6f}")
        self.log(f"  Direction error vs classical normalised solution: {error:.6e}")
        self.log(f"  Residual norm ||Ax - b||: {residual_norm:.6e}")
        self.log(f"  Internal scaling factor: {internal_scale:.6f}")
        self.log("Stage 4/4 complete ✓")

        elapsed = time.time() - overall_start

        # --- Set status ---
        self.status = "success"
        self.summary = (
            f"AQC discrete adiabatic linear solver completed. "
            f"Residual norm ||Ax-b|| = {residual_norm:.6e}, "
            f"Error vs classical = {error:.6e}, "
            f"Elapsed time = {elapsed:.4f} s."
        )

        # --- Record output ---
        output = {
            "Quantum Solution (x)": x_final,
            "Classical Solution": x_classical,
            "Residual Norm ||Ax-b||": residual_norm,
            "Error vs Classical (L2)": error,
            "Internal Scale Factor": internal_scale,
            "Post-selection Amplitude": x_quantum_norm,
            "Simulation Time (s)": sim_time,
            "Elapsed Time (s)": elapsed,
        }
        self.update_output(output)

        # --- Save circuit diagrams & result text ---
        # Full circuit diagram (may be truncated for large T)
        _stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            circuit_path_full = self.save_circuit(qc, name="aqc_full")
        finally:
            sys.stdout = _stdout
        self.log(f"  Circuit diagram saved: {circuit_path_full}")

        # Build and save a representative one-step slice
        qc_one_step = Circuit(sys_qubits, anl_qubits)
        qc_one_step.unitary(Ub_mat, target=sys_qubits[:])
        self._add_adiabatic_step(
            qc_one_step, 1, T_val, n_sys, sys_qubits, anl_qubits,
            Ub_mat, Bl_A, kappa, p, _qc_mcz_template,
        )
        sys.stdout = io.StringIO()
        try:
            circuit_path_slice = self.save_circuit(qc_one_step, name="aqc_one_step")
        finally:
            sys.stdout = _stdout
        self.log(f"  Circuit diagram saved: {circuit_path_slice}")

        if T_val * 11 > 10:
            self.log(f"  Note: Full circuit has ~{T_val * 11} layers. "
                     f"The full diagram may be truncated; "
                     f"see aqc_one_step_circuit.svg for the structure of a single adiabatic step.")

        circuit_path = [circuit_path_full, circuit_path_slice]
        filename = self.save_txt()

        return self._build_return_dict(True, circuit_path, filename, qc)


def test(n: int = 2, T: int = 0, p: float = 1.4) -> Dict[str, Any]:
    """Test entry point for the AQC discrete adiabatic linear solver.

    Parameters:
        n: Number of system qubits (1–6), matrix dimension N = 2^n.
        T: Number of adiabatic evolution steps (0 = auto-select).
        p: Adiabatic schedule parameter (> 1).

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    if not isinstance(n, int):
        n = int(n)
    if not isinstance(T, int):
        T = int(T)
    if not isinstance(p, float):
        p = float(p)

    algo = AQCAlgorithm(text_mode="legacy")
    return algo.run(n=n, T=T, p=p)


if __name__ == "__main__":
    n = 2   # [PARAM]
    T = 0   # [PARAM]
    p = 1.4 # [PARAM]
    test(n=n, T=T, p=p)
