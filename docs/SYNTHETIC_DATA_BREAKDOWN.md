# 📊 Synthetic Data Breakdown - Detailed Index Analysis

## Overview

Your Elasticsearch cluster contains **7 indices** with **~23,000 documents** totaling **~1.8 MB** of data.

---

## 📁 Index-by-Index Breakdown

### 1️⃣ **`events-user-actions`** 
**Type:** User Activity Events | **Status:** ✅ Green | **Size:** 833.1 KB

**Statistics:**
- **Document Count:** 10,000 (largest dataset)
- **Primary Shards:** 1
- **Replicas:** 0
- **Average Doc Size:** ~83 bytes

**Data Structure:**
```json
{
  "timestamp": "2024-01-XX THH:MM:SS Z",
  "message": "Sample log message N",
  "level": "info",
  "user_id": "user_0" to "user_99",
  "value": 0 to 999 (random integer)
}
```

**Sample Document:**
```json
{
  "timestamp": "2024-01-15T14:23:45Z",
  "message": "Sample log message 5432",
  "level": "info",
  "user_id": "user_73",
  "value": 856
}
```

**Data Characteristics:**
- 100 unique users (`user_0` through `user_99`)
- All events have `level: "info"`
- Values distributed randomly from 0-999
- Timestamps spread across January 2024
- **Use Case:** User behavior analysis, activity tracking, value aggregations

**Sample Queries:**
```bash
# Top 10 most active users
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"top_users": {"terms": {"field": "user_id", "size": 10}}}}'

# Average value per user
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"users": {"terms": {"field": "user_id"}, "aggs": {"avg_val": {"avg": {"field": "value"}}}}}}'

# High-value events (> 900)
curl -X POST "http://localhost:9200/events-user-actions/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"range": {"value": {"gte": 900}}}}'
```

---

### 2️⃣ **`orders-2024-q1`**
**Type:** E-commerce Orders | **Status:** ✅ Green | **Size:** 271.8 KB

**Statistics:**
- **Document Count:** 3,000
- **Primary Shards:** 1
- **Replicas:** 0
- **Average Doc Size:** ~91 bytes

**Data Structure:**
```json
{
  "timestamp": "2024-01-XX THH:MM:SS Z",
  "message": "Sample log message N",
  "level": "info",
  "user_id": "user_0" to "user_99",
  "value": 0 to 999 (order value/amount)
}
```

**Sample Document:**
```json
{
  "timestamp": "2024-01-08T09:15:22Z",
  "message": "Sample log message 1247",
  "level": "info",
  "user_id": "user_42",
  "value": 654
}
```

**Data Characteristics:**
- Q1 2024 order data (January focus)
- 100 unique customers
- Order values: $0 - $999
- **Use Case:** Sales analysis, customer ordering patterns, revenue tracking

**Sample Queries:**
```bash
# Total order value
curl -X POST "http://localhost:9200/orders-2024-q1/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"total_revenue": {"sum": {"field": "value"}}}}'

# Top customers by order count
curl -X POST "http://localhost:9200/orders-2024-q1/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"top_customers": {"terms": {"field": "user_id", "size": 10}}}}'

# Daily order volume
curl -X POST "http://localhost:9200/orders-2024-q1/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"daily_orders": {"date_histogram": {"field": "timestamp", "calendar_interval": "day"}}}}'
```

---

### 3️⃣ **`logs-app-2024.01.03`** (Data Stream)
**Type:** Application Logs | **Status:** ⚠️ Yellow | **Size:** 332.2 KB

**Statistics:**
- **Document Count:** 2,000 (highest volume day)
- **Primary Shards:** 1
- **Replicas:** 1 (unassigned - causing yellow status)
- **Average Doc Size:** ~166 bytes
- **Full Name:** `.ds-logs-app-2024.01.03-2026.01.13-000001`

**Data Structure:**
```json
{
  "timestamp": "2024-01-XX THH:MM:SS Z",
  "message": "Sample log message N",
  "level": "info",
  "user_id": "user_0" to "user_99",
  "value": 0 to 999
}
```

**Sample Document:**
```json
{
  "timestamp": "2024-01-03T18:47:33Z",
  "message": "Sample log message 891",
  "level": "info",
  "user_id": "user_8",
  "value": 423
}
```

**Data Characteristics:**
- Part of a data stream (`.ds-` prefix)
- Rolling logs by day (Jan 3rd data)
- Highest activity day in the logs
- **Use Case:** Application monitoring, debugging, log analysis

---

### 4️⃣ **`logs-app-2024.01.02`** (Data Stream)
**Type:** Application Logs | **Status:** ⚠️ Yellow | **Size:** 244.1 KB

**Statistics:**
- **Document Count:** 1,500
- **Primary Shards:** 1
- **Replicas:** 1 (unassigned)
- **Average Doc Size:** ~163 bytes
- **Full Name:** `.ds-logs-app-2024.01.02-2026.01.13-000001`

