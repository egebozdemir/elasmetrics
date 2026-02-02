#!/usr/bin/env python3
"""
Main entry point for Elasticsearch Metrics Collection System.
Supports index metrics and custom aggregation queries from multiple data sources.
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


def collect_metrics(config_path: str = None, config_json: str = None, env: str = None,
                   source: str = None):
    """
    Collect and store index metrics.

    Args:
        config_path: Path to configuration file
        config_json: JSON string configuration (alternative to config_path)
        env: Environment name (STAGING, PRODUCTION) for loading .env files
        source: Specific data source to collect from (optional)
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
        result = service.collect_and_store_metrics(source_name=source)

        # Exit with appropriate code
        if result['success']:
            logger.info("Process completed successfully")
            return 0
        else:
            logger.error("Process failed")
            return 1

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def collect_aggregations(config_path: str = None, config_json: str = None, env: str = None,
                        source: str = None, query: str = None):
    """
    Collect and store aggregation metrics.

    Args:
        config_path: Path to configuration file
        config_json: JSON string configuration (alternative to config_path)
        env: Environment name (STAGING, PRODUCTION) for loading .env files
        source: Specific data source to collect from (optional)
        query: Specific query to run (optional)
    """
    logger = logging.getLogger('main')

    try:
        # Load configuration
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path=config_path, config_json=config_json, env=env)

        # Initialize service
        logger.info("Initializing MetricsService...")
        service = MetricsService(config)

        # Collect and store aggregation metrics
        result = service.collect_and_store_aggregations(source_name=source, query_name=query)

        # Exit with appropriate code
        if result['success']:
            logger.info("Process completed successfully")
            return 0
        else:
            logger.error("Process failed")
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

        # Data Sources
        print("Data Sources:")
        data_sources = health.get('data_sources', {})
        if isinstance(data_sources, dict) and 'error' not in data_sources:
            for name, status in data_sources.items():
                print(f"  [{name}]")
                print(f"    Status: {status.get('status', 'unknown')}")
                if 'cluster_name' in status:
                    print(f"    Cluster: {status['cluster_name']}")
                if 'cluster_status' in status:
                    print(f"    Cluster Status: {status['cluster_status']}")
                if 'error' in status:
                    print(f"    Error: {status['error']}")
        else:
            # Legacy format
            es_health = health.get('elasticsearch', {})
            print(f"  Status: {es_health.get('status', 'unknown')}")
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


def list_sources(config_path: str = None, config_json: str = None, env: str = None):
    """
    List all configured data sources (without connecting).
    """
    logger = logging.getLogger('main')

    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path=config_path, config_json=config_json, env=env)

        # Read sources directly from config without connecting
        data_sources = config.get('data_sources', {})

        # Backward compatibility: if no data_sources, use elasticsearch config
        if not data_sources and 'elasticsearch' in config:
            data_sources = {'default': config['elasticsearch']}

        print("\nConfigured Data Sources:")
        print("-" * 40)
        if not data_sources:
            print("  No data sources configured.")
        else:
            for name, src_config in data_sources.items():
                hosts = src_config.get('hosts', ['(not specified)'])
                if isinstance(hosts, str):
                    hosts = [hosts]
                print(f"  [{name}]")
                print(f"    Hosts: {', '.join(hosts)}")
                if src_config.get('username'):
                    print(f"    Auth: username/password")
                elif src_config.get('api_key'):
                    print(f"    Auth: API key")
                print()

        return 0

    except Exception as e:
        logger.error(f"Failed to list sources: {e}", exc_info=True)
        return 1


def list_queries(config_path: str = None, config_json: str = None, env: str = None):
    """
    List all configured aggregation queries (without connecting).
    """
    logger = logging.getLogger('main')

    try:
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path=config_path, config_json=config_json, env=env)

        # Read queries directly from config without connecting
        queries = config.get('aggregation_queries', [])

        print("\nConfigured Aggregation Queries:")
        print("-" * 40)
        if not queries:
            print("  No aggregation queries configured.")
            print("  Add 'aggregation_queries' section to your config.yaml")
            print("  See config/config.multi-cluster.example.yaml for examples.")
        else:
            for q in queries:
                enabled = q.get('enabled', True)
                status = "" if enabled else " (DISABLED)"
                print(f"  [{q.get('name', 'unnamed')}]{status}")
                print(f"    Source: {q.get('data_source', '(not specified)')}")
                print(f"    Index: {q.get('index_pattern', '(not specified)')}")
                print(f"    Type: {q.get('query_type', 'search')}")
                if q.get('description'):
                    print(f"    Description: {q['description']}")
                print()

        return 0

    except Exception as e:
        logger.error(f"Failed to list queries: {e}", exc_info=True)
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
        result = service.cleanup_old_data(days)

        if isinstance(result, dict):
            print(f"\nCleanup completed:")
            print(f"  Index metrics deleted: {result.get('index_metrics_deleted', 0)}")
            print(f"  Aggregation metrics deleted: {result.get('aggregation_metrics_deleted', 0)}")
            total = result.get('index_metrics_deleted', 0) + result.get('aggregation_metrics_deleted', 0)
            print(f"  Total: {total} records older than {days} days")
        else:
            print(f"\nCleaned up {result} records older than {days} days")

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
  # Collect index metrics from all sources
  python main.py collect

  # Collect index metrics from specific source
  python main.py collect --source main_cluster

  # Collect aggregation metrics (all queries)
  python main.py collect-aggregations

  # Collect specific aggregation query
  python main.py collect-aggregations --query stock_item_count

  # Collect aggregations from specific source
  python main.py collect-aggregations --source enterprise_datahub

  # Health check all components
  python main.py health-check

  # List configured data sources
  python main.py list-sources

  # List configured aggregation queries
  python main.py list-queries

  # Clean up old data (keep last 90 days)
  python main.py cleanup --days 90
        """
    )

    parser.add_argument(
        'command',
        choices=['collect', 'collect-aggregations', 'health-check', 'cleanup',
                 'list-sources', 'list-queries'],
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
        '--source',
        type=str,
        default=None,
        help='Specific data source to use (for collect commands)'
    )

    parser.add_argument(
        '--query',
        type=str,
        default=None,
        help='Specific aggregation query to run (for collect-aggregations)'
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
        return collect_metrics(args.config, args.config_json, args.env, args.source)
    elif args.command == 'collect-aggregations':
        return collect_aggregations(args.config, args.config_json, args.env, args.source, args.query)
    elif args.command == 'health-check':
        return health_check(args.config, args.config_json, args.env)
    elif args.command == 'list-sources':
        return list_sources(args.config, args.config_json, args.env)
    elif args.command == 'list-queries':
        return list_queries(args.config, args.config_json, args.env)
    elif args.command == 'cleanup':
        return cleanup_old_data(args.days, args.config, args.config_json, args.env)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
