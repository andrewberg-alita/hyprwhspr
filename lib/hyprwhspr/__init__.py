"""
hyprwhspr package
"""

import os
from pathlib import Path

def get_project_root() -> Path:
    """
    Resolve the project root directory.
    
    Priority:
    1. HYPRWHSPR_ROOT environment variable
    2. Local development root (heuristically determined)
    3. System install default
    """
    # 1. Environment variable
    env_root = os.environ.get('HYPRWHSPR_ROOT')
    if env_root:
        return Path(env_root)

    # 2. Local development check
    # Structure: .../root/lib/hyprwhspr/__init__.py
    try:
        current_file = Path(__file__).resolve()
        # Go up 3 levels: hyprwhspr -> lib -> root
        potential_root = current_file.parent.parent.parent
        
        # Check for characteristic files
        if (potential_root / "pyproject.toml").exists() or \
           (potential_root / "bin" / "hyprwhspr").exists():
            return potential_root
    except Exception:
        pass

    # 3. System default fallback
    return Path('/usr/lib/hyprwhspr')
