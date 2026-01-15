#!/bin/bash
# Populate Elasticsearch with sample data for testing

echo "📊 Populating Elasticsearch with sample data..."
echo ""

ES_URL="http://localhost:9200"

# Create sample indices with different characteristics
indices=(
    "logs-app-2024.01.01:1000:100"
    "logs-app-2024.01.02:1500:150"
    "logs-app-2024.01.03:2000:200"
    "metrics-system-2024.01:5000:500"
    "events-user-actions:10000:1000"
    "products-catalog:500:50"
    "orders-2024-q1:3000:300"
)

for entry in "${indices[@]}"; do
    IFS=':' read -r index_name doc_count size_mb <<< "$entry"
    
    echo "Creating index: $index_name"
    
    # Create index with settings
    curl -X PUT "$ES_URL/$index_name" -H 'Content-Type: application/json' -d '{
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0
      },
      "mappings": {
        "properties": {
          "timestamp": {"type": "date"},
          "message": {"type": "text"},
          "level": {"type": "keyword"},
          "user_id": {"type": "keyword"},
          "value": {"type": "long"}
        }
      }
    }' -s > /dev/null
    
    # Add some documents
    echo "  Adding $doc_count sample documents..."
    for ((i=1; i<=$doc_count; i++)); do
        curl -X POST "$ES_URL/$index_name/_doc" -H 'Content-Type: application/json' -d "{
          \"timestamp\": \"2024-01-$(printf %02d $((RANDOM % 31 + 1)))T$(printf %02d $((RANDOM % 24))):$(printf %02d $((RANDOM % 60))):00Z\",
          \"message\": \"Sample log message $i\",
          \"level\": \"info\",
          \"user_id\": \"user_$((RANDOM % 100))\",
          \"value\": $((RANDOM % 1000))
        }" -s > /dev/null
        
        # Show progress
        if [ $((i % 100)) -eq 0 ]; then
            echo "    Progress: $i/$doc_count documents"
        fi
    done
    
    echo "  ✅ Created $index_name with $doc_count documents"
    echo ""
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Sample data populated!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Indices created:"
curl -s "$ES_URL/_cat/indices?v"
echo ""
echo "Now you can run:"
echo "  python main.py collect"

