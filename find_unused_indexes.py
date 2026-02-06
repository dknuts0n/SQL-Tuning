#!/usr/bin/env python3
"""
Script to identify unused indexes in a MySQL database.

This script connects to MySQL and queries the performance_schema to find
indexes that have never been used. Unused indexes consume space and slow
down INSERT/UPDATE/DELETE operations without providing query benefits.

Requirements:
    pip install mysql-connector-python

Usage:
    python find_unused_indexes.py
    python find_unused_indexes.py --output-html report.html
    python find_unused_indexes.py --output-csv report.csv
    python find_unused_indexes.py --output-html report.html --output-csv report.csv

Configuration:
    Set database credentials via environment variables:
    - MYSQL_HOST (default: localhost)
    - MYSQL_PORT (default: 3306)
    - MYSQL_USER (default: root)
    - MYSQL_PASSWORD
    - MYSQL_DATABASE
    - OUTPUT_HTML (optional: path to HTML output file)
    - OUTPUT_CSV (optional: path to CSV output file)
"""

import os
import sys
import argparse
import mysql.connector
from mysql.connector import Error
from typing import List, Dict

# Import report generators
try:
    from report_generator import generate_html_report, generate_csv_report
except ImportError:
    # If report_generator is not available, these will be None
    generate_html_report = None
    generate_csv_report = None


def get_db_config() -> Dict[str, str]:
    """Get database configuration from environment variables."""
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', ''),
    }


def connect_to_database(config: Dict[str, str]):
    """Establish connection to MySQL database."""
    try:
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT VERSION()")
            db_info = cursor.fetchone()[0]
            cursor.close()
            print(f"Connected to MySQL Server version {db_info}")
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        sys.exit(1)


def find_unused_indexes(connection) -> List[tuple]:
    """
    Query performance_schema to find unused indexes.

    Returns indexes where:
    - COUNT_STAR = 0 (never used for reads)
    - Not a PRIMARY key
    - Exclude system databases
    """
    query = """
        SELECT
            t.OBJECT_SCHEMA AS database_name,
            t.OBJECT_NAME AS table_name,
            t.INDEX_NAME AS index_name,
            GROUP_CONCAT(DISTINCT s.COLUMN_NAME ORDER BY s.SEQ_IN_INDEX) AS indexed_columns,
            MAX(s.INDEX_TYPE) AS INDEX_TYPE,
            MAX(s.CARDINALITY) AS cardinality
        FROM performance_schema.table_io_waits_summary_by_index_usage t
        LEFT JOIN information_schema.STATISTICS s
            ON t.OBJECT_SCHEMA = s.TABLE_SCHEMA
            AND t.OBJECT_NAME = s.TABLE_NAME
            AND t.INDEX_NAME = s.INDEX_NAME
        WHERE t.INDEX_NAME IS NOT NULL
            AND t.COUNT_STAR = 0
            AND t.INDEX_NAME != 'PRIMARY'
            AND t.OBJECT_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
        GROUP BY t.OBJECT_SCHEMA, t.OBJECT_NAME, t.INDEX_NAME
        ORDER BY t.OBJECT_SCHEMA, t.OBJECT_NAME, t.INDEX_NAME;
    """

    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results


def get_table_sizes(connection, database: str = None) -> Dict[str, Dict[str, float]]:
    """
    Get table sizes for context.
    Returns dict: {schema: {table: size_mb}}
    """
    database_filter = f"AND table_schema = '{database}'" if database else ""

    query = f"""
        SELECT
            table_schema,
            table_name,
            ROUND((data_length + index_length) / 1024 / 1024, 2) AS total_size_mb,
            ROUND(data_length / 1024 / 1024, 2) AS data_size_mb,
            ROUND(index_length / 1024 / 1024, 2) AS index_size_mb
        FROM information_schema.TABLES
        WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
            {database_filter}
        ORDER BY (data_length + index_length) DESC;
    """

    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    sizes = {}
    for schema, table, total_mb, data_mb, index_mb in results:
        if schema not in sizes:
            sizes[schema] = {}
        sizes[schema][table] = {
            'total_mb': float(total_mb) if total_mb is not None else 0.0,
            'data_mb': float(data_mb) if data_mb is not None else 0.0,
            'index_mb': float(index_mb) if index_mb is not None else 0.0
        }
    return sizes


