# 💰 Fiel Finance — Controle Financeiro Pessoal

Painel financeiro pessoal em Python (Streamlit): contas, categorias, transações,
importação de extrato (CSV/OFX), leitura do QR code de cupons fiscais (NFC-e) e
um assistente de chat opcional via API da Anthropic.

### Leitura de QR code de cupom fiscal

Na aba **Transações**, o botão "Ler QR code do cupom" permite fotografar (ou enviar
uma imagem) do QR code de uma NFC-e. Sempre que o portal da Sefaz do estado emissor
usar o layout compartilhado por vários estados, cada item da nota é importado como
uma despesa separada; caso o portal não seja compatível ou esteja indisponível, o
valor total (ou um formulário manual) é usado como alternativa.

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run cofre_app.py
```

Os dados ficam salvos em `cofre_data.json`, na mesma pasta do app.

### Configuração opcional (senha e assistente de IA)

Copie o arquivo de exemplo e preencha com seus próprios valores:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

- `APP_PASSWORD`: se definida, o app exige essa senha antes de mostrar qualquer dado.
  Sem ela, o app abre direto (recomendado só para uso 100% local).
- `ANTHROPIC_API_KEY`: habilita a aba "Assistente" (chat sobre seus próprios dados).
  Sem ela, o resto do app funciona normalmente.

`.streamlit/secrets.toml` já está no `.gitignore` — nunca é enviado ao repositório.

## Publicando no Streamlit Community Cloud

1. Suba este repositório para o GitHub (veja abaixo).
2. Em [share.streamlit.io](https://share.streamlit.io), crie um novo app apontando
   para `cofre_app.py` neste repositório.
3. Em **App settings → Secrets**, cole o conteúdo do seu
   `.streamlit/secrets.toml` preenchido (pelo menos `APP_PASSWORD`).

> **Importante:** o Streamlit Community Cloud roda uma única instância do app.
> Isso significa que **todos os visitantes da URL pública compartilham o mesmo
> `cofre_data.json`** — não há isolamento por usuário. A senha (`APP_PASSWORD`)
> impede acesso não autorizado, mas não separa dados entre sessões. Use este
> deploy como seu painel pessoal (com a senha configurada), não como um serviço
> multiusuário. O sistema de arquivos do Streamlit Cloud também é efêmero: um
> redeploy ou reinício do app pode apagar `cofre_data.json` — para dados que
> você não quer perder, faça backups periódicos do arquivo.

## Publicando o repositório no GitHub

```bash
git init                     # já feito, se você seguiu este guia
git add .
git commit -m "Fiel Finance — controle financeiro pessoal"
git branch -M main
git remote add origin https://github.com/<seu-usuario>/<seu-repo>.git
git push -u origin main
```

Ou, com o GitHub CLI instalado (`gh`):

```bash
gh repo create <seu-repo> --private --source=. --remote=origin --push
```

## Estrutura

- `cofre_app.py` — aplicação Streamlit (única aplicação do projeto).
- `requirements.txt` — dependências Python.
- `.streamlit/config.toml` — tema visual.
- `.streamlit/secrets.toml.example` — modelo de configuração (não é o arquivo real).
- `cofre_data.json` — dados do usuário, gerado automaticamente na primeira execução (não versionado).
