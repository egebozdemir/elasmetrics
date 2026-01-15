"""
AWS Systems Manager Parameter Store service.
Handles fetching configuration and secrets from AWS Parameter Store.
"""
import os
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Optional, Dict, Any


class ParameterStoreService:
    """
    Service for accessing AWS Systems Manager Parameter Store.
    Implements singleton pattern for SSM client.
    """
    
    _ssm_client = None
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def _get_client(cls):
        """
        Get or create SSM client with proper AWS configuration.
        
        Returns:
            boto3 SSM client
        """
        if cls._ssm_client is None:
            region = os.getenv('AWS_REGION', 'eu-west-1')
            cls._logger.info(f"Initializing SSM client for region: {region}")
            cls._ssm_client = boto3.client('ssm', region_name=region)
        return cls._ssm_client
    
    @classmethod
    def get_parameter(
        cls,
        param_name: str,
        with_decryption: bool = True,
        default: Optional[str] = None
    ) -> str:
        """
        Retrieve a parameter value from AWS Systems Manager Parameter Store.
        
        Args:
            param_name: The name/path of the parameter (e.g., '/app/db/password')
            with_decryption: Whether to decrypt SecureString parameters
            default: Default value if parameter not found (optional)
            
        Returns:
            The parameter value as string
            
        Raises:
            RuntimeError: If parameter cannot be fetched and no default provided
        """
        try:
            cls._logger.debug(f"Fetching parameter: {param_name}")
            client = cls._get_client()
            
            response = client.get_parameter(
                Name=param_name,
                WithDecryption=with_decryption
            )
            
            value = response['Parameter']['Value']
            cls._logger.info(f"Successfully fetched parameter: {param_name}")
            return value
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ParameterNotFound':
                if default is not None:
                    cls._logger.warning(
                        f"Parameter {param_name} not found, using default value"
                    )
                    return default
                raise RuntimeError(
                    f"Parameter {param_name} not found in Parameter Store"
                )
            
            cls._logger.error(f"Failed to fetch parameter {param_name}: {e}")
            raise RuntimeError(f"Failed to fetch parameter {param_name}: {e}")
            
        except NoCredentialsError:
            error_msg = (
                "AWS credentials not found. "
                "Set LOCAL_DEV_MODE=true for local development or configure AWS credentials."
            )
            cls._logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    @classmethod
    def get_parameters_by_path(
        cls,
        path: str,
        with_decryption: bool = True,
        recursive: bool = False
    ) -> Dict[str, str]:
        """
        Retrieve multiple parameters under a specific path.
        
        Args:
            path: The parameter path prefix (e.g., '/app/db/')
            with_decryption: Whether to decrypt SecureString parameters
            recursive: Whether to retrieve nested paths
            
        Returns:
            Dictionary mapping parameter names to values
            
        Raises:
            RuntimeError: If parameters cannot be fetched
        """
        try:
            cls._logger.debug(f"Fetching parameters by path: {path}")
            client = cls._get_client()
            
            parameters = {}
            next_token = None
            
            while True:
                kwargs = {
                    'Path': path,
                    'WithDecryption': with_decryption,
                    'Recursive': recursive
                }
                
                if next_token:
                    kwargs['NextToken'] = next_token
                
                response = client.get_parameters_by_path(**kwargs)
                
                for param in response['Parameters']:
                    # Strip the path prefix from parameter name for cleaner keys
                    key = param['Name'].replace(path, '').lstrip('/')
                    parameters[key] = param['Value']
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
            
            cls._logger.info(
                f"Successfully fetched {len(parameters)} parameters from {path}"
            )
            return parameters
            
        except ClientError as e:
            cls._logger.error(f"Failed to fetch parameters by path {path}: {e}")
            raise RuntimeError(f"Failed to fetch parameters by path {path}: {e}")
    
    @classmethod
    def put_parameter(
        cls,
        param_name: str,
        param_value: str,
        param_type: str = 'SecureString',
        description: str = '',
        overwrite: bool = True
    ) -> None:
        """
        Store a parameter in AWS Parameter Store.
        
        Args:
            param_name: The name/path of the parameter
            param_value: The value to store
            param_type: Parameter type ('String', 'StringList', or 'SecureString')
            description: Optional description
            overwrite: Whether to overwrite existing parameter
            
        Raises:
            RuntimeError: If parameter cannot be stored
        """
        try:
            cls._logger.debug(f"Storing parameter: {param_name}")
            client = cls._get_client()
            
            kwargs = {
                'Name': param_name,
                'Value': param_value,
                'Type': param_type,
                'Overwrite': overwrite
            }
            
            if description:
                kwargs['Description'] = description
            
            client.put_parameter(**kwargs)
            cls._logger.info(f"Successfully stored parameter: {param_name}")
            
        except ClientError as e:
            cls._logger.error(f"Failed to store parameter {param_name}: {e}")
            raise RuntimeError(f"Failed to store parameter {param_name}: {e}")
    
    @classmethod
    def delete_parameter(cls, param_name: str) -> None:
        """
        Delete a parameter from AWS Parameter Store.
        
        Args:
            param_name: The name/path of the parameter to delete
            
        Raises:
            RuntimeError: If parameter cannot be deleted
        """
        try:
            cls._logger.debug(f"Deleting parameter: {param_name}")
            client = cls._get_client()
            
            client.delete_parameter(Name=param_name)
            cls._logger.info(f"Successfully deleted parameter: {param_name}")
            
        except ClientError as e:
            cls._logger.error(f"Failed to delete parameter {param_name}: {e}")
            raise RuntimeError(f"Failed to delete parameter {param_name}: {e}")

