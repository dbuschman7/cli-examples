import duckdb

conn = duckdb.connect("database/system_metrics.duckdb")

print("\\n=== HOSTNAMES TABLE (first 5) ===")
print(conn.execute("SELECT * FROM hostnames LIMIT 5").df())

print("\\n=== METRICS TABLE (first 5) ===")
print(conn.execute("SELECT * FROM metrics LIMIT 5").df())

print("\\n=== METRICS PER HOST ===")
print(
    conn.execute(
        """
    SELECT hostname, COUNT(*) as metric_count, 
           MIN(collection_date) as first_date,
           MAX(collection_date) as last_date
    FROM metrics
    GROUP BY hostname
    ORDER BY hostname
    LIMIT 10
"""
    ).df()
)

conn.close()
