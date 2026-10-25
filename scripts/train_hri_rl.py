r"""
Train Fear HRI policy (Double DQN — preferred over tabular Q).

  python scripts/train_hri_rl.py
"""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("train_hri_dqn.py")), run_name="__main__")
