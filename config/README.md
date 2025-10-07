# Configuration Directory

This directory contains runtime configuration files for the Excel -> PostgreSQL import tool.

## Setup

1. Copy the template file:
   ```bash
   cp import.yml.template import.yml
   ```

2. Edit `import.yml` to match your environment:
   - Update `source_directory` to point to your Excel files
   - Configure `sheet_mappings` for your database schema
   - Set database connection parameters (or use environment variables)

## File Descriptions

- **import.yml.template** - Template configuration with examples and comments
- **import.yml** - Your actual configuration (git-ignored for security)

## Environment Variables

Database connection settings can be overridden with environment variables (recommended for production):

- `PG_HOST` - Database host
- `PG_PORT` - Database port
- `PG_USER` - Database user
- `PG_PASSWORD` - Database password
- `PG_DATABASE` - Database name
- `PG_DSN` - Complete connection string (overrides individual settings)

Environment variables take precedence over config file settings (FR-027).
