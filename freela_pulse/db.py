import sqlite3
import os

def connect_to_db():
    """Conecta ao banco de dados e retorna a conexão e o cursor."""
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()
    return conn, cursor


def close_db_connection(conn):
    """Fecha a conexão com o banco de dados."""
    conn.close()


def create_user(conn, cursor, name, email, number, active, expires_at):
    # Verificando se o usuário já existe com base no email
    cursor.execute(
        """
        SELECT id FROM users WHERE email = ?
    """,
        (email,),
    )
    result = cursor.fetchone()

    if result:
        user_id = result[0]
    else:
        cursor.execute(
            """
            INSERT INTO users (name, email, number, active, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (name, email, number, active, expires_at),
        )

        conn.commit()
        user_id = cursor.lastrowid

    return user_id


def create_query(conn, cursor, skills, query, category, language):
    cursor.execute(
        """
        SELECT id FROM queries WHERE skills = ? AND query = ? AND category = ? AND language = ?
    """,
        (skills, query, category, language),
    )
    result = cursor.fetchone()

    if result:
        query_id = result[0]
    else:
        cursor.execute(
            """
            INSERT INTO queries (skills, query, category, language)
            VALUES (?, ?, ?, ?)
        """,
            (skills, query, category, language),
        )

        conn.commit()
        query_id = cursor.lastrowid

    return query_id


def add_query_to_user(conn, cursor, user_id, query_id):
    cursor.execute(
        """
        SELECT * FROM user_queries WHERE user_id = ? AND query_id = ?
    """,
        (user_id, query_id),
    )
    result = cursor.fetchone()

    if not result:
        cursor.execute(
            """
            INSERT INTO user_queries (user_id, query_id)
            VALUES (?, ?)
        """,
            (user_id, query_id),
        )

        conn.commit()


def get_all_queries(cursor):
    # Seleciona todas as queries da tabela
    print("Getting all queries from database")
    cursor.execute(
        """
        SELECT id, skills, query, category, language FROM queries
    """
    )
    results = cursor.fetchall()

    return results


def get_users_from_query(query_id, cursor):
    cursor.execute(
        """
        SELECT users.id, users.name, users.email, users.number, users.active, users.expires_at
        FROM users
        JOIN user_queries ON users.id = user_queries.user_id
        WHERE user_queries.query_id =?
    """,
        (query_id,),
    )
    results = cursor.fetchall()

    return results


def insert_project(conn, cursor, slug, query_id):
    query = "INSERT INTO projects (slug, query_id) VALUES (?,?)"

    try:
        # Executa a inserção
        cursor.execute(query, (slug, query_id))
        # Confirma a transação
        conn.commit()
        print(f"Projeto '{slug}' adicionado com sucesso a query_id {query_id}.")

        # return project id
        return cursor.lastrowid

    except sqlite3.Error as e:
        # Se ocorrer um erro, exibe a mensagem
        print(f"Erro ao adicionar projeto: {e}")


def check_project_exists_for_query(cursor, slug, query_id):
    query = "SELECT * FROM projects WHERE slug =? AND query_id =?"
    project_exists = cursor.execute(query, (slug, query_id)).fetchone()

    return project_exists is not None


def check_project_exists_in_user(cursor, user_id, project_id):
    query = "SELECT * FROM user_projects WHERE user_id =? AND project_id =?"
    project_exists = cursor.execute(query, (user_id, project_id)).fetchone()

    return project_exists


def add_project_to_user(conn, cursor, project_id, user_id):
    query = "INSERT INTO user_projects (user_id, project_id) VALUES (?,?)"
    try:
        cursor.execute(query, (user_id, project_id))
        conn.commit()
        print(
            f"Projeto '{project_id}' adicionado ao usuário no banco de dados com sucesso."
        )
    except sqlite3.Error as e:
        print(f"Erro ao adicionar projeto ao usuário: {e}")

    return cursor.lastrowid


def update_user_status(user_id, active, cursor):
    
    cursor.execute(
        """ 
        """
    )





