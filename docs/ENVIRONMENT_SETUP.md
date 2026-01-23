# Environment Setup Guide

This guide explains how to set up environment-specific configuration for the Elasticsearch Metrics Collection System.

## Overview

The system uses a combination of:
1. **YAML configuration files** - For base configuration and local development
2. **Environment files (.env)** - For environment-specific secrets and overrides
3. **JSON configuration** - For Airflow and dynamic configuration

## Environment Files

### Structure

```
elasmetrics/
├── .env.template        # Template file (tracked in git)
├── .env                 # Local development (not tracked)
├── .env.staging         # Staging environment (not tracked)
└── .env.production      # Production environment (not tracked)
```

### Setup Steps

#### 1. Create Environment Files

Copy the template to create environment-specific files:

```bash
# For local development
cp .env.template .env

# For staging
cp .env.template .env.staging

# For production
cp .env.template .env.production
```

#### 2. Configure Each Environment

Edit each `.env` file with appropriate values:

**.env (Local Development):**
```bash
ENV=STAGING
LOG_LEVEL=DEBUG

ES_HOSTS=http://localhost:9200
ES_USERNAME=
ES_PASSWORD=
ES_API_KEY=
ES_TIMEOUT=30
ES_VERIFY_CERTS=false

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=root
MYSQL_PASSWORD=changeme
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=5
MYSQL_POOL_RECYCLE=3600

SCHEDULING_ENABLED=false
SCHEDULING_CRON=0 2 * * *
SCHEDULING_TIMEZONE=Europe/Istanbul

LOCAL_DEV_MODE=true
```

**.env.staging:**
```bash
ENV=STAGING
LOG_LEVEL=INFO

ES_HOSTS=http://elasticsearch-staging.internal:9200,http://elasticsearch-staging-2.internal:9200
ES_USERNAME=elastic
ES_PASSWORD=staging_elastic_password_here
ES_TIMEOUT=30
ES_VERIFY_CERTS=true

MYSQL_HOST=mysql-staging.internal
MYSQL_PORT=3306
MYSQL_DATABASE=elasticsearch_metrics_staging
MYSQL_USER=metrics_user
MYSQL_PASSWORD=staging_mysql_password_here
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=10
MYSQL_POOL_RECYCLE=3600

METRICS_INCLUDE_PATTERNS=*
METRICS_EXCLUDE_PATTERNS=.security*,.kibana*,.monitoring*,.watcher*,.ml*

SCHEDULING_ENABLED=false
SCHEDULING_CRON=0 */4 * * *
SCHEDULING_TIMEZONE=Europe/Istanbul

LOCAL_DEV_MODE=false
```

**.env.production:**
```bash
ENV=PRODUCTION
LOG_LEVEL=INFO

ES_HOSTS=http://elasticsearch-prod-1.internal:9200,http://elasticsearch-prod-2.internal:9200,http://elasticsearch-prod-3.internal:9200
ES_USERNAME=elastic
ES_PASSWORD=production_elastic_password_here
ES_TIMEOUT=60
ES_VERIFY_CERTS=true

MYSQL_HOST=mysql-prod.internal
MYSQL_PORT=3306
MYSQL_DATABASE=elasticsearch_metrics
MYSQL_USER=metrics_user
MYSQL_PASSWORD=production_mysql_password_here
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=20
MYSQL_POOL_RECYCLE=1800

METRICS_INCLUDE_PATTERNS=*
METRICS_EXCLUDE_PATTERNS=.security*,.kibana*,.monitoring*,.watcher*,.ml*,.tasks*

SCHEDULING_ENABLED=false
SCHEDULING_CRON=0 2 * * *
SCHEDULING_TIMEZONE=Europe/Istanbul

LOCAL_DEV_MODE=false
```

## Configuration Priority

The system loads configuration in the following order (later overrides earlier):

1. **YAML file** (`config/config.yaml`)
2. **Environment file** (`.env`, `.env.staging`, or `.env.production`)
3. **Environment variables** (shell environment)
4. **JSON configuration** (Airflow mode)

### Example Priority Flow

```
config.yaml:
  mysql.host: localhost
  
.env.production:
  MYSQL_HOST=mysql-prod.internal
  
Environment variable:
  export MYSQL_HOST=mysql-override.internal
  
Final value: mysql-override.internal
```

## Usage

### Local Development

Run without specifying environment (uses `.env`):

```bash
python main.py collect
```

### Staging Environment

Specify the staging environment:

```bash
# Option 1: Set ENV variable
export ENV=STAGING
python main.py collect

# Option 2: Use --env flag
python main.py collect --env STAGING
```

### Production Environment

Specify the production environment:

```bash
# Option 1: Set ENV variable
export ENV=PRODUCTION
python main.py collect

# Option 2: Use --env flag
python main.py collect --env PRODUCTION
```

### Airflow Integration

In Airflow, set the environment in your DAG:

