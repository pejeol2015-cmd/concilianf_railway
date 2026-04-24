# ConciliaNF

Sistema web de conciliação de notas fiscais entre **Bling**, **Pagar.me** e **Redecard**.

---

## Deploy no Railway (5 minutos, grátis)

### 1. Crie uma conta
Acesse https://railway.app e faça login com GitHub.

### 2. Suba o código no GitHub
```bash
git init
git add .
git commit -m "ConciliaNF inicial"
# Crie um repositório no github.com e copie a URL
git remote add origin https://github.com/SEU_USUARIO/concilianf.git
git push -u origin main
```

### 3. Deploy no Railway
1. No Railway, clique em **New Project → Deploy from GitHub repo**
2. Selecione o repositório `concilianf`
3. O Railway detecta automaticamente e faz o build

### 4. Variável de ambiente (opcional)
No Railway → seu projeto → **Variables**, adicione:
```
ANTHROPIC_API_KEY = sk-ant-...
```
Se não adicionar aqui, o campo aparece na interface para digitar a cada uso.

### 5. Acesse
No Railway → **Settings → Domains** → clique em **Generate Domain**.
Você recebe uma URL tipo: `https://concilianf-production.up.railway.app`

---

## Uso

1. Acesse a URL gerada pelo Railway
2. Faça upload dos 3 arquivos:
   - **Bling** → PDF do relatório de NFs emitidas
   - **Pagar.me** → CSV ou XLSX de transações
   - **Redecard** → XLSX ou CSV de transações
3. Informe sua API Key da Anthropic (se não configurou no Railway)
4. Clique em **Analisar conciliação**
5. Filtre os resultados e exporte em XLSX

---

## Status de conciliação

| Status | Significado |
|---|---|
| ✅ Conciliado | Transação e NF com valores iguais |
| ⚠️ Divergência de valor | Ambos existem mas valores diferem |
| ❌ Sem NF | Venda recebida sem nota emitida |
| ○ NF sem transação | Nota emitida sem recebimento |
