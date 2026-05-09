#!/usr/bin/env python3
"""Strong-tier wrapper for Hermes Obsidian wake-gate checks."""

from pathlib import Path
import os
import runpy


if __name__ == "__main__":
    os.environ["OBSIDIAN_AGENT_TIER"] = "strong"
    runpy.run_path(str(Path(__file__).with_name("hermes-obsidian-gate.py")), run_name="__main__")
