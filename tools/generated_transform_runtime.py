"""Type-preserving, temporary execution of generated transformation functions."""

from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from ..config import settings
from .multi_table_engine import check_frame_limits

DEFAULT_IMPORTS = "pandas,numpy,math,statistics,re,datetime,collections,itertools,functools,decimal,fractions,json"


def allowed_imports() -> set[str]:
    names = {
        s.strip()
        for s in os.getenv("TRANSFORM_ALLOWED_IMPORTS", DEFAULT_IMPORTS).split(",")
        if s.strip()
    }
    forbidden = {
        "os",
        "sys",
        "pathlib",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "http",
        "builtins",
        "pickle",
        "importlib",
        "ctypes",
        "shutil",
        "io",
    }
    if (
        any(not n.isidentifier() or n.startswith("_") for n in names)
        or names & forbidden
    ):
        raise ValueError("TRANSFORM_ALLOWED_IMPORTS contains an unsafe module name")
    return names


WRAPPER = """from __future__ import annotations
import builtins
import importlib
import json
import os
import pickle
import sys
from pathlib import Path
import pandas as pd
import numpy as np

with open("request.json", encoding="utf-8") as handle:
    request = json.load(handle)
limits = request["limits"]
limit_support = "timeout_only"
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (limits["memory_mb"] * 1024**2, limits["memory_mb"] * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (limits["timeout_seconds"] + 1, limits["timeout_seconds"] + 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["output_mb"] * 1024**2, limits["output_mb"] * 1024**2))
    limit_support = "posix_address_space_cpu_file_size"
except ImportError:
    pass
# Application-level side-effect checks complement validation. They do not
# constitute a kernel sandbox. Enable after wrapper imports and before agent code.
workspace = Path.cwd().resolve()
read_roots = [workspace] + [Path(p).resolve() for p in sys.path if p and Path(p).is_dir()]
def check_path(path, writing=False):
    if isinstance(path, int):
        return
    resolved = Path(os.fsdecode(path)).resolve()
    roots = [workspace] if writing else read_roots
    if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
        raise PermissionError("Generated code attempted access outside its managed workspace or dependency files")
def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.", "os.exec", "os.spawn")) or event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.chdir", "os.symlink", "os.link"}:
        raise PermissionError("Generated code attempted a network or system operation")
    if event == "open":
        path, mode, flags = args
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        check_path(path, writing)
    elif event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.truncate"}:
        check_path(args[0], True)
    elif event in {"os.rename", "os.replace"}:
        check_path(args[0], True)
        check_path(args[1], True)
    elif event in {"os.listdir", "os.scandir"} and args[0] is not None:
        check_path(args[0])
sys.addaudithook(audit)
approved = set(request["approved_imports"])
def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in approved or any(part.startswith("_") for part in name.split(".")):
        raise ImportError("Import is not approved: " + name)
    return builtins.__import__(name, globals, locals, fromlist, 0)

safe_builtins = {name: getattr(builtins, name) for name in (
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float", "frozenset", "int",
    "isinstance", "issubclass", "iter", "len", "list", "map", "max", "min", "next", "pow", "print",
    "range", "repr", "reversed", "round", "set", "slice", "sorted", "str", "sum", "tuple", "type",
    "zip", "Exception", "ValueError", "TypeError", "KeyError", "RuntimeError", "IndexError", "StopIteration")}
safe_builtins["__import__"] = safe_import
with open("inputs.pkl", "rb") as handle:
    frames = pickle.load(handle)
namespace = {"pd": pd, "np": np, "__builtins__": safe_builtins}
np.random.seed(0)
with open("generated_transform.py", encoding="utf-8") as handle:
    code = compile(handle.read(), "generated_transform.py", "exec")
exec(code, namespace, namespace)
argument = ({name: frame.copy(deep=True) for name, frame in frames.items()}
            if request["input_contract"] == "datasets" else next(iter(frames.values())).copy(deep=True))
result = namespace["transform_data"](argument)
if isinstance(result, pd.DataFrame):
    result = {"result": result}
if not isinstance(result, dict) or not result or not all(isinstance(k, str) and isinstance(v, pd.DataFrame) for k, v in result.items()):
    raise TypeError("Return a DataFrame or a nonempty dictionary of named DataFrames")
if len(result) > request["max_outputs"]:
    raise ValueError("Too many output tables")
for name, frame in result.items():
    if len(frame) > limits["max_rows"] or frame.memory_usage(deep=True).sum() > limits["frame_memory_mb"] * 1024**2:
        raise ValueError("Generated result exceeds configured row or memory limit")
with open("results.pkl", "wb") as handle:
    pickle.dump(result, handle, protocol=pickle.HIGHEST_PROTOCOL)
with open("execution.json", "w", encoding="utf-8") as handle:
    versions = {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__}
    for root in approved:
        module = sys.modules.get(root)
        version = getattr(module, "__version__", None)
        if version is not None:
            versions[root] = str(version)
    json.dump({"limit_support": limit_support, "versions": versions}, handle)
"""


