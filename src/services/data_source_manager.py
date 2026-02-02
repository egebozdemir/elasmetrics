"""
Manages multiple Elasticsearch/OpenSearch data sources.
Creates and caches ES clients for each configured source.
"""
import logging
import os
import re
from typing import Dict, Any, Optional, List

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import UnsupportedProductError


class DataSourceManager:
    """
    Singleton manager for ES/OpenSearch data source connections.
    Handles multiple clusters (direct VPC + proxy endpoints like DataHub).
    Implements Singleton pattern consistent with ConfigLoader.
    """
    _instance = None
    _clients: Dict[str, Elasticsearch] = None
    _configs: Dict[str, Dict[str, Any]] = None
    _initialized: bool = False
    _logger = logging.getLogger(__name__)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataSourceManager, cls).__new__(cls)
            cls._instance._clients = {}
            cls._instance._configs = {}
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, config: Dict[str, Any]):
        """
        Initialize all data sources from configuration.

        Args:
            config: Full configuration dictionary containing 'data_sources' key
                   or legacy 'elasticsearch' key for backward compatibility
        """
        if self._initialized:
            self._logger.debug("DataSourceManager already initialized")
            return

        data_sources = config.get('data_sources', {})

        # Backward compatibility: if no data_sources, use elasticsearch config as 'default'
        if not data_sources and 'elasticsearch' in config:
            self._logger.info("Using legacy elasticsearch config as 'default' source")
            data_sources = {'default': config['elasticsearch']}

        if not data_sources:
            raise ValueError("No data sources configured. Add 'data_sources' or 'elasticsearch' to config.")

        for source_name, source_config in data_sources.items():
            try:
                # Apply environment variable overrides
                resolved_config = self._resolve_env_vars(source_config)
                self._configs[source_name] = resolved_config

                client = self._create_client(source_name, resolved_config)
                self._clients[source_name] = client
                self._logger.info(f"Initialized data source: {source_name}")
            except Exception as e:
                self._logger.error(f"Failed to initialize source '{source_name}': {e}")
                raise

        self._initialized = True
        self._logger.info(f"DataSourceManager initialized with {len(self._clients)} source(s)")

    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve environment variable and SSM Parameter Store placeholders in config values.
        Supports:
        - ${VAR_NAME} - Environment variable
        - ${ssm:/path/to/param} - AWS SSM Parameter Store
        """
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_value(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_value(v) if isinstance(v, str) else v
                    for v in value
                ]
            elif isinstance(value, dict):
                resolved[key] = self._resolve_env_vars(value)
            else:
                resolved[key] = value
        return resolved

    def _resolve_value(self, value: str) -> str:
        """
        Resolve a single string value that may contain placeholders.
        Supports:
        - ${VAR_NAME} - Environment variable
        - ${ssm:/path/to/param} - AWS SSM Parameter Store
        """
        if not isinstance(value, str):
            return value

        # Check for SSM parameter syntax: ${ssm:/path/to/param}
        ssm_pattern = r'\$\{ssm:([^}]+)\}'
        ssm_match = re.match(ssm_pattern, value)
        if ssm_match:
            ssm_path = ssm_match.group(1)
            return self._get_ssm_parameter(ssm_path)

        # Check for environment variable syntax: ${VAR_NAME}
        if value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, '')

        return value

    def _get_ssm_parameter(self, path: str) -> str:
        """
        Fetch a parameter from AWS SSM Parameter Store.

        Args:
            path: SSM parameter path (e.g., /PREDICTIVE/PRODUCTION/ELASTICSEARCH/PRODUCT_FEED)

        Returns:
            Parameter value
        """
        try:
            import boto3
            from botocore.exceptions import ClientError

            # Use AWS_REGION from environment or default to us-east-1
            region = os.getenv('AWS_REGION', 'us-east-1')
            ssm_client = boto3.client('ssm', region_name=region)

            response = ssm_client.get_parameter(Name=path, WithDecryption=True)
            value = response['Parameter']['Value']
            self._logger.debug(f"Loaded SSM parameter: {path}")
            return value

        except ImportError:
            self._logger.error("boto3 not installed. Install with: pip install boto3")
            raise RuntimeError(f"boto3 required for SSM parameter: {path}")
        except ClientError as e:
            self._logger.error(f"Failed to get SSM parameter '{path}': {e}")
            raise RuntimeError(f"Cannot fetch SSM parameter '{path}': {e}")

    def get_client(self, source_name: str = None) -> Elasticsearch:
        """
        Get ES client for a data source.

        Args:
            source_name: Name of the data source. If None, returns first available.

        Returns:
            Elasticsearch client instance

        Raises:
            KeyError: If source not found
            RuntimeError: If not initialized
        """
        if not self._initialized:
            raise RuntimeError("DataSourceManager not initialized. Call initialize() first.")

        if source_name is None:
            # Return first available client (backward compatibility)
            if not self._clients:
                raise RuntimeError("No data sources available")
            source_name = list(self._clients.keys())[0]

        if source_name not in self._clients:
            raise KeyError(f"Data source '{source_name}' not found. "
                          f"Available: {list(self._clients.keys())}")
        return self._clients[source_name]

    def get_config(self, source_name: str) -> Dict[str, Any]:
        """Get configuration for a data source."""
        if source_name not in self._configs:
            raise KeyError(f"Data source '{source_name}' not found.")
        return self._configs[source_name]

    def get_path_prefix(self, source_name: str) -> Optional[str]:
        """
        Get path prefix for a data source (e.g., '/v1/proxy' for DataHub).

        Args:
            source_name: Name of the data source

        Returns:
            Path prefix string or None if not configured
        """
        config = self.get_config(source_name)
        return config.get('path_prefix')

    def has_path_prefix(self, source_name: str) -> bool:
        """Check if a data source has a path prefix configured."""
        return self.get_path_prefix(source_name) is not None

    def get_all_clients(self) -> Dict[str, Elasticsearch]:
        """Get all initialized clients."""
        return self._clients.copy()

    def list_sources(self) -> List[str]:
        """List all available source names."""
        return list(self._clients.keys())

    def _create_client(self, name: str, config: Dict[str, Any]) -> Elasticsearch:
        """
        Create ES client from source configuration.
        Works with both direct ES and proxy endpoints (like DataHub).
        """
        hosts = config.get('hosts', ['http://localhost:9200'])

        # Ensure hosts is a list
        if isinstance(hosts, str):
            hosts = [hosts]

        connection_params = {
            'hosts': hosts,
            'timeout': config.get('timeout', 30),
            'verify_certs': config.get('verify_certs', True),
        }

        # Authentication - basic auth
        username = config.get('username')
        password = config.get('password')
        if username and password:
            connection_params['basic_auth'] = (username, password)

        # Authentication - API key
        api_key = config.get('api_key')
        if api_key:
            connection_params['api_key'] = api_key

        # Custom headers (for proxy authentication like DataHub)
        headers = config.get('headers')
        if headers:
            connection_params['headers'] = headers

        # SSL settings
        if config.get('use_ssl', False):
            connection_params['use_ssl'] = True

        # CA certs
        ca_certs = config.get('ca_certs')
        if ca_certs:
            connection_params['ca_certs'] = ca_certs

        self._logger.debug(f"Creating client for '{name}' with hosts: {hosts}")

        client = Elasticsearch(**connection_params)

        # Validate connection
        self._validate_connection(name, client)

        return client

    def _validate_connection(self, name: str, client: Elasticsearch) -> bool:
        """Validate that a client can connect."""
        try:
            # Try cluster health first
            health = client.cluster.health()
            cluster_name = health.get('cluster_name', 'unknown')
            self._logger.info(f"Source '{name}' connected to cluster: {cluster_name}")
            return True
        except UnsupportedProductError as e:
            # AWS OpenSearch detected - this is fine, connection works
            self._logger.warning(f"Source '{name}' is AWS OpenSearch (product check bypassed)")
            return True
        except Exception as e:
            error_msg = str(e)
            # Handle AWS OpenSearch product check errors
            if 'not Elasticsearch' in error_msg or 'unknown product' in error_msg:
                self._logger.warning(f"Source '{name}' is AWS OpenSearch (product check bypassed)")
                return True

            # Try a lightweight fallback check
            try:
                client.cat.indices(h='index', format='json')
                self._logger.info(f"Source '{name}' connected (via fallback check)")
                return True
            except Exception:
                self._logger.error(f"Failed to connect to source '{name}': {e}")
                raise ConnectionError(f"Cannot connect to data source '{name}': {e}")

    def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all data sources.

        Returns:
            Dictionary with health status of each source
        """
        results = {}

        for name, client in self._clients.items():
            try:
                health = client.cluster.health()
                results[name] = {
                    'status': 'healthy',
                    'cluster_name': health.get('cluster_name', 'N/A'),
                    'cluster_status': health.get('status', 'N/A'),
                    'nodes': health.get('number_of_nodes', 'N/A'),
                }
            except Exception as e:
                error_msg = str(e)
                if 'not Elasticsearch' in error_msg or 'unknown product' in error_msg:
                    results[name] = {
                        'status': 'healthy',
                        'cluster_name': 'AWS OpenSearch',
                        'cluster_status': 'connected',
                        'nodes': 'N/A',
                    }
                else:
                    results[name] = {
                        'status': 'unhealthy',
                        'error': str(e),
                    }

        return results

    @classmethod
    def reset(cls):
        """Reset singleton (useful for testing)."""
        if cls._instance:
            # Close all clients
            for client in cls._instance._clients.values():
                try:
                    client.close()
                except Exception:
                    pass
            cls._instance._clients.clear()
            cls._instance._configs.clear()
            cls._instance._initialized = False
        cls._instance = None


# Convenience function
def get_data_source_manager() -> DataSourceManager:
    """Get the singleton DataSourceManager instance."""
    return DataSourceManager()
