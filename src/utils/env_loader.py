"""
Environment loader utility for loading environment-specific configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional


class EnvLoader:
    """
    Utility class for loading environment variables from .env files.
    Supports environment-specific files (.env.staging, .env.production).
    """
    
    _loaded = False
    
    @classmethod
    def load_environment_config(cls, env: Optional[str] = None, env_file: Optional[str] = None) -> None:
        """
        Load environment configuration from .env file.
        
        Args:
            env: Environment name (STAGING, PRODUCTION). If None, uses ENV environment variable.
            env_file: Explicit path to .env file. If provided, env parameter is ignored.
            
        Raises:
            FileNotFoundError: If specified env file doesn't exist
        """
        if cls._loaded and env_file is None:
            return
        
        if env_file:
            env_file_path = Path(env_file)
        else:
            env_value = env or os.getenv('ENV')
            base_dir = Path(__file__).parent.parent.parent
            
            if env_value:
                env_file_path = base_dir / f".env.{env_value.lower()}"
                if not env_file_path.exists():
                    env_file_path = base_dir / ".env"
            else:
                env_file_path = base_dir / ".env"
        
        if env_file_path.exists():
            load_dotenv(env_file_path, override=True)
            cls._loaded = True
        elif env_file:
            raise FileNotFoundError(f"Environment file {env_file_path} not found.")
    
    @classmethod
    def reset(cls):
        """Reset the loaded state (useful for testing)."""
        cls._loaded = False

