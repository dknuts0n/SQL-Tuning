# SQL-Tuning

A collection of tools and scripts for MySQL database performance tuning and optimization.

## Tools

### 1. Find Unused Indexes

`find_unused_indexes.py` - Identifies indexes that are not being used by queries.

Unused indexes waste storage space and slow down INSERT, UPDATE, and DELETE operations without providing any query performance benefits.

#### Prerequisites

1. Create and activate a Python virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (bash/zsh)
source venv/bin/activate

# Or use the helper script
source activate_venv.sh
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

#### Configuration

Set up your database credentials using environment variables:

```bash
export MYSQL_HOST=localhost
export MYSQL_PORT=3306
export MYSQL_USER=your_user
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database  # Optional: leave empty to scan all databases
```

Or copy `.env.example` to `.env` and update with your credentials.

#### Quick Start with Runner Script

The easiest way to run the tool is using the `run.sh` script, which automatically:
- Creates and activates the Python virtual environment
- Installs dependencies if needed
- Loads your `.env` configuration
- Validates database credentials
- Runs the analysis

```bash
# First time setup
cp .env.example .env
# Edit .env with your database credentials

# Run the analysis
./run.sh

# Or with options
./run.sh --output-html report.html
./run.sh --output-csv data.csv
```

#### Usage

**Detailed Report (Default)** - Comprehensive analysis with statistics:

```bash
# Using runner script (recommended)
./run.sh

# Or directly with Python
python find_unused_indexes.py
```

**Simple Report** - Quick list of unused indexes only:

```bash
# Using runner script
DETAILED_REPORT=false ./run.sh

# Or directly with Python
export DETAILED_REPORT=false
python find_unused_indexes.py
```

The detailed report includes:
- Summary statistics (total indexes, unused count, foreign keys, redundant indexes)
- Database and index size analysis
- Unused indexes with foreign key indicators
- Potentially redundant/duplicate indexes
- Most frequently accessed indexes (top 10)
- Prioritized recommendations
- Safe-to-drop index suggestions with SQL statements

#### Export Reports

**Generate HTML Report** - Beautiful, styled report for sharing:

```bash
./run.sh --output-html index_report.html
```

**Generate CSV Report** - Raw data for spreadsheet analysis:

```bash
./run.sh --output-csv index_report.csv
```

**Generate Both** - HTML for viewing + CSV for analysis:

```bash
./run.sh --output-html report.html --output-csv report.csv
```

**Via Environment Variables:**

```bash
# Add to .env file or export
export OUTPUT_HTML=report.html
export OUTPUT_CSV=report.csv
./run.sh
```

The HTML report includes:
- Professional styling with color-coded statistics
- Interactive tables with hover effects
- Categorized sections (unused, redundant, most active)
- Ready-to-execute SQL statements
- Perfect for sharing with team members or management

The CSV report includes:
- All unused indexes with metadata
- Redundant index pairs
- Complete index statistics
- Ideal for importing into Excel, Google Sheets, or data analysis tools

#### Important Notes

- The script uses MySQL's `performance_schema` which must be enabled
- Statistics accumulate over time, so run this after the database has been under normal load
- Always verify with your development team before dropping indexes
- Some indexes may be used infrequently but are critical for specific operations

#### Example Output

**Detailed Report:**

```
====================================================================================================
DETAILED INDEX ANALYSIS REPORT
====================================================================================================

----------------------------------------------------------------------------------------------------
1. SUMMARY STATISTICS
----------------------------------------------------------------------------------------------------
Total indexes analyzed:          45
Unused indexes found:            13 (28.9%)
Foreign key indexes:             8
Potentially redundant indexes:   2

Total database size:             245.67 MB
Total index size:                89.34 MB (36.4% of total)

----------------------------------------------------------------------------------------------------
2. UNUSED INDEXES (NEVER ACCESSED)
----------------------------------------------------------------------------------------------------

Table                                    Index                               Columns                        Type     FK  Card
----------------------------------------------------------------------------------------------------------------------------------
mydb.users                               idx_last_login                      last_login                     BTREE    NO  12,450
  └─ Table size: 45.23 MB (data: 32.10 MB, indexes: 13.13 MB)
mydb.orders                              idx_created_date                    created_date                   BTREE    NO  8,932
  └─ Table size: 123.45 MB (data: 98.12 MB, indexes: 25.33 MB)
mydb.products                            idx_legacy                          old_column                     BTREE    YES 0
  └─ Table size: 12.34 MB (data: 8.90 MB, indexes: 3.44 MB)

Total unused indexes: 3
⚠️  Warning: 1 unused index(es) are associated with foreign keys

----------------------------------------------------------------------------------------------------
3. POTENTIALLY REDUNDANT INDEXES
----------------------------------------------------------------------------------------------------

These indexes may be redundant because one is a prefix of another:

Table                                    Redundant Index                     Covered By
--------------------------------------------------------------------------------------------------------------
mydb.orders                              idx_user_id                         idx_user_created
  ├─ Redundant: user_id
  └─ Covers it: user_id,created_at

Total redundant pairs: 1

----------------------------------------------------------------------------------------------------
4. MOST FREQUENTLY ACCESSED INDEXES (Top 10)
----------------------------------------------------------------------------------------------------

Table                                    Index                                      Reads      Writes       Total
--------------------------------------------------------------------------------------------------------------
mydb.users                               PRIMARY                                1,234,567      45,678   1,280,245
mydb.orders                              idx_user_created                         876,543      23,456     900,000

----------------------------------------------------------------------------------------------------
5. RECOMMENDATIONS
----------------------------------------------------------------------------------------------------

✓ SAFE TO CONSIDER DROPPING:
  - 2 unused non-FK indexes can likely be dropped
    • mydb.users.idx_last_login
    • mydb.orders.idx_created_date

⚠️  REVIEW CAREFULLY:
  - 1 unused indexes are associated with foreign keys
    These may be required for constraint enforcement
  - 1 potentially redundant indexes detected
    Verify query plans before dropping

----------------------------------------------------------------------------------------------------
6. EXAMPLE DROP STATEMENTS
----------------------------------------------------------------------------------------------------

-- Unused, non-FK indexes (safer to drop):
ALTER TABLE mydb.users DROP INDEX idx_last_login;
ALTER TABLE mydb.orders DROP INDEX idx_created_date;

====================================================================================================
END OF REPORT
====================================================================================================
```

