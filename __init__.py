"""
Quantum Algorithms
=========================

This module provides quantum algorithms including:
- Cryptology algorithms
    - Discrete Logarithm Algorithm
    - Shor's Algorithm
    - Simon's Algorithm
- Fundamental algorithms
    - Hadamard Test Algorithm
    - Hadamard Transform Algorithm
    - Grover's Algorithm
    - Amplitude Amplification Algorithm
    - Amplitude Estimation Algorithm
    - Quantum Phase Estimation Algorithm
- Linear Algebra algorithms
    - AQC Algorithm
    - HHL Algorithm
    - LCU Algorithm
    - QFT Algorithm
    - QSP Algorithm
    - QSVT(QLSA) Algorithm
    - VQLS Algorithm
- Hamiltonian Simulation algorithms
    - Trotter Algorithm
    - QDRIFT Algorithm
    - Taylor Series Algorithm
    - QSP Algorithm
    - Cartan Algorithm
- Quantum Chemistry algorithms
    - Molecular DMRG Algorithm
- Quantum Transport algorithms
    - NEGF Algorithm
- Quantum Machine Learning algorithms
    - VQE Algorithm
    - Fermi-Hubbard VQE Algorithm
    - QAOA Algorithm
    - QCBM Algorithm
    - VQC Algorithm
    - CVQNN Algorithm
    - Ising Algorithm
- Schrödingerization algorithms
    - Heat Equation Algorithm
    - Advection Equation Algorithm
    - Heat 2D Equation Algorithm
- State Preparation algorithms
    - Mottonen Algorithm
    - Multiplexer Algorithm
    - MPS Algorithm
    - Pauli Algorithm
    - Superposition Algorithm
- Search algorithms
    - Glued Trees Algorithm
    - Hidden Shift Algorithm
    - Quantum Walk Search Algorithm
    - Quantum Backtracking Algorithm
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("unitarylab_algorithms")
except PackageNotFoundError:
    __version__ = "1.1.13"


from .cryptology import *
from .fundamental_algorithm import *
from .linear_algebra import *
from .quantum_chemistry import *
from .quantum_transport import *
from .hamiltonian_simulation import *
from .quantum_machine_learning import *
from .schrodingerization import *
from .state_preparation import *
from .search import *

__all__ = [
    # Cryptology
    "DiscreteLogAlgorithm",
    "ShorAlgorithm",
    "SimonAlgorithm",

    # Fundamental Algorithms
    "HadamardTransformAlgorithm",
    "HadamardTestAlgorithm",
    "AmplitudeAmplificationAlgorithm",
    "AmplitudeEstimationAlgorithm",
    "GroverAlgorithm",
    "QPEAlgorithm",

    # Hamiltonian Simulation
    "TrotterAlgorithm",
    "QDriftAlgorithm",
    "TaylorAlgorithm",
    "QSPHSAlgorithm",
    "CartanDecompositionAlgorithm",

    # Linear Algebra
    "AQCAlgorithm",
    "HHLAlgorithm",
    "LCUAlgorithm",
    "QFTAlgorithm",
    "QSPAlgorithm",
    "QSVTLinearSolverAlgorithm",
    "VQLSAlgorithm",

    # Quantum Chemistry
    "MolecularDMRGAlgorithm",

    # Quantum Transport
    "NEGFAlgorithm",

    # Quantum Machine Learning
    "VQEAlgorithm",
    "QAOAAlgorithm",
    "CVQNNAlgorithm",
    "QCBMAlgorithm",
    "VQCAlgorithm",
    "FermiHubbardVQEAlgorithm",
    "IsingAlgorithm",

    # Schrödingerization
    "HeatEquationAlgorithm",
    "AdvectionEquationAlgorithm",
    "Heat2dEquationAlgorithm",

    # state preparation
    "MottonenAlgorithm",
    "MultiplexerAlgorithm",
    "MPSAlgorithm",
    "PauliAlgorithm",
    "SuperpositionAlgorithm",

    # search
    "GluedTreesAlgorithm",
    "HiddenShiftAlgorithm",
    "QuantumWalkSearchAlgorithm",
    "QuantumBacktrackingAlgorithm",
]
