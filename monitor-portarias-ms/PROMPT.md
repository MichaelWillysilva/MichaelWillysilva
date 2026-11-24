# Prompt atualizado — robô “O que mudou no SUS”

Implemente neste repositório o monitoramento diário de publicações oficiais de saúde com impacto operacional, financeiro ou regulatório para a Secretaria Municipal de Saúde de Contagem/MG. Use a especificação PDF “Especificacao_Robo_O_que_mudou_no_SUS” fornecida na solicitação como requisito funcional e preserve as funções existentes: histórico SQLite, deduplicação, coleta do texto integral, filtros, relatório, CSV, painel estático e execução em `--dry-run`.

## Fontes

Consulte as fontes independentemente, desde a última execução concluída, preferindo API, RSS ou dados abertos. Respeite `robots.txt`, identifique o User-Agent, limite a frequência e use retry com backoff. Falha de uma fonte não deve impedir as demais; exponha a falha no log e no relatório.

- DOU, Seção 1 (`do1`) e edições extras (`do1e`): atos cujo órgão seja Ministério da Saúde, incluindo Anvisa e ANS; aproveite JSON público da edição e abra o texto integral do ato.
- Ministério da Saúde: notas técnicas, publicações (boletins, estudos, notas informativas, guias, manuais, relatórios e Vigilância em Saúde), portal e secretarias SAPS, SAES, SVSA, SECTICS, SEIDIGI e SGTES.
- e-Gestor AB, SAIPS e FNS: credenciamentos, adesões, propostas, habilitações, prazos, resultados de financiamento e repasses pertinentes a Contagem.
- Saúde Legis/BVS: normas e alterações de portarias consolidadas.
- DATASUS/SIGTAP e CNES: mudanças em procedimentos, cadastros e regras de envio de dados.
- Conitec: decisões de incorporação/exclusão, PCDTs e consultas públicas abertas.
- Anvisa: atos regulatórios, alertas, recolhimentos e suspensões de produtos.
- ANS: resoluções normativas e atualizações do rol.
- Minas Gerais: Diário do Executivo, SES-MG e SESLegis; acompanhar resoluções SES/MG, deliberações CIB-SUS/MG, notas técnicas, alertas epidemiológicos, informes de vacinação e ofícios aos municípios.

Antes de implementar uma fonte, verifique sua acessibilidade, API/RSS/dados abertos e política de acesso. Não contorne login, autenticação ou bloqueios. Se uma fonte exigir acesso institucional, marque-a como pendente de credenciais/autorização e continue com as demais.

## Escopo editorial

Priorize publicações que mudem a rotina dos serviços, tragam recursos ou criem obrigações, prazos ou regras para a SMS. Inclua tabelas e anexos na análise. Exclua atos de pessoal, extratos de contrato, licitações e registros de produtos, salvo quando o conteúdo também satisfizer um critério de interesse acima.

Classifique por temas configuráveis: vacinação e imunização; financiamento e repasses; obras e equipamentos; políticas assistenciais e redes; saúde materno-infantil; saúde mental; urgência e emergência; atenção especializada e filas; saúde bucal; doenças crônicas, cuidados continuados e reabilitação; medicamentos, tecnologias e PCDTs; vigilância sanitária; vigilância epidemiológica e emergências; vigilância ambiental e zoonoses; saúde do trabalhador; populações específicas; força de trabalho e formação; regulação e sistemas de informação (SIGTAP, CNES, SISAB, SIA, SIH, RNDS e e-SUS); saúde digital; gestão, prazos e pactuações. Manter a lista e os termos editáveis em `config.yaml`.

## Classificação: não confundir prioridade e relevância

Grave dois campos independentes:

1. **Prioridade editorial** (`máxima`, `alta`, `média`, `baixa`), aplicando a primeira regra correspondente, nesta ordem:
   - `máxima`: cita Contagem, Município/Prefeitura/Fundo Municipal de Saúde de Contagem, Contagem/MG ou IBGE `311860`/`3118601`; “contagem” como quantidade não vale.
   - `alta`: muda política, programa, rede, linha de cuidado, protocolo/PCDT, calendário vacinal ou incorporação/exclusão de tecnologia no SUS.
   - `média`: trata de habilitação, credenciamento, incentivo, custeio, repasse, teto, emenda ou valores.
   - `baixa`: demais itens; atos da ANS ficam nesta prioridade, exceto quando citarem Contagem.
2. **Relevância para Contagem** (`alta`, `média`, `baixa`): alta para referência direta a Contagem/IBGE; média para regra aplicável aos municípios do porte ou da região metropolitana de Belo Horizonte; baixa nos demais casos.

Não derive um campo do outro: um repasse específico para outra cidade pode ter prioridade média e relevância baixa; uma regra nacional pode ter prioridade alta e relevância média.

Para cada ato, registre fonte, data, órgão emissor, tipo, tema(s), prioridade, relevância, ementa/resumo de até duas linhas, trecho de evidência, link oficial, valor e prazo/vigência quando existirem, municípios/secretarias mencionados e setores destinatários. Analise o texto integral e evite falsos positivos de cidade.

## Encaminhamento e e-mail

Roteie cada item para todos os setores cujos temas estejam presentes. Gabinete da SMS e NISD recebem todos os itens; sem setor identificado, encaminhe somente a esses dois. Use os temas e palavras-chave do quadro de setores da especificação para Atenção Primária, Imunização, Regulação, Atenção Secundária, Saúde Mental, Atenção Hospitalar, Vigilância Sanitária e Vigilância Epidemiológica.

Durante homologação, encaminhe somente ao NISD. Os e-mails setoriais ainda não foram informados: não invente destinatários e mantenha-os configuráveis, inicialmente vazios/desativados. Não envie mensagens a setores sem atos. Em dia sem edição por feriado, envie aviso curto apenas ao Gabinete e NISD.

Ordene o corpo por prioridade (máxima, alta, média, baixa), mostre faixa/badge de cor, citação de Contagem, se houver, tipo/número com link, fonte/data, órgão, resumo, valor, prazo/vigência e setores destinatários. Inclua o rodapé institucional da especificação. Credenciais SMTP devem vir somente de `.env` local ignorado pelo Git ou GitHub Secrets; nunca versioná-las.

Use o assunto `O que mudou no SUS — DD/MM/AAAA — <Setor> (N atos)` e informe no assunto quantos atos citam Contagem.

## Execução, compatibilidade e entrega

- Agende em servidor/VM sempre ligada para dias úteis às 9h; na segunda-feira, inclua publicações e edições extras do fim de semana.
- Mantenha a interface comum das fontes, CLI e execução `--dry-run`; mantenha erros por fonte isolados e nenhum envio/gravação no modo de teste.
- Preserve o painel público responsivo e os formatos existentes; acrescente filtros/indicadores necessários sem publicar segredos ou dados pessoais.
- Atualize `README.md`, configuração de fontes/temas/setores/destinatários e exemplos de ambiente.
- Adicione testes para regras de prioridade, relevância, encaminhamento, falsos positivos, valores/prazos e falhas/fallbacks de fonte.
- Rode testes automatizados e uma consulta `--dry-run` desde a data solicitada. Relate contagens por fonte, prioridades, falhas e fontes inacessíveis; não apresente uma fonte bloqueada como consultada com sucesso.

## Situação da implementação atual

Este prompt descreve o escopo ampliado do PDF, não uma afirmação de que todas as fontes e regras já estejam implementadas. Antes de declarar o projeto completo, compare o código atual com cada requisito, implemente o que faltar e documente explicitamente fontes indisponíveis ou que dependam de acesso institucional.
