# Interface experimental · Etapas 06 a 08

A interface roda em loopback com Gradio 6.32.0. O llama-server atende as explicações documentais e as perguntas sobre conteúdo. Pesquisa, navegação, texto extraído e respostas oficiais do chat funcionam independentemente da inferência.

## Avaliação manual

Use dois terminais PowerShell na raiz do projeto. Se o llama-server já estiver saudável, use a instância existente.

```powershell
.\.venv\Scripts\python -m app.ai.cliente serve
```

```powershell
.\.venv\Scripts\python -X utf8 -m app.interface.painel
```

Abra [a interface](http://127.0.0.1:7860/). Se essa porta pertencer a uma instância anterior, use outra porta na sessão atual e informe o novo número no navegador.

```powershell
$env:LIBERAAI_GRADIO_PORT = "7861"
.\.venv\Scripts\python -X utf8 -m app.interface.painel
```

1. Em **Início**, pesquise PL 411/2026. Clique em **Ver detalhes** para conferir situação, autoria, data, links e histórico. Aguarde **Entenda esta proposta**. Use uma pergunta sugerida e experimente perguntar sobre a proposta com **Enter** ou **Enviar**.
2. Em **Deputados**, a primeira página mostra automaticamente os parlamentares em exercício. Para buscar um período anterior, informe 2007 no ano de exercício, digite Pepe Vargas e use a lupa. Selecione o cartão do parlamentar e ajuste o ano da numeração para 2007. As proposições abrem ao selecionar o deputado ou alterar os filtros. Na aba **Por ano**, a seção **Filtrar e contar por autor** mantém a contagem para todos os tipos e situações.
3. Em **Por ano**, a primeira página abre com o ano atual. Altere o ano para 2024 e use **Anterior** e **Próxima**. As opções de tipo e situação são carregadas da Câmara. A lista acompanha as mudanças de filtro e cada item abre o mesmo detalhe compartilhado. O ano de numeração e a data original de apresentação aparecem separadamente. O filtro de situação pode deixar uma página com menos de cinco itens após a conferência no detalhe.
4. Abra o PL 2597/2024. Confira o aviso sobre versões diferentes e os links oficiais. Para comparação técnica, alterne para **Laboratório de IA**, escolha a EMS de ID 2443615, carregue a peça, escolha página 1 a 1 e informe “Substitutivo do Senado” como seção. Compare o § 2º com a explicação gerada.
5. Abra o PL 1904/2024. Compare as explicações com os dispositivos propostos e verifique onde começa a justificativa. Na visão do cidadão, trocar de proposição limpa a explicação e o chat. No laboratório, **Atualizar dados oficiais** refaz a consulta e mudar a peça ou o recorte limpa a explicação e a conversa.

## Seleção e conferência na visão do cidadão

O fluxo automático usa o inteiro teor indicado pela Câmara quando as referências consultadas permitem identificar uma única versão. Versões concorrentes, referências incompletas e peças compostas sem recorte seguro ficam sinalizadas, com acesso à ficha oficial. O fluxo usa a ementa somente quando a seleção documental identifica que nenhuma peça textual adequada está disponível. Quando há um cabeçalho reconhecível de justificação após os dispositivos, a explicação e a conversa usam os dispositivos e a interface indica essa escolha.

O tokenizador local mede o texto com as instruções de conversa. Documentos que excedem o contexto recebem um recorte de páginas inteiras e um aviso de cobertura. A conferência da Etapa 07 verifica a página, a evidência literal, números e sinais de omissão. Campos sinalizados ficam ocultos e a confirmação semântica depende da leitura humana. A situação de vigência parte do registro oficial. Resultados e trabalhos pendentes são reaproveitados por até cinco minutos. O histórico do chat pertence à sessão e é reiniciado na troca de proposição.

Para um avulso ou anexo de movimento, confira no PDF o intervalo de uma única versão e informe as páginas e a seção. A descoberta lista referências oficiais. A presença de um arquivo na lista não identifica sua vigência. Use a ementa como alternativa após verificar as referências e registrar por que nenhuma peça textual é adequada.

## Registro das etapas anteriores

- As três abas convergem para o mesmo detalhe. A interface reutiliza a Câmara, a descoberta documental, a extração e o fluxo de análise pela IA. O texto e a análise bem-sucedida do recorte são reaproveitados em memória na sessão. A análise começa sob demanda.
- A primeira e a segunda página da busca por PLs de 2024 retornaram cinco IDs distintos cada. O PL 411/2024 apareceu com data original de 2007. A busca histórica retornou Pepe Vargas, PT/RS, ID 141445 e URL de fotografia. A contagem oficial por autoria para o ano de numeração de 2007 retornou 97 IDs distintos.
- A consulta da Câmara com codSituacao 1140 retornou cinco candidatos, incluindo dois com outra situação atual no detalhe. A tela passou a conferir o código atual de cada resultado e exibiu três registros confirmados na primeira página. O link de próxima página continua sendo o da consulta oficial.
- Os históricos exibiram oito votações retornadas para o PL 411 e 103 para o PL 2597. O resultado de cada deliberação permanece no histórico e a situação legislativa vem do campo oficial da proposição. A troca do PL 411 para o PL 2597 foi verificada com o cliente HTTP do Gradio, incluindo a limpeza de texto e chat e a mudança de autoria de Pepe Vargas para José Eduardo Cardozo. Um ID inexistente retornou erro HTTP 404 exibido como falha na consulta.
- A análise das duas páginas da RDF concluiu em 45,906 s. O registro da resposta inclui a possibilidade de adquirir equipamentos, mas chama a proposta de lei e generaliza o prazo de 180 dias. O original reserva esse prazo às alterações do art. 1º. Os demais dispositivos entrariam em vigor na data de publicação. [RDF analisada](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2388635)
- As respostas integrais da explicação e os ensaios de chat constam no registro JSON. O último ensaio levou 49,7 s e ainda acrescentou “o que for menor” ao § 2º. A expressão está ausente no original. Na primeira menção à responsabilidade, a resposta também confundiu a cedente com a cessionária. [Respostas integrais](interface_exemplos.json) · [Substitutivo consultado](https://www.camara.leg.br/proposicoesWeb/prop_mostrarintegra?codteor=2443176)

## Limitações

A pesquisa usa a lista em exercício da Câmara quando o ano opcional está vazio. Com um ano preenchido, usa a janela de exercício correspondente. Cada página consulta até dez deputados ou cinco proposições. A API pode falhar em itens individuais durante o enriquecimento de uma página e a interface indica essas lacunas. A contagem deduplica por identificador e limita a busca a 20 páginas de até 100 resultados. Ao atingir o limite com mais páginas ou receber erro após progresso, ela apresenta apenas o total parcial confirmado.

O chat testa o contexto renderizado pelo servidor local antes de gerar. A conversa do cidadão usa o texto escolhido na abertura e as perguntas recentes quando há espaço. Se fonte, pergunta e instruções não couberem, informa a limitação. No laboratório, a equipe pode ajustar manualmente o recorte. Explicações e respostas são experimentais. Compare condições, prazos, autoria de citações e versão com a fonte oficial.

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m pytest -m live -qs -p no:cacheprovider
```
