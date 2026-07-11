import os
from pathlib import Path
import sys


def configure_nvidia_dll_paths() -> None:
    if os.name != "nt":
        return
    site_packages = Path(sys.prefix) / "Lib" / "site-packages"
    candidates = [
        site_packages / "nvidia" / "cu13" / "bin" / "x86_64",
        site_packages / "nvidia" / "cudnn" / "bin",
    ]
    for path in candidates:
        if not path.is_dir():
            continue
        path_text = str(path)
        os.environ["PATH"] = path_text + os.pathsep + os.environ.get("PATH", "")
        try:
            os.add_dll_directory(path_text)
        except (AttributeError, FileNotFoundError, OSError):
            pass
