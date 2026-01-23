#!/usr/bin/env python3
"""
Main entry point for Elasticsearch Metrics Collection System.
"""
# CRITICAL: Load .env FIRST, before any elasticsearch imports
# This allows setting ELASTIC_CLIENT_APIVERSIONING for AWS OpenSearch compatibility
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()  # Load .env file immediately

import sys
import logging
import argparse
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import MetricsService
from src.utils import ConfigLoader


def setup_logging(config: dict):
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


def collect_metrics(config_path: str = None, config_json: str = None, env: str = None):
    """
    Collect and store metrics.
    
    Args:
        config_path: Path to configuration file
        config_json: JSON string configuration (alternative to config_path)
        env: Environment name (STAGING, PRODUCTION) for loading .env files
    """
    logger = logging.getLogger('main')
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path=config_path, config_json=config_json, env=env)
        
        # Initialize service
        logger.info("Initializing MetricsService...")
        service = MetricsService(config)
        
        # Collect and store metrics
        result = service.collect_and_store_metrics()
        
        # Exit with appropriate code
        if result['success']:
            logger.info("✓ Process completed successfully")
            return 0
        else:
            logger.error("✗ Process failed")
            return 1
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def health_check(config_path: str = None, config_json: str = None, env: str = None):
    """
    Perform health check on all components.
    
    Args:
        config_path: Path to configuration file
        config_json: JSON string configuration (alternative to config_path)
        env: Environment name (STAGING, PRODUCTION) for loading .env files
    """
    logger = logging.getLogger('main')
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path=config_path, config_json=config_json, env=env)
        
        # Initialize service
        service = MetricsService(config)
        
        # Perform health check
        health = service.health_check()
        
        # Print results
        print("\n" + "=" * 60)
        print("HEALTH CHECK RESULTS")
        print("=" * 60)
        print(f"Overall Status: {health['overall'].upper()}")
        print(f"Timestamp: {health['timestamp']}")
        print()
        
        print("Elasticsearch:")
        es_health = health['elasticsearch']
        print(f"  Status: {es_health['status']}")
        if 'details' in es_health:
            for key, value in es_health['details'].items():
                print(f"  {key}: {value}")
        if 'error' in es_health:
            print(f"  Error: {es_health['error']}")
        print()
        
        print("MySQL:")
        mysql_health = health['mysql']
        print(f"  Status: {mysql_health['status']}")
        if 'details' in mysql_health:
            for key, value in mysql_health['details'].items():
                print(f"  {key}: {value}")
        if 'error' in mysql_health:
            print(f"  Error: {mysql_health['error']}")
        print("=" * 60)
        
        # Return appropriate exit code
        return 0 if health['overall'] == 'healthy' else 1
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return 1


def cleanup_old_data(days: int, config_path: str = None, config_json: str = None, env: str = None):
    """
    Clean up old metrics data.
    
    Args:
        days: Number of days to keep
        config_path: Path to configuration file
        config_json: JSON string configuration (alternative to config_path)
        env: Environment name (STAGING, PRODUCTION) for loading .env files
    """
    logger = logging.getLogger('main')
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path=config_path, config_json=config_json, env=env)
        
        # Initialize service
        service = MetricsService(config)
        
        # Cleanup old data
        deleted_count = service.cleanup_old_data(days)
        
        print(f"\n✓ Cleaned up {deleted_count} records older than {days} days")
        return 0
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        return 1


def main():
    """Main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description='Elasticsearch Metrics Collection System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect and store metrics
  python main.py collect
  
  # Collect with custom config
  python main.py collect --config /path/to/config.yaml
  
  # Perform health check
  python main.py health-check
  
  # Clean up old data (keep last 90 days)
  python main.py cleanup --days 90
        """
    )
    
    parser.add_argument(
        'command',
        choices=['collect', 'health-check', 'cleanup'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--config',
        '-c',
        type=str,
        default=None,
        help='Path to configuration file (default: config/config.yaml)'
    )
    
    parser.add_argument(
        '--config-json',
        type=str,
        default=None,
        help='Configuration as JSON string (alternative to --config)'
    )
    
    parser.add_argument(
        '--env',
        type=str,
        choices=['STAGING', 'PRODUCTION'],
        default=None,
        help='Environment for loading .env files (STAGING or PRODUCTION)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=90,
        help='Number of days to keep for cleanup command (default: 90)'
    )
    
    args = parser.parse_args()
    
    # Load configuration first to setup logging
    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config(
            config_path=args.config,
            config_json=args.config_json,
            env=args.env
        )
        setup_logging(config)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1
    
    # Execute command
    if args.command == 'collect':
        return collect_metrics(args.config, args.config_json, args.env)
    elif args.command == 'health-check':
        return health_check(args.config, args.config_json, args.env)
    elif args.command == 'cleanup':
        return cleanup_old_data(args.days, args.config, args.config_json, args.env)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

