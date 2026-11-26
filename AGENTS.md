# Convenções do LiberaAI

- Escreva identificadores próprios em português brasileiro, sem acentos nem caracteres especiais.
- Use PascalCase nas classes, como `CamaraDeputados` e `DocumentoLegislativo`.
- Use camelCase em funções, métodos, parâmetros, atributos e variáveis, como `buscarProposicao` e `textoOriginal`.
- Use maiúsculas com sublinhados nas constantes, como `MARGEM_CONTEXTO`.
- Dê nomes em português aos arquivos Python, como `cliente.py`, `servico.py` e `configuracao.py`. Os diretórios podem manter os nomes atuais.
- Mantenha `app/main.py` como ponto de entrada do FastAPI e use `app.main:app` na inicialização com Uvicorn.
- Preserve as convenções exigidas pelas bibliotecas e os nomes publicados em contratos, como campos JSON da Câmara, parâmetros do llama-server, opções da CLI e esquema OpenAPI.
- Use UTF-8 e português brasileiro correto nas mensagens, na interface, nos comentários e na documentação. Mantenha textos oficiais, respostas brutas da API e registros da IA como recebidos.
- Use docstrings e comentários para explicar responsabilidades, motivos de validação e decisões técnicas que não estejam claras no código.
- Organize os imports por origem e mantenha a separação entre integração, documentos, análise e interface.
- Nomeie os arquivos de teste com o prefixo `teste_` e as funções de teste com `teste` seguido de uma descrição em camelCase, conforme o `pyproject.toml`.
- Ao renomear um módulo, atualize os imports, testes e comandos documentados. Execute a regressão dos fluxos afetados.
