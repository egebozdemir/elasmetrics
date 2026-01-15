# 🔍 Elasticsearch Query Guide

This guide shows you how to interact with the Elasticsearch cluster running in Docker.

## Quick Access Methods

### 1️⃣ **cURL (Command Line)**

The simplest way to query ES from your terminal:

```bash
# Cluster health
curl http://localhost:9200/_cluster/health?pretty

# List all indices
curl http://localhost:9200/_cat/indices?v

# Get documents from an index
curl http://localhost:9200/events-user-actions/_search?pretty&size=3

# Search query
curl -X POST "http://localhost:9200/logs-app-*/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {"level": "info"}
    }
  }'
```

---

### 2️⃣ **Bash Script (Pre-made Queries)**

Run the showcase script with 13 different query examples:

```bash
./scripts/showcase-es-queries.sh
```

This script demonstrates:
- Cluster health and info
- Index statistics
- Document searches
- Aggregations (terms, stats, date histogram)
- Range queries
- Multi-index searches
- Mapping and settings inspection

---

### 3️⃣ **Python Script (Programmatic Access)**

Use the Python client for more control:

```bash
# Activate your virtual environment first
source venv/bin/activate

# Run the showcase
python scripts/showcase_es_queries.py
```

Or write your own queries:

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(["http://localhost:9200"])

# Simple search
response = es.search(
    index="events-user-actions",
    body={
        "size": 10,
        "query": {"match_all": {}}
    }
)

for hit in response['hits']['hits']:
    print(hit['_source'])
```

---

### 4️⃣ **Direct Container Access**

Execute commands directly in the ES container:

```bash
# Enter the container
docker exec -it elasticsearch bash

# Inside container, use curl
curl http://localhost:9200/_cat/indices?v

# Exit
exit
```

---

### 5️⃣ **Using Our Existing Collector**

Use the metrics collector code as a reference:

```python
from elasticsearch import Elasticsearch

# Same connection our project uses
es = Elasticsearch(["http://localhost:9200"])

# Get index stats
stats = es.indices.stats(index="events-user-actions")
print(stats)

# Cat indices API (used by our collector)
indices = es.cat.indices(format='json', h='index,docs.count,store.size')
for idx in indices:
    print(f"{idx['index']}: {idx['docs.count']} docs")
```

---

## 📚 Common Query Examples

### **Search by Field Value**

```bash
curl -X POST "http://localhost:9200/logs-app-*/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "match": {"level": "info"}
    },
    "size": 5
  }'
```

### **Range Query (Date)**

```bash
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "range": {
        "timestamp": {
          "gte": "2024-01-10",
          "lte": "2024-01-20"
        }
      }
    }
  }'
```

### **Aggregation - Count by Field**

```bash
curl -X POST "http://localhost:9200/logs-app-*/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{
    "aggs": {
      "levels": {
        "terms": {
          "field": "level",
          "size": 10
        }
      }
    }
  }'
```

### **Bool Query (Multiple Conditions)**

```bash
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"range": {"value": {"gte": 500}}}
        ],
        "filter": [
          {"exists": {"field": "user_id"}}
        ]
      }
    }
  }'
```

### **Statistical Aggregation**

```bash
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{
    "aggs": {
      "value_stats": {
        "stats": {
          "field": "value"
        }
      }
    }
  }'
```

### **Top N with Sub-aggregation**

```bash
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{
    "aggs": {
      "top_users": {
        "terms": {
          "field": "user_id",
          "size": 5
        },
        "aggs": {
          "avg_value": {
            "avg": {
              "field": "value"
            }
          }
        }
      }
    }
  }'