def get_foreign_keys(connection, database: str = None) -> Dict[str, set]:
    """
    Get foreign key constraints and their indexes.
    Returns dict: {(schema, table, index_name): constraint_name}
    """
    database_filter = f"AND kcu.CONSTRAINT_SCHEMA = '{database}'" if database else ""

    query = f"""
        SELECT DISTINCT
            kcu.CONSTRAINT_SCHEMA,
            kcu.TABLE_NAME,
            kcu.CONSTRAINT_NAME,
            s.INDEX_NAME
        FROM information_schema.KEY_COLUMN_USAGE kcu
        JOIN information_schema.TABLE_CONSTRAINTS tc
            ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
            AND kcu.CONSTRAINT_SCHEMA = tc.CONSTRAINT_SCHEMA
        LEFT JOIN information_schema.STATISTICS s
            ON kcu.TABLE_SCHEMA = s.TABLE_SCHEMA
            AND kcu.TABLE_NAME = s.TABLE_NAME
            AND kcu.COLUMN_NAME = s.COLUMN_NAME
        WHERE tc.CONSTRAINT_TYPE = 'FOREIGN KEY'
            AND kcu.CONSTRAINT_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
            {database_filter}
        ORDER BY kcu.CONSTRAINT_SCHEMA, kcu.TABLE_NAME;
    """

    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    fk_indexes = {}
    for schema, table, constraint, index_name in results:
        if index_name:
            key = (schema, table, index_name)
            fk_indexes[key] = constraint
    return fk_indexes


def get_detailed_index_info(connection, database: str = None) -> List[dict]:
    """
    Get comprehensive index information including size estimates.
    """
    database_filter = f"AND t.OBJECT_SCHEMA = '{database}'" if database else ""

    query = f"""
        SELECT
            t.OBJECT_SCHEMA,
            t.OBJECT_NAME,
            t.INDEX_NAME,
            GROUP_CONCAT(DISTINCT s.COLUMN_NAME ORDER BY s.SEQ_IN_INDEX) AS indexed_columns,
            MAX(s.INDEX_TYPE) AS index_type,
            MAX(s.CARDINALITY) AS cardinality,
            COUNT(DISTINCT s.COLUMN_NAME) AS column_count,
            MAX(s.NON_UNIQUE) AS non_unique,
            t.COUNT_STAR AS total_accesses,
            t.COUNT_READ AS read_accesses,
            t.COUNT_WRITE AS write_accesses,
            t.COUNT_FETCH AS rows_fetched,
            t.COUNT_INSERT AS inserts,
            t.COUNT_UPDATE AS updates,
            t.COUNT_DELETE AS deletes
        FROM performance_schema.table_io_waits_summary_by_index_usage t
        LEFT JOIN information_schema.STATISTICS s
            ON t.OBJECT_SCHEMA = s.TABLE_SCHEMA
            AND t.OBJECT_NAME = s.TABLE_NAME
            AND t.INDEX_NAME = s.INDEX_NAME
        WHERE t.INDEX_NAME IS NOT NULL
            AND t.OBJECT_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
            {database_filter}
        GROUP BY t.OBJECT_SCHEMA, t.OBJECT_NAME, t.INDEX_NAME,
                 t.COUNT_STAR, t.COUNT_READ, t.COUNT_WRITE, t.COUNT_FETCH,
                 t.COUNT_INSERT, t.COUNT_UPDATE, t.COUNT_DELETE
        ORDER BY t.COUNT_STAR ASC, t.OBJECT_SCHEMA, t.OBJECT_NAME;
    """

    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()

    indexes = []
    for row in results:
        indexes.append({
            'schema': row[0],
            'table': row[1],
            'index_name': row[2],
            'columns': row[3],
            'type': row[4],
            'cardinality': row[5] or 0,
            'column_count': row[6],
            'non_unique': row[7],
            'total_accesses': row[8],
            'read_accesses': row[9],
            'write_accesses': row[10],
            'rows_fetched': row[11],
            'inserts': row[12],
            'updates': row[13],
            'deletes': row[14]
        })
    return indexes


def find_redundant_indexes(indexes: List[dict]) -> List[tuple]:
    """
    Find potentially redundant indexes (indexes that are prefixes of other indexes).
    Returns list of (redundant_index, covered_by_index) tuples.
    """
    redundant = []

    # Group by table
    by_table = {}
    for idx in indexes:
        key = (idx['schema'], idx['table'])
        if key not in by_table:
            by_table[key] = []
        by_table[key].append(idx)

    # Check each table's indexes
    for (schema, table), table_indexes in by_table.items():
        for i, idx1 in enumerate(table_indexes):
            if not idx1['columns']:
                continue
            cols1 = [c.strip() for c in idx1['columns'].split(',')]

            for idx2 in table_indexes[i+1:]:
                if not idx2['columns']:
                    continue
                cols2 = [c.strip() for c in idx2['columns'].split(',')]

                # Check if idx1 is a prefix of idx2
                if len(cols1) < len(cols2) and cols2[:len(cols1)] == cols1:
                    redundant.append((idx1, idx2))
                # Check if idx2 is a prefix of idx1
                elif len(cols2) < len(cols1) and cols1[:len(cols2)] == cols2:
                    redundant.append((idx2, idx1))

    return redundant


