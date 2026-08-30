import os


class Config:
    """Compatibility configuration for integrations that import Config."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
