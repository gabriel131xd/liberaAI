# LiberaAI

Backend acadêmico voltado à transparência legislativa brasileira e à Meta 16.6 da ONU. O objetivo do projeto é permitir que cidadãos consultem propostas federais e estaduais e compreendam seu conteúdo em linguagem simples, com referência ao documento oficial.

## Etapa 01

A aplicação oferece a rota de saúde e a documentação interativa do FastAPI. O MVP prevê Bahia e Pernambuco, somente nas esferas estadual e federal, com consulta pública sem contas e inferência local. Integrações legislativas, explicações por IA e interface de consulta pertencem a etapas posteriores. A configuração inicial dispensa banco, cache, credenciais e arquivo de ambiente.

## Ambiente no Windows

Use PowerShell na raiz do projeto, com uv e CPython 3.12. A versão testada foi 3.12.14. O uv pode obter o interpretador se necessário.

```powershell
uv venv --python 3.12.14 .venv
.\.venv\Scripts\Activate.ps1
uv sync --locked
```

Em uma instalação existente, basta sincronizar com `uv sync --locked`. A ativação é opcional ao chamar o executável da .venv diretamente.

## Execução e testes

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra [Swagger UI](http://127.0.0.1:8000/docs). Em outro terminal na raiz, consulte a saúde e execute os testes.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
.\.venv\Scripts\python -m pytest -q
```

A resposta JSON esperada é `{"status":"ok"}`. Encerre o servidor com Ctrl+C.

## Kernel Jupyter

```powershell
$env:IPYTHONDIR = "$PWD\.venv\ipython"
$env:JUPYTER_RUNTIME_DIR = "$PWD\.venv\jupyter-runtime"
.\.venv\Scripts\python -m ipykernel install --sys-prefix --name liberaai --display-name "Python (LiberaAI)"
```

Em um editor com suporte a Jupyter, escolha o interpretador da .venv. Clientes que usam o prefixo desse ambiente também podem selecionar o kernel **Python (LiberaAI)**. O projeto instala apenas o suporte ao kernel nesta etapa.

## Organização e dependências

- `app/main.py` contém o aplicativo FastAPI e o modelo de resposta Pydantic.
- `app/core/configuracao.py` carrega os metadados de inicialização.
- `tests/teste_saude.py` verifica o ciclo de vida, a saúde e a documentação usando Pytest e HTTPX.
- `docs/` e `notebooks/` reservam espaço para documentação técnica e exploração futura.
- `pyproject.toml` declara dependências de execução e desenvolvimento. O servidor é Uvicorn.
- `uv.lock` registra as versões resolvidas para reproduzir a instalação.

## Etapa 02 · Câmara dos Deputados

O módulo `app/integrations/camara/cliente.py` consulta proposições, detalhes, autores, tramitações e temas da API oficial. HTTPX integra as dependências de execução. Consulte os campos, exemplos e limitações no [relatório da integração](docs/camara_api.md).

Na raiz do projeto, execute a suíte local ou selecione explicitamente a consulta real (requer acesso à Câmara).

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m pytest -m live -qs -p no:cacheprovider
```

## Etapa 03 · IA local

Em PowerShell, na raiz do projeto, execute o servidor em um terminal dedicado. O arquivo `.env` define os caminhos do binário e do GGUF, a porta na URL de loopback, o contexto, o timeout e a geração. Em outra máquina, copie `.env.example` para `.env` e ajuste os caminhos. Caminhos relativos partem da raiz do projeto. O binário portátil e suas DLLs ficam juntos. O FastAPI tem inicialização independente.

```powershell
.\.venv\Scripts\python -m app.ai.cliente serve
```

Em outro terminal, confira o modelo e inicie a leitura manual. Cole o texto, inclusive com várias linhas, e termine com um ponto sozinho em uma linha. Use o cliente Python para aplicar o prompt do experimento. O chat nativo permite testar instruções próprias.

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
(Invoke-RestMethod http://127.0.0.1:8080/v1/models).data
Start-Process http://127.0.0.1:8080/
.\.venv\Scripts\python -m app.ai.cliente
```

Encerre com Ctrl+C no terminal do servidor. Para repetir o experimento, inicie o servidor e execute o comando abaixo. São feitas três buscas de ementas na Câmara e sete gerações em loopback. O registro original está em [resultados da Etapa 03](docs/experimento_local.jsonl).

```powershell
.\.venv\Scripts\python -X utf8 -m app.ai.experimento
```

## Etapa 04 · Documentos oficiais

Execute `uv sync --locked` e consulte um PDF pelo identificador oficial da proposição. Use `--pagina 3` para selecionar uma página e `--bruto` para conferir a camada textual original.

```powershell
.\.venv\Scripts\python -X utf8 -m app.documents --id 380852 --pagina 3
```

O [relatório de extração](docs/extracao_documentos.md) reúne as cinco peças, as comparações visuais, os limites de qualidade e os comandos de testes.
`--referencias` lista documentos de tramitação, proposições relacionadas e o avulso indicado na ficha oficial antes de recorrer à ementa.

## Etapa 05 · Explicação documental local

Com o llama-server em execução, consulte a peça com o Python da .venv. A saída JSON separa a ficha da proposição, a identificação e o hash da fonte, as gerações por parte e a explicação de cada seção. O serviço importável é `app.analysis.servico.analisarProposicao`. A interface aceita a peça principal, uma proposição relacionada por ID, `movimento:N` pela sequência oficial ou `avulso:N` pela posição na ficha atual. Use o catálogo da Etapa 04.1 para identificar a fonte. Cada análise usa uma única peça. Escolher duas peças requer duas análises independentes.

```powershell
.\.venv\Scripts\python -m app.ai.cliente serve
# Em outro terminal
.\.venv\Scripts\python -X utf8 -m app.documents --id 253500 --referencias
.\.venv\Scripts\python -X utf8 -m app.analysis --id 253500 --peca 2443615 --inicio 1 --fim 1 --secao "Substitutivo do Senado"
.\.venv\Scripts\python -X utf8 -m app.analysis --id 380852 --peca 2418402 --secao "Redação final da Câmara"
.\.venv\Scripts\python -X utf8 -m app.analysis --id 2434493 --peca 2434493 --inicio 10 --fim 10 --secao "Justificativa com citações atribuídas a terceiros"
```

Para guardar resultados, acrescente `--registro caminho.json`. Uma consulta ambígua exige escolher a versão. Em avulsos compostos, confira o intervalo exato no PDF e informe a seção. O serviço sinaliza páginas fora do recorte e páginas ilegíveis. Na ausência de texto, a ementa fica disponível quando a pesquisa não identifica alternativas ou quando o avaliador, após verificar as referências, registra a razão pela qual nenhuma é adequada em `--motivo-ementa`. Indisponibilidade de rede deixa a consulta pendente.

O orçamento é calculado sobre as mensagens renderizadas por `/apply-template` e tokenizadas em `/tokenize` com reconhecimento de tokens especiais. Com contexto de 4096, reserva de 1024 tokens de saída (incluindo raciocínio) e margem de 8, o teto de entrada é 3064 tokens incluindo instruções e marcadores de página. Uma unidade indivisível acima do limite ou falha da geração deixa a análise incompleta. Partes previamente concluídas ficam no registro. A consolidação combina pares de respostas da mesma seção, repetindo a contagem em cada rodada, até obter uma explicação por seção. A cobertura indica processamento técnico da camada textual; a avaliação de significado requer leitura humana.

## Etapa 06 · Interface experimental em Gradio

Execute o servidor local de IA e abra outro terminal para a interface:

```powershell
.\.venv\Scripts\python -m app.ai.cliente serve
.\.venv\Scripts\python -X utf8 -m app.interface.painel
```

Acesse [LiberaAI](http://127.0.0.1:7860/). As abas **Deputados** e **Por ano** carregam a primeira página ao abrir. Use **Anterior** e **Próxima** para navegar. O [guia de avaliação](docs/interface_experimental.md) reúne os passos e os registros da interface experimental.

## Etapa 07 · Refinamento da IA local

Após abrir uma proposição, acesse o **Laboratório de IA**, carregue uma peça e abra **Comparação experimental de instruções** para executar a v1 e a v2 sobre o mesmo recorte. O [relatório de refinamento](docs/refinamento_ia.md) reúne as saídas integrais, métricas e limites da conferência.

## Etapa 08 · Visão do cidadão

Clique em **Ver detalhes** em **Início**, **Deputados** ou **Por ano**. A tela exibe os dados oficiais, os links e o histórico enquanto a IA local prepara **Entenda esta proposta**. Use as perguntas sugeridas ou envie uma pergunta com **Enviar** ou **Enter**. O **Laboratório de IA** reúne a seleção manual de peças, recortes e comparação de instruções.