---

### 2. Adaptive Hash Index Monitor

`monitor_adaptive_hash.py` - Monitors MySQL InnoDB Adaptive Hash Index (AHI) performance and effectiveness.

The Adaptive Hash Index is an InnoDB optimization that automatically builds hash indexes for frequently accessed index pages. This tool helps you determine if AHI is beneficial for your workload.

#### Quick Start with Runner Script

```bash
# Single snapshot of AHI status
./run_ahi_monitor.sh

# Monitor continuously every 5 seconds
./run_ahi_monitor.sh --interval 5

# Monitor for 60 seconds with updates every 10 seconds
./run_ahi_monitor.sh --interval 10 --duration 60

# Generate HTML report
./run_ahi_monitor.sh --output-html ahi_report.html

# Monitor and generate report
./run_ahi_monitor.sh --interval 5 --duration 60 --output-html ahi_report.html
```

#### Usage Options

**Single Snapshot** - Get current AHI status:
```bash
./run_ahi_monitor.sh
```

**Continuous Monitoring** - Track AHI performance over time:
```bash
# Monitor every 5 seconds indefinitely (Ctrl+C to stop)
./run_ahi_monitor.sh --interval 5

# Monitor for specific duration
./run_ahi_monitor.sh --interval 5 --duration 60
```

**Generate Reports**:
```bash
# HTML report with visualizations
./run_ahi_monitor.sh --output-html ahi_report.html

# Combined monitoring and reporting
./run_ahi_monitor.sh --interval 10 --duration 120 --output-html ahi_report.html
```

#### What It Monitors

The tool tracks the following AHI metrics:

- **Configuration**: AHI enabled status, partition count, buffer pool size
- **Hit Rate**: Percentage of searches satisfied by AHI vs B-tree lookups
- **Search Statistics**: Total AHI searches and B-tree searches
- **Memory Usage**: Hash table size and buffer allocation
- **Page Operations**: Pages added to and removed from AHI
- **Row Operations**: Row-level AHI activity (additions, updates, removals)

#### Performance Interpretation

The tool automatically interprets AHI effectiveness:

- **≥80% hit rate**: Excellent - AHI is highly effective for your workload
- **60-79% hit rate**: Good - AHI is providing measurable benefits
- **40-59% hit rate**: Moderate - AHI may provide some benefit
- **<40% hit rate**: Low - Consider disabling AHI for your workload

#### When to Use AHI

**Enable AHI when:**
- You have a read-heavy workload
- Queries repeatedly access the same index pages
- You see high buffer pool read activity
- Hit rate is consistently above 60%

**Consider disabling AHI when:**
- You have a write-heavy workload
- Access patterns are highly random
- Hit rate is consistently below 40%
- You need to reduce memory overhead

#### Example Output

```
==============================================================================
Adaptive Hash Index Status - 2025-01-15 10:30:45
==============================================================================

Configuration:
  AHI Enabled: True
  AHI Partitions: 8
  Buffer Pool Size: 8.00 GB

Memory Usage:
  Hash Table Size: 276,671
  Hash Buffers: 2,208

Search Statistics:
  Total AHI Searches: 45,892,341
  B-tree Searches: 8,234,567
  AHI Hit Rate: 82.05%
    Status: Excellent - AHI is highly effective

Page Operations:
  Pages Added: 156,789
  Pages Removed: 12,345

Row Operations:
  Rows Added: 2,345,678
  Rows Removed: 234,567
  Rows Updated: 456,789
  Rows Deleted (no hash entry): 12,345
```

#### Important Notes

- AHI metrics are cumulative since server start
- The tool automatically enables InnoDB AHI metrics if not already active
- Monitor over a representative workload period for accurate assessment
- AHI effectiveness varies significantly based on access patterns
- Changes to AHI settings require a server restart in some MySQL versions