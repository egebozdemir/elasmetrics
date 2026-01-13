# Changelog

All notable changes to the Elasticsearch Metrics Collection System project.

## [1.1.0] - 2026-01-13

### Added - Environment Management System

#### New Files
- **`.env.template`** - Template file for environment configuration
- **`src/enums/environment.py`** - Environment enumeration (STAGING, PRODUCTION)
- **`src/utils/env_loader.py`** - Environment file loader utility
- **`airflow_runner.py`** - Airflow-compatible runner script
- **`setup_env.sh`** - Interactive environment setup script
- **`examples/config_example.json`** - JSON configuration example
- **`examples/airflow_dag_example.py`** - Example Airflow DAG

#### New Documentation
- **`ENVIRONMENT_SETUP.md`** - Comprehensive environment configuration guide
- **`AIRFLOW_INTEGRATION.md`** - Apache Airflow integration documentation
- **`QUICK_REFERENCE.md`** - Quick reference guide for common tasks
- **`CHANGELOG.md`** - This file

#### Features
- **Multi-Environment Support**: Separate configurations for local, staging, and production
- **Environment Files**: `.env`, `.env.staging`, `.env.production` support
- **Airflow Integration**: Native support for Apache Airflow DAGs with JSON configuration
- **JSON Configuration**: Support for passing configuration as JSON (for Airflow)
- **Enhanced ConfigLoader**: 
  - Load from YAML, environment files, or JSON
  - Support for environment variable overrides
  - Configuration priority system
  - Dynamic environment switching
- **Environment Enum**: Type-safe environment management
- **Environment Loader**: Automatic loading of environment-specific `.env` files

#### Command-Line Interface
- New `--env` flag: Specify environment (STAGING or PRODUCTION)
- New `--config-json` flag: Pass configuration as JSON string
- New `--config-file` flag in airflow_runner: Load JSON from file

### Changed

#### Updated Files
- **`main.py`**: 
  - Added support for `--env` and `--config-json` arguments
  - Updated all functions to accept environment parameter
  - Enhanced configuration loading with multi-source support
  
- **`src/utils/config_loader.py`**: 
  - Complete rewrite to support multiple configuration sources
  - Added JSON configuration support
  - Added environment file integration
  - Improved environment variable override logic
  - Added support for METRICS_CONFIG JSON override
  
- **`src/utils/__init__.py`**: 
  - Added EnvLoader export
  
- **`.gitignore`**: 
  - Added `.env.staging` and `.env.production` to ignore list
  
- **`requirements.txt`**: 
  - Added `python-dotenv>=1.0.0` dependency
  
- **`README.md`**: 
  - Updated with environment management documentation
  - Added Airflow integration section
  - Enhanced configuration hierarchy explanation
  - Added new documentation references
  - Updated version history

### Configuration Priority

The new system implements a configuration priority hierarchy:

1. **Command-line JSON** (`--config-json`) - Highest priority
2. **Environment Variables** (from `.env` files or shell)
3. **YAML Configuration** (`config/config.yaml`) - Lowest priority

### Environment Variables Added

#### Core
- `ENV` - Environment name (STAGING, PRODUCTION)
- `LOCAL_DEV_MODE` - Local development mode flag

#### Elasticsearch (Enhanced)
- `ES_HOSTS` - Comma-separated Elasticsearch hosts
- `ES_USERNAME` - Elasticsearch username
- `ES_PASSWORD` - Elasticsearch password
- `ES_API_KEY` - Elasticsearch API key
- `ES_TIMEOUT` - Request timeout
- `ES_VERIFY_CERTS` - Verify SSL certificates

#### MySQL (Enhanced)
- `MYSQL_HOST` - MySQL host
- `MYSQL_PORT` - MySQL port
- `MYSQL_DATABASE` - Database name
- `MYSQL_USER` - MySQL username
- `MYSQL_PASSWORD` - MySQL password
- `MYSQL_CHARSET` - Character set
- `MYSQL_POOL_SIZE` - Connection pool size
- `MYSQL_POOL_RECYCLE` - Connection recycle time

#### Metrics
- `METRICS_CONFIG` - JSON metrics configuration override
- `METRICS_INCLUDE_PATTERNS` - Comma-separated include patterns
- `METRICS_EXCLUDE_PATTERNS` - Comma-separated exclude patterns

#### Scheduling
- `SCHEDULING_ENABLED` - Enable/disable scheduling
- `SCHEDULING_CRON` - Cron expression
- `SCHEDULING_TIMEZONE` - Timezone

#### Airflow
- `CONFIG_JSON` - Full JSON configuration (Airflow integration)

### Usage Examples

#### Traditional Usage (with environment)
```bash
# Local development
python main.py collect

# Staging environment
python main.py collect --env STAGING

# Production environment
python main.py collect --env PRODUCTION
```

#### Airflow Integration
```bash
# Run with JSON configuration
python airflow_runner.py \
    --config-file examples/config_example.json \
    --env PRODUCTION

# Or with JSON string
python airflow_runner.py \
    --config '{"elasticsearch":{...},"mysql":{...}}' \
    --env PRODUCTION
```

#### In Airflow DAG
```python
from airflow_runner import run_collection
import json

config = {"elasticsearch": {...}, "mysql": {...}}
result = run_collection(json.dumps(config), env='PRODUCTION')
```

### Migration Guide

For existing installations:

1. **Create environment files**:
   ```bash
   ./setup_env.sh
   ```

2. **Update deployment scripts**:
   ```bash
   # Before
   python main.py collect --config config/config.yaml
   
   # After
   python main.py collect --env PRODUCTION
   ```

3. **Move secrets from YAML to .env files**:
   - Copy sensitive values from `config.yaml` to `.env.production`
   - Remove sensitive values from `config.yaml`
   - Keep `config.yaml` for base configuration only

### Security Improvements

- Secrets separated from code via `.env` files
- `.env.staging` and `.env.production` added to `.gitignore`
- File permissions recommendation (chmod 600)
- Environment-specific credentials support
- Secret management system recommendations

### Breaking Changes

None. The system is backward compatible:
- Existing YAML-only configuration still works
- No changes required to existing deployments
- Environment files are optional (defaults to YAML)

### Deprecation Notices

None in this release.

---

## [1.0.0] - 2026-01-13

### Initial Release

- Elasticsearch index metrics collection
- MySQL storage with connection pooling
- Health check functionality
- Cleanup old data functionality
- YAML-based configuration
- Environment variable overrides (basic)
- Comprehensive logging
- CLI interface
- Design patterns implementation (Strategy, Repository, Facade, Singleton, Factory)
- Modular architecture

---

## Future Enhancements

Planned features for future releases:

- [ ] Support for additional secret management systems (Vault, AWS Secrets Manager)
- [ ] Kubernetes deployment configurations
- [ ] Docker Compose setup for local development
- [ ] Metrics export to Prometheus
- [ ] Web UI for configuration management
- [ ] Multi-cluster Elasticsearch support
- [ ] Real-time alerting
- [ ] Advanced filtering and aggregation
- [ ] API endpoints for external access
- [ ] Grafana dashboard templates

