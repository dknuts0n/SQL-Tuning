# SQL-Tuning

A collection of tools and scripts for MySQL database performance tuning and optimization.

## Tools

### Find Unused Indexes

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