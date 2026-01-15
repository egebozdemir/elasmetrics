#!/usr/bin/env python3
"""
Test script to verify time-series + current state setup.
"""

from src.repositories import MySQLRepository
from src.utils import ConfigLoader


def test_current_state():
    """Test the current state VIEW."""
    print("=" * 60)
    print("Testing Current State Queries")
    print("=" * 60)
    
    config = ConfigLoader().load_config()
    repo = MySQLRepository(config['mysql'])
    
    # Get current state (latest for each index)
    current_state = repo.get_current_state()
    
    print(f"\n✅ Found {len(current_state)} indices in current state\n")
    print(f"{'Index Name':<45} {'Docs':>10} {'Size':>12} {'Health':>8}")
    print("-" * 80)
    
    for metric in current_state:
        print(f"{metric['index_name']:<45} {metric['docs_count']:>10} {metric['store_size_human']:>12} {metric['health']:>8}")
    
    print("\n" + "=" * 60)


def test_historical_data():
    """Test historical time-series queries."""
    print("\nTesting Historical Queries")
    print("=" * 60)
    
    config = ConfigLoader().load_config()
    repo = MySQLRepository(config['mysql'])
    
    # Get latest 20 records (all collection runs)
    historical = repo.get_latest_metrics(limit=20)
    
    print(f"\n✅ Found {len(historical)} recent records\n")
    
    # Group by timestamp to show collection runs
    from collections import defaultdict
    by_timestamp = defaultdict(list)
    
    for record in historical:
        ts = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        by_timestamp[ts].append(record['index_name'])
    
    print(f"{'Collection Time':<20} {'Index Count':>15}")
    print("-" * 40)
    for ts, indices in sorted(by_timestamp.items(), reverse=True):
        print(f"{ts:<20} {len(indices):>15}")
    
    print(f"\nTotal collection runs: {len(by_timestamp)}")
    print("=" * 60)


def test_summary():
    """Test summary statistics."""
    print("\nTesting Summary Statistics")
    print("=" * 60)
    
    config = ConfigLoader().load_config()
    repo = MySQLRepository(config['mysql'])
    
    summary = repo.get_indices_summary()
    
    print(f"\n✅ Summary for {len(summary)} indices\n")
    print(f"{'Index Name':<45} {'Records':>10} {'Avg Docs':>12}")
    print("-" * 70)
    
    for item in summary:
        avg_docs = int(item.get('avg_docs', 0)) if item.get('avg_docs') else 0
        print(f"{item['index_name']:<45} {item['total_records']:>10} {avg_docs:>12}")
    
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_current_state()
        test_historical_data()
        test_summary()
        
        print("\n✅ All tests passed!")
        print("\n💡 Next steps:")
        print("   1. View QUERY_GUIDE.md for more query examples")
        print("   2. Use index_metrics_latest for current state queries")
        print("   3. Use index_metrics for trend analysis")
        print("   4. Set up Grafana dashboards using provided queries")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

