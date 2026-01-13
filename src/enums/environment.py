"""Environment enumeration for deployment environments."""
from enum import Enum


class Environment(Enum):
    """Supported deployment environments."""
    STAGING = 'STAGING'
    PRODUCTION = 'PRODUCTION'
    
    @staticmethod
    def get_all() -> list[str]:
        """
        Get all environment values.
        
        Returns:
            List of environment value strings
        """
        return [e.value for e in Environment]
    
    @staticmethod
    def check_is_production(env: str) -> bool:
        """
        Check if the given environment is production.
        
        Args:
            env: Environment string to check
            
        Returns:
            True if production, False otherwise
        """
        return env == Environment.PRODUCTION.value

