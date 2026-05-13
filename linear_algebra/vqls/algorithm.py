import time
import os
import numpy as np
from typing import Dict, Any, List, Optional
from scipy.optimize import minimize

from unitarylab.core import Circuit, Register, ClassicalRegister
try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class VQLSAlgorithm(BaseAlgorithm):
    """
    Variational Quantum Linear Solver (VQLS)
    
    Solve linear system Ax = b using variational quantum algorithm, where A = c_0*A_0 + c_1*A_1 + c_2*A_2.
    
    Algorithm Flow:
        1. Parameter preparation and initialization
        2. Construct variational quantum circuit
        3. Execute variational optimization
        4. Classical post-processing and accuracy analysis
        5. Export results and circuit diagrams
    
    Example:
        >>> algo = VQLSAlgorithm(seed=42)
        >>> result = algo.run(n_qubits=2, max_iterations=100)
        >>> self.log(result['fidelity'])
    """
    
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="VQLS Algorithm", prefix="VQLS", text_mode=text_mode, algo_dir=algo_dir)

        np.random.seed(42)
        
        # Quantum system parameters
        self.n_qubits = None
        self.tot_qubits = None
        self.ancilla_idx = None
        
        # Problem parameters
        self.c = None
        self.A_num = None
        self.b_state = None
        self.Ub_matrix = None
        self.Ub_dag_matrix = None
        
        # Optimization history
        self.optimization_history = []

    def run(
        self,
        n_qubits: int = 3,
        coefficients: Optional[List[float]] = None,
        max_iterations: int = 200,
        tolerance: float = 1e-6,
        initial_spread: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Execute VQLS algorithm main process
        
        Solve linear system A = c_0*A_0 + c_1*A_1 + c_2*A_2 using variational quantum algorithm
        
        Parameters:
            n_qubits: Number of system qubits
            coefficients: Linear combination coefficients [c_0, c_1, c_2], default is [1.0, 0.2, 0.2]
            max_iterations: Maximum optimization iteration count
            tolerance: Optimization convergence tolerance
            initial_spread: Random range for initial parameters
            
        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """
        
        input = {"System qubits": n_qubits, "Linear combination coefficients": coefficients, "Max Iterations": max_iterations, "Tolerance": tolerance, "Initial Spread": initial_spread}
        self.update_input(input)
        
        start_time = time.time()

        # Stage 1: Parameter preparation and initialization
        self.log(f"Stage 1/5: Parameter preparation and initialization")
        
        if n_qubits < 1:
            raise ValueError("Number of qubits must be greater than 0")
        
        self.n_qubits = n_qubits
        self.tot_qubits = n_qubits + 1
        self.ancilla_idx = n_qubits
        
        if coefficients is None:
            coefficients = [1.0, 0.2, 0.2]
        self.c = np.array(coefficients)
        
        dim = 2 ** n_qubits
        
        # Construct problem matrix A = c_0*A_0 + c_1*A_1 + c_2*A_2
        Id = np.identity(2)
        Z = np.array([[1, 0], [0, -1]])
        X = np.array([[0, 1], [1, 0]])
        
        A_0 = np.identity(dim)
        
        if n_qubits == 2:
            A_1 = np.kron(X, Z)
            A_2 = np.kron(X, Id)
        elif n_qubits == 3:
            A_1 = np.kron(np.kron(X, Z), Id)
            A_2 = np.kron(np.kron(X, Id), Id)
        else:
            A_1 = np.kron(X, np.identity(2**(n_qubits-1)))
            A_2 = np.kron(X, np.identity(2**(n_qubits-1)))
        
        self.A_num = self.c[0] * A_0 + self.c[1] * A_1 + self.c[2] * A_2
        
        # Construct |b> state
        Ub_circuit = self._build_b_circuit()
        self.Ub_matrix = Ub_circuit.get_matrix()
        
        Ub_dag_circuit = Ub_circuit.dagger()
        self.Ub_dag_matrix = Ub_dag_circuit.get_matrix()
        
        init_state = np.zeros(dim, dtype=complex)
        init_state[0] = 1.0 + 0.0j
        self.b_state = Ub_circuit.execute(initial_state=init_state).state
        
        self.log(f"  - Number of system qubits: {n_qubits}")
        self.log(f"  - Total qubits: {self.tot_qubits} (including 1 ancilla qubit)")
        self.log(f"  - Problem dimension: {dim}")
        self.log(f"  - Linear combination coefficients: {self.c}")
        self.log(f"  - Maximum iterations: {max_iterations}")
        self.log(f"Stage 1/5 completed")

        # Stage 2: Quantum circuit construction
        self.log(f"Stage 2/5: Construct variational quantum circuit")
        
        # Initialize variational parameters
        init_params = np.random.uniform(-initial_spread, initial_spread, size=n_qubits)
        
        # Build example circuit for visualization
        example_circuit = self._build_full_circuit_for_visualization(init_params)
        
        self.log(f"  - Number of variational parameters: {n_qubits}")
        self.log(f"  - Initial parameter range: [-{initial_spread}, {initial_spread}]")
        self.log(f"Stage 2/5 completed")

        # Stage 3: Quantum simulation calculation and optimization
        self.log(f"Stage 3/5: Execute variational optimization")
        sim_start = time.time()
        
        self.optimization_history = []
        
        result = minimize(
            self._cost_loc,
            init_params,
            method="COBYLA",
            options={"maxiter": max_iterations, "tol": tolerance, "rhobeg": 0.5}
        )
        
        theta_opt = result.x
        final_cost = result.fun
        
        sim_time = time.time() - sim_start
        self.log(f"  - Optimization successful: {result.success}")
        self.log(f"  - Iteration count: {len(self.optimization_history)}")
        self.log(f"  - Final loss: {final_cost:.6e}")
        self.log(f"  - Optimization time: {sim_time:.4f} seconds")
        self.log(f"Stage 3/5 completed")

        # Stage 4: Classical post-processing and accuracy analysis
        self.log(f"Stage 4/5: Classical post-processing and result analysis")
        
        # Get variational solution
        x_quantum = self._get_solution_state(theta_opt)
        x_quantum_normalized = x_quantum / np.linalg.norm(x_quantum)
        
        # Calculate exact solution as reference
        x_classical = np.linalg.solve(self.A_num, self.b_state)
        x_classical_normalized = x_classical / np.linalg.norm(x_classical)
        
        # Calculate fidelity
        fidelity = abs(np.vdot(x_classical_normalized, x_quantum_normalized)) ** 2
        
        # Calculate residual
        residual = np.linalg.norm(self.A_num @ x_quantum_normalized - self.b_state)
        relative_error = residual / np.linalg.norm(self.b_state)
        
        self.log(f"  - Fidelity: {fidelity:.6f}")
        self.log(f"  - Relative error: {relative_error:.6e}")
        self.log(f"  - Residual norm: {residual:.6e}")
        self.log(f"Stage 4/5 completed")

        # Stage 5: Export circuit diagrams and results
        self.log(f"Stage 5/5: Export quantum circuit diagram")

        output = {"Fidelity": fidelity, "Relative Error": relative_error, "Residual Norm": residual, "Solution State (Quantum)": x_quantum_normalized, "Solution State (Classical)": x_classical_normalized, 
                  "Computation Time (s)": sim_time}
        self.update_output(output)
        self.status = "success" if result.success else "failed"
        self.summary = f"VQLS optimization completed, fidelity {fidelity:.6f}, relative error {relative_error:.6e}"
        
        circuit_path = self.save_circuit(example_circuit)
        filename = self.save_txt()
        return self._build_return_dict(True, circuit_path, filename, example_circuit)

    def _build_b_circuit(self) -> Circuit:
        """Construct circuit U_b to prepare |b> state, such that |b> = U_b |0>"""
        reg = Register('q', self.n_qubits)
        qc = Circuit(reg, name="U_b")
        for idx in range(self.n_qubits):
            qc.h(idx)
        return qc

    def _build_ansatz(self, theta: np.ndarray) -> Circuit:
        """Construct parameterized variational circuit, mapping |0> to variational state |x(theta)>"""
        reg = Register('q', self.n_qubits)
        qc = Circuit(reg, name="Ansatz")
        
        for idx in range(self.n_qubits):
            qc.h(idx)
        
        for idx, element in enumerate(theta):
            qc.ry(element, idx)
        
        return qc

    def _CA(self, idx: int) -> Circuit:
        """Construct controlled A_l operation (idx: 0=Identity, 1=A_1, 2=A_2)"""
        reg = Register('q', self.tot_qubits)
        qc = Circuit(reg, name=f"CA_{idx}")
        
        if idx == 0:
            pass
        elif idx == 1:
            qc.cx(control=self.ancilla_idx, target=self.ancilla_idx-1)
            qc.cz(control=self.ancilla_idx, target=self.ancilla_idx-2)
        elif idx == 2:
            qc.cx(control=self.ancilla_idx, target=self.ancilla_idx-1)
        
        return qc

    def _local_hadamard_test(
        self,
        weights: np.ndarray,
        l: int,
        lp: int,
        j: int,
        part: Optional[str] = None
    ) -> Circuit:
        """Construct local Hadamard test circuit for measuring local expectation values"""
        reg = Register('q', self.tot_qubits)
        qc = Circuit(reg, name="Local_Hadamard_Test")
        
        qc.h(self.ancilla_idx)
        
        if part == "Im" or part == "im":
            qc.sdag(self.ancilla_idx)
        
        ansatz_circuit = self._build_ansatz(weights)
        qc.append(ansatz_circuit, range(self.n_qubits))
        
        ca_circuit = self._CA(l)
        qc.append(ca_circuit, range(self.tot_qubits))
        
        ub_circuit = self._build_b_circuit()
        ub_dag_circuit = ub_circuit.dagger()
        qc.append(ub_dag_circuit, range(self.n_qubits))
        
        if j != -1:
            qc.cz(control=self.ancilla_idx, target=j)
        
        qc.append(ub_circuit, range(self.n_qubits))
        
        ca_lp_circuit = self._CA(lp)
        qc.append(ca_lp_circuit, range(self.tot_qubits))
        
        qc.h(self.ancilla_idx)
        
        return qc

    def _measure_expectation(self, qc: Circuit) -> float:
        """Measure Z expectation value on ancilla qubit"""
        init_state = np.zeros(2 ** self.tot_qubits, dtype=complex)
        init_state[0] = 1.0 + 0.0j
        
        final_state = qc.execute(initial_state=init_state).state
        
        exp_val = 0.0
        for i, amp in enumerate(final_state):
            bit = (i >> self.ancilla_idx) & 1
            exp_val += (1.0 if bit == 0 else -1.0) * (abs(amp) ** 2)
        
        return float(np.real(exp_val))

    def _mu(self, weights: np.ndarray, l: int, lp: int, j: int) -> complex:
        """Calculate complex coefficient mu for local cost function"""
        qc_real = self._local_hadamard_test(weights, l, lp, j, part="Re")
        mu_real = self._measure_expectation(qc_real)
        
        qc_imag = self._local_hadamard_test(weights, l, lp, j, part="Im")
        mu_imag = self._measure_expectation(qc_imag)
        
        return mu_real + 1.0j * mu_imag

    def _psi_norm(self, weights: np.ndarray) -> float:
        """Calculate normalization constant <psi|psi>, where |psi> = A|x>"""
        norm = 0.0
        for l in range(len(self.c)):
            for lp in range(len(self.c)):
                norm += self.c[l] * np.conj(self.c[lp]) * self._mu(weights, l, lp, -1)
        return abs(norm)

    def _cost_loc(self, weights: np.ndarray) -> float:
        """Calculate local cost function (approaches zero when A|x> ∝ |b>)"""
        mu_sum = 0.0
        for l in range(len(self.c)):
            for lp in range(len(self.c)):
                for j in range(self.n_qubits):
                    mu_sum += self.c[l] * np.conj(self.c[lp]) * self._mu(weights, l, lp, j)
        
        mu_sum = abs(mu_sum)
        psi_norm_val = self._psi_norm(weights)
        
        cost = 0.5 - 0.5 * mu_sum / (self.n_qubits * psi_norm_val)
        cost_real = float(np.real(cost))
        
        self.optimization_history.append(cost_real)
        
        return cost_real

    def _get_solution_state(self, weights: np.ndarray) -> np.ndarray:
        """Calculate variational solution state |x(theta)> based on optimization parameters"""
        ansatz_circuit = self._build_ansatz(weights)
        init_state = np.zeros(2 ** self.n_qubits, dtype=complex)
        init_state[0] = 1.0 + 0.0j
        return ansatz_circuit.execute(initial_state=init_state).state

    def _build_full_circuit_for_visualization(self, weights: np.ndarray) -> Circuit:
        """Construct example circuit for visualization (local Hadamard test)"""
        return self._local_hadamard_test(weights, l=1, lp=2, j=1, part="Re")


def test(n=3, coefficients=[1.0, 0.2, 0.2], max_iterations=100, tolerance=1e-6):
    """
    Execute VQLS algorithm main process
    
    Solve linear system A = c_0*A_0 + c_1*A_1 + c_2*A_2 using variational quantum algorithm
    
    Parameters:
        n_qubits: Number of system qubits
        coefficients: Linear combination coefficients [c_0, c_1, c_2], default is [1.0, 0.2, 0.2]
        max_iterations: Maximum optimization iteration count
        tolerance: Optimization convergence tolerance
        
    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """
    algo = VQLSAlgorithm(text_mode="legacy")
    result = algo.run(n_qubits=n, coefficients=coefficients, max_iterations=max_iterations, tolerance=tolerance)
    return result


if __name__ == "__main__":
    n = 3
    coefficients = [1.0, 0.2, 0.2] # [PARAM]
    max_iterations = 100 # [PARAM]
    tolerance = 1e-6 # [PARAM]
    test(n, coefficients, max_iterations, tolerance)