def get_index_stats(connection, database: str = None) -> List[tuple]:
    """
    Get overall index statistics including size and usage.
    """
    database_filter = f"AND t.OBJECT_SCHEMA = '{database}'" if database else ""

    query = f"""
        SELECT
            t.OBJECT_SCHEMA AS database_name,
            t.OBJECT_NAME AS table_name,
            t.INDEX_NAME AS index_name,
            t.COUNT_STAR AS total_accesses,
            t.COUNT_READ AS read_accesses,
            t.COUNT_WRITE AS write_accesses,
            t.COUNT_FETCH AS rows_fetched
        FROM performance_schema.table_io_waits_summary_by_index_usage t
        WHERE t.INDEX_NAME IS NOT NULL
            AND t.OBJECT_SCHEMA NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
            {database_filter}
        ORDER BY t.COUNT_STAR ASC, t.OBJECT_SCHEMA, t.OBJECT_NAME;
    """

    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    return results


def print_unused_indexes(unused_indexes: List[tuple]):
    """Display unused indexes in a formatted table."""
    if not unused_indexes:
        print("\nNo unused indexes found!")
        print("Note: The performance_schema may need time to collect statistics.")
        print("Consider running this after the database has been under normal load.")
        return

    print(f"\nFound {len(unused_indexes)} unused index(es):\n")
    print(f"{'Database':<20} {'Table':<30} {'Index Name':<30} {'Columns':<40} {'Type':<10}")
    print("-" * 140)

    for row in unused_indexes:
        db_name, table_name, index_name, columns, index_type, cardinality = row
        columns = columns if columns else 'N/A'
        index_type = index_type if index_type else 'N/A'
        print(f"{db_name:<20} {table_name:<30} {index_name:<30} {columns:<40} {index_type:<10}")

    print("\nRecommendation:")
    print("Review these indexes and consider dropping them if they are truly not needed.")
    print("Before dropping, verify with application developers and review query patterns.")
    print("\nExample DROP statement:")
    if unused_indexes:
        first = unused_indexes[0]
        print(f"  ALTER TABLE {first[0]}.{first[1]} DROP INDEX {first[2]};")


