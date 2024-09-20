from dotenv import load_dotenv
import os
from prefect import task, flow
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

load_dotenv()


@task
def get_queries():
    supabase_credentials = os.getenv("SUPABASE_KEY")
    supabase = create_supabase_client(supabase_credentials)
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

    # Get environment variables
    url = os.getenv("WORKANA_URL")
    publication = os.getenv("PUBLICATION")

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
    token = os.getenv("WHATSAPP_TOKEN")
    id_sender = os.getenv("ID_SENDER")
    query_id = payload.get("query_id")
    query = payload.get("query")

    # TODO: Criar uma view para mesclar o user_id com a tabela users
    # Get user ids of users who are interested in the current query
    # Connect to the database
    supabase_credentials = os.getenv("SUPABASE_KEY")
    supabase = create_supabase_client(supabase_credentials)
    users = get_users_from_query(supabase, query_id)
    print(f"Found {len(users)} users interested in query: {query}. {users}")

    # Send whatsapp messages to interested users with the project details
    for project in projects:
        try:
            slug = project.get("slug")
            message = project.get("message")

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
                            id_sender, username, user_number, token, message
                        )
                    except Exception as e:
                        delete_project_from_user(supabase, project_id)
                        raise Exception(f"Error sending whatsapp message: {e}")

        except AssertionError as err:
            raise Exception(f"Assertion Error sending whatsapp message: {err}")
        except KeyError as err:
            raise Exception(f"Key Error sending whatsapp message: {err}")


@flow
def freela_pulse():
    queries = get_queries()
    for query in queries:
        query_data = get_query_data(query)
        projects = get_projects(query_data)
        send_pulse_workana(projects, query_data)

