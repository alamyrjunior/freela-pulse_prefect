from db import create_user, create_query, add_query_to_user, connect_to_db, close_db_connection

name = "Alamyr"
email = "alamyrjunior@gmail.com"
number = 21976085063
active = True
date = "2025-10-01"
query_id = 2

conn, cursor = connect_to_db()
user_id = create_user(conn, cursor, name, email, number, active, date)
add_query_to_user(conn, cursor, user_id, query_id)
