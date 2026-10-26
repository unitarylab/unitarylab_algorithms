# NEGF Algorithm

This module uses the built-in UnitaryLab SDK QSVT solver for a rectangular
square-lattice device connected to two semi-infinite leads. Kwant supplies the
Hamiltonian and lead self-energies. QSVT solves the lead-injection equations,
whose responses give transmission, local density of states, and bond current.

## Parameters and usage

| Parameter | Default | Meaning |
| --- | ---: | --- |
| `L` | `4` | Number of scattering-region sites along x; integer at least 2 |
| `W` | `4` | Number of sites along y, also the width of each lead; integer at least 2 |
| `a` | `1.0` | Lattice constant; a positive value is intended for this model |
| `t` | `1.0` | Hopping energy scale in eV; a positive value is intended for this model |
| `inverse_tolerance` | `2e-3` | Reciprocal polynomial relative-error tolerance, strictly between 0 and 1 |

The onsite energy is `4 * t` and nearest-neighbor hopping is `-t`. `ENERGY` is
computed automatically from the first two transverse subband thresholds:

```text
E_FIRST = 2 * t * (1 - cos(pi / (W + 1)))
E_SECOND = 2 * t * (1 - cos(2 * pi / (W + 1)))
ENERGY = (E_FIRST + E_SECOND) / 2
```

There is no separate energy parameter. `a` and `t` retain the source Python
behavior; the positive-value guidance above does not add validation rules.

This example uses the default `4 × 4` device, within the QASM2 export size limit.

```python
from unitarylab_algorithms import NEGFAlgorithm

result = NEGFAlgorithm(text_mode="plain").run(
    L=4,
    W=4,
    a=1.0,
    t=1.0,
    inverse_tolerance=2e-3,
)
print(result["transmission"])
print(result["injection_residuals"])
print(result["qasm_paths"])
```

The constructor also accepts `algo_dir` to choose the output directory. The
`test(...)` entry point exposes the same five algorithm parameters.

## Calculation

1. Build the square-lattice scattering Hamiltonian and leads with Kwant.
2. Obtain the lead self-energies `Sigma_L`, `Sigma_R` and broadenings
   `Gamma_L`, `Gamma_R`; assemble
   `A = ENERGY * I - H_C - Sigma_L - Sigma_R`, with the interface blocks embedded
   into the scattering region.
3. Factor each broadening into lead-injection vectors `C_L`, `C_R` and solve
   `A @ injection_responses = [C_L, C_R]`. Build the SDK QSVT core once using the
   basis vector `e0` and reuse it across the right-hand sides. A full device
   inverse is not constructed.
4. Build an executed `Circuit` for each injection channel: normalize and pad the
   right-hand side, prepare it with `initialize` on the low-order system qubits,
   and append the shared QSVT core. Call `execute()` without an external initial
   state to run the entire circuit, including input preparation, from zero.
5. Read the block with every auxiliary qubit at 0 and take its first `L * W`
   complex amplitudes. Multiply by the original right-hand-side norm and the
   SDK scaling factor to recover the injection response.
6. Split the responses into `X_L`, `X_R`, calculate their equation residuals, and
   compute transmission, local density of states, and bond current classically.

The source expressions are retained:

```text
transmission = ||C_R.conj().T @ X_L||_F**2
ldos = (sum(abs(X_L)**2, axis=1) + sum(abs(X_R)**2, axis=1)) / (2*pi)
current_on_bond(i, j) = 2 * imag(H_C[i, j] * vdot(X_L[i], X_L[j]))
```

`bond_current` follows the directed-bond order of `fsyst.graph`. Its sign and
unit convention follow the source expression. It is not a finite-bias current
in SI amperes: this workflow adds no bias-window integration, occupations, or
SI current prefactor.

## Results and files

The default directory is `results/quantum_transport/negf/`.

