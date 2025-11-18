#!/usr/bin/env python3
"""
Quick environment verification script for Healthcare-RAG.

This script attempts to import the key Python modules used by the
project and prints version information or a clear "MISSING" marker.

Run after creating/activating the centralized venv and installing
`requirements.txt` to confirm everything is active:

    python3 scripts/verify_env.py

Exit code: 0 = all present, 1 = one or more missing
"""
import importlib
import sys

CHECKS = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("pydantic", "pydantic"),
    ("python-multipart", "multipart"),
    ("chromadb", "chromadb"),
    ("sentence-transformers", "sentence_transformers"),
    ("torch", "torch"),
    ("transformers", "transformers"),
    ("huggingface-hub", "huggingface_hub"),
    ("onnxruntime", "onnxruntime"),
    ("pyarrow", "pyarrow"),
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("datasets", "datasets"),
    ("requests", "requests"),
    ("PyPDF2", "PyPDF2"),
    ("python-dotenv", "dotenv"),
    ("tqdm", "tqdm"),
    ("PyMuPDF", "fitz"),
    ("langchain", "langchain"),
]


def check_module(pkg_name: str, module_name: str):
    try:
        m = importlib.import_module(module_name)
        ver = getattr(m, '__version__', None)
        if ver is None:
            # Try common places for version
            ver = getattr(m, 'VERSION', None) or getattr(m, 'version', None)
        print(f"OK  - {pkg_name} (import '{module_name}') - version: {ver}")
        return True
    except Exception as e:
        print(f"MISSING - {pkg_name} (import '{module_name}') - {e}")
        return False


def main():
    all_ok = True
    print("Verifying environment imports for Healthcare-RAG...\n")
    for pkg, mod in CHECKS:
        ok = check_module(pkg, mod)
        all_ok = all_ok and ok

    if all_ok:
        print("\nAll checked packages are importable.")
        sys.exit(0)
    else:
        print("\nOne or more packages are missing or failed to import.")
        print("If imports failed, run: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == '__main__':
    main()
