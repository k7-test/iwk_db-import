import psycopg2
import os
from dotenv import load_dotenv
import psycopg2.extras

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))

cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
cur.execute("select id, name, file from ts_kkk_99999 where id = 2;")

row = cur.fetchone()
pic = row['file']

f = open(row['name'], 'wb')
f.write(pic)
f.close()
cur.close()
conn.close()
