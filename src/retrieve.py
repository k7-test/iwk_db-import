import psycopg2
import os
from dotenv import load_dotenv
import psycopg2.extras
import argparse
import sys

load_dotenv()

parser = argparse.ArgumentParser(description="Retrieve a file from a specified table and id.")
parser.add_argument('--table', required=True, help='Table name to query')
parser.add_argument('--id', required=True, type=int, help='ID value to query')
args = parser.parse_args()

# Basic validation for table name (alphanumeric and underscores only)
if not args.table.replace('_', '').isalnum():
    print("Invalid table name. Only alphanumeric characters and underscores are allowed.", file=sys.stderr)
    sys.exit(1)

conn = psycopg2.connect(os.getenv('DATABASE_URL'))

cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
query = f"select id, name, file from {args.table} where id = %s;"
cur.execute(query, (args.id,))

row = cur.fetchone()
pic = row['file']

f = open(row['name'], 'wb')
f.write(pic)
f.close()
cur.close()
conn.close()
