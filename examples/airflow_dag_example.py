"""
Example Airflow DAG for Elasticsearch Metrics Collection.

This DAG demonstrates how to run the elasmetrics collector as an Airflow task
with JSON configuration passed as an argument.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import json
import os


# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


# Configuration for metrics collection
# This can be customized per DAG or loaded from Airflow Variables
METRICS_CONFIG = {
    "elasticsearch": {
        "hosts": ["http://elasticsearch-host:9200"],
        "username": "elastic",
        "password": "{{ var.value.ES_PASSWORD }}",  # Use Airflow Variables for secrets
        "timeout": 30,
        "verify_certs": False
    },
    "mysql": {
        "host": "mysql-host",
        "port": 3306,
        "database": "elasticsearch_metrics",
        "user": "metrics_user",
        "password": "{{ var.value.MYSQL_PASSWORD }}",  # Use Airflow Variables for secrets
        "charset": "utf8mb4",
        "pool_size": 5,
        "pool_recycle": 3600
    },
    "metrics": {
        "index_stats": [
            "docs.count",
            "docs.deleted",
            "store.size_in_bytes",
            "pri.store.size_in_bytes",
            "creation.date.string",
            "store.size.human",
            "pri.store.size.human"
        ],
        "include_patterns": ["*"],
        "exclude_patterns": [
            ".security*",
            ".kibana*",
            ".monitoring*",
            ".watcher*",
            ".ml*"
        ],
        "batch_size": 100
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "/var/log/airflow/elastic_metrics.log",
        "console": True
    }
}


# Create the DAG
dag = DAG(
    'elasticsearch_metrics_collection',
    default_args=default_args,
    description='Collect Elasticsearch index metrics and store in MySQL',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    catchup=False,
    tags=['elasticsearch', 'metrics', 'monitoring'],
)


def collect_metrics(**context):
    """
    Python callable to run metrics collection.
    This imports and runs the collection directly in Python.
    """
    import sys
    from pathlib import Path
    
    # Add elasmetrics to path
    elasmetrics_path = Path('/path/to/elasmetrics')
    sys.path.insert(0, str(elasmetrics_path))
    
    from airflow_runner import run_collection
    
    # Get config (can be rendered with Airflow Variables/Connections)
    config_json = json.dumps(METRICS_CONFIG)
    
    # Get environment from Airflow Variable or use default
    env = context.get('params', {}).get('environment', 'PRODUCTION')
    
    # Run collection
    result = run_collection(config_json, env)
    
    if not result['success']:
        raise Exception(f"Metrics collection failed: {result.get('error', 'Unknown error')}")
    
    return result


# Task 1: Collect metrics using Python operator
collect_metrics_task = PythonOperator(
    task_id='collect_elasticsearch_metrics',
    python_callable=collect_metrics,
    params={
        'environment': 'PRODUCTION'  # Can be overridden per DAG run
    },
    dag=dag,
)


# Alternative Task: Collect metrics using Bash operator
# This approach runs the script as a subprocess
collect_metrics_bash = BashOperator(
    task_id='collect_elasticsearch_metrics_bash',
    bash_command='''
    cd /path/to/elasmetrics && \
    source venv/bin/activate && \
    python airflow_runner.py \
        --config '{{ params.config_json }}' \
        --env {{ params.environment }}
    ''',
    params={
        'config_json': json.dumps(METRICS_CONFIG),
        'environment': 'PRODUCTION'
    },
    dag=dag,
)


# You can use either approach - choose one and comment out the other
# For this example, we'll use the Python operator
# collect_metrics_task  # Uncomment to use Python operator
# collect_metrics_bash  # Uncomment to use Bash operator


# Optional: Add notification task on success
def send_success_notification(**context):
    """Send notification on successful collection."""
    print("Metrics collection completed successfully!")
    # Add your notification logic here (email, Slack, etc.)


success_notification = PythonOperator(
    task_id='send_success_notification',
    python_callable=send_success_notification,
    dag=dag,
)


# Set task dependencies
collect_metrics_task >> success_notification

