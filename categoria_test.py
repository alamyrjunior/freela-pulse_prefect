import re

descricao = "Olá, bom dia, preciso de um bot para criação de contas em uma&nbsp; casa de aposta, automação simples, em Python.<br/>\n<br/>\nEu tenho um modelo aqui para “modelar”, simplesmente o bot entra em um link que eu determino, utiliza proxy para entrar no “navegador” e fazer a criação da conta com e-mail aleatorio. Senha pode ser fixa.<br /><br /><strong>Categoria</strong>: TI e Programação<br /><strong>Subcategoria</strong>: Programação<br />"
resultado = re.search(r".*(?=Categoria)", descricao)
descricao = descricao[0, 900]
# Mostrando o resultado
if resultado:
    print(resultado.group(0))
else:
    print("A palavra 'Categoria' não foi encontrada.")


def cortar_texto(texto, limite=900):
    # Verifica se o texto é maior ou igual ao limite de 900 caracteres
    if len(texto) > limite:
        return texto[:limite] + "... (continua)"  # Corta o texto até o caractere 900
    else:
        return texto  # Retorna o texto sem alterações se for menor que 900
