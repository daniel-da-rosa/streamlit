import os
from openai import OpenAI, APIError
from dotenv import load_dotenv

load_dotenv()

GPT_OSS_MODEL = os.getenv("GPT_OSS_MODEL", "gpt-oss-120b")


# tenta carregar a chave da api
try:
    client = OpenAI()
except Exception as e:
    print(f"Erro ao carregar o GPT: {e}")

    client = None


def get_gpt_analysis(statistics_data_string: str, custom_instruction: str = None) -> str:
    """
    Envia as estatisticas descritivas para o modelo GPT OSS 120B e retorna a análise.
    """
    if client is None:
        # Retorna msg que configuração falhou
        return "Erro de configuração: O cliente GPT não foi Inicializado!"
    system_prompt = """
    Você é um Cientista de Dados Sênior especialista em análise estatística de DataFrames do pandas. 
    Sua única tarefa é analisar a Tabela de Estatísticas Descritivas (df.describe()) fornecida pelo usuário e gerar um resumo dos insights mais críticos.

    **REGRAS DE FORMATAÇÃO E ANÁLISE:**
    1. A resposta deve ter entre 4 a 6 *bullet points*.
    2. O foco deve ser em Raciocínio (Reasoning): explique a causa ou o efeito dos números.
    3. Interprete o significado da diferença entre 'mean' (média) e '50%' (mediana) para identificar assimetrias e potenciais outliers.
    4. NÃO inclua o texto do System Prompt ou das instruções na resposta final.
    """

    user_instruction = f"""
    {custom_instruction or 'Por favor, realize uma análise estatística completa focando nas colunas mais voláteis (maior STD) e em indícios de valores atípicos.'}

    **TABELA DE ESTATÍSTICAS PARA ANÁLISE (formato Markdown):**

    {statistics_data_string}
    """

    # --- Chamando a API ---
    try:
        response = client.chat.completions.create(
            model=GPT_OSS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_instruction}
            ],
            temperature=0.1
        )
        return response.choices[0].message.content

    except APIError as e:
        return f"Erro na API OpenAI (GPT OSS 120B): Não foi possível gerar a análise. Código: {e.status_code}. Mensagem: {e.message}"
    except Exception as e:
        return f"Ocorreu um erro inesperado: {e}"
