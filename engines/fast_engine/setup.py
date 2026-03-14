# fast_engine/setup.py
from __future__ import annotations

import sys
from pathlib import Path

from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

THIS_DIR = Path(__file__).resolve().parent

# Correct compiler flags per platform.
# MSVC needs /std:c++17 (NOT -std=c++17)
if sys.platform.startswith("win"):
    extra_compile_args = ["/std:c++17", "/O2"]
else:
    extra_compile_args = ["-std=c++17", "-O3"]

ext_modules = [
    Pybind11Extension(
        # IMPORTANT: compile as a submodule INSIDE the package
        # so it won't conflict with the package name "fast_engine"
        name="fast_engine._core",
        sources=[str(THIS_DIR / "src" / "fast_engine.cpp")],
        cxx_std=17,
        extra_compile_args=extra_compile_args,
    )
]

setup(
    name="fast_engine",
    version="0.0.1",
    description="Fast chess engine (C++/pybind11)",
    packages=["fast_engine"],        # IMPORTANT: treat folder as package
    package_dir={"fast_engine": "."}, # package is THIS folder
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)