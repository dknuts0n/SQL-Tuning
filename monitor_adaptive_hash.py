#!/usr/bin/env python3
"""
Script to monitor MySQL InnoDB Adaptive Hash Index (AHI) usage.

The Adaptive Hash Index is an InnoDB optimization that builds hash indexes
automatically for frequently accessed index pages. This script monitors
AHI performance metrics to help determine if AHI is beneficial for your
workload.

Requirements:
    pip install mysql-connector-python

Usage:
    python monitor_adaptive_hash.py
    python monitor_adaptive_hash.py --interval 5 --duration 60
    python monitor_adaptive_hash.py --output-html ahi_report.html

Configuration:
    Set database credentials via environment variables:
    - MYSQL_HOST (default: localhost)
    - MYSQL_PORT (default: 3306)
    - MYSQL_USER (default: root)
    - MYSQL_PASSWORD
    - MYSQL_DATABASE (optional)
"""

import os
import sys
import argparse
import time
import mysql.connector
from mysql.connector import Error
from typing import Dict, List, Optional
from datetime import datetime


def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables."""
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
    }

    password = os.getenv('MYSQL_PASSWORD')
    if password:
        config['password'] = password

    database = os.getenv('MYSQL_DATABASE')
    if database:
        config['database'] = database

    return config


def check_ahi_enabled(cursor) -> bool:
    """Check if Adaptive Hash Index is enabled."""
    cursor.execute("SHOW VARIABLES LIKE 'innodb_adaptive_hash_index'")
    result = cursor.fetchone()
    if result:
        return result[1].upper() == 'ON'
    return False


def get_ahi_status(cursor) -> Dict[str, any]:
    """Get current Adaptive Hash Index status and metrics."""
    metrics = {}

    # Get AHI enabled status
    cursor.execute("SHOW VARIABLES LIKE 'innodb_adaptive_hash_index'")
    result = cursor.fetchone()
    metrics['ahi_enabled'] = result[1].upper() == 'ON' if result else False

    # Get AHI partitions (MySQL 5.7.9+)
    cursor.execute("SHOW VARIABLES LIKE 'innodb_adaptive_hash_index_parts'")
    result = cursor.fetchone()
    metrics['ahi_partitions'] = int(result[1]) if result else 'N/A'

    # Get metrics from INFORMATION_SCHEMA.INNODB_METRICS
    metrics_query = """
        SELECT NAME, COUNT
        FROM INFORMATION_SCHEMA.INNODB_METRICS
        WHERE NAME IN (
            'adaptive_hash_searches',
            'adaptive_hash_searches_btree',
            'adaptive_hash_pages_added',
            'adaptive_hash_pages_removed',
            'adaptive_hash_rows_added',
            'adaptive_hash_rows_removed',
            'adaptive_hash_rows_deleted_no_hash_entry',
            'adaptive_hash_rows_updated'
        )
        AND STATUS = 'enabled'
    """

    cursor.execute(metrics_query)
    for row in cursor.fetchall():
        metrics[row[0]] = row[1]

    # Calculate hit rate if we have the data
    searches = metrics.get('adaptive_hash_searches', 0)
    btree_searches = metrics.get('adaptive_hash_searches_btree', 0)

    if searches > 0:
        # AHI hit = total searches - btree searches
        ahi_hits = searches - btree_searches
        metrics['ahi_hit_rate'] = (ahi_hits / searches) * 100
    else:
        metrics['ahi_hit_rate'] = 0.0

    # Get buffer pool info
    cursor.execute("""
        SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_size'
    """)
    result = cursor.fetchone()
    if result:
        metrics['buffer_pool_size'] = int(result[1])

    return metrics


def get_ahi_memory_info(cursor) -> Dict[str, any]:
    """Get memory usage information for Adaptive Hash Index."""
    memory_info = {}

    # Try to get AHI memory usage from ENGINE INNODB STATUS
    cursor.execute("SHOW ENGINE INNODB STATUS")
    result = cursor.fetchone()

    if result:
        status_text = result[2]

        # Parse the status text for AHI information
        for line in status_text.split('\n'):
            line = line.strip()

            # Look for adaptive hash index info
            if 'Hash table size' in line:
                parts = line.split(',')
                for part in parts:
                    if 'Hash table size' in part:
                        try:
                            memory_info['hash_table_size'] = int(part.split()[-1])
                        except (ValueError, IndexError):
                            pass
                    elif 'node heap has' in part:
                        try:
                            # Extract buffer count
                            words = part.split()
                            if 'buffer(s)' in part:
                                idx = words.index('buffer(s)')
                                memory_info['hash_buffers'] = int(words[idx - 1])
                        except (ValueError, IndexError):
                            pass

    return memory_info


def enable_ahi_metrics(cursor):
    """Enable InnoDB AHI metrics if not already enabled."""
    metrics_to_enable = [
        'adaptive_hash_searches',
        'adaptive_hash_searches_btree',
        'adaptive_hash_pages_added',
        'adaptive_hash_pages_removed',
        'adaptive_hash_rows_added',
        'adaptive_hash_rows_removed',
        'adaptive_hash_rows_deleted_no_hash_entry',
        'adaptive_hash_rows_updated'
    ]

    for metric in metrics_to_enable:
        try:
            cursor.execute(f"SET GLOBAL innodb_monitor_enable = '{metric}'")
        except Error as e:
            # Metric might already be enabled or not available
            pass


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def format_number(num: int) -> str:
    """Format number with thousand separators."""
    return f"{num:,}"


def print_ahi_status(metrics: Dict[str, any], memory_info: Dict[str, any], timestamp: Optional[str] = None):
    """Print formatted AHI status."""
    if timestamp:
        print(f"\n{'='*80}")
        print(f"Adaptive Hash Index Status - {timestamp}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print("Adaptive Hash Index Status")
        print(f"{'='*80}")

    print(f"\nConfiguration:")
    print(f"  AHI Enabled: {metrics.get('ahi_enabled', 'Unknown')}")
    print(f"  AHI Partitions: {metrics.get('ahi_partitions', 'N/A')}")

    if 'buffer_pool_size' in metrics:
        print(f"  Buffer Pool Size: {format_bytes(metrics['buffer_pool_size'])}")

    print(f"\nMemory Usage:")
    if memory_info:
        if 'hash_table_size' in memory_info:
            print(f"  Hash Table Size: {format_number(memory_info['hash_table_size'])}")
        if 'hash_buffers' in memory_info:
            print(f"  Hash Buffers: {format_number(memory_info['hash_buffers'])}")
    else:
        print("  Unable to retrieve memory information")

    print(f"\nSearch Statistics:")
    if 'adaptive_hash_searches' in metrics:
        print(f"  Total AHI Searches: {format_number(metrics['adaptive_hash_searches'])}")
    if 'adaptive_hash_searches_btree' in metrics:
        print(f"  B-tree Searches: {format_number(metrics['adaptive_hash_searches_btree'])}")
    if 'ahi_hit_rate' in metrics:
        hit_rate = metrics['ahi_hit_rate']
        print(f"  AHI Hit Rate: {hit_rate:.2f}%")

        # Provide interpretation
        if hit_rate >= 80:
            print(f"    Status: Excellent - AHI is highly effective")
        elif hit_rate >= 60:
            print(f"    Status: Good - AHI is providing benefit")
        elif hit_rate >= 40:
            print(f"    Status: Moderate - AHI may provide some benefit")
        else:
            print(f"    Status: Low - Consider disabling AHI")

    print(f"\nPage Operations:")
    if 'adaptive_hash_pages_added' in metrics:
        print(f"  Pages Added: {format_number(metrics['adaptive_hash_pages_added'])}")
    if 'adaptive_hash_pages_removed' in metrics:
        print(f"  Pages Removed: {format_number(metrics['adaptive_hash_pages_removed'])}")

    print(f"\nRow Operations:")
    if 'adaptive_hash_rows_added' in metrics:
        print(f"  Rows Added: {format_number(metrics['adaptive_hash_rows_added'])}")
    if 'adaptive_hash_rows_removed' in metrics:
        print(f"  Rows Removed: {format_number(metrics['adaptive_hash_rows_removed'])}")
    if 'adaptive_hash_rows_updated' in metrics:
        print(f"  Rows Updated: {format_number(metrics['adaptive_hash_rows_updated'])}")
    if 'adaptive_hash_rows_deleted_no_hash_entry' in metrics:
        print(f"  Rows Deleted (no hash entry): {format_number(metrics['adaptive_hash_rows_deleted_no_hash_entry'])}")


def monitor_ahi(connection, interval: int, duration: Optional[int] = None):
    """Monitor AHI continuously."""
    cursor = connection.cursor()

    # Enable metrics
    enable_ahi_metrics(cursor)

    # Check if AHI is enabled
    if not check_ahi_enabled(cursor):
        print("\nWARNING: Adaptive Hash Index is currently DISABLED!")
        print("To enable it, set: SET GLOBAL innodb_adaptive_hash_index = ON;")
        print("\nShowing current status anyway...\n")

    start_time = time.time()
    iteration = 0

    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            metrics = get_ahi_status(cursor)
            memory_info = get_ahi_memory_info(cursor)

            print_ahi_status(metrics, memory_info, timestamp)

            # Check if we should stop
            if duration and (time.time() - start_time) >= duration:
                print(f"\nMonitoring completed after {duration} seconds ({iteration} iterations)")
                break

            # Wait for next interval (unless this is the last iteration)
            if not duration or (time.time() - start_time) < duration:
                print(f"\nNext update in {interval} seconds... (Ctrl+C to stop)")
                time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\nMonitoring stopped by user after {iteration} iterations")

    finally:
        cursor.close()


def generate_html_report(metrics: Dict[str, any], memory_info: Dict[str, any], output_file: str):
    """Generate HTML report of AHI status."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    hit_rate = metrics.get('ahi_hit_rate', 0)
    if hit_rate >= 80:
        status_class = 'excellent'
        status_text = 'Excellent'
    elif hit_rate >= 60:
        status_class = 'good'
        status_text = 'Good'
    elif hit_rate >= 40:
        status_class = 'moderate'
        status_text = 'Moderate'
    else:
        status_class = 'poor'
        status_text = 'Poor'

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Adaptive Hash Index Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric-box {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        .metric-label {{
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .metric-value {{
            color: #333;
            font-size: 24px;
            font-weight: bold;
        }}
        .hit-rate {{
            text-align: center;
            padding: 30px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .hit-rate.excellent {{
            background-color: #d4edda;
            border: 2px solid #28a745;
        }}
        .hit-rate.good {{
            background-color: #d1ecf1;
            border: 2px solid #17a2b8;
        }}
        .hit-rate.moderate {{
            background-color: #fff3cd;
            border: 2px solid #ffc107;
        }}
        .hit-rate.poor {{
            background-color: #f8d7da;
            border: 2px solid #dc3545;
        }}
        .hit-rate-value {{
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .hit-rate-label {{
            font-size: 18px;
            color: #666;
        }}
        .status {{
            font-size: 24px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .timestamp {{
            color: #999;
            text-align: right;
            font-size: 14px;
            margin-top: 30px;
        }}
        .recommendation {{
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .recommendation h3 {{
            margin-top: 0;
            color: #1976D2;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Adaptive Hash Index Monitoring Report</h1>

        <div class="hit-rate {status_class}">
            <div class="hit-rate-label">AHI Hit Rate</div>
            <div class="hit-rate-value">{hit_rate:.2f}%</div>
            <div class="status">Status: {status_text}</div>
        </div>

        <h2>Configuration</h2>
        <div class="metric-grid">
            <div class="metric-box">
                <div class="metric-label">AHI Enabled</div>
                <div class="metric-value">{"Yes" if metrics.get('ahi_enabled') else "No"}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">AHI Partitions</div>
                <div class="metric-value">{metrics.get('ahi_partitions', 'N/A')}</div>
            </div>
            {"" if 'buffer_pool_size' not in metrics else f'''
            <div class="metric-box">
                <div class="metric-label">Buffer Pool Size</div>
                <div class="metric-value">{format_bytes(metrics['buffer_pool_size'])}</div>
            </div>
            '''}
        </div>

        <h2>Search Statistics</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                {"" if 'adaptive_hash_searches' not in metrics else f'''
                <tr>
                    <td>Total AHI Searches</td>
                    <td>{format_number(metrics['adaptive_hash_searches'])}</td>
                </tr>
                '''}
                {"" if 'adaptive_hash_searches_btree' not in metrics else f'''
                <tr>
                    <td>B-tree Searches</td>
                    <td>{format_number(metrics['adaptive_hash_searches_btree'])}</td>
                </tr>
                '''}
                {"" if 'ahi_hit_rate' not in metrics else f'''
                <tr>
                    <td>Hit Rate</td>
                    <td>{metrics['ahi_hit_rate']:.2f}%</td>
                </tr>
                '''}
            </tbody>
        </table>

        <h2>Operations</h2>
        <table>
            <thead>
                <tr>
                    <th>Operation</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                {"" if 'adaptive_hash_pages_added' not in metrics else f'''
                <tr>
                    <td>Pages Added</td>
                    <td>{format_number(metrics['adaptive_hash_pages_added'])}</td>
                </tr>
                '''}
                {"" if 'adaptive_hash_pages_removed' not in metrics else f'''
                <tr>
                    <td>Pages Removed</td>
                    <td>{format_number(metrics['adaptive_hash_pages_removed'])}</td>
                </tr>
                '''}
                {"" if 'adaptive_hash_rows_added' not in metrics else f'''
                <tr>
                    <td>Rows Added</td>
                    <td>{format_number(metrics['adaptive_hash_rows_added'])}</td>
                </tr>
                '''}
                {"" if 'adaptive_hash_rows_removed' not in metrics else f'''
                <tr>
                    <td>Rows Removed</td>
                    <td>{format_number(metrics['adaptive_hash_rows_removed'])}</td>
                </tr>
                '''}
                {"" if 'adaptive_hash_rows_updated' not in metrics else f'''
                <tr>
                    <td>Rows Updated</td>
                    <td>{format_number(metrics['adaptive_hash_rows_updated'])}</td>
                </tr>
                '''}
                {"" if 'adaptive_hash_rows_deleted_no_hash_entry' not in metrics else f'''
                <tr>
                    <td>Rows Deleted (no hash entry)</td>
                    <td>{format_number(metrics['adaptive_hash_rows_deleted_no_hash_entry'])}</td>
                </tr>
                '''}
            </tbody>
        </table>

        <div class="recommendation">
            <h3>Recommendations</h3>
            {"<p><strong>Excellent performance!</strong> The Adaptive Hash Index is working very well for your workload. Keep it enabled.</p>" if hit_rate >= 80 else ""}
            {"<p><strong>Good performance.</strong> The Adaptive Hash Index is providing benefits. Monitor over time to ensure continued effectiveness.</p>" if 60 <= hit_rate < 80 else ""}
            {"<p><strong>Moderate performance.</strong> The AHI is providing some benefit but may not be optimal. Monitor your workload patterns and consider testing with AHI disabled.</p>" if 40 <= hit_rate < 60 else ""}
            {"<p><strong>Low effectiveness.</strong> The Adaptive Hash Index is not providing significant benefits for your workload. Consider disabling it with: <code>SET GLOBAL innodb_adaptive_hash_index = OFF;</code></p>" if hit_rate < 40 else ""}
            <p>Note: AHI is most beneficial for read-heavy workloads with repeated access to the same index pages. Write-heavy workloads may see less benefit.</p>
        </div>

        <div class="timestamp">Report generated: {timestamp}</div>
    </div>
</body>
</html>
"""

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"\nHTML report generated: {output_file}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Monitor MySQL InnoDB Adaptive Hash Index usage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single snapshot
  python monitor_adaptive_hash.py

  # Monitor continuously every 5 seconds
  python monitor_adaptive_hash.py --interval 5

  # Monitor for 60 seconds with 5-second intervals
  python monitor_adaptive_hash.py --interval 5 --duration 60

  # Generate HTML report
  python monitor_adaptive_hash.py --output-html ahi_report.html
        """
    )

    parser.add_argument(
        '--interval',
        type=int,
        help='Monitoring interval in seconds (omit for single snapshot)'
    )

    parser.add_argument(
        '--duration',
        type=int,
        help='Total monitoring duration in seconds (only with --interval)'
    )

    parser.add_argument(
        '--output-html',
        type=str,
        help='Generate HTML report to specified file'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.duration and not args.interval:
        parser.error("--duration requires --interval to be specified")

    # Get database configuration
    config = get_db_config()

    if not config.get('password'):
        print("Warning: MYSQL_PASSWORD environment variable not set")

    try:
        # Connect to database
        print(f"Connecting to MySQL at {config['host']}:{config['port']}...")
        connection = mysql.connector.connect(**config)

        if connection.is_connected():
            db_info = connection.server_info
            print(f"Connected to MySQL Server version {db_info}")

            cursor = connection.cursor()

            # Enable metrics
            enable_ahi_metrics(cursor)

            # Get current status
            metrics = get_ahi_status(cursor)
            memory_info = get_ahi_memory_info(cursor)

            # Check if monitoring is requested
            if args.interval:
                monitor_ahi(connection, args.interval, args.duration)
            else:
                # Single snapshot
                if not check_ahi_enabled(cursor):
                    print("\nWARNING: Adaptive Hash Index is currently DISABLED!")
                    print("To enable it, set: SET GLOBAL innodb_adaptive_hash_index = ON;")
                    print("\nShowing current status anyway...\n")

                print_ahi_status(metrics, memory_info)

            # Generate HTML report if requested
            if args.output_html:
                # Get fresh metrics for report
                metrics = get_ahi_status(cursor)
                memory_info = get_ahi_memory_info(cursor)
                generate_html_report(metrics, memory_info, args.output_html)

            cursor.close()

    except Error as e:
        print(f"Error connecting to MySQL: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("\nMySQL connection closed")


if __name__ == "__main__":
    main()
