#!/bin/bash
# Quick script to inspect synthetic data in Elasticsearch

ES_URL="http://localhost:9200"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Synthetic Data Inspector"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Summary
echo "📈 CLUSTER SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$ES_URL/_cat/indices?v&h=index,docs.count,store.size,health,status&s=docs.count:desc"
echo ""

# Total counts
echo "📊 TOTAL COUNTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
total_docs=$(curl -s "$ES_URL/_all/_count" | jq '.count')
echo "Total Documents: $total_docs"
echo ""

# Pattern counts
echo "🔍 COUNTS BY PATTERN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
for pattern in "logs-*" "events-*" "orders-*" "products-*" "metrics-*"; do
    count=$(curl -s "$ES_URL/$pattern/_count" 2>/dev/null | jq '.count // 0')
    printf "%-20s : %s documents\n" "$pattern" "$count"
done
echo ""

# Sample documents
echo "📄 SAMPLE DOCUMENTS (1 from each index)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get list of indices
indices=$(curl -s "$ES_URL/_cat/indices?h=index" | grep -v "^\.")

for idx in $indices; do
    echo ""
    echo "Index: $idx"
    echo "---"
    curl -s "$ES_URL/$idx/_search?size=1&pretty" | jq '.hits.hits[0]._source' 2>/dev/null || echo "No documents"
done

# Also show data stream indices
echo ""
echo "Data Stream Indices:"
echo "---"
ds_indices=$(curl -s "$ES_URL/_cat/indices?h=index" | grep "^\.ds-")
for idx in $ds_indices; do
    count=$(curl -s "$ES_URL/$idx/_count" | jq '.count')
    echo "$idx: $count documents"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Field mappings
echo ""
echo "🗺️  FIELD MAPPINGS (events-user-actions)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s "$ES_URL/events-user-actions/_mapping?pretty" | jq '.."properties"' | head -20

echo ""
echo "✅ Inspection complete! See SYNTHETIC_DATA_BREAKDOWN.md for full details."