def generate_detailed_report(connection, config: Dict[str, str]):
    """
    Generate a comprehensive detailed report with statistics.
    """
    database = config.get('database')

    print("\n" + "=" * 100)
    print("DETAILED INDEX ANALYSIS REPORT")
    print("=" * 100)

    # Get all comprehensive data
    print("\nGathering data...")
    all_indexes = get_detailed_index_info(connection, database)
    table_sizes = get_table_sizes(connection, database)
    fk_indexes = get_foreign_keys(connection, database)
    redundant = find_redundant_indexes(all_indexes)

    # Filter unused indexes
    unused = [idx for idx in all_indexes if idx['total_accesses'] == 0 and idx['index_name'] != 'PRIMARY']

    # Section 1: Summary Statistics
    print("\n" + "-" * 100)
    print("1. SUMMARY STATISTICS")
    print("-" * 100)

    total_indexes = len(all_indexes)
    total_unused = len(unused)
    total_fk = len(fk_indexes)
    total_redundant = len(redundant)

    print(f"Total indexes analyzed:          {total_indexes}")
    print(f"Unused indexes found:            {total_unused} ({100*total_unused/total_indexes if total_indexes > 0 else 0:.1f}%)")
    print(f"Foreign key indexes:             {total_fk}")
    print(f"Potentially redundant indexes:   {total_redundant}")

    # Calculate total table and index sizes
    total_table_mb = sum(sizes['total_mb'] for schema_tables in table_sizes.values() for sizes in schema_tables.values())
    total_index_mb = sum(sizes['index_mb'] for schema_tables in table_sizes.values() for sizes in schema_tables.values())

    print(f"\nTotal database size:             {total_table_mb:.2f} MB")
    print(f"Total index size:                {total_index_mb:.2f} MB ({100*total_index_mb/total_table_mb if total_table_mb > 0 else 0:.1f}% of total)")

    # Section 2: Unused Indexes Detail
    print("\n" + "-" * 100)
    print("2. UNUSED INDEXES (NEVER ACCESSED)")
    print("-" * 100)

    if not unused:
        print("\nNo unused indexes found!")
    else:
        print(f"\n{'Table':<40} {'Index':<35} {'Columns':<30} {'Type':<8} {'FK':<3} {'Card':<10}")
        print("-" * 130)

        unused_sorted = sorted(unused, key=lambda x: (x['schema'], x['table'], x['index_name']))
        for idx in unused_sorted:
            table_full = f"{idx['schema']}.{idx['table']}"
            columns = idx['columns'][:28] + '..' if idx['columns'] and len(idx['columns']) > 30 else (idx['columns'] or 'N/A')
            is_fk = 'YES' if (idx['schema'], idx['table'], idx['index_name']) in fk_indexes else 'NO'
            cardinality = f"{idx['cardinality']:,}" if idx['cardinality'] else 'N/A'

            print(f"{table_full:<40} {idx['index_name']:<35} {columns:<30} {idx['type'] or 'N/A':<8} {is_fk:<3} {cardinality:<10}")

            # Show table size context
            if idx['schema'] in table_sizes and idx['table'] in table_sizes[idx['schema']]:
                size_info = table_sizes[idx['schema']][idx['table']]
                print(f"  └─ Table size: {size_info['total_mb']:.2f} MB (data: {size_info['data_mb']:.2f} MB, indexes: {size_info['index_mb']:.2f} MB)")

        print(f"\nTotal unused indexes: {len(unused)}")

        # Count FK indexes in unused
        unused_fk_count = sum(1 for idx in unused if (idx['schema'], idx['table'], idx['index_name']) in fk_indexes)
        if unused_fk_count > 0:
            print(f"⚠️  Warning: {unused_fk_count} unused index(es) are associated with foreign keys")

    # Section 3: Redundant Indexes
    if redundant:
        print("\n" + "-" * 100)
        print("3. POTENTIALLY REDUNDANT INDEXES")
        print("-" * 100)
        print("\nThese indexes may be redundant because one is a prefix of another:")
        print(f"\n{'Table':<40} {'Redundant Index':<35} {'Covered By':<35}")
        print("-" * 110)

        for idx1, idx2 in redundant:
            table_full = f"{idx1['schema']}.{idx1['table']}"
            print(f"{table_full:<40} {idx1['index_name']:<35} {idx2['index_name']:<35}")
            print(f"  ├─ Redundant: {idx1['columns']}")
            print(f"  └─ Covers it: {idx2['columns']}")

        print(f"\nTotal redundant pairs: {len(redundant)}")
        print("Note: Review these carefully - the 'redundant' index may be kept for query performance reasons")

    # Section 4: Most Active Indexes
    print("\n" + "-" * 100)
    print("4. MOST FREQUENTLY ACCESSED INDEXES (Top 10)")
    print("-" * 100)

    active = [idx for idx in all_indexes if idx['total_accesses'] > 0]
    active_sorted = sorted(active, key=lambda x: x['total_accesses'], reverse=True)[:10]

    if active_sorted:
        print(f"\n{'Table':<40} {'Index':<35} {'Reads':<12} {'Writes':<12} {'Total':<12}")
        print("-" * 110)

        for idx in active_sorted:
            table_full = f"{idx['schema']}.{idx['table']}"
            print(f"{table_full:<40} {idx['index_name']:<35} {idx['read_accesses']:>11,} {idx['write_accesses']:>11,} {idx['total_accesses']:>11,}")

    # Section 5: Recommendations
    print("\n" + "-" * 100)
    print("5. RECOMMENDATIONS")
    print("-" * 100)

    print("\n✓ SAFE TO CONSIDER DROPPING:")
    safe_unused = [idx for idx in unused if (idx['schema'], idx['table'], idx['index_name']) not in fk_indexes]
    if safe_unused:
        print(f"  - {len(safe_unused)} unused non-FK indexes can likely be dropped")
        for idx in safe_unused[:5]:  # Show first 5
            print(f"    • {idx['schema']}.{idx['table']}.{idx['index_name']}")
        if len(safe_unused) > 5:
            print(f"    ... and {len(safe_unused) - 5} more")
    else:
        print("  - No obvious candidates found")

    print("\n⚠️  REVIEW CAREFULLY:")
    if unused_fk_count > 0:
        print(f"  - {unused_fk_count} unused indexes are associated with foreign keys")
        print("    These may be required for constraint enforcement")

    if redundant:
        print(f"  - {len(redundant)} potentially redundant indexes detected")
        print("    Verify query plans before dropping")

    # Generate SQL statements
    print("\n" + "-" * 100)
    print("6. EXAMPLE DROP STATEMENTS")
    print("-" * 100)

    if safe_unused:
        print("\n-- Unused, non-FK indexes (safer to drop):")
        for idx in safe_unused[:5]:
            print(f"ALTER TABLE {idx['schema']}.{idx['table']} DROP INDEX {idx['index_name']};")

    print("\n" + "=" * 100)
    print("END OF REPORT")
    print("=" * 100)


