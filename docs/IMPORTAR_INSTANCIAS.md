# Importar instâncias Evolution de um CSV

Para exibir no MassFlow as instâncias que já estão conectadas na Evolution API (por exemplo, as que você tem no projeto devocional), use o script de importação.

## 1. Preparar o CSV

Coloque o arquivo CSV na pasta `backend/` ou na raiz do projeto (`MassFlow/instancias.csv`). O arquivo **não** é commitado (está no `.gitignore`) para não expor API keys. Exemplo de formato:

| name       | instance_name  | api_url                                      | api_key   | status    |
|------------|----------------|----------------------------------------------|-----------|-----------|
| MotriG - 01 | assistente-01  | https://motrig-evolution-api.easypanel.host  | sua_chave | connected |
| MotriG - 02 | assistente-02  | https://motrig-evolution-api.easypanel.host  | sua_chave | connected |

- **name**: nome de exibição na UI (ex.: "MotriG - 01")
- **instance_name**: nome da instância na Evolution API (ex.: "assistente-01")
- **api_url**: URL base da Evolution API
- **api_key**: chave da API
- **status**: opcional; ex.: `connected`

Se o CSV tiver só a coluna `name` (sem `instance_name`), o script usa `name` tanto para exibição quanto para o nome na Evolution.

Há um exemplo em `backend/instancias.exemplo.csv`.

## 2. Descobrir o ID do tenant

O tenant é a organização/conta com a qual você fez login. Para importar para a **sua** conta, use o **tenant_id** dessa conta. Você pode obter no banco (tabela `tenants`, coluna `id`) ou, se souber o slug da sua organização, use `--tenant-slug`.

## 3. Rodar o script (local)

Na pasta **backend**, com o ambiente Python do projeto ativo (venv com `pip install -r requirements.txt`) e o `.env` configurado (mesma `DATABASE_URL` do MassFlow):

```bash
# Por ID do tenant (ex.: 1)
python -m app.scripts.import_instances_csv instancias.csv --tenant-id 1

# Ou por slug do tenant
python -m app.scripts.import_instances_csv instancias.csv --tenant-slug meu-tenant
```

Instâncias duplicadas (mesmo tenant + mesmo `name` Evolution + mesmo `owner`) são ignoradas.

## 4. No Easypanel (produção)

Se o banco do MassFlow estiver só no servidor, você pode:

1. **Opção A:** Rodar o script **localmente** apontando o `.env` para a `DATABASE_URL` do banco em produção (se o PostgreSQL permitir conexão externa).
2. **Opção B:** Entrar no container do backend no Easypanel (shell) e rodar o script lá, depois de copiar o CSV para dentro do container (ou montar um volume com o CSV).

Exemplo no container (após copiar o CSV para `/app/instancias.csv`):

```bash
cd /app
python -m app.scripts.import_instances_csv instancias.csv --tenant-id 1
```

## 5. Ver no MassFlow

Depois da importação, faça login no MassFlow e acesse **Instâncias**. A lista é carregada da API (`GET /api/instances`) e mostrará as instâncias importadas para o seu tenant.
