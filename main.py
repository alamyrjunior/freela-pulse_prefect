from prefect.variables import Variable
from prefect import task, flow, unmapped
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
    request_get_workana_projects,
    format_project,
    send_whats_app_message,
)
import json

@task
def get_variables():
    secrets = Secret.load("freela-pulse-secrets").get()
    config = Variable.get("freela_pulse_config")

    return config, secrets


@task(name="query-data", task_run_name="a")
def get_query_data(query: dict):
    print(query)
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


def get_projects(query, config):
    workana_url = config.get("workana_url")
    publication = config.get("publication")

    # Get environment variables

    if not workana_url:
        raise ValueError("A url não existe")

    try:
        query_name = query.get("query")
        category = query.get("category")
        language = query.get("language")
        skills = query.get("skills")
        query_id = query.get("id")

        # Search project for query, category, language, skills on workana website
        projects = request_get_workana_projects(
            workana_url, query_name, publication, language, category, skills
        )
        return projects

    except Exception as e:
        print(f"Error getting projects of query: {query} - {query_id}")
        raise Exception(f"Error: {e}")


@task
def send_project_to_user(user, project, supabase, query_id, secrets):
    try:
        slug = project.get("slug")
        if not slug:
            raise AssertionError("Project slug is not provided")
        project_exists, project_id = insert_project(supabase, slug, query_id)
        if project_exists:
            print("Project was already sent!")
            return
        
        print(user)
        user_id = user.get("user_id")
        users = user.get("users")
        username = users.get("name")
        usernumber = users.get("number")
        is_active = users.get("active")
        print("Checking if user is active:", is_active)

        if is_active:
            # TODO Check if current date is greater than active date
            # TODO Warn user about his being inactive
            project_exists = insert_project_to_user(supabase, project_id, user_id)
            if project_exists:
                return
          
            try:
                send_whats_app_message(username, usernumber, project, secrets)
            except Exception as e:
                delete_project_from_user(supabase, project_id)
                raise Exception(f"Error sending whatsapp message: {e}")
    except AssertionError as err:
        raise Exception(f"Assertion Error sending project to user: {err}")


@task(log_prints=True)
def process_query(query, supabase, config, secrets):
    print(f"Processing query: {query['query']}")
    query_id = query["id"]

    # Obtenha os projetos e formate-os
    projects = get_projects(query, config)
    formatted_projects = format_project.map(projects)

    # Obtenha os usuários
    users = get_users_from_query(supabase, query["id"])

    # Gera os pares de usuários e projetos
    pairs = [(user, project) for user in users for project in formatted_projects]

    # Lista para armazenar os futuros
    futures = []

    # Enviar os projetos para os usuários
    for user, project in pairs:
        future = send_project_to_user.submit(
            user,
            project,
            supabase,
            query_id,
            secrets,
            wait_for=[formatted_projects, projects],
        )
        futures.append(future)

    # Aguarda todos os futuros serem resolvidos
    for future in futures:
        future.result()

    """
    for user, project in pairs:
        sent_project = send_project_to_user.submit(user, project, supabase, query_id, secrets, wait_for=[format_project, get_projects])
        sent_project.result()
    """


@flow(name="freela-pulse")
def main():
    config, secrets = get_variables()
    url = config.get("supabase_url")
    key = secrets.get("supabase_key")

    supabase = create_supabase_client(url, key)
    queries = get_all_queries(supabase)
    queries_results = process_query.map(
        queries, unmapped(supabase), unmapped(config), unmapped(secrets)
    )
    queries_results.result()


main()
