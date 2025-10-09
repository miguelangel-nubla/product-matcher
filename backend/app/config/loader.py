"""
Configuration loader for YAML backend configuration with environment variable support.
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml

from app.models import BackendConfig, GlobalSettings


def _substitute_env_vars(value: Any) -> Any:
    """
    Recursively substitute environment variables in configuration values.

    Supports patterns like:
    - ${VAR_NAME} - required variable (raises error if not found)
    - ${VAR_NAME:-default} - optional variable with default value
    """
    if isinstance(value, str):
        # Pattern to match ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}"

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            default_value = match.group(3) if match.group(3) is not None else None

            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                raise ValueError(f"Required environment variable {var_name} not found")

        return re.sub(pattern, replace_var, value)

    elif isinstance(value, dict):
        return {k: _substitute_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [_substitute_env_vars(item) for item in value]

    else:
        return value


def load_backends_config() -> dict[str, Any]:
    """
    Load backends configuration from YAML file with environment variable substitution.

    Returns:
        Dictionary containing the parsed and processed configuration
    """
    # Allow environment variable to override config path (for tests)
    config_path_str = os.getenv("BACKENDS_CONFIG_PATH", "/app/config/backends.yaml")
    config_path = Path(config_path_str)

    if not config_path.exists():
        raise FileNotFoundError(f"Backend configuration file not found: {config_path}")

    try:
        with open(config_path) as file:
            config = yaml.safe_load(file)

        # Substitute environment variables
        config = _substitute_env_vars(config)

        return config if isinstance(config, dict) else {}

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in backends configuration: {e}")
    except Exception as e:
        raise ValueError(f"Error loading backends configuration: {e}")


def get_backend_config(backend_name: str) -> BackendConfig:
    """
    Get configuration for a specific backend.

    Args:
        backend_name: Name of the backend (e.g., "mock", "grocy1")

    Returns:
        Typed BackendConfig instance

    Raises:
        ValueError: If backend is not found in configuration
    """
    config = load_backends_config()

    if backend_name not in config.get("backends", {}):
        available = list(config.get("backends", {}).keys())
        raise ValueError(
            f"Backend '{backend_name}' not found. Available backends: {available}"
        )

    backend_config_dict = config["backends"][backend_name]
    return BackendConfig.model_validate(backend_config_dict)


def get_available_backends() -> list[str]:
    """
    Get list of all configured backend names.

    Returns:
        List of backend names
    """
    config = load_backends_config()
    return list(config.get("backends", {}).keys())


def get_global_settings() -> GlobalSettings:
    """
    Get global configuration settings.

    Returns:
        GlobalSettings object
    """
    config = load_backends_config()
    settings = config.get("settings", {})

    return GlobalSettings(
        default_threshold=settings["default_threshold"],
        max_candidates=settings["max_candidates"],
    )


def get_language_configs() -> dict[str, Any]:
    """
    Get language-specific normalizer configurations.

    Returns:
        Dict mapping language codes to normalizer configs
    """
    config = load_backends_config()
    return dict(config.get("languages", {}))
