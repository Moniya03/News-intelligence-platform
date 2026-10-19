"""Configuration loader module for News Intelligence Platform.

Loads YAML configuration files with environment variable interpolation
(supporting `${VAR:-default}` and `${VAR}` syntax).
"""

import os
import re
from pathlib import Path
from typing import Any, Dict
import yaml

CONFIG_PATH_DEFAULT = Path(__file__).resolve().parent.parent / "config" / "default.yaml"

ENV_VAR_PATTERN = re.compile(r"\$\{([^:-]+)(?::-(.*?))?\}")


def _expand_env_vars(content: str) -> str:
    """Expand environment variables in ${VAR:-default} or ${VAR} format."""
    def _replacer(match: re.Match) -> str:
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) is not None else ""
        return os.environ.get(var_name, default_val)

    return ENV_VAR_PATTERN.sub(_replacer, content)


def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load and parse the project YAML configuration.

    Args:
        config_path: Optional path to config file. Defaults to `config/default.yaml`.

    Returns:
        Dict[str, Any]: Parsed configuration dictionary.
    """
    path = Path(config_path) if config_path else CONFIG_PATH_DEFAULT
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    expanded_text = _expand_env_vars(raw_text)
    config = yaml.safe_load(expanded_text) or {}
    return config


# Global cached config instance
_CONFIG_CACHE: Dict[str, Any] | None = None


def get_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return cached configuration or load on demand."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None or config_path is not None:
        _CONFIG_CACHE = load_config(config_path)
    return _CONFIG_CACHE
