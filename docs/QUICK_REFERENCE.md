# Quick Reference Guide

## Environment Setup

### Initial Setup

```bash
# 1. Create environment files
./scripts/setup_env.sh

# 2. Edit with your credentials
vi .env                  # For local dev
vi .env.staging         # For staging
vi .env.production      # For production

# 3. Test configuration
python main.py health-check --env STAGING
```

## Running the Application

### Local Development

```bash
# Using default .env
python main.py collect

# With explicit environment
python main.py collect --env STAGING
```

### Staging Environment

```bash
# Method 1: Set ENV variable
export ENV=STAGING
python main.py collect

# Method 2: Use --env flag
python main.py collect --env STAGING
```

### Production Environment

```bash
# Method 1: Set ENV variable
export ENV=PRODUCTION
python main.py collect

# Method 2: Use --env flag
python main.py collect --env PRODUCTION
```

### With JSON Configuration (Airflow Mode)

```bash
# Using JSON config file
python airflow_runner.py \
    --config-file examples/config_example.json \
    --env PRODUCTION

# Using JSON string
python airflow_runner.py \
    --config '{"elasticsearch":{"hosts":["http://localhost:9200"]},...}' \
    --env PRODUCTION
```

## Common Commands

### Health Check

```bash
# Check all components
python main.py health-check

# Check specific environment
python main.py health-check --env PRODUCTION
```

### Data Collection

```bash
# Collect metrics (default environment)
python main.py collect

# Collect with custom config
python main.py collect --config config/custom.yaml

# Collect with JSON config
python main.py collect --config-json '{"elasticsearch":{...}}'
```

### Cleanup Old Data

```bash
# Keep last 90 days (default)
python main.py cleanup

# Keep last 30 days
python main.py cleanup --days 30

# Cleanup in production
python main.py cleanup --days 90 --env PRODUCTION
```

## Configuration Priority

From lowest to highest priority:

1. `config/config.yaml` - Base configuration
2. `.env.{environment}` - Environment file
3. Shell environment variables - Runtime overrides
4. `--config-json` argument - Airflow mode

## Environment Variables

### Quick Reference

| Variable | Example | Description |
|----------|---------|-------------|
| `ENV` | `PRODUCTION` | Environment name |
| `ES_HOSTS` | `http://es:9200` | Elasticsearch hosts |
| `ES_USERNAME` | `elastic` | ES username |
| `ES_PASSWORD` | `changeme` | ES password |
| `MYSQL_HOST` | `localhost` | MySQL host |
| `MYSQL_DATABASE` | `metrics` | Database name |
| `MYSQL_USER` | `root` | MySQL user |
| `MYSQL_PASSWORD` | `changeme` | MySQL password |
| `LOG_LEVEL` | `INFO` | Logging level |

See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) for complete list.

## Airflow Integration

### Basic DAG

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
import json

def collect_metrics(**context):
    import sys
    sys.path.insert(0, '/opt/elasmetrics')
    from airflow_runner import run_collection
    
    config = {"elasticsearch": {...}, "mysql": {...}}
    result = run_collection(json.dumps(config), env='PRODUCTION')
    
    if not result['success']:
        raise Exception(f"Failed: {result.get('error')}")
    return result

dag = DAG('elasticsearch_metrics', schedule_interval='0 2 * * *', ...)
task = PythonOperator(task_id='collect', python_callable=collect_metrics, dag=dag)
```

See [AIRFLOW_INTEGRATION.md](AIRFLOW_INTEGRATION.md) for detailed guide.

## File Structure

```
elasmetrics/
├── .env.template           # Template for environment files
├── .env                    # Local development (create from template)
├── .env.staging           # Staging environment (create from template)
├── .env.production        # Production environment (create from template)
├── main.py                # Main CLI entry point
├── airflow_runner.py      # Airflow-compatible runner
├── config/
│   ├── config.yaml        # Base YAML configuration
│   └── config.example.yaml
├── src/
│   ├── enums/
│   │   └── environment.py # Environment enum
│   ├── utils/
│   │   ├── config_loader.py   # Configuration loader
│   │   └── env_loader.py      # Environment loader
│   ├── services/
│   ├── collectors/
│   ├── models/
│   └── repositories/
└── examples/
    ├── config_example.json        # JSON config example
    └── airflow_dag_example.py     # Airflow DAG example
```

## Troubleshooting

### Configuration Not Loading

```bash
# Check which environment is active
echo $ENV

# Verify environment file exists
ls -la .env.*

# Test with explicit environment
python main.py health-check --env PRODUCTION
```

### Connection Issues

```bash
# Test connections
python main.py health-check

# Check configuration values
python -c "
from src.utils import ConfigLoader
config = ConfigLoader()
config.load_config(env='PRODUCTION')
print(config.get_elasticsearch_config())
print(config.get_mysql_config())
"
```

### Permission Issues

```bash
# Fix environment file permissions
chmod 600 .env.production

# Verify permissions
ls -la .env.*
```

## Security Checklist

- [ ] Never commit `.env`, `.env.staging`, or `.env.production` to git
- [ ] Use strong passwords for production
- [ ] Rotate credentials regularly
- [ ] Set file permissions to 600 for .env files
- [ ] Use separate database users for each environment
- [ ] Enable SSL/TLS for production connections
- [ ] Store secrets in secret management systems (AWS Secrets Manager, Vault, etc.)

## Performance Tips

### MySQL Connection Pooling

```bash
# Increase pool size for high-volume environments
MYSQL_POOL_SIZE=20
MYSQL_POOL_RECYCLE=1800
```

### Elasticsearch Timeout

```bash
# Increase timeout for large clusters
ES_TIMEOUT=60
```

### Batch Size

```bash
# Adjust batch size based on cluster size
METRICS_CONFIG='{"batch_size":200}'
```

## Quick Tests

### Test Configuration Loading

```python
from src.utils import ConfigLoader, EnvLoader

# Test environment loading
EnvLoader.load_environment_config(env='STAGING')

# Test config loading
config_loader = ConfigLoader()
config = config_loader.load_config(env='STAGING')
print(config)
```

### Test Elasticsearch Connection

```python
from elasticsearch import Elasticsearch
import os

es = Elasticsearch(
    hosts=[os.getenv('ES_HOSTS', 'http://localhost:9200')],
    basic_auth=(os.getenv('ES_USERNAME'), os.getenv('ES_PASSWORD'))
)
print(es.info())
```

### Test MySQL Connection

```python
import pymysql
import os

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST', 'localhost'),
    user=os.getenv('MYSQL_USER', 'root'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE')
)
print(conn.get_server_info())
conn.close()
```

## Useful Commands

```bash
# Show all available commands
python main.py --help

# Show current configuration
python -c "from src.utils import ConfigLoader; c = ConfigLoader(); c.load_config(); print(c.config)"

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify imports
python -c "from src.utils import ConfigLoader, EnvLoader; from src.enums import Environment; print('All imports OK')"

# Test with verbose logging
LOG_LEVEL=DEBUG python main.py collect --env STAGING
```

## Documentation

- [README.md](../README.md) - Main documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) - Detailed environment configuration
- [AIRFLOW_INTEGRATION.md](AIRFLOW_INTEGRATION.md) - Airflow integration guide
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Project overview

## Support

For issues, questions, or contributions, please refer to the main documentation or create an issue in the project repository.

