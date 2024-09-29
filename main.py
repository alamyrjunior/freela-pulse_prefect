from prefect.variables import Variable
from prefect import task, flow
from prefect.blocks.system import Secret
from freela_pulse.supabase_db import (
    create_supabase_client,
    insert_project,
    insert_project_to_user,
    get_all_queries,
    get_users_from_query,
    delete_project_from_user,
)
from freela_pulse.workana import (
    search_projects,
    format_projects,
    send_whats_app_message,
)


@task
def get_variables():
    secrets = Secret.load("freela-pulse-secrets").get()
    config = Variable.get("freela_pulse_config")

    return config, secrets


@task
def get_queries():
    config, secrets = get_variables()
    url = config.get("supabase_url")
    key = secrets.get("supabase_key")
    supabase = create_supabase_client(url, key)
    queries = get_all_queries(supabase)
    return queries


@task
def get_query_data(query: dict):
    print(f"Adding query to workitems: {query}")
    query_id = query.get("id")
    query_name = query.get("query")
    category = query.get("category")
    skills = query.get("skills")
    language = query.get("language")

    # Search project for query, category, language, skills on workana website
    payload = {
        "query_id": query_id,
        "query": query_name,
        "category": category,
        "skills": skills,
        "language": language,
    }
    return payload


@task
def get_projects(payload):
    config, secrets = get_variables()
    # Get environment variables
    url = config.get("workana_url")
    if not url:
        raise ValueError("A url não existe")
    publication = config.get("publication")

    try:
        query = payload.get("query")
        category = payload.get("category")
        language = payload.get("language")
        skills = payload.get("skills")
        query_id = payload.get("query_id")

        print(f"Processing query: {query} - {query_id}")

        # Search project for query, category, language, skills on workana website
        projects = search_projects(url, query, publication, language, category, skills)
        # Format project results into whatsapp format
        projects = format_projects(projects)

        return projects
    except Exception as e:
        print(f"Error processing query: {query} - {query_id}")
        print(f"Error: {e}")
        return []


@task
def send_pulse_workana(projects, payload):
    config, secrets = get_variables()
    token = secrets.get("whatsapp_token")
    id_sender = secrets.get("whatsapp_id_sender")
    query_id = payload.get("query_id")
    query = payload.get("query")

    # TODO: Criar uma view para mesclar o user_id com a tabela users
    # Get user ids of users who are interested in the current query
    # Connect to the database
    url = config.get("supabase_url")
    key = secrets.get("supabase_key")
    supabase = create_supabase_client(url, key)
    users = get_users_from_query(supabase, query_id)
    print(f"Found {len(users)} users interested in query: {query}. {users}")

    # Send whatsapp messages to interested users with the project details
    for project in projects:
        try:
            slug = project.get("slug")
       
            # If project does not exist, add it to the database and send whatsapp messages to interested users
            project_exists, project_id = insert_project(supabase, slug, query_id)
            if project_exists:
                continue

            print(f"Sending project {slug} to users")

            for user in users:
                user_id = user.get("user_id")
                # Get user data
                user_data = user.get("users")
                username = user_data.get("name")
                user_number = user_data.get("number")
                is_active = user_data.get("active")

                if is_active:
                    # TODO Check if current date is greater than active date
                    # TODO Warn user about his being inactive
                    project_exists = insert_project_to_user(
                        supabase, project_id, user_id
                    )
                    # check if user already have the project
                    if project_exists:
                        continue
                    try:
                        print(f"Enviando projeto para {username}")
                        send_whats_app_message(
                            id_sender, username, user_number, token, project
                        )
                    except Exception as e:
                        delete_project_from_user(supabase, project_id)
                        raise Exception(f"Error sending whatsapp message: {e}")

        except AssertionError as err:
            raise Exception(f"Assertion Error sending whatsapp message: {err}")
        except KeyError as err:
            raise Exception(f"Key Error sending whatsapp message: {err}")


@flow(log_prints=True)
def freela_pulse():

    queries = get_queries()
    for query in queries:
        query_data = get_query_data(query)
        projects = get_projects(query_data)
        send_pulse_workana(projects, query_data)


if __name__ == "__main__":
    freela_pulse()
