import os, io, re, json
from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import pdfplumber
import anthropic

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

def extract_pdf(file_bytes):
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
            for table in page.extract_tables():
                for row in table:
                    if row:
                        parts.append(" | ".join(str(c or "") for c in row))
    return "\n".join(parts)

def extract_sheet(file_bytes, filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext == 'csv':
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            for sep in [',', ';', '\t']:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding=enc, sep=sep)
                    if len(df.columns) > 1:
                        return df
                except:
                    pass
    else:
        return pd.read_excel(io.BytesIO(file_bytes))

def build_prompt(bling_text, pagarme_df, redecard_df):
    def df_info(df):
        if df is None:
            return "(não fornecido)"
        return f"Colunas: {list(df.columns)}\nRegistros totais: {len(df)}\nAmostra:\n{df.head(30).to_string()}"

    return f"""Você é especialista em conciliação fiscal brasileira.

Analise os dados abaixo e cruze cada transação (Pagar.me/Redecard) com a nota fiscal correspondente do Bling.

=== BLING (PDF de notas fiscais emitidas) ===
{bling_text[:5000] if bling_text else '(não fornecido)'}

=== PAGAR.ME ===
{df_info(pagarme_df)}

=== REDECARD ===
{df_info(redecard_df)}

Retorne SOMENTE JSON válido, sem markdown:
{{
  "periodo": "período identificado",
  "resumo": "3-4 frases: total processado, % conciliado, principais divergências, recomendações",
  "valor_total_transacoes": 0.00,
  "valor_total_nfs": 0.00,
  "total_nf": 0,
  "total_transacoes": 0,
  "total_conciliados": 0,
  "total_divergencias": 0,
  "itens": [
    {{
      "data": "DD/MM/AAAA",
      "origem": "Pagar.me | Redecard | Bling",
      "cliente": "nome ou null",
      "valor_transacao": 0.00,
      "numero_nf": "NF-000 ou null",
      "valor_nf": 0.00,
      "status": "conciliado | divergencia_valor | sem_nf | sem_transacao",
      "diferenca": 0.00,
      "observacao": "explicação objetiva"
    }}
  ]
}}

Status:
- conciliado: transação + NF com valores iguais (tolerância R$0,01)
- divergencia_valor: ambos existem mas valores diferem
- sem_nf: transação sem NF emitida
- sem_transacao: NF emitida sem transação

Se dados reais forem insuficientes, informe no resumo e crie registros representativos."""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/conciliar', methods=['POST'])
def conciliar():
    api_key = request.form.get('api_key') or os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'API Key da Anthropic não informada.'}), 400

    bling_text = None
    pagarme_df = None
    redecard_df = None

    try:
        if 'bling' in request.files and request.files['bling'].filename:
            bling_text = extract_pdf(request.files['bling'].read())
    except Exception as e:
        return jsonify({'error': f'Erro no PDF do Bling: {e}'}), 400

    try:
        if 'pagarme' in request.files and request.files['pagarme'].filename:
            f = request.files['pagarme']
            pagarme_df = extract_sheet(f.read(), f.filename)
    except Exception as e:
        return jsonify({'error': f'Erro no arquivo Pagar.me: {e}'}), 400

    try:
        if 'redecard' in request.files and request.files['redecard'].filename:
            f = request.files['redecard']
            redecard_df = extract_sheet(f.read(), f.filename)
    except Exception as e:
        return jsonify({'error': f'Erro no arquivo Redecard: {e}'}), 400

    if not any([bling_text, pagarme_df is not None, redecard_df is not None]):
        return jsonify({'error': 'Nenhum arquivo válido enviado.'}), 400

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model='claude-opus-4-5',
            max_tokens=4096,
            messages=[{'role': 'user', 'content': build_prompt(bling_text, pagarme_df, redecard_df)}]
        )
        raw = msg.content[0].text
        raw = re.sub(r'```json\s*|```', '', raw).strip()
        return jsonify(json.loads(raw))
    except json.JSONDecodeError:
        return jsonify({'error': 'Erro ao interpretar resposta da IA.', 'raw': raw[:300]}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/exportar', methods=['POST'])
def exportar():
    itens = request.json.get('itens', [])
    if not itens:
        return jsonify({'error': 'Sem dados'}), 400
    df = pd.DataFrame(itens).rename(columns={
        'data':'Data','origem':'Origem','cliente':'Cliente',
        'valor_transacao':'Vl. Transação (R$)','numero_nf':'Nº NF',
        'valor_nf':'Vl. NF (R$)','status':'Status',
        'diferenca':'Diferença (R$)','observacao':'Observação'
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='Conciliação')
        ws = w.sheets['Conciliação']
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(
                max(len(str(c.value or '')) for c in col) + 4, 45)
    buf.seek(0)
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='conciliacao_nf.xlsx')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
