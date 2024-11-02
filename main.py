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
    check_project_exists,
)
from freela_pulse.workana import request_get_workana_projects, format_project

import requests
import json


@task
def get_assets():
    secrets = Secret.load("freela-pulse-secrets").get()
    config = Variable.get("freela_pulse_config")

    return config, secrets


@task()
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


def send_whatsapp_message(config, usernumber, username, project):
    print("Sending whatsapp message...")

    title = project.get("title")
    description = project.get("description")
    posted = project.get("posted")
    budget = project.get("budget")
    slug = project.get("slug")

    evolution_api_url = config.get("evolution_api_url")
    instance = config.get("instance_evolution_api")
    api_key = config.get("evolution_api_key")
    message = f"""*Olá {username}, encontramos um novo projeto para você!*\n\n_Informações do projeto_\n\n*Título:* {title}\n\n*Descrição:* {description}\n\n*Foi postado:* {posted}\n\n*Orçamento:* {budget}\n\n*Link:* workana.com/job/{slug}\n\n              _Boa sorte nos freelas!_\n\n```        Freela Pulse      ``` """

    payload = json.dumps(
        {"number": str(usernumber) + "@s.whatsapp.net", "text": message}
    )
    headers = {"Content-Type": "application/json", "apikey": api_key}

    response = requests.request(
        "POST",
        f"{evolution_api_url}/message/SendText/{instance}",
        headers=headers,
        data=payload,
    )
    response.raise_for_status()
    response = response.json()
    remoteJid = response["key"]["remoteJid"]
    id = response["key"]["id"]

    payload = json.dumps(
        {"readMessages": [{"remoteJid": remoteJid, "fromMe": True, "id": id}]}
    )

    response = requests.request(
        "POST",
        f"{evolution_api_url}/chat/markMessageAsRead/{instance}",
        headers=headers,
        data=payload,
    )
    response.raise_for_status()

    read = response.json()["read"]
    if read == "success":
        return True
    else:
        raise Exception("There was an error sending message")


@task(log_prints=True)
def send_project_to_user(user, project, supabase, query_id, config):
    try:
        slug = project.get("slug")
        if not slug:
            raise AssertionError("Project slug is not provided")
        project_exists, project_id = insert_project(supabase, slug, query_id)

        print(f"Enviando projetos para {user}")
        user_id = user.get("user_id")
        users = user.get("users")
        username = users.get("name")
        usernumber = users.get("number")
        is_active = users.get("active")
        print("Checking if user is active:", is_active)

        if is_active:
            # TODO Check if current date is greater than active date
            # TODO Warn user about his being inactive

            project_exists = check_project_exists(supabase, user_id, project_id)
            if not project_exists:
                try:
                    send_whatsapp_message(config, usernumber, username, project)
                    project_exists = insert_project_to_user(
                        supabase, project_id, user_id
                    )
                except Exception as e:

                    raise Exception(f"Error sending whatsapp message: {e}")
            else:
                print("Project already sent!")
    except AssertionError as err:
        raise Exception(f"Assertion Error sending project to user: {err}")


@task(log_prints=True)
def get_users_projects(query, supabase, config, secrets):
    print(f"Processing query: {query['query']}")
    query_id = query["id"]

    # Obtenha os projetos e formate-os
    projects = get_projects(query, config)
    formatted_projects = format_project.map(projects)

    # Obtenha os usuários
    users = get_users_from_query(supabase, query["id"])

    # Gera os pares de usuários e projetos
    users_projects = [
        (user, project) for user in users for project in formatted_projects
    ]
    results = []
    for user, project in users_projects:
        sent_project = send_project_to_user.submit(
            user, project, supabase, query_id, config
        )
        results.append(sent_project.wait())
    return results


@flow(log_prints=True)
def main():
    config, secrets = get_assets()
    url = config.get("supabase_url")
    key = secrets.get("supabase_key")

    supabase = create_supabase_client(url, key)
    queries = get_all_queries(supabase)
    ### FOR EACH QUERY GET USERS AND PROJECTS FOR EACH ONE AND SEND THE PROJECTS  ###
    results = get_users_projects.map(
        queries, unmapped(supabase), unmapped(config), unmapped(secrets)
    )
    results.wait()


main()
