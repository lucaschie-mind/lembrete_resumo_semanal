from datetime import datetime, timedelta
import pandas as pd
import requests
from sqlalchemy import create_engine
from io import StringIO
import os
from dotenv import load_dotenv

load_dotenv()

# Variáveis de ambiente
URL_API = 'https://full.mindsight.com.br/mindsight/api/v1/people/export_info/'
TOKEN_API = os.getenv("TOKEN_API")
DATABASE_URL = os.getenv("DATABASE_URL")
DELTA_TEMPO = 5
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def obter_access_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'client_id': CLIENT_ID,
        'scope': 'https://graph.microsoft.com/.default',
        'client_secret': CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, headers=headers, data=data)
    response.raise_for_status()
    return response.json()['access_token']

def enviar_email(destinatario, nome_funcionario, access_token):
    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    corpo_email = f"Olá {nome_funcionario}, não identificamos o registro do seu resumo semanal dessa semana. Por favor, responda no bot resumo semanal do Teams por favor. Obrigado."
    email_data = {
        "message": {
            "subject": "Lembrete - Resumo Semanal",
            "body": {
                "contentType": "Text",
                "content": corpo_email
            },
            "toRecipients": [
                {"emailAddress": {"address": destinatario}}
            ]
        }
    }
    response = requests.post(url, headers=headers, json=email_data)
    if response.status_code == 202:
        print(f"✅ E-mail enviado para: {destinatario}")
    else:
        print(f"❌ Erro ao enviar para {destinatario}: {response.status_code} - {response.text}")

def executar_envio():
    headers = {'Authorization': f'Token {TOKEN_API}'}
    response = requests.get(URL_API, headers=headers)
    if response.status_code == 200:
        try:
            data = response.json()
            if isinstance(data, dict) and 'results' in data:
                df = pd.DataFrame(data['results'])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
        except Exception:
            df = pd.read_csv(StringIO(response.content.decode('utf-8')))
    else:
        raise Exception(f"Erro na requisição: {response.status_code} - {response.text}")

    df['employee_name'] = df['nome'].astype(str) + ' ' + df['sobrenome'].astype(str)
    df_ativos = df[df['status do funcionario'].str.lower() == 'ativo']
    df_tratado = df_ativos[['employee_name', 'email', 'gestor', 'email_gestor', 'área', 'posição']]

    engine = create_engine(DATABASE_URL)
    df_resumos = pd.read_sql_table('resumos', con=engine)
    df_resumos['timestamp'] = pd.to_datetime(df_resumos['timestamp'])
    data_limite = datetime.now() - timedelta(days=DELTA_TEMPO)
    df_filtrado = df_resumos[df_resumos['timestamp'] >= data_limite]

    df_final = df_tratado.merge(
        df_filtrado[['employee_email', 'summary', 'timestamp', 'id']],
        how='left',
        left_on='email',
        right_on='employee_email'
    )
    df_final.drop(columns=['employee_email'], inplace=True)
    df_final = df_final[df_final['gestor'].notna() & (df_final['gestor'].str.strip() != '')]
    df_final['summary'] = df_final['summary'].fillna('Não preencheu no período')
    df_final.to_excel('df_final.xlsx', index=False)

    access_token = obter_access_token()
    df_lembrete = df_final[df_final['summary'] == 'Não preencheu no período']
    for _, row in df_lembrete.iterrows():
        enviar_email(row['email'], row['employee_name'], access_token)

    print("✅ Todos os lembretes foram enviados.")

if __name__ == "__main__":
    executar_envio()