```

---

## 🎯 Useful ES APIs

| API | Endpoint | Description |
|-----|----------|-------------|
| **Cluster Health** | `GET /_cluster/health` | Cluster status |
| **Node Info** | `GET /_nodes` | Node information |
| **Cat Indices** | `GET /_cat/indices?v` | List all indices |
| **Index Stats** | `GET /<index>/_stats` | Detailed index statistics |
| **Mapping** | `GET /<index>/_mapping` | Field mappings |
| **Settings** | `GET /<index>/_settings` | Index settings |
| **Search** | `POST /<index>/_search` | Search documents |
| **Count** | `GET /<index>/_count` | Count documents |
| **Get Document** | `GET /<index>/_doc/<id>` | Get specific document |
| **Bulk** | `POST /_bulk` | Bulk operations |

---

## 🔧 Testing Your Queries

### Check if ES is Running

```bash
curl http://localhost:9200
```

Expected output:
```json
{
  "name" : "...",
  "cluster_name" : "docker-cluster",
  "version" : {
    "number" : "8.11.0"
  }
}
```

### Quick Index Check

```bash
curl http://localhost:9200/_cat/indices?v
```

### View All Data in an Index

```bash
curl "http://localhost:9200/products-catalog/_search?pretty&size=100"
```

---

## 📊 Sample Data Overview

Your Docker ES cluster has these indices:

| Index Pattern | Count | Purpose |
|---------------|-------|---------|
| `logs-app-2024.01.*` | 4,500 | Application logs |
| `metrics-system-2024.01` | 5,000 | System metrics |
| `events-user-actions` | 10,000 | User activity events |
| `products-catalog` | 500 | Product data |
| `orders-2024-q1` | 3,000 | Order records |

All documents have these common fields:
- `timestamp` (date)
- `message` (text)
- `level` (keyword)
- `user_id` (keyword)
- `value` (long)

---

## 🚀 Interactive Tools

### Option A: Install Kibana (Recommended for GUI)

Add to `docker-compose.yml`:

```yaml
kibana:
  image: docker.elastic.co/kibana/kibana:8.11.0
  ports:
    - "5601:5601"
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
  depends_on:
    - elasticsearch
```

Then access: http://localhost:5601

### Option B: Use ES Head Plugin

```bash
docker run -p 9100:9100 mobz/elasticsearch-head:5
```

Access: http://localhost:9100

### Option C: Use Dejavu (Web UI)

```bash
docker run -p 1358:1358 -d appbaseio/dejavu
```

Access: http://localhost:1358

---

## 💡 Tips

1. **Use `pretty` parameter** for readable JSON output:
   ```bash
   curl "http://localhost:9200/_search?pretty"
   ```

2. **Pipe to `jq`** for better formatting:
   ```bash
   curl -s http://localhost:9200/_search | jq '.'
   ```

3. **Use `size=0`** for aggregation-only queries (faster):
   ```bash
   curl "http://localhost:9200/logs-*/_search?size=0" -d '{"aggs": {...}}'
   ```

4. **Check query performance** with `explain`:
   ```bash
   curl "http://localhost:9200/logs-*/_search?explain=true"
   ```

5. **Use wildcards** for multiple indices:
   ```bash
   curl "http://localhost:9200/logs-*/_search"
   ```

---

## 🐛 Troubleshooting

### ES not responding?

```bash
# Check if container is running
docker ps | grep elasticsearch

# Check ES logs
docker logs elasticsearch

# Restart ES
docker restart elasticsearch
```

### Port conflict?

```bash
# Check what's using port 9200
lsof -i :9200

# Use different port in docker-compose.yml
ports:
  - "9201:9200"
```

---

## 📖 Further Reading

- [Elasticsearch Query DSL](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
- [Aggregations Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations.html)
- [Python ES Client Docs](https://elasticsearch-py.readthedocs.io/)
- [ES REST APIs](https://www.elastic.co/guide/en/elasticsearch/reference/current/rest-apis.html)

---

**Quick Start:**

```bash
# 1. Run the bash showcase
./scripts/showcase-es-queries.sh

# 2. Or run the Python showcase
python scripts/showcase_es_queries.py

# 3. Or just explore with curl
curl http://localhost:9200/_cat/indices?v
```

🎉 **Happy Querying!**