**Data Characteristics:**
- January 2nd logs
- Medium activity day
- Same structure as other log indices
- **Use Case:** Day-over-day log comparison

---

### 5️⃣ **`logs-app-2024.01.01`** (Data Stream)
**Type:** Application Logs | **Status:** ⚠️ Yellow | **Size:** 166.7 KB

**Statistics:**
- **Document Count:** 1,000 (lowest log volume)
- **Primary Shards:** 1
- **Replicas:** 1 (unassigned)
- **Average Doc Size:** ~167 bytes
- **Full Name:** `.ds-logs-app-2024.01.01-2026.01.13-000001`

**Data Characteristics:**
- New Year's Day logs
- Lowest activity (holiday effect simulation)
- Same structure as other log indices
- **Use Case:** Baseline comparison, holiday analysis

**Combined Logs Sample Queries:**
```bash
# Search across all log indices (wildcard)
curl "http://localhost:9200/logs-app-*/_search?pretty&size=5"

# Total log count
curl "http://localhost:9200/logs-app-*/_count"

# Logs per day
curl -X POST "http://localhost:9200/logs-app-*/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"by_day": {"date_histogram": {"field": "timestamp", "calendar_interval": "day"}}}}'

# Distribution by user
curl -X POST "http://localhost:9200/logs-app-*/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"users": {"terms": {"field": "user_id", "size": 20}}}}'
```

---

### 6️⃣ **`products-catalog`**
**Type:** Product Database | **Status:** ✅ Green | **Size:** 91.6 KB

**Statistics:**
- **Document Count:** 500 (smallest document set)
- **Primary Shards:** 1
- **Replicas:** 0
- **Average Doc Size:** ~183 bytes

**Data Structure:**
```json
{
  "timestamp": "2024-01-XX THH:MM:SS Z",
  "message": "Sample log message N",
  "level": "info",
  "user_id": "user_0" to "user_99",
  "value": 0 to 999 (product price/SKU)
}
```

**Sample Document:**
```json
{
  "timestamp": "2024-01-12T11:30:15Z",
  "message": "Sample log message 234",
  "level": "info",
  "user_id": "user_91",
  "value": 749
}
```

**Data Characteristics:**
- 500 unique products
- Product prices: $0 - $999
- Static catalog data
- **Use Case:** Product search, pricing analysis, inventory queries

**Sample Queries:**
```bash
# All products
curl "http://localhost:9200/products-catalog/_search?pretty&size=10"

# Price statistics
curl -X POST "http://localhost:9200/products-catalog/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"price_stats": {"stats": {"field": "value"}}}}'

# Expensive products (> $800)
curl -X POST "http://localhost:9200/products-catalog/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"range": {"value": {"gte": 800}}}}'
```

---

### 7️⃣ **`metrics-system-2024.01`** (Data Stream)
**Type:** System Metrics | **Status:** ⚠️ Yellow | **Size:** 249 bytes

**Statistics:**
- **Document Count:** 0 (empty - created but not populated)
- **Primary Shards:** 1
- **Replicas:** 1 (unassigned)
- **Full Name:** `.ds-metrics-system-2024.01-2026.01.13-000001`

**Data Characteristics:**
- Data stream template created
- No documents ingested yet
- Ready for system metrics ingestion
- **Use Case:** System monitoring, performance metrics

**Note:** This index was created but not populated with data. You could add metrics like:
```json
{
  "timestamp": "2024-01-15T10:00:00Z",
  "cpu_usage": 45.2,
  "memory_usage": 78.5,
  "disk_io": 1234,
  "network_rx": 5678
}
```

---

## 🎯 **Aggregate Statistics**

### Overall Cluster Data

| Metric | Value |
|--------|-------|
| **Total Documents** | 23,000 |
| **Total Size** | 1.94 MB |
| **Total Indices** | 7 |
| **Active Indices** | 6 (1 empty) |
| **Document Types** | 5 (logs, events, orders, products, metrics) |
| **Unique Users** | 100 (`user_0` - `user_99`) |
| **Date Range** | January 2024 |
| **Data Streams** | 4 (logs x3, metrics x1) |
| **Standard Indices** | 3 (events, orders, products) |

---

## 📈 **Data Distribution**

### Documents by Index Type

```
events-user-actions:  10,000 (43.5%) ████████████████████
orders-2024-q1:        3,000 (13.0%) ██████
logs-app-2024.01.03:   2,000 ( 8.7%) ████
logs-app-2024.01.02:   1,500 ( 6.5%) ███
logs-app-2024.01.01:   1,000 ( 4.3%) ██
products-catalog:        500 ( 2.2%) █
metrics-system:            0 ( 0.0%)
```

### Storage by Index Type

```
events-user-actions:  833.1 KB (42.8%) ████████████████████
orders-2024-q1:       271.8 KB (14.0%) ███████
logs-app-2024.01.03:  332.2 KB (17.1%) ████████
logs-app-2024.01.02:  244.1 KB (12.5%) ██████
logs-app-2024.01.01:  166.7 KB ( 8.6%) ████
products-catalog:      91.6 KB ( 4.7%) ██
metrics-system:       249 bytes (0.0%)
```

