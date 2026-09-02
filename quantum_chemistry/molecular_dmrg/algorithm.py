"""Molecular DMRG algorithm backed by the chemistry workflow."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ...algo_base import BaseAlgorithm
from unitarylab.library.chemistry import Molecule, MolecularDMRGWorkflow

ALGORITHM_DIRECTORY = Path(__file__).resolve().parent
MOLECULES_DIRECTORY = ALGORITHM_DIRECTORY / "molecules"
DEFAULT_XYZ_FILE = MOLECULES_DIRECTORY / "CH4.xyz"
OUTPUT_DIRECTORY = "output"


class MolecularDMRGAlgorithm(BaseAlgorithm):
    """Run electronic structure, DMRG, CVD, and grouped measurement."""

    def __init__(self, text_mode: str = "plain", algo_dir: str | None = None):
        if algo_dir is None:
            algo_dir = os.path.join(
                os.getcwd(),
                "results",
                "quantum_chemistry",
                "molecular_dmrg",
            )
        os.makedirs(algo_dir, exist_ok=True)
        super().__init__(
            "Molecular DMRG",
            prefix="MDM",
            text_mode=text_mode,
            algo_dir=algo_dir,
        )

    def run(
        self,
        xyz_file: str | os.PathLike[str] | None = None,
        basis: str = "sto-3g",
        charge: int = 0,
        multiplicity: int = 1,
        *,
        active_occupied_orbitals: int = 3,
        active_virtual_orbitals: int = 3,
        max_iterations: int = 100,
        cvd_restarts: int = 3,
        cvd_init_scale: float = 0.5,
        chi0: int = 20,
        nsweeps: int = 100,
        maxdim: int = 100,
        cutoff: float = 1e-8,
        shots: int = 10_000,
        seed: int | None = 2077,
        backend: str = "torch",
        device: str = "cpu",
        dtype=np.complex128,
    ):
        xyz_path = _resolve_xyz_file(xyz_file)
        resolved_dtype = np.dtype(dtype).type
        output_directory = Path(self.algo_dir) / OUTPUT_DIRECTORY
        output_directory.mkdir(parents=True, exist_ok=True)

        self.update_input(
            {
                "XYZ file": str(xyz_path),
                "Basis": basis,
                "Charge": charge,
                "Multiplicity": multiplicity,
                "Maximum active occupied orbitals": active_occupied_orbitals,
                "Maximum active virtual orbitals": active_virtual_orbitals,
                "Random seed": seed,
                "Shots": shots,
                "Simulation backend": backend,
                "Simulation device": device,
                "Simulation dtype": np.dtype(resolved_dtype).name,
            }
        )

        molecule = Molecule.from_xyz(
            xyz_path,
            basis=basis,
            charge=charge,
            multiplicity=multiplicity,
            active_occupied=active_occupied_orbitals,
            active_virtual=active_virtual_orbitals,
        )
        self.log("Running electronic structure, DMRG, CVD, and QWC measurement")
        result = MolecularDMRGWorkflow(
            molecule,
            shots=shots,
            dmrg_chi0=chi0,
            dmrg_maxdim=maxdim,
            dmrg_max_sweeps=nsweeps,
            dmrg_cutoff=cutoff,
            cvd_maxiter=max_iterations,
            cvd_restarts=cvd_restarts,
            cvd_init_scale=cvd_init_scale,
            workdir=output_directory,
            seed=seed,
            backend=backend,
            device=device,
            dtype=resolved_dtype,
        ).run()

        electronic = result.electronic_structure
        dmrg_result = result.dmrg
        cvd_result = result.cvd
        measurement = result.measurement
        if any(stage is None for stage in (electronic, dmrg_result, cvd_result, measurement)):
            raise RuntimeError(
                "the Molecular DMRG workflow did not complete all stages")
        if cvd_result.circuit is None:
            raise RuntimeError(
                "the CVD stage did not return a preparation circuit")

        circuit = cvd_result.circuit
        circuit_info = circuit.analyze(show=False)
        circuit_depth = circuit_info.depth()
        circuit_gates = circuit_info.size()
        infidelity = max(0.0, 1.0 - cvd_result.overlap_mod**2)
        exact_difference = abs(
            measurement.exact_energy - dmrg_result.dmrg_energy)
        fci_value = (
            electronic.fci_energy if electronic.fci_dimension else "skipped"
        )

        self.update_output(
            {
                "HF energy": electronic.hf_energy,
                "Active-space FCI energy": fci_value,
                "Active space": (
                    f"CAS({electronic.active_electrons}e,"
                    f"{len(electronic.active_orbitals)}o), "
                    f"{electronic.n_qubits} qubits"
                ),
                "DMRG energy": dmrg_result.dmrg_energy,
                "CVD layers": cvd_result.circuit_layers,
                "CVD infidelity": infidelity,
                "UnitaryLab exact energy": measurement.exact_energy,
                "Exact energy difference": exact_difference,
                "Sampled energy": measurement.sampled_energy,
                "Measurement groups": measurement.n_qwc_groups,
                "Circuit depth": circuit_depth,
                "Circuit gates": circuit_gates,
                "QASM directory": str(output_directory.resolve()),
            }
        )
        self.status = "success"
        self.summary = (
            f"Generated a {electronic.n_qubits}-qubit molecular state-preparation "
            f"circuit with disentangle infidelity {infidelity:.3e}."
        )

        circuit_path = self.save_circuit(circuit)
        result_filename = self.save_txt()
        files = [result_filename, *(str(path)
                                    for path in measurement.qasm_files)]
        response = self._build_return_dict(
            True,
            circuit_path,
            files,
            circuit,
        )
        for artifact in response["plot"]:
            if artifact["filename"].lower().endswith(".qasm"):
                artifact["format"] = "qasm"
        return response


def _resolve_xyz_file(xyz_file: str | os.PathLike[str] | None) -> Path:
    if xyz_file is None:
        return DEFAULT_XYZ_FILE

    xyz_path = Path(xyz_file).expanduser()
    if xyz_path.parent == Path(".") and not xyz_path.suffix:
        resolved_path = (MOLECULES_DIRECTORY /
                         f"{xyz_path.name}.xyz").resolve()
    else:
        resolved_path = xyz_path.resolve()

    if resolved_path.suffix.lower() != ".xyz":
        raise ValueError(
            "molecular geometry files must use the .xyz extension")
    if not resolved_path.is_file():
        raise FileNotFoundError(f"XYZ file does not exist: {resolved_path}")
    return resolved_path


def test(xyz_file: str | os.PathLike[str] | None = None):
    return MolecularDMRGAlgorithm(text_mode="legacy").run(xyz_file)


if __name__ == "__main__":
    test()
