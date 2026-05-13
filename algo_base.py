from typing import Any, Dict, List, Optional
import os


class BaseAlgorithm:
    """Shared base class for algorithm result/log formatting."""

    def __init__(self, name: str, prefix: str = "", text_mode: str = "plain", algo_dir: Optional[str] = None):
        self.name = self.__class__.__name__ if name == "" else name
        self.prefix = self.name[:3].upper() if prefix == "" else prefix
        self.prefix = '[' + self.prefix + ']' if not self.prefix.startswith('[') else self.prefix

        self.text_mode = text_mode
        self.algo_dir = algo_dir
        self.status = ""
        self.input: Dict[str, Any] = {}
        self.output: Dict[str, Any] = {}
        self.info: list = []
        self.summary: str = ""

    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """Run the algorithm with given parameters. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the run() method.")
    
    def _auxiliary_method(self, *args, **kwargs) -> Any:
        """An example auxiliary method that can be used by subclasses."""
        pass

    def log(self, message) -> None:
        """Print a message and save it into info logs."""
        if isinstance(message, str):
            msg = self.prefix + ": " + message
            print(msg)
            self.info.append(message)
        elif isinstance(message, dict):
            for key, value in message.items():
                msg = f"        - {key} = {value}"
                print(msg)

    def update_input(self, input_dict: Dict[str, Any]) -> None:
        """Update the input parameters dictionary."""
        self.input.update(input_dict)
        print(f"{self.prefix}: Starting {self.name}")
        print(f"{self.prefix}: Input parameters: ")
        self.log(self.input)

    def update_output(self, output_dict: Dict[str, Any]) -> None:
        """Update the output information dictionary."""
        self.output.update(output_dict)
        print(f"{self.prefix}: Output information: ")
        self.log(self.output)

    def save_circuit(self, circuit, name=None) -> str:
        """Save the circuit into a file."""
        if name is None:
            filename = f"{self.name.replace(' ', '_').lower()}_circuit.svg"
        else:
            filename = f"{name}.svg"
        
        filepath = f"{self.algo_dir}/{filename}"
        circuit.draw(filename=filepath, title=f"{self.name} Circuit")
        self.log(f"  Circuit diagram saved: {filepath}")
        return filepath

    def save_txt(self) -> None:
        """Save the algorithm result into a file."""
        filename = f"{self.name.replace(' ', '_').lower()}_result.txt"
        filepath = f"{self.algo_dir}/{filename}"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.format_result_ascii())
        self.log(f"  Result saved: {filepath}")
        return filename

    def _build_return_dict(self, success: bool, circuit_path, filepath, circuit=None) -> Dict[str, Any]:
        """Build a dictionary containing all relevant information for returning."""
        success = 'ok' if success else 'failed'
        if isinstance(filepath, str):
            filepath = [filepath]
        files = []
        for filename in filepath:
            files.append({"format": filename[-3:], "filename": filename})
        
        result = {"status": success, "circuit_path": circuit_path, "plot": files, "circuit": circuit}
        return result.update(self.output) or result

    def format_result_ascii(self) -> str:
        """Format the most recent algorithm result as text output."""
        result = ""
        # Algorithm start
        if self.text_mode == "plain":
            result += '\n' + f'{"=" * 25}\n{self.name} Algorithm Result\n{"=" * 25}\n'
        elif self.text_mode == "legacy":
            result += '=' * 70 + '\n' + f"{' ' * 10}⚛️ {self.name} Algorithm Result ⚛️\n" + '=' * 70 + '\n'

        # Solve status
        if self.text_mode == "plain":
            result += f"Status: {self.status}\n\n"
        elif self.text_mode == "legacy":
            result += f"📊 Status: {self.status}\n\n"

        # Input parameters
        if self.text_mode == "plain":
            result += "Input parameters:\n"
        elif self.text_mode == "legacy":
            result += "-" * 70 + '\n' + "📥 Input parameters:\n" + "-" * 70 + "\n"
        result += "\n".join([f"  - {key}: {value}" for key, value in self.input.items()]) + "\n\n"

        # Runtime logs
        if self.text_mode == "plain":
            result += "Runtime logs:\n"
        elif self.text_mode == "legacy":
            result += "-" * 70 + '\n' + "📝 Runtime logs:\n" + "-" * 70 + "\n"
        result += "\n".join([f"  - {line}" for line in self.info]) + "\n\n"

        # Output information
        if self.text_mode == "plain":
            result += "Output information:\n"
        elif self.text_mode == "legacy":
            result += "-" * 70 + '\n' + "📤 Output information:\n" + "-" * 70 + "\n"
        result += "\n".join([f"  - {key}: {value}" for key, value in self.output.items()]) + "\n\n"

        # Summary
        if self.text_mode == "plain":
            result += "Summary:\n"
        elif self.text_mode == "legacy":
            result += "-" * 70 + '\n' + "🔍 Summary:\n" + "-" * 70 + "\n"
        result += f"  {self.summary}\n"

        return result