"""Fermi-Hubbard VQE algorithm workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import os
import time

import matplotlib.pyplot as plt
import numpy as np

try:
    from ...algo_base import BaseAlgorithm
except ImportError:  # pragma: no cover - supports direct script execution
    import sys

    _algorithms_dir = Path(__file__).resolve().parents[2]
    if str(_algorithms_dir) not in sys.path:
        sys.path.insert(0, str(_algorithms_dir))
    from algo_base import BaseAlgorithm

from unitarylab.library.fermi_hubbard.fermi_hubbard_pauli import (
    fermi_hubbard_hamiltonian,
    fermi_hubbard_pauli,
    qubit_site_spin_mapping,
)
from unitarylab.library.fermi_hubbard.pauli_ground_state import pauli_ground_state

from .vqe_adapter import run_pauli_vqe


class FermiHubbardVQEAlgorithm(BaseAlgorithm):
    """Run VQE for the open one-dimensional Fermi-Hubbard model."""

    def __init__(self, text_mode: str = "plain", algo_dir: str = None):
        if algo_dir is None:
            _this = Path(__file__).resolve()
            algo_dir = os.path.join(
                os.getcwd(),
                "results",
                _this.parents[1].name,
                _this.parent.name,
            )
        os.makedirs(algo_dir, exist_ok=True)
        super().__init__(
            name="Fermi-Hubbard VQE Algorithm",
            prefix="FH-VQE",
            text_mode=text_mode,
            algo_dir=algo_dir,
        )

    def run(
        self,
        params: Dict[str, Any] | str | None = None,
        *,
        L: int = 2,
        t: float = 1.0,
        U: float = 4.0,
        B: float = 1.5,
        layers: int = 5,
        max_iter: int = 1000,
        seed: int = 7,
        measure_shots: int = 10000,
    ) -> Dict[str, Any]:
        """Execute the standard Fermi-Hubbard VQE workflow."""
        parsed = _load_params(params)
        if parsed:
            L = int(parsed.get("L", L))
            t = float(parsed.get("t", t))
            U = float(parsed.get("U", U))
            B = float(parsed.get("B", B))
            layers = int(parsed.get("layers", parsed.get("vqe_layers", layers)))
            max_iter = int(parsed.get("max_iter", parsed.get("vqe_max_iter", max_iter)))
            seed = int(parsed.get("seed", seed))
            measure_shots = int(
                parsed.get(
                    "measure_shots",
                    parsed.get("measurement_shots", measure_shots),
                )
            )

        input_data = {
            "Lattice Sites": L,
            "Hopping t": t,
            "Interaction U": U,
            "Magnetic Field B": B,
            "VQE Layers": layers,
            "Max Iterations": max_iter,
            "Seed": seed,
            "Measurement Shots": measure_shots,
        }
        self.update_input(input_data)
        total_start = time.time()

        self.log("Stage 1: Building Fermi-Hubbard Pauli Hamiltonian")
        mapping = qubit_site_spin_mapping(L)
        fermionic_hamiltonian = fermi_hubbard_hamiltonian(L, t, U, B)
        pauli_expression = fermi_hubbard_pauli(L, t, U, B)

        self.log("Stage 2: Running dense exact diagonalization")
        exact = pauli_ground_state(pauli_expression)

        self.log("Stage 3: Running VQE optimization")
        vqe_start = time.time()
        vqe_result = run_pauli_vqe(
            pauli_expression,
            layers=layers,
            max_iter=max_iter,
            seed=seed,
            algo_dir=self.algo_dir,
        )
        vqe_time = time.time() - vqe_start

        self.log("Stage 4: Exporting standard algorithm outputs")
        circuit_path, plot_paths = self._generate_outputs(vqe_result)

        measurement = None
        if measure_shots > 0:
            self.log("Stage 5: Measuring total spin magnetic moment")
            from unitarylab.library.fermi_hubbard.measure import (
                measure_circuit_magnetic_moment,
            )

            measurement = measure_circuit_magnetic_moment(
                vqe_result.circuit,
                shots=measure_shots,
            )

        total_time = time.time() - total_start
        output = {
            "Exact Energy": exact.energy,
            "VQE Energy": vqe_result.energy,
            "Absolute Error": vqe_result.absolute_error,
            "Circuit Energy": vqe_result.circuit_energy,
            "Number of Qubits": vqe_result.number_of_qubits,
            "Optimizer Evaluations": vqe_result.evaluations,
            "Optimizer Converged": vqe_result.optimizer_converged,
            "Optimizer Message": vqe_result.optimizer_message,
            "VQE Runtime": vqe_time,
            "Total Runtime": total_time,
            "Qubit Mapping": mapping,
            "Fermionic Hamiltonian": fermionic_hamiltonian,
            "Pauli Hamiltonian": pauli_expression,
        }
        if measurement is not None:
            output.update(
                {
                    "Measured Magnetic Moment": measurement.magnetic_moment,
                    "Magnetic Moment Standard Errors": measurement.standard_errors,
                    "Measurement Total Shots": measurement.total_shots,
                }
            )

        self.update_output(output)
        self.status = "success"
        self.summary = (
            f"Fermi-Hubbard VQE completed with energy {vqe_result.energy:.6f}; "
            f"exact energy {exact.energy:.6f}; absolute error "
            f"{vqe_result.absolute_error:.6e}."
        )
        self.save_txt()
        return self._build_return_dict(True, circuit_path, plot_paths, vqe_result.circuit)

    def _generate_outputs(self, vqe_result):
        circuit_path = os.path.abspath(
            os.path.join(self.algo_dir, "Fermi_Hubbard_VQE_Circuit.svg")
        )
        vqe_result.circuit.draw(filename=circuit_path)

        convergence_path = os.path.abspath(
            os.path.join(self.algo_dir, "Fermi_Hubbard_VQE_Convergence.svg")
        )
        plt.figure(figsize=(6, 4))
        plt.plot(vqe_result.convergence, color="#3498db", lw=2)
        plt.xlabel("Evaluation")
        plt.ylabel("Energy")
        plt.title("Fermi-Hubbard VQE Energy Convergence")
        plt.tight_layout()
        plt.savefig(convergence_path)
        plt.close()

        parameters_path = os.path.abspath(
            os.path.join(self.algo_dir, "Fermi_Hubbard_VQE_Parameters.npy")
        )
        np.save(parameters_path, vqe_result.parameters)
        return circuit_path, [convergence_path, parameters_path]


def _load_params(params: Dict[str, Any] | str | None) -> Dict[str, Any]:
    if params is None:
        return {}
    if isinstance(params, dict):
        return params
    if isinstance(params, str):
        return json.loads(params)
    raise TypeError("params must be a dict, JSON string, or None")


def test(
    L: int = 2,
    t: float = 1.0,
    U: float = 4.0,
    B: float = 1.5,
    layers: int = 5,
    max_iter: int = 1000,
    seed: int = 7,
    measurement_shots: int = 10000,
):
    """Execute the Fermi-Hubbard VQE workflow."""
    algo = FermiHubbardVQEAlgorithm(text_mode="legacy")
    return algo.run(
        L=L,
        t=t,
        U=U,
        B=B,
        layers=layers,
        max_iter=max_iter,
        seed=seed,
        measure_shots=measurement_shots,
    )


if __name__ == "__main__":
    test()