| Result field | Meaning |
| --- | --- |
| `status` | Whether execution succeeded |
| `circuit_path` | SVG path of the first executed injection circuit |
| `plot` | Generated-file metadata with `format` and `filename` |
| `circuit` | First executed injection circuit, including input preparation and the QSVT core |
| `circuits` | All executed injection circuits in left-lead then right-lead channel order |
| `circuit_paths` | SVG paths for the injection circuits |
| `qasm_paths` | QASM2 file paths for successfully exported injection circuits |
| `qasm_export_errors` | List of QASM2 exports unsupported by the SDK, each with the circuit name in `circuit` and original SDK exception text in `reason` |
| `ENERGY` | Automatically computed injection energy |
| `left_channels`, `right_channels` | Number of retained injection channels in each lead |
| `transmission` | Transmission calculated from the injection responses |
| `injection_residuals` | Relative residual `norm(A @ x - b) / norm(b)` for each injection equation |
| `epsilon` | Internal SDK parameter calibrated against reciprocal polynomial error |
| `inverse_polynomial_error` | Maximum reciprocal polynomial relative error measured during calibration |
| `scaling_factor` | SDK scaling factor used to recover the linear response |
| `rhs_norms` | Original norms of the injection right-hand sides |
| `system_size` | Original scattering-matrix dimension `L * W` |
| `ldos` | Local density of states in scattering-site order |
| `bond_current` | Current values in directed-bond order |

Generated files are:

- `negf_result.txt`: BaseAlgorithm input, log, and result summary.
- `kwant_square_system.png`: Device and lead geometry.
- `kwant_square_ldos.png`: Local density of states.
- `kwant_square_current.png`: Bond-current plot.
- `negf_circuit.svg`: First executed injection circuit.
- `negf_circuit_2.svg`, and so on: Remaining injection circuits.
- `negf_circuit.qasm`, `negf_circuit_2.qasm`, and so on: Created only when QASM2 export succeeds for the corresponding circuit.

`BaseAlgorithm.save_circuit` uses the SDK drawing for SVG files. QASM2 files are
exported with `circuit.to_qasm2(transpile=True)`. The current SDK drawing shows
at most 25 layout layers by default, so an SVG may truncate a long circuit and
does not establish its total gate count.

The current SDK Nagy unitary decomposition supports at most 6 target qubits.
For these QSVT circuits, QASM2 export requires a padded system dimension
`N <= 32`, equivalent to `L * W <= 32`. The default `4 × 4` device has 16 sites
and a system dimension of `N = 16`; its decomposition has 5 target qubits,
within the current size limit.

If the SDK raises `NotImplementedError` during QASM2 export, the algorithm records
the channel in `qasm_export_errors`, for example
`{"circuit": "negf_circuit", "reason": "original SDK exception text"}`, and reports
the skipped export and its reason in the log and `negf_result.txt`. No QASM2 file
or `qasm_paths` entry is produced for that channel. The algorithm continues with
success status, numerical results, every SVG, and the actual `Circuit` objects
preserved. Other exceptions are propagated.

QASM2 export omits uncontrolled global phases. The exported state remains
physically equivalent, but this global phase matters when recovering a linear
response from individual complex amplitudes of a QASM2 execution.

## Dependencies and numerical behavior

Direct dependencies are `numpy`, `scipy`, `matplotlib`, `kwant`, and `unitarylab`.

The Hamiltonian is assembled sparsely. The built-in SDK QSVT path expands the
solver matrix into a dense array and pads its dimension to a power of two, so
this is not an entirely sparse calculation.

`inverse_tolerance` is calibrated once before building the QSVT core. Calibration
locally divides the matrix by its spectral norm and recomputes its singular
values, condition number, and SDK normalization factor `alpha`. It checks the
SDK reciprocal polynomial with its actual scaling `beta` over 20001 grid points
and every actual singular value, returning `epsilon` and
`inverse_polynomial_error`.

The tolerance controls the reciprocal polynomial approximation and does not
guarantee the final equation residual. Final residuals are reported separately
in `injection_residuals`; the same tolerance is not used as a failure assertion
for those residuals.
