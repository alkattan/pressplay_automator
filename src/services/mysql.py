import mysql.connector 
import config

def get_mysql_connection():
    """
    returns a DB connection to Toaster DB
    """
    try:
        db = mysql.connector.connect(host=config.host,
                        user=config.DATABASE_USER,
                        password=config.DATABASE_PASSWORD,
                        database=config.DATABASE_NAME,
                        port=config.DATABASE_PORT,
                        ssl_ca = 'certs/ca.pem',
                        ssl_key = 'certs/client-key.pem',
                        ssl_cert= 'certs/client-cert.pem'
                        ) 
        print("Connected")
        return db
    except Exception as e:
        print(str(e))
        print("Can't connect to the Toaster database")


def execute_sql_dict(sql):
    """
    Execute the query against the Toaster DB
    """
    db = get_mysql_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e: 
        print(str(e))
        return None
    


def execute_sql(sql):
    """
    Execute the query against the Toaster DB
    """
    db = get_mysql_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql)
    except Exception as e:
        print(str(e))
        return None