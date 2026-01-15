#!/bin/bash
# Showcase Elasticsearch queries on Docker cluster

ES_URL="http://localhost:9200"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Elasticsearch Query Showcase"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Cluster Health
echo "1️⃣  Cluster Health:"
curl -s "$ES_URL/_cluster/health?pretty" | jq '.'
echo ""

# 2. List all indices
echo "2️⃣  All Indices:"
curl -s "$ES_URL/_cat/indices?v&h=index,docs.count,store.size,health,status"
echo ""
echo ""

# 3. Index stats for a specific index
echo "3️⃣  Detailed Stats for 'events-user-actions':"
curl -s "$ES_URL/events-user-actions/_stats?pretty" | jq '.indices."events-user-actions".total.docs, .indices."events-user-actions".total.store'
echo ""

# 4. Search query - get sample documents
echo "4️⃣  Sample Documents from 'events-user-actions' (limit 3):"
curl -s "$ES_URL/events-user-actions/_search?pretty&size=3" -H 'Content-Type: application/json' -d '{
  "query": {
    "match_all": {}
  },
  "sort": [
    {"timestamp": "desc"}
  ]
}' | jq '.hits.hits[] | {_id, _source}'
echo ""

# 5. Aggregation query - count by level
echo "5️⃣  Aggregation: Count Documents by Level:"
curl -s "$ES_URL/logs-app-*/_search?pretty&size=0" -H 'Content-Type: application/json' -d '{
  "aggs": {
    "levels": {
      "terms": {
        "field": "level",
        "size": 10
      }
    }
  }
}' | jq '.aggregations.levels.buckets'
echo ""

# 6. Range query - documents in date range
echo "6️⃣  Range Query: Documents from January 15-20, 2024:"
curl -s "$ES_URL/logs-app-*/_search?pretty&size=0" -H 'Content-Type: application/json' -d '{
  "query": {
    "range": {
      "timestamp": {
        "gte": "2024-01-15",
        "lte": "2024-01-20"
      }
    }
  }
}' | jq '.hits.total'
echo ""

# 7. Terms aggregation with stats
echo "7️⃣  User Activity Stats (Top 5 Users by Event Count):"
curl -s "$ES_URL/events-user-actions/_search?pretty&size=0" -H 'Content-Type: application/json' -d '{
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
}' | jq '.aggregations.top_users.buckets'
echo ""

# 8. Multi-index search
echo "8️⃣  Search Across Multiple Indices (logs-* pattern):"
curl -s "$ES_URL/logs-*/_search?pretty&size=5" -H 'Content-Type: application/json' -d '{
  "query": {
    "bool": {
      "must": [
        {"match": {"level": "info"}}
      ]
    }
  },
  "_source": ["timestamp", "message", "level"]
}' | jq '.hits.hits[] | {index: ._index, source: ._source}'
echo ""

# 9. Count API
echo "9️⃣  Total Document Count by Index Pattern:"
for pattern in "logs-*" "events-*" "metrics-*" "orders-*" "products-*"; do
    count=$(curl -s "$ES_URL/$pattern/_count" | jq '.count')
    echo "  $pattern: $count documents"
done
echo ""

# 10. Mapping info
echo "🔟  Mapping for 'products-catalog':"
curl -s "$ES_URL/products-catalog/_mapping?pretty" | jq '.."properties"'
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Showcase complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

