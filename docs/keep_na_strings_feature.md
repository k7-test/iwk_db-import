# keep_na_strings Configuration Feature

## Overview
This feature allows users to prevent specific strings (like "NA") from being automatically converted to NaN (NULL) by pandas when reading Excel files.

## Problem Statement
By default, pandas treats certain strings as NaN values during Excel import, including:
- "NA"
- "N/A"
- "null"
- "NULL"
- "#N/A"
- And many others

However, in some cases, "NA" might be a meaningful value in the Excel data that should be preserved as a string in the database.

## Solution
Added a configuration option `keep_na_strings` that allows users to specify which strings should NOT be treated as NaN.

## Configuration

### YAML Configuration
Add the `keep_na_strings` array to your `import.yml` file:

```yaml
source_directory: ./data
keep_na_strings:
  - "NA"
  # Add more strings as needed
  # - "N/A"
sheet_mappings:
  # ... your sheet mappings
```

### Behavior
- **When `keep_na_strings` is specified**: The listed strings will be preserved as strings in the data
- **When `keep_na_strings` is NOT specified**: Default pandas behavior applies (all standard NA values are converted to NaN/NULL)

## Example

### Excel Data
```
| 商品コード | 商品名      | ステータス |
|----------|------------|----------|
| P001     | Product A  | NA       |
| P002     | NA         | ACTIVE   |
| P003     | Product C  | NA       |
```

### Without keep_na_strings (default)
```python
Row 1: {'商品コード': 'P001', '商品名': 'Product A', 'ステータス': None}
Row 2: {'商品コード': 'P002', '商品名': None, 'ステータス': 'ACTIVE'}
Row 3: {'商品コード': 'P003', '商品名': 'Product C', 'ステータス': None}
```

### With keep_na_strings: ["NA"]
```python
Row 1: {'商品コード': 'P001', '商品名': 'Product A', 'ステータス': 'NA'}
Row 2: {'商品コード': 'P002', '商品名': 'NA', 'ステータス': 'ACTIVE'}
Row 3: {'商品コード': 'P003', '商品名': 'Product C', 'ステータス': 'NA'}
```

## Implementation Details

### Modified Files
1. **config_schema.json**: Added `keep_na_strings` property
2. **src/config/loader.py**: Added `keep_na_strings` to ImportConfig
3. **src/models/config_models.py**: Added `keep_na_strings` to domain ImportConfig
4. **src/excel/reader.py**: Modified `read_excel_file()` to accept and use `keep_na_strings` parameter
5. **src/services/orchestrator.py**: Pass `keep_na_strings` from config to Excel reader

### Technical Approach
The implementation uses pandas' `keep_default_na` and `na_values` parameters:
- When `keep_na_strings` is provided, we get pandas' default NA values and remove the specified strings
- Pass the modified list to pandas via the `na_values` parameter with `keep_default_na=False`
- This gives fine-grained control over which strings are treated as NA

### Tests
- **Unit tests** (`tests/unit/test_keep_na_strings.py`): 5 tests covering various scenarios
- **Integration tests** (`tests/integration/test_keep_na_strings_integration.py`): 2 end-to-end tests
- All existing tests updated to support the new parameter

## Backward Compatibility
This feature is fully backward compatible:
- Existing configurations without `keep_na_strings` continue to work with default pandas behavior
- No breaking changes to existing APIs or configurations
