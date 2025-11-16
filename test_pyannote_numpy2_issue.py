#!/usr/bin/env python3
"""
Minimal script to reproduce pyannote.audio incompatibility with numpy 2.0

This script demonstrates that pyannote.audio fails to import with numpy 2.0
due to the use of np.NaN which was removed in numpy 2.0 (replaced with np.nan).

Error: AttributeError: `np.NaN` was removed in the NumPy 2.0 release. Use `np.nan` instead.

To reproduce:
1. pip install numpy>=2.0 pyannote.audio
2. python test_pyannote_numpy2_issue.py
"""

import numpy as np

print(f"NumPy version: {np.__version__}")

# This import will fail with numpy 2.0+
try:
    from pyannote.audio import Pipeline
    print("✓ Successfully imported pyannote.audio.Pipeline")
except AttributeError as e:
    print(f"✗ Failed to import pyannote.audio.Pipeline")
    print(f"  Error: {e}")
    raise
