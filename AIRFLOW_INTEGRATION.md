# Airflow Integration Guide

This guide explains how to integrate the Elasticsearch Metrics Collection System with Apache Airflow.

## Overview

The system can be run as an Airflow DAG with configuration passed as a JSON argument. This allows for flexible, scheduled metric collection with Airflow's built-in monitoring and retry capabilities.

## Architecture

### Components

1. **airflow_runner.py** - Main entry point for Airflow integration
2. **Environment Management** - Uses `.env.staging` or `.env.production` files
3. **JSON Configuration** - Metrics and connection configs passed as JSON
4. **ConfigLoader** - Handles both YAML and JSON configuration sources

### Configuration Flow

```
Airflow DAG → JSON Config → airflow_runner.py → ConfigLoader → MetricsService
                                                       ↓
                                              .env.{environment}
```

## Setup

### 1. Environment Configuration

Create environment-specific `.env` files based on `.env.template`:

```bash
# For staging
cp .env.template .env.staging

# For production
cp .env.template .env.production
```

Edit each file with environment-specific values:

**.env.staging:**
```bash
ENV=STAGING
LOG_LEVEL=DEBUG

ES_HOSTS=http://elasticsearch-staging:9200
ES_USERNAME=elastic
ES_PASSWORD=staging_password

MYSQL_HOST=mysql-staging
MYSQL_DATABASE=elasticsearch_metrics_staging
MYSQL_USER=metrics_user
MYSQL_PASSWORD=staging_mysql_password
```

**.env.production:**
```bash
ENV=PRODUCTION
LOG_LEVEL=INFO

ES_HOSTS=http://elasticsearch-prod:9200
ES_USERNAME=elastic
ES_PASSWORD=prod_password

MYSQL_HOST=mysql-prod
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=metrics_user
MYSQL_PASSWORD=prod_mysql_password
```

### 2. Install Requirements

```bash
pip install -r requirements.txt
```

### 3. Deploy to Airflow

Copy the project to your Airflow environment:

```bash
# Copy to Airflow DAGs folder
cp examples/airflow_dag_example.py /path/to/airflow/dags/

# Copy the entire project to a shared location
cp -r /path/to/elasmetrics /opt/elasmetrics/
```

## Usage

### Method 1: Python Operator (Recommended)

This method imports and runs the collection directly in Python:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
import json

def collect_metrics(**context):
    import sys
    sys.path.insert(0, '/opt/elasmetrics')
    
    from airflow_runner import run_collection
    
    config_json = json.dumps({
        "elasticsearch": {"hosts": ["http://es:9200"]},
        "mysql": {"host": "mysql", "database": "metrics"},
        # ... rest of config
    })
    
    result = run_collection(config_json, env='PRODUCTION')
    
    if not result['success']:
        raise Exception(f"Collection failed: {result.get('error')}")
    
    return result

dag = DAG('elasticsearch_metrics', ...)

collect_task = PythonOperator(
    task_id='collect_metrics',
    python_callable=collect_metrics,
    dag=dag,
)
```

### Method 2: Bash Operator

This method runs the script as a subprocess:

```python
from airflow.operators.bash import BashOperator

collect_task = BashOperator(
    task_id='collect_metrics',
    bash_command='''
        cd /opt/elasmetrics && \
        source venv/bin/activate && \
        python airflow_runner.py \
            --config '{{ params.config_json }}' \
            --env {{ params.environment }}
    ''',
    params={
        'config_json': json.dumps(CONFIG),
        'environment': 'PRODUCTION'
    },
    dag=dag,
)
```

### Method 3: Direct Command Line

Run directly from command line (useful for testing):

```bash
# With JSON string
python airflow_runner.py \
    --config '{"elasticsearch":{"hosts":["http://localhost:9200"]},...}' \
    --env PRODUCTION

# With JSON file
python airflow_runner.py \
    --config-file examples/config_example.json \
    --env STAGING
```

## Configuration Options

### Environment Variables

The system supports these environment variables:

#### Core Settings
- `ENV` - Environment name (STAGING or PRODUCTION)
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

#### Elasticsearch
- `ES_HOSTS` - Comma-separated list of hosts
- `ES_USERNAME` - Username for authentication
- `ES_PASSWORD` - Password for authentication
- `ES_API_KEY` - API key (alternative to username/password)
- `ES_TIMEOUT` - Request timeout in seconds
- `ES_VERIFY_CERTS` - Verify SSL certificates (true/false)

#### MySQL
- `MYSQL_HOST` - MySQL host
- `MYSQL_PORT` - MySQL port
- `MYSQL_DATABASE` - Database name
- `MYSQL_USER` - MySQL user
- `MYSQL_PASSWORD` - MySQL password
- `MYSQL_CHARSET` - Character set
- `MYSQL_POOL_SIZE` - Connection pool size
- `MYSQL_POOL_RECYCLE` - Connection recycle time

#### Metrics
- `METRICS_CONFIG` - JSON object with metrics configuration
- `METRICS_INCLUDE_PATTERNS` - Comma-separated include patterns
- `METRICS_EXCLUDE_PATTERNS` - Comma-separated exclude patterns

### JSON Configuration

The JSON configuration passed to `--config` should follow this structure:

```json
{
  "elasticsearch": {
    "hosts": ["http://localhost:9200"],
    "username": "elastic",
    "password": "changeme",
    "timeout": 30,
    "verify_certs": false
  },
  "mysql": {
    "host": "localhost",
    "port": 3306,
    "database": "elasticsearch_metrics",
    "user": "root",
    "password": "changeme",
    "charset": "utf8mb4",
    "pool_size": 5,
    "pool_recycle": 3600
  },
  "metrics": {
    "index_stats": [
      "docs.count",
      "store.size_in_bytes"
    ],
    "include_patterns": ["*"],
    "exclude_patterns": [".security*", ".kibana*"],
    "batch_size": 100
  },
  "logging": {
    "level": "INFO",
    "file": "logs/elastic_metrics.log",
    "console": true
  }
}
```

## Best Practices

### 1. Use Airflow Variables for Secrets

Store sensitive data in Airflow Variables or Connections:

```python
from airflow.models import Variable

