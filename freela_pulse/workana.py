import requests
import re
import json
from prefect import task

@task
def request_get_workana_projects(
    url, query, publication, language=None, category=None, skills=None
):
    print("Requesting workana projects")
    params = {
        "query": query,
        "publication": publication,
        "category": category,
        "skills": skills,
        "language": language,
    }

    # Remove parâmetros com valor None ou strings vazias
    params = {k: v for k, v in params.items() if v not in (None, "")}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Encoding": "gzip,deflate, br",
        "Accept": "*/*",
    }
    try:
        # Envio da requisição
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Levanta uma exceção para erros HTTP
        projects = response.json()["results"]["results"]
        # Processa e retorna a resposta JSON
        return projects

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Erro na requisição: {e}")
    except ValueError:
        raise RuntimeError("Erro ao decodificar a resposta JSON.")


def converter_dolares_para_reais(budget):
    # Função que faz a multiplicação por 5.4 e formata o resultado com duas casas decimais
    def multiplicar(match):
        numero = float(match.group())
        return f"{numero * 5.4:.2f}"

    # Regex para encontrar os números na string
    regex = r"\d+(\.\d+)?"

    # Substitui os números na string aplicando a multiplicação
    nova_string = re.sub(regex, multiplicar, budget)

    return nova_string


def format_description(html_message):
    regex_categoria = re.search(r".*(?=Categoria)", html_message)
    if regex_categoria:
        html_message = regex_categoria.group(0)
    else:
        print("Não foi possivel filtrar o texto da descricao")

    html_message = re.sub(r'\s*(target|class|rel)="[^"]*"', "", html_message)

    # Substitui as tags <a> pelo próprio link contido nelas
    html_message = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"\1", html_message)
    # Substitui as quebras de linha, incluindo espaços ao redor
    formatted_message = re.sub(r"\s*<br\s*/?>\s*", "\n", html_message)

    # Substitui as tags <strong> pelo asterisco
    formatted_message = re.sub(r"</?strong>", "", formatted_message)

    formatted_message = formatted_message.replace("&nbsp", " ")

    # Remove qualquer espaço em branco extra que possa ter ficado
    formatted_message = formatted_message.strip().replace("\n", "")

    if len(formatted_message) > 900:
        formatted_message = (
            formatted_message[:900] + "... (continua)"
        )  # Limita a descrição à 900 caracteres e adiciona "..." no final caso seja maior

    return formatted_message


@task
def  format_project(project):
    slug = project.get("slug")
    title = project.get("title")
    title_regex = r'title="([^"]+)"'
    title_match = re.search(title_regex, title)

    if title_match:
        title_value = title_match.group(1)
        title = title_value

    description = project.get("description")
    description = format_description(description)
    posted_date = project.get("postedDate")
    budget = project.get("budget")
    budget = converter_dolares_para_reais(budget)
    budget = budget.replace("USD", "R$")

    project = {
        "title": title,
        "description": description,
        "posted": posted_date,
        "budget": budget,
        "slug": slug,
    }

    return project

@task
def send_whats_app_message(username, usernumber, project, secrets):
    print("Sending whatsapp message...")
    token = secrets.get("whatsapp_token")
    id_number = secrets.get("whatsapp_id_sender")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"https://graph.facebook.com/v20.0/{id_number}/messages"

    title = project.get("title")
    description = project.get("description")
    posted = project.get("posted")
    budget = project.get("budget")
    slug = project.get("slug")

    payload = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": usernumber,
            "type": "template",
            "template": {
                "name": "workana_projects",
                "language": {"code": "pt_BR"},
                "components": [
                    {
                        "type": "header",
                        "parameters": [{"type": "text", "text": username}],
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": title},
                            {
                                "type": "text",
                                "text": description,
                            },
                            {"type": "text", "text": posted},
                            {"type": "text", "text": budget},
                        ],
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 0,
                        "parameters": [
                            {
                                "type": "text",
                                "text": slug,
                            }
                        ],
                    },
                ],
            },
        }
    )
    print(f"Payload: \n{payload}")
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + token}
    try:
        # Envio da requisição
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()  # Levanta uma exceção para erros HTTP

        print("Project sent successfully")
        # Processa e retorna a resposta JSON
        return response.json()

    except requests.exceptions.RequestException as e:
        raise Exception(f"Erro ao enviar mensagem: {e}")
    except ValueError:
        raise Exception("Erro ao decodificar a resposta JSON.")
