"""
Configuration loader utility for loading and validating application configuration.
"""
import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from .env_loader import EnvLoader


class ConfigLoader:
    """
    Singleton class for loading and managing application configuration.
    Implements Singleton pattern to ensure single configuration instance.
    Supports both YAML-based config and environment variable overrides.
    Integrates with AWS Parameter Store for secure credential management.
    """
    _instance = None
    _config: Dict[str, Any] = None
    _logger = logging.getLogger(__name__)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def load_config(
        self, 
        config_path: Optional[str] = None,
        config_json: Optional[str] = None,
        env: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load configuration from YAML file and/or JSON string.
        
        Args:
            config_path: Path to configuration file. If None, uses default path.
            config_json: JSON string to override configuration (for Airflow integration)
            env: Environment name (STAGING, PRODUCTION) for loading .env files
            
        Returns:
            Dictionary containing configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
            json.JSONDecodeError: If config_json is invalid
        """
        if self._config is not None:
            return self._config
        
        EnvLoader.load_environment_config(env)
        
        if config_json is None:
            config_json = os.getenv('CONFIG_JSON')
        
        if config_json:
            self._config = self._load_from_json(config_json)
        else:
            self._config = self._load_from_yaml(config_path)
        
        self._validate_config()
        self._apply_env_overrides()
        
        return self._config
    
    def _load_from_yaml(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML config file
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Default config path
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "config.yaml"
        
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_from_json(self, config_json: str) -> Dict[str, Any]:
        """
        Load configuration from JSON string.
        
        Args:
            config_json: JSON string containing configuration
            
        Returns:
            Configuration dictionary
            
        Raises:
            json.JSONDecodeError: If JSON is invalid
        """
        try:
            return json.loads(config_json)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON configuration: {e.msg}",
                e.doc,
                e.pos
            )
    
    def _validate_config(self):
        """Validate required configuration fields."""
        required_sections = ['elasticsearch', 'mysql', 'metrics']
        
        for section in required_sections:
            if section not in self._config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        if 'hosts' not in self._config['elasticsearch']:
            raise ValueError("Elasticsearch hosts must be specified")
        
        mysql_required = ['host', 'database', 'user', 'password']
        for field in mysql_required:
            if field not in self._config['mysql']:
                raise ValueError(f"Missing required MySQL field: {field}")
    
    def _apply_env_overrides(self):
        """
        Apply environment variable overrides to configuration.
        Supports AWS Parameter Store integration for secure credential management.
        """
        use_parameter_store = os.getenv('USE_PARAMETER_STORE', 'false').lower() == 'true'
        local_dev_mode = os.getenv('LOCAL_DEV_MODE', 'false').lower() == 'true'
        
        if use_parameter_store and not local_dev_mode:
            self._load_from_parameter_store()
        
        if os.getenv('ES_HOSTS'):
            self._config['elasticsearch']['hosts'] = os.getenv('ES_HOSTS').split(',')
        if os.getenv('ES_USERNAME'):
            self._config['elasticsearch']['username'] = os.getenv('ES_USERNAME')
        if os.getenv('ES_PASSWORD'):
            self._config['elasticsearch']['password'] = os.getenv('ES_PASSWORD')
        if os.getenv('ES_API_KEY'):
            self._config['elasticsearch']['api_key'] = os.getenv('ES_API_KEY')
        if os.getenv('ES_TIMEOUT'):
            self._config['elasticsearch']['timeout'] = int(os.getenv('ES_TIMEOUT'))
        if os.getenv('ES_VERIFY_CERTS'):
            self._config['elasticsearch']['verify_certs'] = os.getenv('ES_VERIFY_CERTS').lower() == 'true'
        
        if os.getenv('MYSQL_HOST'):
            self._config['mysql']['host'] = os.getenv('MYSQL_HOST')
        if os.getenv('MYSQL_PORT'):
            self._config['mysql']['port'] = int(os.getenv('MYSQL_PORT'))
        if os.getenv('MYSQL_DATABASE'):
            self._config['mysql']['database'] = os.getenv('MYSQL_DATABASE')
        if os.getenv('MYSQL_USER'):
            self._config['mysql']['user'] = os.getenv('MYSQL_USER')
        if os.getenv('MYSQL_PASSWORD'):
            self._config['mysql']['password'] = os.getenv('MYSQL_PASSWORD')
        if os.getenv('MYSQL_CHARSET'):
            self._config['mysql']['charset'] = os.getenv('MYSQL_CHARSET')
        if os.getenv('MYSQL_POOL_SIZE'):
            self._config['mysql']['pool_size'] = int(os.getenv('MYSQL_POOL_SIZE'))
        if os.getenv('MYSQL_POOL_RECYCLE'):
            self._config['mysql']['pool_recycle'] = int(os.getenv('MYSQL_POOL_RECYCLE'))
        
        if os.getenv('METRICS_CONFIG'):
            try:
                metrics_override = json.loads(os.getenv('METRICS_CONFIG'))
                self._config['metrics'].update(metrics_override)
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON
        
        if os.getenv('METRICS_INCLUDE_PATTERNS'):
            self._config['metrics']['include_patterns'] = os.getenv('METRICS_INCLUDE_PATTERNS').split(',')
        if os.getenv('METRICS_EXCLUDE_PATTERNS'):
            self._config['metrics']['exclude_patterns'] = os.getenv('METRICS_EXCLUDE_PATTERNS').split(',')
        
        if 'scheduling' not in self._config:
            self._config['scheduling'] = {}
        
        if os.getenv('SCHEDULING_ENABLED'):
            self._config['scheduling']['enabled'] = os.getenv('SCHEDULING_ENABLED').lower() == 'true'
        if os.getenv('SCHEDULING_CRON'):
            self._config['scheduling']['cron'] = os.getenv('SCHEDULING_CRON')
        if os.getenv('SCHEDULING_TIMEZONE'):
            self._config['scheduling']['timezone'] = os.getenv('SCHEDULING_TIMEZONE')
        
        if 'logging' not in self._config:
            self._config['logging'] = {}
        
        if os.getenv('LOG_LEVEL'):
            self._config['logging']['level'] = os.getenv('LOG_LEVEL')
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key using dot notation.
        
        Args:
            key: Configuration key (e.g., 'elasticsearch.hosts')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if self._config is None:
            self.load_config()
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_elasticsearch_config(self) -> Dict[str, Any]:
        """Get Elasticsearch configuration."""
        return self.get('elasticsearch', {})
    
    def get_mysql_config(self) -> Dict[str, Any]:
        """Get MySQL configuration."""
        return self.get('mysql', {})
    
    def get_metrics_config(self) -> Dict[str, Any]:
        """Get metrics configuration."""
        return self.get('metrics', {})
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration dictionary."""
        if self._config is None:
            self.load_config()
        return self._config
    
    def _load_from_parameter_store(self):
        """
        Load credentials from AWS Parameter Store.
        Uses environment-specific paths based on ENV variable.
        """
        try:
            from ..services.parameter_store_service import ParameterStoreService
            
            env = os.getenv('ENV', 'STAGING').upper()
            param_prefix = os.getenv('PARAMETER_STORE_PREFIX', '/ELASMETRICS')
            
            self._logger.info(f"Loading configuration from Parameter Store (ENV={env})")
            
            try:
                es_password = ParameterStoreService.get_parameter(
                    f"{param_prefix}/{env}/ELASTICSEARCH/PASSWORD"
                )
                self._config['elasticsearch']['password'] = es_password
                self._logger.info("Loaded Elasticsearch password from Parameter Store")
            except RuntimeError as e:
                self._logger.warning(f"Could not load ES password from Parameter Store: {e}")
            
            try:
                es_username = ParameterStoreService.get_parameter(
                    f"{param_prefix}/{env}/ELASTICSEARCH/USERNAME",
                    default=None
                )
                if es_username:
                    self._config['elasticsearch']['username'] = es_username
                    self._logger.info("Loaded Elasticsearch username from Parameter Store")
            except RuntimeError as e:
                self._logger.warning(f"Could not load ES username from Parameter Store: {e}")
            
            try:
                es_api_key = ParameterStoreService.get_parameter(
                    f"{param_prefix}/{env}/ELASTICSEARCH/API_KEY",
                    default=None
                )
                if es_api_key:
                    self._config['elasticsearch']['api_key'] = es_api_key
                    self._logger.info("Loaded Elasticsearch API key from Parameter Store")
            except RuntimeError as e:
                self._logger.warning(f"Could not load ES API key from Parameter Store: {e}")
            
            try:
                mysql_password = ParameterStoreService.get_parameter(
                    f"{param_prefix}/{env}/MYSQL/PASSWORD"
                )
                self._config['mysql']['password'] = mysql_password
                self._logger.info("Loaded MySQL password from Parameter Store")
            except RuntimeError as e:
                self._logger.warning(f"Could not load MySQL password from Parameter Store: {e}")
            
            try:
                mysql_user = ParameterStoreService.get_parameter(
                    f"{param_prefix}/{env}/MYSQL/USER",
                    default=None
                )
                if mysql_user:
                    self._config['mysql']['user'] = mysql_user
                    self._logger.info("Loaded MySQL username from Parameter Store")
            except RuntimeError as e:
                self._logger.warning(f"Could not load MySQL username from Parameter Store: {e}")
            
            try:
                mysql_host = ParameterStoreService.get_parameter(
                    f"{param_prefix}/{env}/MYSQL/HOST",
                    default=None
                )
                if mysql_host:
                    self._config['mysql']['host'] = mysql_host
                    self._logger.info("Loaded MySQL host from Parameter Store")
            except RuntimeError as e:
                self._logger.warning(f"Could not load MySQL host from Parameter Store: {e}")
                
        except ImportError:
            self._logger.error("boto3 not installed. Install with: pip install boto3")
            raise RuntimeError("boto3 required for Parameter Store integration")
        except Exception as e:
            self._logger.error(f"Failed to load configuration from Parameter Store: {e}")
            self._logger.warning("Falling back to environment variables or config file values")
    
    @classmethod
    def reset(cls):
        """Reset configuration (useful for testing)."""
        if cls._instance is not None:
            cls._instance._config = None
