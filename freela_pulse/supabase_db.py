import os
from supabase import create_client
from dotenv import load_dotenv
from supabase import PostgrestAPIError
from prefect.variables import Variable
from prefect.blocks.system import Secret


def create_supabase_client(url, key):
    supabase = create_client(url, key)

    return supabase


### INSERTS ###
def create_user(supabase, name, email, number, active, expires_at):

    new_user = {
        "name": name,
        "email": email,
        "number": number,
        "active": active,
        "expires_at": expires_at,
    }

    try:
        # Tenta inserir o novo usuário
        response = supabase.table("users").insert(new_user).execute()

        print("Usuário criado com sucesso!")
        return response

    except PostgrestAPIError as e:
        # Captura erros da API (como o de chave duplicada)
        if "duplicate key value" in str(e):
            return "Usuário com esse email já existe."
        else:
            return f"Erro ao criar usuário: {e}"


def create_query(supabase, query, category, language, skills):
    new_query = {
        "query": query,
        "category": category,
        "language": language,
        "skills": skills,
    }

    try:
        # Tenta inserir a nova query
        response = supabase.table("queries").insert(new_query).execute()
        print(response)
        return "Query criada com sucesso!"

    except PostgrestAPIError as e:
        # Captura erro de chave duplicada devido à restrição UNIQUE
        if "duplicate key value" in str(e):
            return "Essa query já existe."
        else:
            return f"Erro ao criar query: {e}"


def insert_project_to_user(supabase, project_id, user_id):

    query = {"user_id": user_id, "project_id": project_id}
    try:
        response = supabase.table("user_projects").insert(query).execute()
        print("Projeto adicionado ao user com sucesso!")
        print(response)
        project_exists = False
        return project_exists

    except PostgrestAPIError as e:
        # Captura erro de chave duplicada devido à restrição UNIQUE
        if "duplicate key value" in str(e):
            project_exists = True
            print("Esse projeto já existe para esse user!")
            return project_exists
        else:
            raise Exception(f"Erro ao adicionar projeto ao usuário: {e}")


def insert_project(supabase, slug, query_id):
    query = {"slug": slug, "query_id": query_id}

    try:
        response = supabase.table("projects").insert(query).execute()
        print("Projeto adicionado com sucesso!")
        print(response)
        project_id = response.data[0]["id"]
        project_exists = False
        return project_exists, project_id

    except PostgrestAPIError as e:
        # Captura erro de chave duplicada devido à restrição UNIQUE
        if "duplicate key value" in str(e):
            project_exists = True
            print("Esse projeto já existe!")

            # Consulta o project_id do projeto existente
            response = (
                supabase.from_("projects")
                .select("id")
                .eq("slug", slug)
                .execute()
            )

            # Verifica se encontrou o project_id
            project_id = response.data[0]["id"] if response.data else None
            return project_exists, project_id
        else:
            raise Exception("Houve um erro ao adicionar o projeto:", e)


### CHECK IF PROJECT_EXISTS ###
def check_project_exists(supabase, user_id, project_id) -> bool:
    # Executa a consulta para verificar se o projeto existe na tabela user_projects
    response = (
        supabase.from_("user_projects")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("project_id", project_id)
        .execute()
    )

    # Verifica se algum registro foi encontrado
    if response.count > 0:
        return True
    else:
        return False


### SELECTS ####


def get_all_queries(supabase):
    response = supabase.table("queries").select("*").execute()
    return response.data


def get_users_from_query(supabase, query_id):
    response = (
        supabase.table("user_queries")
        .select("user_id, users(name, number, active, expires_at)")
        .eq("query_id", query_id)
        .execute()
    )
    return response.data


def delete_project_from_user(supabase: create_client, project_id: int):
    supabase.table("projects_users").delete().eq("project_id", project_id).execute()
    print("Projeto excluído com sucesso!")


#url = "https://vhdvimpscrnuwrihfydx.supabase.co"
#key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZoZHZpbXBzY3JudXdyaWhmeWR4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU4MDQxOTMsImV4cCI6MjA0MTM4MDE5M30.hXDwuAr2fjKXFq6k8xj2VoXm6MH0yjhnVNG0fDyPWbg"
#supabase = create_supabase_client(url, key)
# response = create_user(supabase, 'billl', 'bill2@example.com', 6666666666, True, '2024-12-12')
# response = create_query(supabase, "bott", "it-programming", "xx", "aa")
# response = add_query_to_user(supabase, 1, 21)
# response = insert_project(supabase, "billll", 21)
# response = insert_project_to_user(supabase, 2, 1)
# response = get_users_from_query(supabase, 21)
#response = check_project_exists(supabase, 1, 1)

"""
for user in response:
    userdata = user.get("users")
    name = userdata.get("name")
    print(name)
"""
