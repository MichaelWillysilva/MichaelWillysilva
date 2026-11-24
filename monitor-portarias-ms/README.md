# Monitor de Atos em Saúde — Contagem/MG

Consulta atos públicos do Ministério da Saúde, da Secretaria de Estado de Saúde de Minas Gerais, do Diário Oficial mineiro e da Anvisa. Classifica o impacto para Contagem e a gestão municipal do SUS, preserva o histórico em SQLite e publica um painel estático.

O escopo funcional ampliado e as regras consolidadas a partir do PDF fornecido estão em [PROMPT.md](./PROMPT.md). Esse documento é uma especificação para a próxima etapa; ele não significa que todas as fontes e regras de encaminhamento setorial já estejam implementadas no código atual.

## Requisitos

- Python 3.10 ou superior
- Acesso à internet

## Instalação

No PowerShell, na pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `config.yaml` para informar um contato real no User-Agent e ajustar os termos de busca, os temas da Anvisa e os critérios de abrangência municipal/regional. Para teste local, SMTP pode ser configurado em `.env`; nunca versione esse arquivo.

## Uso

```powershell
python main.py
python main.py --desde 2026-11-01
python main.py --fonte bvs
python main.py --fonte dou --desde 2026-11-01 --dry-run
python main.py --fonte anvisa --desde 2026-11-01
```

`--desde` aceita `AAAA-MM-DD`; sem ele, consulta a partir de ontem. `--fonte` aceita `dou`, `bvs`, `govbr`, `sesmg`, `iofmg`, `anvisa` ou `all`. O modo `--dry-run` consulta, classifica e imprime um resumo por fonte, mas não grava o banco, relatório, CSV ou painel e não envia e-mail.

## Dados produzidos

- `portarias.db`: publicações já examinadas (número, data, título/ementa, URL e SHA-256 do texto), evitando novo processamento.
- `relatorios/AAAA-MM-DD.md`: relatório da execução, fontes consultadas, correspondências e falhas.
- `contagem_portarias.csv`: exportação acumulada das publicações relevantes.
- `site/data.json`: dados públicos serializados do SQLite para o painel web.
- `site/index.html`: painel responsivo, sem build ou dependências JavaScript externas.

O banco e o JSON contêm apenas metadados, trechos e links de atos públicos. O workflow versiona o SQLite junto do `data.json` para manter o histórico e a deduplicação entre execuções no GitHub Actions.

## Fontes e limitações

- **DOU, Seção 1:** consulta o portal do Diário Oficial (`in.gov.br`). Na execução de 60 dias, o acesso à rota de busca foi bloqueado pelas regras de `robots.txt`; o monitor não tenta contornar a restrição e registra a falha.
- **Saúde Legis / BVS:** consulta o formulário público do sistema Saúde Legis por data de publicação e Seção I do DOU; se a consulta não estiver disponível ou não retornar normas, usa a API REST pública do WordPress (`/wp-json/wp/v2/posts`) como fonte complementar. A API REST estava acessível; o RSS testado retornou erro HTTP 500. O índice de posts não garante cobertura integral da base jurídica.
- **gov.br/saude:** consulta a busca do portal Plone. A página e o `robots.txt` estavam acessíveis, que permite rastreamento anônimo. O portal tem conteúdo editorial e não substitui o DOU.
- **SES-MG:** usa a API REST pública do WordPress e seus filtros de data/pesquisa para localizar notícias e publicações que mencionem CIB-SUS, resoluções, habilitações ou recursos. RSS também está publicado; a busca REST facilita filtrar por termos e data.
- **Diário Oficial de Minas Gerais:** usa a API JSON pública do novo Jornal Minas Gerais (`jornalminasgerais.mg.gov.br`), decodifica o PDF oficial do Diário do Executivo e examina o texto extraído por página. O endereço `jornal.iof.mg.gov.br` ainda expõe RSS/DSpace, mas é um acervo antigo e não cobre as edições atuais; o domínio novo entrega a interface da API. Páginas digitalizadas sem texto extraível podem não ser detectadas.
- **Anvisa:** usa o formulário oficial de busca pública do AnvisaLegis/DataLegis, com intervalo de publicação e endpoint JSON de paginação. O catálogo é filtrado pelos temas configurados em `themes`; atos temáticos sem menção local ficam com relevância baixa. A busca do Portal gov.br da Anvisa estava em manutenção durante a verificação, mas a legislação oficial no AnvisaLegis estava acessível.
- FNS foi deixado de fora por ser opcional e sua página de consulta exigir JavaScript; não foi localizada uma API pública simples na validação.

Cada fonte é consultada independentemente. O programa consulta e respeita `robots.txt`, identifica o User-Agent, limita a frequência, repete tentativas com backoff e registra erros por fonte no relatório e no log. O portal do Jornal Minas Gerais entrega HTML da aplicação para `/robots.txt`, sem regras de bloqueio legíveis; o RSS do domínio antigo não tem `robots.txt` (404), mas não é usado para coletar as edições atuais. Se uma rede corporativa interceptar TLS, configure `REQUESTS_CA_BUNDLE` com a CA confiável; a validação TLS permanece habilitada. Resultados em PDF dependem de texto extraível; documentos digitalizados sem OCR podem não ser detectados. O hash registra o texto visto, mas publicações já processadas não são baixadas novamente para detectar alterações posteriores.

## Classificação e testes

Relevância **alta** significa referência direta a Contagem, termos institucionais ou IBGE `3118601`/`311860`. **Média** é aplicada a regras de abrangência municipal ou da RMBH configuradas em `filters`. **Baixa** é usada para atos temáticos da Anvisa sem evidência local ou de abrangência municipal. A classificação por município e os termos de abrangência estão em `config.yaml`; termos de temas da Anvisa também são editáveis ali.

```powershell
python -m pytest -q
```

## Atualização diária e Vercel

Nesta publicação, o monitor fica na subpasta `monitor-portarias-ms/` do repositório de perfil. O GitHub Actions só executa workflows em `.github/workflows/` na raiz do repositório; por isso, o workflow diário desta implantação fica em `.github/workflows/monitor-portarias.yml` na raiz, fora desta pasta. Ele executa diariamente (12:20 UTC), também pode ser iniciado manualmente em **Actions**, instala as dependências, consulta as fontes, executa os testes e faz commit do banco público e de `monitor-portarias-ms/site/data.json`. Ative **Settings → Actions → General → Workflow permissions → Read and write permissions** para permitir o commit pelo `GITHUB_TOKEN`.

Para publicar no Vercel:

1. Importe o repositório de perfil no Vercel.
2. Em **Project Settings → Build and Deployment**, defina **Root Directory** como `monitor-portarias-ms/site`.
3. Use **Framework Preset: Other**, deixe o comando de build vazio e use `.` como output directory (ou mantenha os padrões de site estático).
4. Conecte a branch principal. Cada commit do workflow atualiza `site/data.json` e aciona uma nova publicação.

Não é necessária variável de ambiente no Vercel: o painel lê somente `site/data.json`. Para enviar e-mail pelo workflow, crie GitHub Actions Secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` e `EMAIL_TO`. O digest inclui todas as novas publicações processadas pelas fontes habilitadas, mesmo quando não há correspondência direta com Contagem; por isso, o volume pode variar conforme as fontes. O envio é ativado quando `SMTP_HOST`, `EMAIL_TO` e um remetente (`EMAIL_FROM` ou `SMTP_USER`) estão configurados. Não coloque credenciais no YAML, no `config.yaml`, no HTML ou no repositório.
