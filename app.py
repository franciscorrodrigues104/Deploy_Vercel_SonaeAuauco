from flask import Flask, render_template, request
from datetime import datetime
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

SUPABASE_TABLE = os.getenv("SUPABASE_TABLE")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

# Na Vercel, a app Flask é instanciada diretamente para ser gerida pelo servidor deles
app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    data_filtro = request.args.get('data')
    hoje_cpu = datetime.now().strftime('%Y-%m-%d')

    try:
        query = supabase.table(SUPABASE_TABLE).select("*")

        if data_filtro:
            response = query.filter("timestamp_inicio", "ilike", f"{data_filtro}%")\
                            .order("counter_dia", desc=True).execute()
            dados = response.data
            total_real = len(dados)
        else:
            response = query.filter("timestamp_inicio", "ilike", f"{hoje_cpu}%")\
                            .order("counter_dia", desc=True).execute()
            dados = response.data
            total_real = len(dados)

            dados = dados[:20]

    except Exception as e:
        print(f"Erro ao processar dados: {e}")
        dados = []
        total_real = 0

    return render_template('index.html',
                           detecoes=dados,
                           data_selecionada=data_filtro or hoje_cpu,
                           total=total_real)


@app.route('/atualizar_check/<int:detecao_id>', methods=['POST'])
def atualizar_check(detecao_id):
    try:
        dados = request.get_json(silent=True) or {}
        novo_valor = 1 if dados.get("check") else 0
        
        # Na nuvem, se não houver um utilizador de sistema direto, definimos um fallback
        utilizador = "utilizador_web"

        timestamp_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        supabase.table(SUPABASE_TABLE)\
            .update({
                "check": novo_valor,
                "utilizador_check": utilizador,
                "timestamp_check": timestamp_check,
            })\
            .eq("id", detecao_id)\
            .execute()

        supabase.table("historico_checks").insert({
            "detecao_id": detecao_id,
            "user": utilizador,
            "acao": "check" if novo_valor else "uncheck",
            "timestamp": timestamp_check,
        }).execute()

        return {"sucesso": True, "check": novo_valor, "utilizador": utilizador, "timestamp_check": timestamp_check}, 200
    except Exception as e:
        print(f"Erro ao atualizar check (id={detecao_id}): {e}")
        return {"sucesso": False}, 500


@app.route('/historico_checks/<int:detecao_id>', methods=['GET'])
def historico_checks(detecao_id):
    try:
        response = supabase.table("historico_checks")\
            .select("*")\
            .eq("detecao_id", detecao_id)\
            .order("id", desc=True)\
            .execute()
        return {"sucesso": True, "historico": response.data}, 200
    except Exception as e:
        print(f"Erro ao obter histórico (detecao_id={detecao_id}): {e}")
        return {"sucesso": False, "historico": []}, 500


@app.route('/tabela_atualizada', methods=['GET'])
def tabela_atualizada():
    data_filtro = request.args.get('data')
    hoje_cpu = datetime.now().strftime('%Y-%m-%d')
    alvo = data_filtro if data_filtro else hoje_cpu

    try:
        response = supabase.table(SUPABASE_TABLE)\
            .select("*")\
            .filter("timestamp_inicio", "ilike", f"{alvo}%")\
            .order("counter_dia", desc=True).execute()

        dados = response.data
        total_real = len(dados)
        exibir_dados = dados
    except Exception as e:
        print(f"Erro: {e}")
        exibir_dados = []
        total_real = 0

    return render_template('tabela_parcial.html', detecoes=exibir_dados, total=total_real, data_selecionada=alvo)