def run_generated_transform(
    code: str, frames: dict[str, pd.DataFrame]
) -> tuple[dict[str, pd.DataFrame], dict]:
    from .data_transformation_tools import validate_generated_python_transform_code

    validation = validate_generated_python_transform_code(code)
    if not validation["valid"]:
        raise ValueError(
            "Generated Python failed validation: " + "; ".join(validation["errors"])
        )
    if validation["input_contract"] == "data" and len(frames) != 1:
        raise ValueError(
            "transform_data(data) requires exactly one input; use transform_data(datasets) for multiple inputs"
        )
    with tempfile.TemporaryDirectory(prefix="plotworks_transform_") as folder:
        run = Path(folder)
        with (run / "inputs.pkl").open("wb") as handle:
            pickle.dump(frames, handle, protocol=pickle.HIGHEST_PROTOCOL)
        (run / "generated_transform.py").write_text(code, encoding="utf-8")
        (run / "run_transform.py").write_text(WRAPPER, encoding="utf-8")
        request = {
            "input_contract": validation["input_contract"],
            "approved_imports": sorted(allowed_imports()),
            "max_outputs": settings.max_bundle_datasets,
            "limits": {
                "memory_mb": settings.generated_transform_memory_mb,
                "timeout_seconds": settings.data_transform_timeout_seconds,
                "output_mb": settings.max_transform_output_mb,
                "max_rows": settings.max_transform_rows,
                "frame_memory_mb": settings.max_transform_memory_mb,
            },
        }
        (run / "request.json").write_text(json.dumps(request), encoding="utf-8")
        # Use an allowlist: model credentials, cloud tokens, and unrelated variables
        # never reach generated code. Inputs are wrapper-created DataFrame pickles.
        env = {
            key: os.environ[key]
            for key in (
                "PATH",
                "SYSTEMROOT",
                "WINDIR",
                "COMSPEC",
                "LANG",
                "LC_ALL",
                "TZ",
            )
            if key in os.environ
        }
        env.update(
            {
                "PYTHONNOUSERSITE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONHASHSEED": "0",
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
                "HOME": str(run),
                "USERPROFILE": str(run),
                "TMPDIR": str(run),
                "TEMP": str(run),
                "TMP": str(run),
            }
        )
        for path in (
            run / "inputs.pkl",
            run / "request.json",
            run / "generated_transform.py",
            run / "run_transform.py",
        ):
            path.chmod(0o400)
        with (
            (run / "stdout.log").open("wb") as stdout,
            (run / "stderr.log").open("wb") as stderr,
        ):
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", "run_transform.py"],
                    check=False,
                    cwd=run,
                    env=env,
                    stdout=stdout,
                    stderr=stderr,
                    timeout=settings.data_transform_timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise ValueError(
                    f"Generated transformation exceeded {settings.data_transform_timeout_seconds}-second timeout"
                ) from exc

        def log_text(name):
            with (run / name).open("rb") as handle:
                return handle.read(16000).decode("utf-8", errors="replace")

        logs = {
            "stdout": log_text("stdout.log"),
            "stderr": log_text("stderr.log"),
            "returncode": proc.returncode,
        }
        if proc.returncode or not (run / "results.pkl").exists():
            raise ValueError(
                "Generated transformation failed: " + logs["stderr"][-6000:]
            )
        if (
            run / "results.pkl"
        ).stat().st_size > settings.max_transform_output_mb * 1024**2:
            raise ValueError("Generated output exceeds MAX_TRANSFORM_OUTPUT_MB")
        with (run / "results.pkl").open("rb") as handle:
            result = pickle.load(handle)
        for name, frame in result.items():
            if (
                not name
                or len(name) > 80
                or not all(c.isalnum() or c in "_-" for c in name)
            ):
                raise ValueError(
                    "Generated output IDs must use letters, digits, _ or -"
                )
            check_frame_limits(frame)
        total = sum(int(f.memory_usage(deep=True).sum()) for f in result.values())
        if total > settings.max_transform_memory_mb * 1024**2:
            raise ValueError(
                "Combined generated outputs exceed MAX_TRANSFORM_MEMORY_MB"
            )
        logs.update(json.loads((run / "execution.json").read_text(encoding="utf-8")))
        return result, logs
