#!/usr/bin/env python3
"""
Report generation module for MySQL index analysis.
Supports HTML and CSV output formats.
"""

import csv
from datetime import datetime
from typing import List, Dict
import html


def generate_html_report(
    config: Dict,
    all_indexes: List[dict],
    unused: List[dict],
    table_sizes: Dict,
    fk_indexes: Dict,
    redundant: List[tuple],
    output_file: str
) -> str:
    """Generate an HTML report with styling."""

    total_indexes = len(all_indexes)
    total_unused = len(unused)
    total_fk = len(fk_indexes)
    total_redundant = len(redundant)

    # Calculate totals
    total_table_mb = sum(sizes['total_mb'] for schema_tables in table_sizes.values() for sizes in schema_tables.values())
    total_index_mb = sum(sizes['index_mb'] for schema_tables in table_sizes.values() for sizes in schema_tables.values())

    # Get active indexes
    active = [idx for idx in all_indexes if idx['total_accesses'] > 0]
    active_sorted = sorted(active, key=lambda x: x['total_accesses'], reverse=True)[:10]

    # Get safe to drop
    safe_unused = [idx for idx in unused if (idx['schema'], idx['table'], idx['index_name']) not in fk_indexes]
    unused_fk_count = total_unused - len(safe_unused)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MySQL Index Analysis Report - {config.get('database', 'All Databases')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        header {{
            border-bottom: 4px solid #2563eb;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            color: #1e40af;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .meta {{
            color: #64748b;
            font-size: 14px;
        }}
        h2 {{
            color: #1e40af;
            font-size: 24px;
            margin-top: 40px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}
        h3 {{
            color: #334155;
            font-size: 18px;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f8fafc;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #2563eb;
        }}
        .stat-card.warning {{
            border-left-color: #f59e0b;
        }}
        .stat-card.success {{
            border-left-color: #10b981;
        }}
        .stat-label {{
            font-size: 14px;
            color: #64748b;
            margin-bottom: 5px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: bold;
            color: #1e293b;
        }}
        .stat-sub {{
            font-size: 14px;
            color: #64748b;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        th {{
            background: #1e40af;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        tr:hover {{
            background: #f8fafc;
        }}
        .table-sub {{
            font-size: 12px;
            color: #64748b;
            padding-left: 30px;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .badge-yes {{
            background: #fee2e2;
            color: #991b1b;
        }}
        .badge-no {{
            background: #dcfce7;
            color: #166534;
        }}
        .alert {{
            padding: 15px;
            border-radius: 6px;
            margin: 15px 0;
        }}
        .alert-warning {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            color: #92400e;
        }}
        .alert-info {{
            background: #dbeafe;
            border-left: 4px solid #2563eb;
            color: #1e40af;
        }}
        .alert-success {{
            background: #d1fae5;
            border-left: 4px solid #10b981;
            color: #065f46;
        }}
        code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        pre code {{
            background: transparent;
            color: #e2e8f0;
        }}
        .number {{
            font-family: 'Courier New', monospace;
            text-align: right;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #64748b;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>MySQL Index Analysis Report</h1>
            <div class="meta">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
                Database: {html.escape(config.get('database', 'All Databases'))} |
                Host: {html.escape(config.get('host', 'localhost'))}
            </div>
        </header>

        <h2>1. Summary Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Indexes</div>
                <div class="stat-value">{total_indexes:,}</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">Unused Indexes</div>
                <div class="stat-value">{total_unused:,}</div>
                <div class="stat-sub">{100*total_unused/total_indexes if total_indexes > 0 else 0:.1f}% of total</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Foreign Key Indexes</div>
                <div class="stat-value">{total_fk:,}</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">Redundant Indexes</div>
                <div class="stat-value">{total_redundant:,}</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card success">
                <div class="stat-label">Total Database Size</div>
                <div class="stat-value">{total_table_mb:,.2f} MB</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Index Size</div>
                <div class="stat-value">{total_index_mb:,.2f} MB</div>
                <div class="stat-sub">{100*total_index_mb/total_table_mb if total_table_mb > 0 else 0:.1f}% of database</div>
            </div>
        </div>

        <h2>2. Unused Indexes (Never Accessed)</h2>
"""

    if not unused:
        html_content += '<div class="alert alert-success">✓ No unused indexes found!</div>\n'
    else:
        html_content += f"""
        <table>
            <thead>
                <tr>
                    <th>Table</th>
                    <th>Index Name</th>
                    <th>Columns</th>
                    <th>FK</th>
                    <th class="number">Cardinality</th>
                </tr>
            </thead>
            <tbody>
"""
        unused_sorted = sorted(unused, key=lambda x: (x['schema'], x['table'], x['index_name']))
        for idx in unused_sorted:
            table_full = f"{html.escape(idx['schema'])}.{html.escape(idx['table'])}"
            columns = html.escape(idx['columns'] or 'N/A')
            is_fk = (idx['schema'], idx['table'], idx['index_name']) in fk_indexes
            badge_class = 'badge-yes' if is_fk else 'badge-no'
            badge_text = 'YES' if is_fk else 'NO'
            cardinality = f"{idx['cardinality']:,}" if idx['cardinality'] else 'N/A'

            html_content += f"""
                <tr>
                    <td>{table_full}</td>
                    <td><code>{html.escape(idx['index_name'])}</code></td>
                    <td>{columns}</td>
                    <td><span class="badge {badge_class}">{badge_text}</span></td>
                    <td class="number">{cardinality}</td>
                </tr>
"""
            # Add size info
            if idx['schema'] in table_sizes and idx['table'] in table_sizes[idx['schema']]:
                size_info = table_sizes[idx['schema']][idx['table']]
                html_content += f"""
                <tr>
                    <td colspan="5" class="table-sub">
                        Table size: {size_info['total_mb']:.2f} MB
                        (data: {size_info['data_mb']:.2f} MB, indexes: {size_info['index_mb']:.2f} MB)
                    </td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
"""
        if unused_fk_count > 0:
            html_content += f'<div class="alert alert-warning">⚠️ Warning: {unused_fk_count} unused index(es) are associated with foreign keys</div>\n'

    # Redundant indexes
    if redundant:
        html_content += """
        <h2>3. Potentially Redundant Indexes</h2>
        <div class="alert alert-info">These indexes may be redundant because one is a prefix of another.</div>
        <table>
            <thead>
                <tr>
                    <th>Table</th>
                    <th>Redundant Index</th>
                    <th>Columns</th>
                    <th>Covered By</th>
                    <th>Columns</th>
                </tr>
            </thead>
            <tbody>
"""
        for idx1, idx2 in redundant:
            table_full = f"{html.escape(idx1['schema'])}.{html.escape(idx1['table'])}"
            html_content += f"""
                <tr>
                    <td>{table_full}</td>
                    <td><code>{html.escape(idx1['index_name'])}</code></td>
                    <td>{html.escape(idx1['columns'] or 'N/A')}</td>
                    <td><code>{html.escape(idx2['index_name'])}</code></td>
                    <td>{html.escape(idx2['columns'] or 'N/A')}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""

    # Most active indexes
    html_content += """
        <h2>4. Most Frequently Accessed Indexes (Top 10)</h2>
        <table>
            <thead>
                <tr>
                    <th>Table</th>
                    <th>Index Name</th>
                    <th class="number">Reads</th>
                    <th class="number">Writes</th>
                    <th class="number">Total Accesses</th>
                </tr>
            </thead>
            <tbody>
"""
    for idx in active_sorted:
        table_full = f"{html.escape(idx['schema'])}.{html.escape(idx['table'])}"
        html_content += f"""
                <tr>
                    <td>{table_full}</td>
                    <td><code>{html.escape(idx['index_name'])}</code></td>
                    <td class="number">{idx['read_accesses']:,}</td>
                    <td class="number">{idx['write_accesses']:,}</td>
                    <td class="number">{idx['total_accesses']:,}</td>
                </tr>
"""
    html_content += """
            </tbody>
        </table>
"""

    # Recommendations
    html_content += """
        <h2>5. Recommendations</h2>
"""
    if safe_unused:
        html_content += f"""
        <div class="alert alert-success">
            <strong>✓ SAFE TO CONSIDER DROPPING:</strong><br>
            {len(safe_unused)} unused non-FK index(es) can likely be dropped
        </div>
"""

    if unused_fk_count > 0 or redundant:
        html_content += '<div class="alert alert-warning"><strong>⚠️ REVIEW CAREFULLY:</strong><br>'
        if unused_fk_count > 0:
            html_content += f'{unused_fk_count} unused index(es) are associated with foreign keys<br>'
        if redundant:
            html_content += f'{len(redundant)} potentially redundant index(es) detected<br>'
        html_content += '</div>'

    # SQL statements
    if safe_unused:
        html_content += """
        <h2>6. Example DROP Statements</h2>
        <pre><code>-- Unused, non-FK indexes (safer to drop):
"""
        for idx in safe_unused[:10]:
            html_content += f"ALTER TABLE {html.escape(idx['schema'])}.{html.escape(idx['table'])} DROP INDEX {html.escape(idx['index_name'])};\n"
        html_content += """</code></pre>
"""

    html_content += """
        <footer>
            Generated by MySQL Index Analysis Tool
        </footer>
    </div>
</body>
</html>
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return output_file


def generate_csv_report(
    all_indexes: List[dict],
    unused: List[dict],
    table_sizes: Dict,
    fk_indexes: Dict,
    redundant: List[tuple],
    output_file: str
) -> str:
    """Generate a CSV report with all index data."""

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write unused indexes
        writer.writerow(['UNUSED INDEXES'])
        writer.writerow([
            'Schema', 'Table', 'Index Name', 'Columns', 'Type',
            'Is Foreign Key', 'Cardinality', 'Table Size (MB)',
            'Data Size (MB)', 'Index Size (MB)'
        ])

        unused_sorted = sorted(unused, key=lambda x: (x['schema'], x['table'], x['index_name']))
        for idx in unused_sorted:
            is_fk = 'YES' if (idx['schema'], idx['table'], idx['index_name']) in fk_indexes else 'NO'

            table_mb = data_mb = index_mb = 0
            if idx['schema'] in table_sizes and idx['table'] in table_sizes[idx['schema']]:
                size_info = table_sizes[idx['schema']][idx['table']]
                table_mb = size_info['total_mb']
                data_mb = size_info['data_mb']
                index_mb = size_info['index_mb']

            writer.writerow([
                idx['schema'],
                idx['table'],
                idx['index_name'],
                idx['columns'] or 'N/A',
                idx['type'] or 'N/A',
                is_fk,
                idx['cardinality'] or 0,
                f"{table_mb:.2f}",
                f"{data_mb:.2f}",
                f"{index_mb:.2f}"
            ])

        # Write redundant indexes
        writer.writerow([])
        writer.writerow(['REDUNDANT INDEXES'])
        writer.writerow([
            'Schema', 'Table', 'Redundant Index', 'Redundant Columns',
            'Covered By Index', 'Covered By Columns'
        ])

        for idx1, idx2 in redundant:
            writer.writerow([
                idx1['schema'],
                idx1['table'],
                idx1['index_name'],
                idx1['columns'] or 'N/A',
                idx2['index_name'],
                idx2['columns'] or 'N/A'
            ])

        # Write all index statistics
        writer.writerow([])
        writer.writerow(['ALL INDEX STATISTICS'])
        writer.writerow([
            'Schema', 'Table', 'Index Name', 'Columns', 'Type',
            'Non-Unique', 'Cardinality', 'Total Accesses', 'Read Accesses',
            'Write Accesses', 'Rows Fetched', 'Inserts', 'Updates', 'Deletes'
        ])

        for idx in sorted(all_indexes, key=lambda x: (x['schema'], x['table'], x['index_name'])):
            writer.writerow([
                idx['schema'],
                idx['table'],
                idx['index_name'],
                idx['columns'] or 'N/A',
                idx['type'] or 'N/A',
                idx['non_unique'],
                idx['cardinality'],
                idx['total_accesses'],
                idx['read_accesses'],
                idx['write_accesses'],
                idx['rows_fetched'],
                idx['inserts'],
                idx['updates'],
                idx['deletes']
            ])

    return output_file
