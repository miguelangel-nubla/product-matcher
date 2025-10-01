#!/usr/bin/env python3
"""
Download required spaCy language models.
This script can be used both in Docker containers and during development.
"""

import subprocess
import sys

REQUIRED_MODELS = [
    "en_core_web_sm",  # English
    "es_core_news_sm",  # Spanish
]


def download_model(model_name: str) -> bool:
    """Download a spaCy model if not already installed."""
    try:
        import spacy

        # Try to load the model to check if it's already installed
        spacy.load(model_name)
        return True
    except (ImportError, OSError):
        pass

    try:
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    """Download all required spaCy models."""
    failed_models: list[str] = []

    for model in REQUIRED_MODELS:
        if not download_model(model):
            failed_models.append(model)

    if failed_models:
        sys.exit(1)


if __name__ == "__main__":
    main()
