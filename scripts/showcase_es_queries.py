#!/usr/bin/env python3
"""
Showcase Elasticsearch queries using Python client.
Demonstrates various ES query types against the Docker cluster.
"""

from elasticsearch import Elasticsearch
from datetime import datetime
import json


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def showcase_es_queries():
    """Run various Elasticsearch queries for demonstration."""
    
    # Connect to ES
    es = Elasticsearch(["http://localhost:9200"])
    
    print_section("🔍 Elasticsearch Query Showcase")
    
    # 1. Cluster Info
    print_section("1️⃣  Cluster Information")
    info = es.info()
    print(f"Cluster Name: {info['cluster_name']}")
    print(f"ES Version: {info['version']['number']}")
    print(f"Lucene Version: {info['version']['lucene_version']}")
    
    # 2. Cluster Health
    print_section("2️⃣  Cluster Health")
    health = es.cluster.health()
    print(f"Status: {health['status']}")
    print(f"Number of Nodes: {health['number_of_nodes']}")
    print(f"Active Shards: {health['active_shards']}")
    print(f"Unassigned Shards: {health['unassigned_shards']}")
    
    # 3. List All Indices
    print_section("3️⃣  All Indices")
    indices = es.cat.indices(format='json', h='index,docs.count,store.size,health')
    for idx in indices:
        print(f"  {idx['index']:<45} | Docs: {idx['docs.count']:>6} | Size: {idx['store.size']:>10} | Health: {idx['health']}")
    
    # 4. Simple Search - Get Sample Documents
    print_section("4️⃣  Sample Documents from 'events-user-actions'")
    response = es.search(
        index="events-user-actions",
        body={
            "size": 3,
            "query": {"match_all": {}},
            "sort": [{"timestamp": "desc"}]
        }
    )
    for hit in response['hits']['hits']:
        print(f"  Doc ID: {hit['_id']}")
        print(f"  Source: {json.dumps(hit['_source'], indent=2)}")
        print()
    
    # 5. Aggregation - Count by Level
    print_section("5️⃣  Aggregation: Event Counts by Level")
    response = es.search(
        index="logs-app-*",
        body={
            "size": 0,
            "aggs": {
                "levels": {
                    "terms": {
                        "field": "level",
                        "size": 10
                    }
                }
            }
        }
    )
    for bucket in response['aggregations']['levels']['buckets']:
        print(f"  {bucket['key']:<15} : {bucket['doc_count']:>6} documents")
    
    # 6. Range Query
    print_section("6️⃣  Range Query: Documents from Jan 15-20, 2024")
    response = es.search(
        index="logs-app-*",
        body={
            "size": 0,
            "query": {
                "range": {
                    "timestamp": {
                        "gte": "2024-01-15",
                        "lte": "2024-01-20"
                    }
                }
            }
        }
    )
    total = response['hits']['total']['value']
    print(f"  Found {total} documents in date range")
    
    # 7. Terms Aggregation with Sub-aggregation
    print_section("7️⃣  Top Users by Activity (with Average Values)")
    response = es.search(
        index="events-user-actions",
        body={
            "size": 0,
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
        }
    )
    for bucket in response['aggregations']['top_users']['buckets']:
        avg = bucket['avg_value']['value']
        print(f"  {bucket['key']:<15} : {bucket['doc_count']:>5} events (avg value: {avg:.2f})")
    
    # 8. Bool Query with Multiple Conditions
    print_section("8️⃣  Bool Query: Info-level logs with specific user")
    response = es.search(
        index="logs-app-*",
        body={
            "size": 5,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"level": "info"}}
                    ],
                    "filter": [
                        {"exists": {"field": "user_id"}}
                    ]
                }
            },
            "_source": ["timestamp", "message", "level", "user_id"]
        }
    )
    print(f"  Found {response['hits']['total']['value']} matching documents")
    print(f"  Showing first {len(response['hits']['hits'])}:")
    for hit in response['hits']['hits']:
        src = hit['_source']
        print(f"    [{src['timestamp']}] {src['level']}: {src['message'][:50]}...")
    
    # 9. Multi-Index Search
    print_section("9️⃣  Multi-Index Search (logs-*, events-*, metrics-*)")
    for pattern in ["logs-*", "events-*", "metrics-*"]:
        response = es.count(index=pattern)
        print(f"  {pattern:<20} : {response['count']:>6} documents")
    
    # 10. Stats Aggregation
    print_section("🔟  Statistical Aggregation on 'value' Field")
    response = es.search(
        index="events-user-actions",
        body={
            "size": 0,
            "aggs": {
                "value_stats": {
                    "stats": {
                        "field": "value"
                    }
                }
            }
        }
    )
    stats = response['aggregations']['value_stats']
    print(f"  Count: {stats['count']}")
    print(f"  Min: {stats['min']:.2f}")
    print(f"  Max: {stats['max']:.2f}")
    print(f"  Avg: {stats['avg']:.2f}")
    print(f"  Sum: {stats['sum']:.2f}")
    
    # 11. Date Histogram Aggregation
    print_section("1️⃣1️⃣  Date Histogram: Documents per Day")
    response = es.search(
        index="logs-app-*",
        body={
            "size": 0,
            "aggs": {
                "daily_docs": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "day"
                    }
                }
            }
        }
    )
    for bucket in response['aggregations']['daily_docs']['buckets']:
        date = bucket['key_as_string']
        count = bucket['doc_count']
        print(f"  {date:<25} : {count:>5} documents")
    
    # 12. Get Mapping
    print_section("1️⃣2️⃣  Index Mapping for 'products-catalog'")
    mapping = es.indices.get_mapping(index="products-catalog")
    props = mapping['products-catalog']['mappings']['properties']
    print("  Fields:")
    for field, config in props.items():
        field_type = config.get('type', 'N/A')
        print(f"    {field:<20} : {field_type}")
    
    # 13. Index Settings
    print_section("1️⃣3️⃣  Index Settings for 'orders-2024-q1'")
    settings = es.indices.get_settings(index="orders-2024-q1")
    idx_settings = settings['orders-2024-q1']['settings']['index']
    print(f"  Number of Shards: {idx_settings.get('number_of_shards', 'N/A')}")
    print(f"  Number of Replicas: {idx_settings.get('number_of_replicas', 'N/A')}")
    print(f"  Creation Date: {idx_settings.get('creation_date', 'N/A')}")
    print(f"  UUID: {idx_settings.get('uuid', 'N/A')}")
    
    print_section("✅ Showcase Complete!")


if __name__ == "__main__":
    try:
        showcase_es_queries()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Docker ES is running: docker ps")
        print("  2. ES is accessible: curl http://localhost:9200")