---

## 🔍 **Common Field Mappings**

All active indices share these fields:

| Field | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `timestamp` | `date` | ISO 8601 timestamp | `2024-01-15T14:23:45Z` |
| `message` | `text` | Log/event message | `"Sample log message 1234"` |
| `level` | `keyword` | Log level | `"info"` |
| `user_id` | `keyword` | User identifier | `"user_0"` to `"user_99"` |
| `value` | `long` | Numeric value | `0` to `999` |

---

## 🎪 **Showcase Query Examples**

### Cross-Index Analytics

```bash
# Total documents across all indices
curl "http://localhost:9200/_cat/count?v"

# Storage usage by index
curl "http://localhost:9200/_cat/indices?v&h=index,store.size&s=store.size:desc"

# Search across all indices
curl "http://localhost:9200/_all/_search?size=5"
```

### User Activity Analysis

```bash
# User with most activity across ALL indices
curl -X POST "http://localhost:9200/_all/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"top_users": {"terms": {"field": "user_id", "size": 10}}}}'

# User activity by index
curl -X POST "http://localhost:9200/_all/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"by_index": {"terms": {"field": "_index"}, "aggs": {"top_users": {"terms": {"field": "user_id", "size": 5}}}}}}'
```

### Time Series Analysis

```bash
# Document volume over time (all indices)
curl -X POST "http://localhost:9200/_all/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"over_time": {"date_histogram": {"field": "timestamp", "calendar_interval": "day"}}}}'

# Hourly distribution
curl -X POST "http://localhost:9200/_all/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"hourly": {"date_histogram": {"field": "timestamp", "calendar_interval": "hour"}}}}'
```

### Value Analysis

```bash
# Global value statistics
curl -X POST "http://localhost:9200/_all/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"value_stats": {"stats": {"field": "value"}}}}'

# Value distribution (histogram)
curl -X POST "http://localhost:9200/_all/_search?pretty&size=0" \
  -H 'Content-Type: application/json' \
  -d '{"aggs": {"value_ranges": {"histogram": {"field": "value", "interval": 100}}}}'
```

---

## 📊 **Data Quality Notes**

### Strengths
- ✅ Consistent schema across all indices
- ✅ Realistic data distribution (varied doc counts)
- ✅ Proper data stream usage for logs/metrics
- ✅ Appropriate shard/replica configuration
- ✅ Good variety of use cases (logs, events, orders, products)

### Known Limitations
- ⚠️ `metrics-system` index is empty (no data populated)
- ⚠️ All `level` fields are "info" (no debug/warn/error diversity)
- ⚠️ `message` field is generic (not contextual)
- ⚠️ Single timestamp format (no timezone variations)
- ⚠️ Limited user pool (only 100 users)

### Improvement Opportunities
```bash
# To add more realistic data:
# 1. Vary log levels
# 2. Add error/warning events
# 3. Populate metrics-system with real metrics
# 4. Add more user diversity (1000+ users)
# 5. Add geographic/demographic fields
# 6. Simulate realistic message patterns
```

---

## 🚀 **Quick Data Exploration Commands**

```bash
# Get a sample document from each index
for idx in events-user-actions orders-2024-q1 products-catalog logs-app-2024.01.01; do
  echo "=== $idx ==="
  curl -s "http://localhost:9200/$idx/_search?size=1&pretty" | jq '.hits.hits[0]._source'
  echo ""
done

# Compare index sizes
curl -s "http://localhost:9200/_cat/indices?v&h=index,docs.count,store.size&s=docs.count:desc"

# Get mapping for any index
curl "http://localhost:9200/events-user-actions/_mapping?pretty"

# Count documents by pattern
for pattern in "logs-*" "events-*" "orders-*" "products-*"; do
  count=$(curl -s "http://localhost:9200/$pattern/_count" | jq '.count')
  echo "$pattern: $count"
done
```

---

## 📚 **Use This Data For:**

1. **Metrics Collection Testing** - Run `python main.py collect` to gather metrics
2. **Query Performance Testing** - Benchmark different query types
3. **Aggregation Demonstrations** - Show various aggregation patterns
4. **Data Stream Examples** - Work with rolling indices
5. **Time Series Analysis** - Analyze trends over time
6. **User Behavior Analytics** - Track user patterns
7. **E-commerce Analytics** - Order and product analysis
8. **Log Analysis** - Application monitoring patterns
9. **Cross-Index Queries** - Multi-index search demonstrations
10. **Dashboard Prototyping** - Use for visualization tools (Kibana, Grafana)

---

**Summary:** You have a well-structured, multi-purpose dataset with 23K documents across 7 indices, perfect for demonstrating Elasticsearch capabilities and metrics collection! 🎯

