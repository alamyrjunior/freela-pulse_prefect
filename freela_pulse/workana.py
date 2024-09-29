import requests
import re
import json


def search_projects(url, query, publication, language=None, category=None, skills=None):

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

        # Processa e retorna a resposta JSON
        return response.json()

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
        raise Exception("Não foi possivel filtrar o texto da descricao")

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


def format_projects(response):
    # n_pages = response["results"]["pagination"]["pages"]
    base_url = "https://www.workana.com"
    results = response["results"]["results"]
    href_regex = r'href="([^"]+)"'
    title_regex = r'title="([^"]+)"'
    projects = []

    for job in results:
        slug = job.get("slug")
        title = job.get("title")
        """
        href_match = re.search(href_regex, title)

        if href_match:
            href_value = href_match.group(1)
            url = href_value
        """
        title_match = re.search(title_regex, title)

        if title_match:
            title_value = title_match.group(1)
            title = title_value
        # author = job["authorName"]
        description = job.get("description")
        description = format_description(description)
        posted_date = job.get("postedDate")
        budget = job.get("budget")
        budget = converter_dolares_para_reais(budget)
        budget = budget.replace("USD", "R$")
        """  message = (
            f"*Informações do projeto:*\n\n"
            f"*Link do projeto:* {url}\n\n"
            f"*Título:* {title_value}\n\n"
            f"*Descrição:* {description}\n"
            f"*Foi postado:* {posted_date}\n"
            f"*Orçamento:* {budget}"

        )
        message = message.replace("\n", "")"""

        projects.append(
            {
                "title": title,
                "description": description,
                "posted": posted_date,
                "budget": budget,
                "slug": slug,
            }
        )
    return projects


def send_whats_app_message(id_number, username, to_number, token, project):

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"https://graph.facebook.com/v20.0/{id_number}/messages"
    # url = f"https://graph.facebook.com/v20.0/{id_number}/message_templates"
    """
    greetings = f"*Olá! {username} encontramos um novo projeto para você!*\n\n"
    payload = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "preview_url": True,
            "text": {"body": greetings + message},
        }
    )
    """
    title = project.get("title")
    description = project.get("description")
    posted = project.get("posted")
    budget = project.get("budget")
    slug = project.get("slug")

    payload = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
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
        print(f"Erro ao enviar mensagem: {e}")
    except ValueError:
        print("Erro ao decodificar a resposta JSON.")


def freela_pulse(url, query, publication, language, category, skills):
    response = search_projects(url, query, publication, language, category, skills)
    messages = format_projects(response)
    id = 365993156607854
    to_number = 5521976085063
    rafa_number = 5521964709429
    token = "EAAO52Q8n6KwBOz8bucAdHy65ZAPteGIZAb45EzqGhFwXeAm768dEU9hNGjUNL33TSKdZABrd55D2CishKvzFpAl9XU44dgVfIZCQVMRz2IhDl6jqLZAEZBZBi2iULjLAQKSi57wZCCDXoEq36Iip6xPWfsVcFLg3dwerdgxOSIMYpNMXsLhJMbG2ELiSv0A5dNYQFVgnSdpVQucE0LlDwyIjLBnqwarWxaqiPY7ZC"
    for message in messages:
        response = send_whats_app_message(id, to_number, token, message)
        print("response whatsapp:", response)


token = "EAAO52Q8n6KwBOZCOeOQ7AX161w6tZCFwvommLWbVsZCIoeSl0MUV6RKPbgXGxnMzILZAS8EYtHzSdUOSKXOAmtd8iL11SK5VpL6bvaJp9i72ISbpZC0hDT5xYQHAQzXaCZBYHGaiLbXu5hMOBtlq4sw3k9hnpjm45mCSbLSjXWujeHdyRWmJY4RRdZBXp287UX5vr9nAgY2ety9vOQO"
id = 365993156607854
message = "teste testando teste"
to_number = 5521976085063
# response = send_whats_app_message(id, "Alamyr", to_number, token, message, "bot-para-runescape-3")
# print(response)
