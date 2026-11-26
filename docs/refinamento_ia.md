# Etapa 07 · Refinamento da IA local

## Diagnóstico e desenho

Os registros anteriores mostram três problemas. A explicação do PL 411 generalizou os 180 dias para toda a redação. O chat do PL 2597 acrescentou um critério de desempate e confundiu cedente e cessionária. Na justificativa do PL 1904, a proximidade entre argumentação e citações favoreceu a leitura de afirmações fora de contexto. O limite de palavras do prompt anterior competia com a preservação das condições. Na consolidação, o modelo podia herdar omissões das explicações parciais.

- A **v1** conserva as instruções anteriores de simplificação, análise, consolidação e chat. O Gradio compara as instruções documentais v1 e v2 sobre a mesma peça e o mesmo recorte.
- A **v2** orienta a identificação prévia de sujeitos, ações, permissões, obrigações, proibições, valores, prazos, condições e exceções. Na análise documental e no chat, o llama-server restringe o formato a pontos com explicação, página e citação literal. A explicação e a evidência saem da mesma inferência.
- A conferência determinística sinaliza páginas, citações e números incompatíveis com o texto e possíveis perdas de prazos, condições e alternativas. É uma triagem lexical. O Gradio mantém as respostas sinalizadas em **Explicações detalhadas por parte** e pede revisão do original. No chat, falhas de evidência geram uma indicação de insuficiência com o link oficial.
- Artigos que atravessam páginas continuam juntos. Cada seção mantém suas fontes para conferência na consolidação. O tokenizador local mede as mensagens renderizadas antes de cada chamada. Unidades acima do contexto e respostas incompletas são sinalizadas.
- Autoria, situação, apresentação, data registrada no status e votações reconhecidas são respondidas pelos dados da Câmara. Perguntas sobre o prazo de vigência previsto na peça seguem para o texto documental. Para perguntas de conteúdo, a evidência vem da peça atual.

As instruções estão em [app/ai/instrucoes.py](../app/ai/instrucoes.py), e o ramo documental v1 está em [app/analysis/processamento.py](../app/analysis/processamento.py).

## Comparação com as peças oficiais

Os três PDFs tinham o mesmo SHA-256 dos registros anteriores. Reutilizei os rótulos e recortes documentais. Cada caso abaixo consumiu uma inferência. O tempo interno soma a avaliação do prompt e a geração reportadas pelo servidor.

| Caso e recorte | Tokens de entrada → saída v1 / v2 | Tempo interno v1 → v2 | Resultado técnico da leitura |
|---|---|---:|---|
| [PL 411/2024, RDF, pp. 1–2](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2388635) | 1069→327 / 1259→237 | 58,94 → 48,75 s | A v1 generalizou os 180 dias. A v2 explicou a permissão de adquirir equipamentos e medicamentos, mas omitiu a vigência e outras condições e apresentou uma citação alterada. A conferência final sinalizou a ausência de 180 dias na explicação. |
| [PL 2597/2024, EMS, p. 1](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2443176) | 759→301 / 949→214 | 51,91 → 44,08 s | A v1 atribuiu à peça a substituição da LC 126/2007. A v2 resumiu os requisitos do caput do art. 3º a “sem autorização” e omitiu a responsabilidade da cedente diante da insolvência da cessionária e o prazo de 24 meses. |
| [PL 1904/2024, justificativa, p. 10](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2425262) | 947→408 / 1137→522 | 69,69 → 89,79 s | A v1 classificou a seção como justificativa, mas citou uma página fora do recorte. A v2 citou a p. 10, mas mudou o sentido da passagem sobre o que a recomendação caracterizava como violência institucional. |

No **chat do PL 2597**, a saída v2 identificou a cedente como responsável, preservou a alternativa temporal e retirou “o que for menor”. Ainda atribuiu a solidariedade à parte errada e inseriu reticências na evidência. A interface reteve a resposta e mostrou o link oficial. Tempo total de 49,7 s na resposta anterior e 54,3 s na v2. A v2 usou 969 tokens de entrada e 247 de saída.

No **caso fictício adicional**, a v2 preservou a permissão de abrir aos domingos, a presença de servidor, a proibição de cobrança e a exceção de feriados. A resposta repetiu informações. Usou 395 tokens de entrada, 375 de saída e 56,67 s de tempo total.

O [registro final](refinamento_final.jsonl) contém as respostas novas integrais em `resposta_bruta` e indica os arquivos anteriores. `conferencia_final` reaplica as regras finais aos mesmos recortes e hashes. O [piloto](refinamento_piloto.jsonl) preserva o ensaio inicial em texto livre, que atingiu 1.024 tokens com geração incompleta. O formato estruturado encerrou os três recortes reais e o caso fictício, com variação de tempo e de cobertura. Os resultados ainda não sustentam melhora semântica geral.

## Desempenho e reprodução

Foram mantidos temperatura 0,1, top-k 50, penalidade de repetição 1,1, contexto 4.096, reserva de saída 1.024 e orçamento de raciocínio 96. Foram feitas cinco inferências finais, uma por caso. O conjunto de trabalho do processo do servidor foi de aproximadamente 1,78 GiB antes e 1,88 GiB depois da rodada. São observações do processo em dois momentos. O pico por chamada ficou sem medição.

```powershell
.\.venv\Scripts\python -m app.ai.cliente serve
# Em outro terminal
.\.venv\Scripts\python -X utf8 -m app.interface.painel
.\.venv\Scripts\python -X utf8 -m app.ai.avaliacao --registro docs/novo_ensaio_ia.jsonl
```

No Gradio, pesquise a proposição, carregue a peça e indique o recorte. Para o PL 411, use a RDF de ID 2418402, páginas 1 e 2. Abra **Comparação experimental de instruções** e clique em **Comparar versões na peça e no recorte atuais**. Confira as duas respostas, o hash, as páginas e os tempos. Compare o art. 3º com os dois marcos de vigência. Na EMS do PL 2597, confira sujeito, destinatário, insolvência e os 24 meses. Na p. 10 do PL 1904, verifique quem fez cada afirmação e a que ela se refere.

Passaram 75 testes locais e seis testes reais de regressão da Câmara. O fluxo de comparação também foi exercitado na interface Gradio servida por HTTP, com inferência simulada para verificar a entrega das duas versões e dos metadados. As medições da tabela vieram da execução separada com o modelo real.
