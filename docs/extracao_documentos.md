# Extração de documentos da Câmara · 25/11/2026

## Recuperação e proveniência

O comando consulta o detalhe com `CamaraDeputados`, confere o ID e usa o campo oficial `urlInteiroTeor`. O resultado mantém o detalhe original, inclusive o número e o ano, separado do download e das medidas calculadas. A referência de inteiro teor comprova a associação da peça ao projeto. A versão legislativa ficou **não confirmada nos cinco casos**. Data de recuperação, destino final, Content-Type, tamanho e SHA-256 descrevem a cópia consultada. O hash permite comparar bytes em consultas futuras, sem atestar assinatura digital ou vigência.

Os movimentos com URL foram contados separadamente. Para os IDs 253500, 380852, 510035, 2434493 e 2256735, respectivamente, foram 167, 38, 33, 10 e 53 registros. Exemplos de codteor distintos do documento principal foram 222980, 534420, 945342, 2432177 e 1910545. A existência de outra peça em um movimento não determina seu tipo ou se ela substituiu o texto apresentado. [Detalhe oficial de exemplo](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500) · [Histórico correspondente](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500/tramitacoes)

## Amostra de documentos

Todos retornaram PDF. Os tempos são de uma execução do serviço, incluindo a consulta ao detalhe, transferência e extração. Cada link abaixo é o destino final observado. Caracteres são a soma das páginas brutas, sem o separador artificial entre páginas.

| Projeto e ID | Bytes | Páginas | Caracteres | Palavras | Tokens estimados | Segundos |
|---|---:|---:|---:|---:|---:|---:|
| [PL 2597/2024 · 253500](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=1279376) | 1410384 | 23 | 0 | 0 | indeterminado | 1,15 |
| [PL 411/2024 · 380852](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=531477) | 38572 | 6 | 19267 | 2828 | 4817 | 0,59 |
| [PL 934/2024 · 510035](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=891953) | 372962 | 44 | 93459 | 12759 | 23365 | 1,76 |
| [PL 1904/2024 · 2434493](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2425262) | 276955 | 19 | 47255 | 7066 | 11814 | 0,67 |
| [PL 2630/2020 · 2256735](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=1909983) | 199050 | 14 | 35323 | 5268 | 8831 | 0,64 |

| ID | SHA-256 |
|---|---|
| 253500 | 6198dd2146db25e07dac373459229a1636e9e37748261f34e62ed18aec06c50b |
| 380852 | 6b749381a25b2d61f37a2c69f2f2b27ae19b426611052147e505adb3d0a974a2 |
| 510035 | 5265f4d3a46ffd2bd4f093056ec9bce2849dc9403572fb94a4176ba8ea13a0ab |
| 2434493 | e75e4ddf35f5965cca65ec130047ed4d560cd9bb41878c2d868ef34ff2bcd732 |
| 2256735 | 0247dc39eb7ed949e3c4722dc8c3428eaf62ad4d0fa375b5a0c95fa06c1aea7b |

## Conferência visual

Foram comparados recortes renderizados da primeira página, de uma intermediária e da última de cada original com sua camada textual. A tabela apresenta fragmentos curtos, com espaços de diagramação desconsiderados para leitura. A inspeção é amostral.

| Projeto | Páginas | Original visível, na ordem das páginas | Resultado na extração |
|---|---|---|---|
| PL 2597 | 1, 12, 23 | “DISPOSIÇÕES GERAIS”, “Cabe à seguradora executar a regulação e a liquidação do sinistro”, “Recebidas as contribuições” | Texto vazio nas três e nas demais 20 páginas. A imagem é legível. |
| PL 411 | 1, 3, 6 | “não se consideram”, “Art. 14)”, “abandono dos idosos” | Mesmas expressões. A exceção da primeira página inclui “8 idosos”. A última usa itálico, distinção visual perdida no texto simples. |
| PL 934 | 1, 22, 44 | “prioridade epidemiológica”, “sub-aguda ou crônica”, “McGraw-Hill, 1994.” | Mesmas expressões. O documento combina artigos, exposição técnica e bibliografia. O rodapé institucional se repete e foi preservado. |
| PL 1904 | 1, 10, 19 | “dois parágrafos ao artigo”, “violência psicológica”, “Dep. Eli Borges (PL/TO)” | Mesmas expressões. Na p. 10, quebras dividem uma citação em negrito. Na p. 19, há signatários. |
| PL 2630 | 1, 7, 14 | “DISPOSIÇÕES PRELIMINARES”, “IX – dados relacionados”, “Senador Davi Alcolumbre” | Mesmas expressões. A numeração do inciso e a identificação do signatário permaneceram legíveis. |

## Estratégia e limites

