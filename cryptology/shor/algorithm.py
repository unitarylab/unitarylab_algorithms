import os
import time
import math
import random
from fractions import Fraction
import numpy as np
from typing import Dict, Any

from unitarylab import Circuit
from unitarylab.library import QFT, IQFT

try:
    from ...algo_base import BaseAlgorithm
except ImportError:
    # 单独运行时，将上级目录加入 sys.path，使 base 模块可被找到
    import sys
    _algorithms_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _algorithms_dir not in sys.path:
        sys.path.insert(0, _algorithms_dir)
    from algo_base import BaseAlgorithm


class ShorAlgorithm(BaseAlgorithm):
    """
    Shor Algorithm Module

    Implements Shor's prime factorization algorithm, supporting matrix and operator methods.
    Resamples the base up to max_retries times within a single run.
    """
    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = os.path.abspath(__file__)
            _directory = os.path.dirname(_this)
            algo_dir = os.path.join(os.getcwd(), "results", os.path.basename(os.path.dirname(_directory)), os.path.basename(_directory))
        os.makedirs(algo_dir, exist_ok=True)

        super().__init__(name="Shor Algorithm", prefix="SHOR", text_mode=text_mode, algo_dir=algo_dir)

    def run(self, N: int, method: str = "matrix", max_retries: int = 15) -> Dict[str, Any]:
        """
        Run Shor's algorithm for prime factorization.

        Args:
            N: Composite number to factor (e.g. 15)
            method: Solving method, 'matrix' or 'operator'
            max_retries: Maximum number of retry attempts

        Returns:
            Dictionary containing algorithm results with fields:
            - status: Execution status, 'ok' on success
            - circuit_path: Local path to saved quantum circuit diagram (SVG)
            - file_path: Local path to saved text file with results
        """

        input = {"Composite number": N, "Method": method, "Max retries": max_retries}
        self.update_input(input)
        
        # Stage 1: Classical pre-check
        if N % 2 == 0:
            factors = [2, N // 2]
            msg = "Direct factorization: N is even"
            self.log(f"  - {msg} -> {factors}")

            output = {"factors": factors, "period": None, "Selected base": None}
            self.update_output(output)
            self.status = "success"
            self.summary = msg

            # Save results
            filename = self.save_txt()
            return self._build_return_dict(True, None, filename)

        # Stage 2: Base sampling and quantum circuit execution
        for attempt in range(1, max_retries + 1):
            self.log(f"\n[Attempt {attempt}/{max_retries}]")
            
            # Sub-stage 2.1: Parameter preparation
            self.log(f"Sub-stage 2.1: Parameter preparation")
            
            a = random.randint(2, N - 1)
            gcd_val = math.gcd(a, N)
            
            if gcd_val > 1:
                factors = [gcd_val, N // gcd_val]
                msg = f"Classical factorization: random base a={a} has common factor with N"
                self.log(f"  Selected base a: {a}")
                self.log(f"  Classical path triggered (common factor found)")
                self.log(f"  Final factors: {factors}")

                output = {"factors": factors, "period": None, "Selected base": a}
                self.update_output(output)
                self.status = "success"
                self.summary = msg

                # Save results
                filename = self.save_txt()
                return self._build_return_dict(True, None, filename)
            
            n_work = N.bit_length()
            n_count = 2 * n_work
            
            if method == 'matrix':
                n_work_actual = n_work
            elif method == 'operator':
                n_work_actual = n_work * 2 + 2
            else:
                raise ValueError(f"Unsupported method: {method}")

            total_qubits = n_count + n_work_actual
            
            self.log(f"  Selected base a: {a}")
            self.log(f"  method: {method}, total_qubits: {total_qubits}")

            # Sub-stage 2.2: Quantum circuit construction
            self.log(f"Sub-stage 2.2: Building quantum circuit")
            
            gs = Circuit(total_qubits, name=f'Shor_N{N}_a{a}_{method}')
            gs.h(range(n_count))
            gs.x(n_count) 

            if method == 'matrix':
                self._build_modular_matrix_circuit(gs, n_count, n_work, a, N)
            else:
                self._build_modular_operator_circuit(gs, n_count, n_work, n_work_actual, a, N)

            gs.append(IQFT(n_count), range(n_count))
            
            # Sub-stage 2.3: Quantum simulation
            self.log(f"Sub-stage 2.3: Running quantum simulation")
            
            start_time = time.time()
            result = gs.execute()
            measure_bin = result.measure(range(n_count), endian='little')
            measure_int = int(measure_bin, 2)
            end_time = time.time()
            comp_time = end_time - start_time

            self.log(f"  Computation time: {comp_time:.4f} s")
            self.log(f"  Measurement: {measure_int} (|{measure_bin}>)")
            
            # Sub-stage 2.4: Classical post-processing
            self.log(f"Sub-stage 2.4: Classical post-processing (continued fractions)")
            
            phase = measure_int / (2**n_count)
            frac = Fraction(phase).limit_denominator(N)
            r = frac.denominator
            self.log(f"  Estimated period r: {r}")
            
            factors = []
            if r % 2 == 0 and r > 0:
                guess = pow(a, r // 2, N)
                if guess != N - 1 and guess != 1:
                    p = math.gcd(guess - 1, N)
                    q = math.gcd(guess + 1, N)
                    
                    if p * q == N or (p > 1 and N % p == 0):
                        factors = [p, N // p] if p * q != N else [p, q]
                        msg = f"Quantum computation successful (attempt {attempt})"
                        self.log(f"  Final factors: {factors}")
                        
                        # Sub-stage 2.5: Export circuit diagram
                        self.log(f"Sub-stage 2.5: Exporting circuit diagram")

                        output = {"factors": factors, "period": r, "Selected base": a, "Computation time (s)": round(comp_time, 4), "Measurement": measure_int, "Total qubits": total_qubits}
                        self.update_output(output)
                        self.status = "success"
                        self.summary = msg
                        
                        # Save results
                        circuit_path = self.save_circuit(gs)                        
                        filename = self.save_txt()
                        return self._build_return_dict(True, circuit_path, filename)
                    else:
                        self.log("  No valid factors this attempt (factor verification failed)")
                else:
                    self.log(f"  No valid factors this attempt (trivial root guess={guess})")
            else:
                self.log("  No valid factors this attempt (period r is odd or 0)")

        # Loop ended without success
        msg = f"Maximum retry limit ({max_retries}) reached without successful factorization"
        self.log(f"\n{msg}")

        output = {"factors": None, "period": None, "Selected base": a, "Computation time (s)": round(comp_time, 4), "Measurement": measure_int, "Total qubits": total_qubits}
        self.update_output(output)
        self.status = "failed"
        self.summary = msg

        # Save results
        circuit_path = self.save_circuit(gs)
        filename = self.save_txt()
        return self._build_return_dict(False, circuit_path, filename, gs)
    

    # Matrix method components
    def _get_modular_matrix(self, a, N, n_qubits):
        """Build modular multiplication unitary: y -> (a * y) mod N."""
        dim = 2**n_qubits
        matrix = np.zeros((dim, dim))
        for y in range(dim):
            if y < N: target = (a * y) % N
            else: target = y
            matrix[target, y] = 1.0
        return matrix

    def _build_modular_matrix_circuit(self, gs, n_count, n_work, a, N):
        """Build controlled modular multiplication circuit for phase estimation."""
        total_qubits = n_count + n_work
        for q in range(n_count):
            power_factor = pow(a, 2**q, N)
            matrix = self._get_modular_matrix(power_factor, N, n_work)
            gs.unitary(matrix, range(n_count, total_qubits), q, '1')

    # Operator method components
    def _Ph(self, n, a, gs):
        """Phase rotation gate."""
        for i in range(n):
            theta = 2 * np.pi * a / (2 ** (n-i))
            gs.p(theta, i)

    def _Controlled_Ph(self, n, a, gs, control_qubit, data_qubits):
        """Controlled phase rotation gate."""
        for i in range(n):
            theta = 2 * np.pi * a / (2 ** (n-i))
            gs.cp(theta, control_qubit, data_qubits[i])

    def _Add_constant_mod_opt(self, n_qubits: int, a: int, N: int):
        """Quantum modular adder."""
        n_padding = n_qubits + 1      
        n_total = n_qubits + 2        
        
        gs = Circuit(n_total, name=f"+({a})%({N})")
        all_qubits = list(range(n_total))           
        work_qubits = list(range(n_padding))        
        ancilla = n_total - 1                       

        gs.append(QFT(n_total), all_qubits)
        self._Ph(n_total, a - N, gs)
        gs.append(IQFT(n_total), all_qubits)
        
        gs.append(QFT(n_padding), work_qubits)    
        self._Controlled_Ph(n_padding, N, gs, ancilla, work_qubits)
        
        self._Ph(n_padding, -a, gs)
        gs.append(IQFT(n_padding), work_qubits)    
        msb_padding = n_qubits 
        gs.x(ancilla)
        gs.cnot(msb_padding, ancilla)
        gs.append(QFT(n_padding), work_qubits)
        self._Ph(n_padding, a, gs)
        gs.append(IQFT(n_padding), work_qubits)

        return gs

    def _multiple_mod(self, n_qubits, a, N):
        """Quantum modular multiplier."""
        a = a % N
        n_data = n_qubits
        n_work = n_qubits + 2
        n_total = n_data + n_work
        
        list_n_data = list(range(n_data))
        list_n_work = list(range(n_data, n_total))
        
        gs = Circuit(n_total, name=f'M')

        for i in list_n_data:
            gs_add_mod = self._Add_constant_mod_opt(n_qubits, (2**i * a) % N, N)
            gs.append(gs_add_mod, list_n_work, list_n_data[i])
        
        for i in range(len(list_n_data)):
            gs.swap(list_n_data[i], list_n_work[i])

        try:
            a_inv = pow(a, -1, N) 
        except ValueError:
            raise ValueError(f"a={a} and N={N} are not coprime, Shor algorithm cannot continue")

        for i in range(n_data):
            term = (a_inv * (2**i)) % N
            sub_val = (N - term) % N
            gs_sub_mod = self._Add_constant_mod_opt(n_qubits, sub_val, N)
            gs.append(gs_sub_mod, list_n_work, list_n_data[i])
            
        return gs

    def _build_modular_operator_circuit(self, gs, n_count, n_work, n_work_actual, a, N):
        """Connect modular multipliers to the main circuit."""
        total_qubits = n_count + n_work_actual
        for q in range(n_count):
            b = pow(a, 2**q, N)
            gs_tem = self._multiple_mod(n_work, b, N)
            gs.append(gs_tem, range(n_count, total_qubits), q)

def test(N=15, method='matrix', max_retries=15):
    """
    Run Shor's algorithm for prime factorization.

    Args:
        N: Composite number to factor (e.g. 15)
        method: Solving method, 'matrix' or 'operator'
        max_retries: Maximum number of retry attempts

    Returns:
        Dictionary containing algorithm results with fields:
        - status: Execution status, 'ok' on success
        - circuit_path: Local path to saved quantum circuit diagram (SVG)
        - file_path: Local path to saved text file with results
    """

    if not isinstance(N, int):
        N = int(N)
    if not isinstance(method, str):
        method = str(method)
    if method not in ['matrix', 'operator']:
        raise ValueError(f"Invalid method: {method}. Choose 'matrix' or 'operator'.")
    if not isinstance(max_retries, int):
        max_retries = int(max_retries)
    
    shor = ShorAlgorithm(text_mode="legacy")
    result = shor.run(N, method=method, max_retries=max_retries)
    return result


if __name__ == "__main__":
    N = 15 # [PARAM]
    method = 'matrix' # [PARAM] 'matrix' or 'operator'
    max_retries = 15
    test(N, method, max_retries)
