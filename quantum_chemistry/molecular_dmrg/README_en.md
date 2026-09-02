# Molecular DMRG Algorithm

This example wraps `unitarylab.library.chemistry.MolecularDMRGWorkflow` and always runs the
complete molecular workflow: electronic structure, TenPy DMRG, SciPy CVD,
and UnitaryLab grouped measurement/QASM export.

The default input is bundled H2 with the STO-3G basis. The bundled molecule
selector includes H2, LiH, H2O, CH4, CO, CO2, C6H6, HF, N2, NH3, and O2. A
name such as `LiH` is resolved in `molecules/`; an `.xyz` filename or path is
read directly.

The original four demos correspond to these algorithm inputs:

| Original demo | `xyz_file` | `basis` | `active_occupied_orbitals` | `active_virtual_orbitals` |
| --- | --- | --- | ---: | ---: |
| `h2` | `H2` | `sto-3g` | 1 | 1 |
| `lih` | `LiH` | `sto-3g` | 2 | 2 |
| `h2o-small` | `H2O` | `sto-3g` | 2 | 2 |
| `h2o` | `H2O` | `6-31g` | 3 | 4 |

`h2o-small` is a smaller H2O parameter preset, not a different XYZ geometry.

```python
from unitarylab_algorithms import MolecularDMRGAlgorithm

result = MolecularDMRGAlgorithm().run(
    xyz_file="H2",
    basis="sto-3g",
    active_occupied_orbitals=1,
    active_virtual_orbitals=1,
    backend="torch",
    device="cpu",
    dtype="complex128",
)
```

The result directory contains the BaseAlgorithm text result and circuit SVG.
PySCF data and per-group OpenQASM 2.0 files are placed under `output/`.

The active-space FCI reference already implemented by the Python pipeline is
retained. Legacy MP2, CISD, CCSD, post-SCF controls, Julia sweep output, and
Julia convergence artifacts are not part of this implementation.