- **Download.** HTTPX em memória, timeout de 30 segundos por operação e teto padrão de 20 MiB aplicado também durante a leitura. Apenas HTTPS no host exato www.camara.leg.br, com validação TLS e de cada salto. O comando aceita ID. Exige resposta 200, tipo PDF ou binário genérico, assinatura PDF e abertura pelo parser. A validação identifica HTML inesperado, arquivos vazios, corrompidos e falhas HTTP ou de transporte.
- **Extração.** PyMuPDF 1.28.2, executado no Python 3.12 do projeto, permite renderização e leitura por página. Licença dual GNU AGPL v3 ou comercial da Artifex, conforme os metadados do pacote instalado. A faixa 1.x mantém a instalação restrita ao leitor necessário. [Documentação do PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)
- **Texto bruto e tratado.** O bruto mantém a ordem interna dos objetos de texto, que pode divergir da ordem visual. O tratado uniformiza apenas finais de linha. Espaços repetidos, hifens no fim da linha, palavras partidas entre páginas, artigos, títulos, cabeçalhos e rodapés permanecem disponíveis. As páginas têm numeração a partir de 1 e a representação conjunta usa quebra de página. Sem uma fronteira confiável, a divisão em dispositivos, justificativa, anexos e assinaturas exige conferência humana. Citações na justificativa não devem ser apresentadas como obrigações propostas.
- **Qualidade.** Páginas vazias, caracteres de substituição ou controle, falha de extração por página e reparo estrutural recebem avisos. Texto em todas as páginas não comprova cobertura de imagens, tabelas, símbolos, ordem de colunas ou formatação. A conferência dos trechos acima não certifica o restante do documento.
- **Contexto.** A aproximação usa quatro caracteres por token e arredonda para cima. É uma heurística sem tokenização do LFM2.5. Nos quatro textos legíveis a estimativa excede 4.096, antes de reservar espaço para instruções e resposta. No PDF sem texto a necessidade de contexto permanece desconhecida. O serviço entrega todas as páginas recuperadas.

## Execução em PowerShell

Na raiz, sincronize a dependência registrada no lock. O primeiro comando de consulta abaixo mostra todas as páginas. O segundo mostra a página solicitada em modo bruto. Os bytes e textos ficam em memória durante a execução.

```powershell
uv sync --locked
.\.venv\Scripts\python -X utf8 -m app.documents --id 380852
.\.venv\Scripts\python -X utf8 -m app.documents --id 380852 --pagina 3 --bruto
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m pytest -m live -qs -p no:cacheprovider
```

## Complemento de 25/11/2026 · Avulsos e peças relacionadas

A ausência de camada textual no codteor 1279376 aplica-se somente àquele arquivo. A extração em memória do [avulso indicado pelo avaliador](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2459135) retornou 72 páginas, 994.989 bytes, 145.074 caracteres e 22.685 palavras. SHA-256: fa445216ba59d7dff97d3bc7b93bd756467fed9d0916443c96ac44f6b1a0a9f5.

| Páginas físicas do PDF | Identificação e evidência |
|---|---|
| 1 | Capa e sumário do PL 2597-D/2024. O índice atribui o primeiro texto à aprovação na Câmara em 04/04/2017. |
| 2–46 | Autógrafo do projeto aprovado na Câmara, anteriormente PL 3555/2004. O fim da p. 46 identifica o relator. |
| 47 | Referências do CEDI à legislação citada e identificação de autenticação da EMS. |
| 48–71 | Substitutivo do Senado. A p. 48 traz “Substitua-se o Projeto pelo seguinte” e a numeração interna começa em 1 de 24. A p. 71 traz 24 de 24 e a identificação do presidente do Senado. |
| 72 | Encerramento editorial. |

**Como encontrar.** O detalhe, as 336 relacionadas e os 325 movimentos do projeto consultados não continham literalmente o código 2459135. A [ficha oficial](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=253500) expunha o link identificado como “Avulsos” para o codteor 2814996. Seu hash foi 18c05620dbf38ee535bd14a6acc5d4da39feb6932645949da6b8f224d368e1d0. A comparação do texto por página, ignorando diferenças de espaço em branco, identificou diferença apenas na capa. Essa comparação é textual e se refere aos arquivos obtidos nesta data. Não foi confirmado um caminho atual que reconstrua o código histórico exato sem a referência fornecida.

A API oferece um caminho direto às peças individuais. A [lista de relacionadas](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500/relacionadas) fornece IDs e tipos. Consulte o detalhe da relacionada pelo seu próprio ID e leia seu urlInteiroTeor. A EMS 2443615 levou ao codteor 2443176, também indicado na movimentação de apresentação de 26/06/2024. O PDF individual retornou 24 páginas e 62.803 caracteres. O ofício de recebimento da mesma data aponta para outro arquivo. O movimento 361 menciona publicação em avulso, mas seu link respondeu HTML ao downloader. A descrição do evento, por si, não identifica o formato ou o papel do anexo. [Tramitações](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500/tramitacoes)

| Projeto | ID da relacionada e tipo | Documento individual testado | Extração |
|---|---|---|---|
| PL 2597/2024 | 2127931 · RDF | [1540988](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=1540988) | 45 páginas, 64.555 caracteres |
| PL 2597/2024 | 2470688 · RDF | [2824001](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2824001) | 46 páginas, 77.598 caracteres |
| PL 411/2024 | 2418402 · RDF | [2388635](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2388635) | 2 páginas, 2.801 caracteres |
| PL 934/2024 | 2128317 · SBE-A | [1542323](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=1542323) | 1 página, 582 caracteres |

**Regra para a Etapa 05.** Identificar a peça adequada à pergunta por origem, tipo, evento e data. Registrar projeto, ID da peça, URL, hash e páginas. Diante de um avulso composto, usar exclusivamente o intervalo confirmado da versão escolhida ou o documento individual. Diante de versões ambíguas, pedir a escolha ou sinalizar a incerteza. A extensão do arquivo ou a presença de texto não decide a versão. Uma falha de rede deixa a busca pendente. Somente após investigar as alternativas e constatar que nenhuma peça adequada pôde ser recuperada cabe usar a ementa, com a indicação “Explicação limitada à ementa; a peça legislativa adequada não pôde ser recuperada”. O catálogo não dispara inferência.

Na raiz, execute `python -m app.documents --id 253500 --referencias` com o Python da .venv. A listagem usa duas consultas de API e uma leitura pontual do link rotulado na ficha, sem baixar os documentos da lista. Para inspecionar uma peça individual, use o ID retornado com `--pagina`.