def main():
    """Main execution function."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Analyze MySQL database indexes and identify unused/redundant indexes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Console output only
  %(prog)s --output-html report.html         # Generate HTML report
  %(prog)s --output-csv data.csv             # Generate CSV report
  %(prog)s --output-html report.html --output-csv data.csv  # Both formats
  %(prog)s --simple                          # Simple console output (no detailed report)

Environment Variables:
  MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
        """
    )
    parser.add_argument('--output-html', dest='html_file', metavar='FILE',
                        help='Generate HTML report to FILE')
    parser.add_argument('--output-csv', dest='csv_file', metavar='FILE',
                        help='Generate CSV report to FILE')
    parser.add_argument('--simple', action='store_true',
                        help='Simple console output (no detailed report)')

    args = parser.parse_args()

    # Check for environment variable overrides
    if not args.html_file:
        args.html_file = os.getenv('OUTPUT_HTML')
    if not args.csv_file:
        args.csv_file = os.getenv('OUTPUT_CSV')

    print("MySQL Unused Index Finder")
    print("=" * 50)

    # Get database configuration
    config = get_db_config()

    if not config['database']:
        print("\nWarning: No specific database specified (MYSQL_DATABASE not set).")
        print("Will analyze all user databases.\n")

    # Connect to database
    connection = connect_to_database(config)

    try:
        # Check if detailed report is requested
        detailed_report = not args.simple and os.getenv('DETAILED_REPORT', 'true').lower() == 'true'

        # Check if file output is requested
        generate_files = args.html_file or args.csv_file

        if detailed_report or generate_files:
            # Gather all data for detailed report and/or file generation
            print("\nGathering comprehensive index data...")
            all_indexes = get_detailed_index_info(connection, config.get('database'))
            table_sizes = get_table_sizes(connection, config.get('database'))
            fk_indexes = get_foreign_keys(connection, config.get('database'))
            redundant = find_redundant_indexes(all_indexes)
            unused = [idx for idx in all_indexes if idx['total_accesses'] == 0 and idx['index_name'] != 'PRIMARY']

            # Display console report if not simple
            if detailed_report:
                generate_detailed_report(connection, config)

            # Generate HTML report if requested
            if args.html_file:
                if generate_html_report is None:
                    print("\n⚠️  Warning: report_generator module not found. Cannot generate HTML report.")
                else:
                    print(f"\nGenerating HTML report: {args.html_file}")
                    output_path = generate_html_report(
                        config, all_indexes, unused, table_sizes,
                        fk_indexes, redundant, args.html_file
                    )
                    print(f"✓ HTML report saved to: {output_path}")

            # Generate CSV report if requested
            if args.csv_file:
                if generate_csv_report is None:
                    print("\n⚠️  Warning: report_generator module not found. Cannot generate CSV report.")
                else:
                    print(f"\nGenerating CSV report: {args.csv_file}")
                    output_path = generate_csv_report(
                        all_indexes, unused, table_sizes,
                        fk_indexes, redundant, args.csv_file
                    )
                    print(f"✓ CSV report saved to: {output_path}")

        else:
            # Simple report (original functionality)
            print("\nSearching for unused indexes...")
            unused_indexes = find_unused_indexes(connection)
            print_unused_indexes(unused_indexes)

            # Optional: Show all index statistics for context
            show_all = os.getenv('SHOW_ALL_STATS', 'false').lower() == 'true'
            if show_all:
                print("\n\nAll Index Statistics (sorted by usage):")
                print("=" * 140)
                all_stats = get_index_stats(connection, config.get('database'))
                print(f"{'Database':<20} {'Table':<30} {'Index':<30} {'Total':<12} {'Reads':<12} {'Writes':<12}")
                print("-" * 140)
                for row in all_stats[:50]:  # Show top 50
                    print(f"{row[0]:<20} {row[1]:<30} {row[2]:<30} {row[3]:<12} {row[4]:<12} {row[5]:<12}")

    except Error as e:
        print(f"Error querying database: {e}")
        sys.exit(1)

    finally:
        if connection.is_connected():
            connection.close()
            print("\n\nDatabase connection closed.")


if __name__ == "__main__":
    main()
