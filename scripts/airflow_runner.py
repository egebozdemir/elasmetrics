#!/usr/bin/env python3
"""
Airflow-compatible runner for Elasticsearch Metrics Collection System.
This script is designed to be called from Airflow DAGs with JSON configuration.
"""
import sys
import os
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import MetricsService
from src.utils import ConfigLoader, EnvLoader
from src.enums import Environment


def setup_logging(config: Dict[str, Any]):
    """
    Setup logging configuration.
    
    Args:
        config: Configuration dictionary
    """
    log_config = config.get('logging', {})
    
    # Create logs directory if it doesn't exist
    log_file = log_config.get('file', 'logs/elastic_metrics.log')
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    log_level = getattr(logging, log_config.get('level', 'INFO'))
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Setup handlers
    handlers = []
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)
    
    # Console handler (if enabled)
    if log_config.get('console', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    # Suppress verbose logs from some libraries
    logging.getLogger('elasticsearch').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def validate_environment(env: str):
    """
    Validate environment value.
    
    Args:
        env: Environment string to validate
        
    Raises:
        ValueError: If environment is invalid
    """
    valid_environments = Environment.get_all()
    if env not in valid_environments:
        raise ValueError(
            f'Environment value {env} is not supported. '
            f'Supported values: {valid_environments}'
        )


def run_collection(config_json: str, env: str = None) -> Dict[str, Any]:
    """
    Run metrics collection with JSON configuration.
    
    Args:
        config_json: JSON string containing configuration
        env: Environment name (STAGING, PRODUCTION)
        
    Returns:
        Dictionary containing execution results
        
    Raises:
        Exception: If collection fails
    """
    logger = logging.getLogger('airflow_runner')
    
    try:
        # Validate and set environment
        if env:
            validate_environment(env)
            os.environ['ENV'] = env
            logger.info(f"Running in {env} environment")
        
        # Load environment variables
        env_value = os.getenv('ENV')
        if env_value:
            EnvLoader.load_environment_config(env_value)
            logger.info(f"Loaded environment config from .env.{env_value.lower()}")
        
        # Load configuration
        logger.info("Loading configuration from JSON...")
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_json=config_json, env=env)
        
        # Setup logging based on config
        setup_logging(config)
        
        # Initialize service
        logger.info("Initializing MetricsService...")
        service = MetricsService(config)
        
        # Collect and store metrics
        logger.info("Starting metrics collection...")
        result = service.collect_and_store_metrics()
        
        # Log results
        if result['success']:
            logger.info(f"✓ Collection completed successfully: {result['stats']}")
        else:
            logger.error(f"✗ Collection failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Fatal error during collection: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


def main():
    """Main function with CLI argument parsing for Airflow integration."""
    parser = argparse.ArgumentParser(
        description='Airflow-compatible Elasticsearch Metrics Collection Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with JSON config
  python airflow_runner.py --config '{"elasticsearch":{"hosts":["http://localhost:9200"]},...}'
  
  # Run with JSON config and environment
  python airflow_runner.py --config '...' --env PRODUCTION
  
  # Run with JSON from file
  python airflow_runner.py --config-file /path/to/config.json --env STAGING
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Configuration as JSON string'
    )
    
    parser.add_argument(
        '--config-file',
        type=str,
        help='Path to JSON configuration file'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        choices=['STAGING', 'PRODUCTION'],
        help='Environment (STAGING or PRODUCTION)'
    )
    
    args = parser.parse_args()
    
    # Get config JSON
    config_json = None
    if args.config:
        config_json = args.config
    elif args.config_file:
        with open(args.config_file, 'r') as f:
            config_json = f.read()
    else:
        print("Error: Either --config or --config-file must be provided", file=sys.stderr)
        return 1
    
    # Validate JSON
    try:
        json.loads(config_json)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON configuration: {e}", file=sys.stderr)
        return 1
    
    # Run collection
    result = run_collection(config_json, args.env)
    
    # Return exit code
    return 0 if result['success'] else 1


if __name__ == '__main__':
    sys.exit(main())

