import psycopg2
import urllib.parse as up

# PostgreSQL connection string
DATABASE_URL = "postgresql://postgres:vVMyqWjrqgVhEnwyFifTQxkDtPjQutGb@interchange.proxy.rlwy.net:30451/railway?sslmode=require"

# Parse the connection string
url = up.urlparse(DATABASE_URL)

# Establish connection
try:
    connection = psycopg2.connect(
        dbname=url.path[1:],  # Skip the leading '/'
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users LIMIT 1;")
    row = cursor.fetchone()

    if row:
        print("✅ PostgreSQL connection successful!")
        print("Sample Row:", row)
    else:
        print("❌ No data found in the users table.")
        
except Exception as e:
    print("❌ Failed to connect to PostgreSQL:", e)
finally:
    if connection:
        cursor.close()
        connection.close()
