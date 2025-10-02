# Scripts

This directory contains utility scripts for the Excel -> PostgreSQL bulk import tool.

## gen_perf_dataset.py

Dataset generation script for performance testing (implements task T028).

### Purpose

Generates synthetic Excel files with parameterized rows/columns for performance testing. The generated files follow the exact format expected by the Excel reader:

- **Row 1**: Title row (optional, often ignored)
- **Row 2**: Header row with column names  
- **Row 3+**: Data rows

### Usage

```bash
# Generate default 50k rows, 40 columns (matches performance test targets)
python scripts/gen_perf_dataset.py dataset.xlsx

# Generate custom size dataset
python scripts/gen_perf_dataset.py large_dataset.xlsx --rows 100000 --cols 50

# Generate multi-sheet dataset
python scripts/gen_perf_dataset.py multi_sheet.xlsx --rows 25000 --cols 30 --sheets Customers Orders Products

# Dry run to see what would be generated
python scripts/gen_perf_dataset.py --dry-run test.xlsx --rows 1000 --cols 10

# Generate with custom parameters
python scripts/gen_perf_dataset.py custom.xlsx --rows 10000 --cols 20 --title "Custom Test Data" --seed 123
```

### Data Types Generated

The script generates realistic mixed data types:

- **String columns (30%)**: Names, categories, descriptions
- **Numeric columns (50%)**: IDs, amounts, quantities (integers and decimals)
- **Boolean columns (10%)**: Active flags, status indicators
- **Date columns (remaining)**: Creation dates, timestamps

### Integration with Performance Tests

This script is designed to work with the existing performance testing infrastructure:

1. **For T012 (throughput budget test)**: Generate 50k rows, 40 columns dataset
2. **For T013 (batch size experiments)**: Generate datasets with varying sizes
3. **For integration tests**: Generate smaller datasets for faster CI execution

### Examples for Performance Testing

```bash
# Generate standard performance test dataset (T012)
python scripts/gen_perf_dataset.py perf_50k.xlsx --rows 50000 --cols 40

# Generate smaller dataset for smoke tests
python scripts/gen_perf_dataset.py perf_smoke.xlsx --rows 5000 --cols 10

# Generate batch size experiment datasets
python scripts/gen_perf_dataset.py batch_500.xlsx --rows 25000 --cols 20
python scripts/gen_perf_dataset.py batch_1000.xlsx --rows 25000 --cols 20 --seed 1000
python scripts/gen_perf_dataset.py batch_2000.xlsx --rows 25000 --cols 20 --seed 2000
```

### File Size Estimates

The script provides size estimates and warnings for large datasets:

- **Small (1k rows, 10 cols)**: ~0.2 MB
- **Medium (10k rows, 20 cols)**: ~3.8 MB  
- **Large (50k rows, 40 cols)**: ~38 MB
- **Extra Large (100k rows, 50 cols)**: ~95 MB

Files larger than 100 MB will prompt for confirmation unless running in automation.

### Output Format

The generated Excel files are immediately compatible with:
- `src.excel.reader.read_excel_file()`
- `src.excel.reader.normalize_sheet()`
- All existing performance and integration tests

### Reproducibility

Using the same `--seed` parameter ensures reproducible datasets for consistent performance measurements across test runs.