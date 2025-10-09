#!/usr/bin/env python3
"""Dataset generation script for performance testing (T028).

Generates synthetic Excel files with parameterized rows/columns for performance testing.
The generated Excel files follow the expected format:
- Row 1: Title row (optional, often ignored)
- Row 2: Header row with column names
- Row 3+: Data rows

This script produces files suitable for use with the Excel -> PostgreSQL bulk import tool.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def generate_synthetic_data(rows: int, cols: int, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic DataFrame with mixed data types.
    
    Creates realistic data similar to typical Excel imports:
    - String columns (names, descriptions, categories)
    - Numeric columns (IDs, amounts, quantities)
    - Date columns
    - Boolean flags
    
    Args:
        rows: Number of data rows to generate
        cols: Number of columns to generate
        seed: Random seed for reproducible data
        
    Returns:
        DataFrame with mixed synthetic data
    """
    np.random.seed(seed)
    
    data: dict[str, list[Any]] = {}
    
    # Distribute column types proportionally
    string_cols = max(1, int(cols * 0.3))     # 30% strings
    numeric_cols = max(1, int(cols * 0.5))    # 50% numeric
    bool_cols = max(1, int(cols * 0.1))       # 10% boolean
    date_cols = cols - string_cols - numeric_cols - bool_cols  # remainder dates
    
    # String columns - names, categories, descriptions
    for i in range(string_cols):
        if i == 0:
            # First string column: names
            data["name"] = [
                f"Item_{np.random.randint(1000, 9999)}_{chr(65 + (j % 26))}"
                for j in range(rows)
            ]
        elif i == 1 and string_cols > 1:
            # Second string column: categories
            categories = ["Electronics", "Clothing", "Books", "Food", "Sports", "Home"]
            data["category"] = np.random.choice(categories, rows).tolist()
        else:
            # Other string columns: descriptions
            descriptions = [
                f"Description for item {j+1} with details and specifications"
                for j in range(rows)
            ]
            data[f"description_{i}"] = descriptions
        
    # Numeric columns - IDs, amounts, quantities
    for i in range(numeric_cols):
        if i == 0:
            # First numeric: ID column (integers)
            data["id"] = [i for i in range(1, rows + 1)]
        elif i % 3 == 1:
            # Price/amount columns (decimals)
            data[f"amount_{i}"] = np.round(
                np.random.uniform(0.01, 9999.99, rows), 2
            ).tolist()
        elif i % 3 == 2:
            # Quantity columns (integers) 
            data[f"quantity_{i}"] = np.random.randint(1, 1000, rows).tolist()
        else:
            # General numeric columns
            data[f"value_{i}"] = np.round(
                np.random.uniform(0, 10000, rows), 2
            ).tolist()
        
    # Boolean columns - flags
    for i in range(bool_cols):
        if i == 0:
            data["active"] = np.random.choice([True, False], rows).tolist()
        else:
            data[f"flag_{i}"] = np.random.choice([True, False], rows).tolist()
        
    # Date columns
    for i in range(date_cols):
        # Generate dates in recent range
        start_date = pd.Timestamp('2023-01-01')
        end_date = pd.Timestamp('2024-12-31')
        date_range = pd.date_range(start_date, end_date, periods=100)
        if i == 0:
            data["created_date"] = np.random.choice(date_range, rows).tolist()
        else:
            data[f"date_{i}"] = np.random.choice(date_range, rows).tolist()
    
    return pd.DataFrame(data)