config = {
    "elasticsearch": {
        "password": Variable.get("ES_PASSWORD")
    },
    "mysql": {
        "password": Variable.get("MYSQL_PASSWORD")
    }
}
```

### 2. Use Airflow Connections

Define connections in Airflow UI and reference them:

```python
from airflow.hooks.base import BaseHook

es_conn = BaseHook.get_connection('elasticsearch_prod')
mysql_conn = BaseHook.get_connection('mysql_metrics')

config = {
    "elasticsearch": {
        "hosts": [es_conn.host],
        "username": es_conn.login,
        "password": es_conn.password
    },
    "mysql": {
        "host": mysql_conn.host,
        "user": mysql_conn.login,
        "password": mysql_conn.password
    }
}
```

### 3. Environment-Specific DAGs

Create separate DAGs for staging and production:

```python
# dags/elasticsearch_metrics_staging.py
dag = DAG(
    'elasticsearch_metrics_staging',
    schedule_interval='0 */4 * * *',  # Every 4 hours
    ...
)

# dags/elasticsearch_metrics_production.py
dag = DAG(
    'elasticsearch_metrics_production',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    ...
)
```

### 4. Add Health Checks

Include pre-collection health checks:

```python
def health_check(**context):
    import sys
    sys.path.insert(0, '/opt/elasmetrics')
    
    from src.services import MetricsService
    from src.utils import ConfigLoader
    
    config_loader = ConfigLoader()
    config = config_loader.load_config(config_json=context['params']['config_json'])
    
    service = MetricsService(config)
    health = service.health_check()
    
    if health['overall'] != 'healthy':
        raise Exception(f"Health check failed: {health}")
    
    return health

health_check_task = PythonOperator(
    task_id='health_check',
    python_callable=health_check,
    dag=dag,
)

health_check_task >> collect_metrics_task
```

### 5. Configure Retries and Alerts

```python
default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'email_on_failure': True,
    'email_on_retry': False,
    'email': ['data-team@company.com'],
}
```

## Monitoring

### Task Logs

View logs in Airflow UI under Task Instance → Log

### Metrics

Track these metrics in your DAG:

```python
def collect_metrics(**context):
    result = run_collection(config_json, env)
    
    # Push stats to XCom for monitoring
    context['task_instance'].xcom_push(
        key='metrics_stats',
        value=result['stats']
    )
    
    return result
```

### Alerts

Set up alerts based on collection results:

```python
def check_collection_stats(**context):
    stats = context['task_instance'].xcom_pull(
        task_ids='collect_metrics',
        key='metrics_stats'
    )
    
    if stats.get('indices_collected', 0) == 0:
        raise Exception("No indices were collected!")
```

## Troubleshooting

### Issue: Environment variables not loaded

**Solution:** Ensure `.env.{environment}` file exists and `ENV` is set:

```bash
export ENV=PRODUCTION
python airflow_runner.py --config '...' --env PRODUCTION
```

### Issue: Module not found

**Solution:** Add project path to Python path in your DAG:

```python
import sys
sys.path.insert(0, '/opt/elasmetrics')
```

### Issue: Connection timeout

**Solution:** Increase timeout in configuration:

```json
{
  "elasticsearch": {
    "timeout": 60
  }
}
```

### Issue: MySQL connection pool exhausted

**Solution:** Increase pool size:

```json
{
  "mysql": {
    "pool_size": 10,
    "pool_recycle": 1800
  }
}
```

## Example DAG

See `examples/airflow_dag_example.py` for a complete working example.

## Testing

Test the Airflow integration locally:

```bash
# Test with staging config
python airflow_runner.py \
    --config-file examples/config_example.json \
    --env STAGING

# Test with production config
ENV=PRODUCTION python airflow_runner.py \
    --config-file examples/config_example.json \
    --env PRODUCTION
```

## Support

For issues or questions:
1. Check logs in Airflow UI
2. Review this documentation
3. Check main README.md for general troubleshooting