```python
from airflow_runner import run_collection

result = run_collection(config_json, env='PRODUCTION')
```

## Environment Variables Reference

### Core Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ENV` | Environment name | `STAGING`, `PRODUCTION` | Yes |
| `LOG_LEVEL` | Logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR` | No |
| `LOCAL_DEV_MODE` | Local development mode flag | `true`, `false` | No |

### Elasticsearch Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `ES_HOSTS` | Comma-separated Elasticsearch hosts | `http://es1:9200,http://es2:9200` | Yes |
| `ES_USERNAME` | Elasticsearch username | `elastic` | No |
| `ES_PASSWORD` | Elasticsearch password | `changeme` | No |
| `ES_API_KEY` | Elasticsearch API key | `base64_encoded_key` | No |
| `ES_TIMEOUT` | Request timeout (seconds) | `30` | No |
| `ES_VERIFY_CERTS` | Verify SSL certificates | `true`, `false` | No |

### MySQL Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `MYSQL_HOST` | MySQL host | `localhost` | Yes |
| `MYSQL_PORT` | MySQL port | `3306` | No |
| `MYSQL_DATABASE` | Database name | `elasticsearch_metrics` | Yes |
| `MYSQL_USER` | MySQL username | `root` | Yes |
| `MYSQL_PASSWORD` | MySQL password | `changeme` | Yes |
| `MYSQL_CHARSET` | Character set | `utf8mb4` | No |
| `MYSQL_POOL_SIZE` | Connection pool size | `5` | No |
| `MYSQL_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` | No |

### Metrics Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `METRICS_CONFIG` | JSON metrics configuration | `{"batch_size":100}` | No |
| `METRICS_INCLUDE_PATTERNS` | Comma-separated include patterns | `*,logs-*` | No |
| `METRICS_EXCLUDE_PATTERNS` | Comma-separated exclude patterns | `.security*,.kibana*` | No |

### Scheduling Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `SCHEDULING_ENABLED` | Enable scheduling | `true`, `false` | No |
| `SCHEDULING_CRON` | Cron expression | `0 2 * * *` | No |
| `SCHEDULING_TIMEZONE` | Timezone | `Europe/Istanbul` | No |

## Security Best Practices

### 1. Never Commit Secrets

The `.gitignore` file excludes:
- `.env`
- `.env.staging`
- `.env.production`

**Always verify before committing:**

```bash
git status
# Ensure no .env files are staged
```

### 2. Use Strong Passwords

Generate strong passwords for production:

```bash
# Generate random password
openssl rand -base64 32
```

### 3. Rotate Credentials Regularly

Set up a schedule for rotating:
- Database passwords
- Elasticsearch credentials
- API keys

### 4. Use Secret Management Systems

For production deployments, consider:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

### 5. Limit Access

Restrict file permissions:

```bash
chmod 600 .env.production
chmod 600 .env.staging
```

### 6. Use Environment-Specific Accounts

Create separate database users for each environment:

```sql
-- Staging user
CREATE USER 'metrics_staging'@'%' IDENTIFIED BY 'staging_password';
GRANT SELECT, INSERT ON elasticsearch_metrics_staging.* TO 'metrics_staging'@'%';

-- Production user
CREATE USER 'metrics_prod'@'%' IDENTIFIED BY 'production_password';
GRANT SELECT, INSERT ON elasticsearch_metrics.* TO 'metrics_prod'@'%';
```

## Testing Configuration

### Validate Configuration

Test your environment configuration:

```bash
# Test staging
python main.py health-check --env STAGING

# Test production
python main.py health-check --env PRODUCTION
```

### Dry Run

Test without actually collecting:

```bash
# Use health-check to verify connections
python main.py health-check --env PRODUCTION
```

### Check Loaded Configuration

Add debug logging to see what's loaded:

```python
from src.utils import ConfigLoader

config_loader = ConfigLoader()
config = config_loader.load_config(env='PRODUCTION')

print(f"Loaded config: {config}")
```

## Troubleshooting

### Issue: Wrong environment loaded

**Symptom:** Connection to wrong database or Elasticsearch cluster

**Solution:** Explicitly set the environment:

```bash
# Clear existing ENV
unset ENV

# Run with explicit environment
python main.py collect --env PRODUCTION
```

### Issue: Environment file not found

**Symptom:** `FileNotFoundError: Environment file .env.production not found`

**Solution:** Create the file from template:

```bash
cp .env.template .env.production
# Edit .env.production with correct values
```

### Issue: Variables not being loaded

**Symptom:** Still using default values from YAML

**Solution:** Check file exists and ENV is set:

```bash
# Check if file exists
ls -la .env.*

# Check ENV variable
echo $ENV

# Set ENV before running
export ENV=PRODUCTION
python main.py collect
```

### Issue: Permission denied

**Symptom:** Cannot read .env file

**Solution:** Fix file permissions:

```bash
chmod 600 .env.production
```

### Issue: AWS Elasticsearch / OpenSearch Connection Error