def create_excel_file(
    output_path: Path,
    rows: int,
    cols: int,
    sheets: list[str] | None = None,
    title: str = "Performance Test Data",
    seed: int = 42
) -> None:
    """Create Excel file with synthetic data in the expected format.
    
    Creates Excel file with:
    - Row 1: Title row
    - Row 2: Header row with column names  
    - Row 3+: Data rows
    
    Args:
        output_path: Path where Excel file will be saved
        rows: Number of data rows per sheet
        cols: Number of columns per sheet
        sheets: List of sheet names (default: ["Sheet1"])
        title: Title for the first row
        seed: Random seed for reproducible data
    """
    if sheets is None:
        sheets = ["Sheet1"]
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name in sheets:
            # Generate synthetic data
            df = generate_synthetic_data(rows, cols, seed)
            
            # Create the Excel format expected by the reader:
            # Row 1: Title
            # Row 2: Headers
            # Row 3+: Data
            
            # Build the full sheet data
            sheet_data = []
            
            # Row 1: Title row 
            title_row = [title] + [""] * (len(df.columns) - 1)
            sheet_data.append(title_row)
            
            # Row 2: Header row
            header_row = df.columns.tolist()
            sheet_data.append(header_row)
            
            # Row 3+: Data rows
            for _, row in df.iterrows():
                sheet_data.append(row.tolist())
            
            # Convert to DataFrame and write to Excel
            final_df = pd.DataFrame(sheet_data)
            final_df.to_excel(
                writer,
                sheet_name=sheet_name,
                header=False,
                index=False
            )
            
    print(f"Created Excel file: {output_path}")
    print(f"  Sheets: {len(sheets)} ({', '.join(sheets)})")
    print(f"  Rows per sheet: {rows} (+ 2 header rows)")
    print(f"  Columns per sheet: {cols}")
    print(f"  Total data cells: {len(sheets) * rows * cols:,}")


def main() -> int:
    """Main CLI interface for dataset generation."""
    parser = argparse.ArgumentParser(
        description="Generate synthetic Excel datasets for performance testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate default 50k rows, 40 columns
  %(prog)s output.xlsx
  
  # Generate custom size dataset
  %(prog)s large_dataset.xlsx --rows 100000 --cols 50
  
  # Generate multi-sheet dataset
  %(prog)s multi_sheet.xlsx --rows 25000 --cols 30 --sheets Sheet1 Sheet2 Sheet3
  
  # Generate with custom title and seed
  %(prog)s custom.xlsx --rows 10000 --cols 20 --title "Custom Test Data" --seed 123
        """
    )
    
    parser.add_argument(
        "output",
        type=Path,
        help="Output Excel file path"
    )
    
    parser.add_argument(
        "--rows",
        type=int,
        default=50_000,
        help="Number of data rows per sheet (default: 50,000)"
    )
    
    parser.add_argument(
        "--cols", 
        type=int,
        default=40,
        help="Number of columns per sheet (default: 40)"
    )
    
    parser.add_argument(
        "--sheets",
        nargs="+",
        default=["Sheet1"],
        help="Sheet names (default: Sheet1)"
    )
    
    parser.add_argument(
        "--title",
        default="Performance Test Data",
        help="Title for first row (default: 'Performance Test Data')"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data (default: 42)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without creating files"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.rows <= 0:
        print("Error: --rows must be positive", file=sys.stderr)
        return 1
        
    if args.cols <= 0:
        print("Error: --cols must be positive", file=sys.stderr)
        return 1
        
    if not args.sheets:
        print("Error: At least one sheet name required", file=sys.stderr)
        return 1
    
    # Show what will be generated
    total_cells = len(args.sheets) * args.rows * args.cols
    total_size_mb = total_cells * 20 / (1024 * 1024)  # Rough estimate: 20 bytes per cell
    
    print("Dataset generation plan:")
    print(f"  Output file: {args.output}")
    print(f"  Sheets: {len(args.sheets)} ({', '.join(args.sheets)})")
    print(f"  Rows per sheet: {args.rows:,} (+ 2 header rows)")
    print(f"  Columns per sheet: {args.cols}")
    print(f"  Total data cells: {total_cells:,}")
    print(f"  Estimated size: ~{total_size_mb:.1f} MB")
    print(f"  Random seed: {args.seed}")
    
    if args.dry_run:
        print("\n[DRY RUN] Would generate files but not creating them.")
        return 0
        
    if total_size_mb > 100:
        print(f"\nWarning: Large file size (~{total_size_mb:.1f} MB)")
        response = input("Continue? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Cancelled.")
            return 0
    
    try:
        print("\nGenerating dataset...")
        create_excel_file(
            args.output,
            args.rows,
            args.cols,
            args.sheets,
            args.title,
            args.seed
        )
        print("\nDataset generation completed successfully!")
        return 0
        
    except Exception as e:
        print(f"\nError generating dataset: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())