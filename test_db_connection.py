
from backend.app.database import get_db_connection


try:
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            database_name = cursor.fetchone()[0]

            print("Database connection successful!")
            print(f"Connected database: {database_name}")

except Exception as error:
    print("Database connection failed.")
    print("Error:", error)