**Symptom:** `The client noticed that the server is not Elasticsearch and we do not support this unknown product`

**Cause:** AWS Elasticsearch Service (now OpenSearch Service) identifies itself differently than vanilla Elasticsearch, but is API-compatible.

**Solution:** ✅ **Already fixed in v1.0+**

The system automatically disables product checking (`_product_check=False`) to support AWS Elasticsearch/OpenSearch clusters.

**Example `.env` for AWS Elasticsearch:**
```bash
# AWS Elasticsearch (OpenSearch Service)
ES_HOSTS=https://vpc-my-cluster.eu-west-1.es.amazonaws.com
ES_USERNAME=
ES_PASSWORD=
ES_VERIFY_CERTS=true  # AWS has valid certs
ES_TIMEOUT=30
```

**Verify connection:**
```bash
# Test with curl first
curl -X GET "https://your-cluster.eu-west-1.es.amazonaws.com/_cluster/health?pretty"

# Then test with the app
python main.py health-check
```

### Issue: .env file parsing error

**Symptom:** `python-dotenv could not parse statement starting at line X`

**Cause:** Syntax error in `.env` file (spaces around `=`, quotes, multiline values, etc.)

**Common mistakes:**

```bash
# ❌ BAD: Spaces around equals
ES_HOSTS = http://localhost:9200

# ❌ BAD: Unquoted values with spaces
ES_HOSTS=http://localhost:9200 http://localhost:9201

# ❌ BAD: Multiline without proper format
METRICS_EXCLUDE_PATTERNS=.security*,
.kibana*,
.monitoring*

# ✅ GOOD: No spaces, comma-separated
ES_HOSTS=http://localhost:9200,http://localhost:9201

# ✅ GOOD: Quoted if necessary
METRICS_EXCLUDE_PATTERNS=".security*,.kibana*,.monitoring*"

# ✅ GOOD: Single line
METRICS_EXCLUDE_PATTERNS=.security*,.kibana*,.monitoring*
```

**Solution:** Fix the syntax error at the reported line:

```bash
# Check which line has the error
python -c "from dotenv import load_dotenv; load_dotenv('.env')"

# Common fixes:
# 1. Remove spaces around =
# 2. Remove extra quotes
# 3. Put comma-separated values on one line
# 4. Remove comments on same line as values
```

## Migration from YAML-only

If you're migrating from YAML-only configuration:

1. Keep your `config/config.yaml` for base configuration
2. Create `.env` files for environment-specific values
3. Move secrets from YAML to `.env` files
4. Update deployment scripts to use `--env` flag

**Before:**
```bash
python main.py collect --config config/config.production.yaml
```

**After:**
```bash
python main.py collect --env PRODUCTION
```

## Troubleshooting AWS OpenSearch

### Issue: "The client noticed that the server is not Elasticsearch"

**Symptom:**
```
elasticsearch.UnsupportedProductError: The client noticed that the server is not Elasticsearch and we do not support this unknown product
```

**Solution:**

1. **Add to `.env` file:**
   ```bash
   ELASTIC_CLIENT_APIVERSIONING=0
   ```

2. **If using `.env.staging` or `.env.production`, add it there too:**
   ```bash
   echo -e "\n# AWS OpenSearch Compatibility\nELASTIC_CLIENT_APIVERSIONING=0" >> .env.staging
   ```

3. **Verify it's loaded:**
   ```bash
   python scripts/check_env.py
   ```

**Why This Happens:**
- AWS Elasticsearch/OpenSearch is API-compatible with Elasticsearch but reports itself as "OpenSearch"
- The elasticsearch-py client has a product check that can be disabled with `ELASTIC_CLIENT_APIVERSIONING=0`
- ElasMetrics automatically falls back to raw transport when it detects AWS OpenSearch

**Note:** ElasMetrics v1.0+ handles AWS OpenSearch automatically. You should see:
```
✓ Connected to AWS OpenSearch cluster (bypassing product check)
✓ Retrieved X indices from AWS OpenSearch (via raw transport)
```

### Issue: ".env parsing error"

**Symptom:**
```
python-dotenv could not parse statement starting at line X
```

**Solution:**
```bash
# Check your .env syntax
python scripts/check_env.py

# Common issues:
# ❌ BAD:  ES_HOSTS = https://...  (spaces around =)
# ✅ GOOD: ES_HOSTS=https://...

# ❌ BAD:  Multi-line without quotes
# ✅ GOOD: Wrap multi-line values in quotes
```

## Examples

See the `examples/` directory for:
- `config_example.json` - JSON configuration format
- `airflow_dag_example.py` - Airflow DAG integration

## Further Reading

- [AIRFLOW_INTEGRATION.md](AIRFLOW_INTEGRATION.md) - Airflow integration guide
- [README.md](../README.md) - Main documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick setup guide
- [INDEX.md](INDEX.md) - Complete documentation index

