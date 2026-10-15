# Heyface

Heyface busca pessoas ou animais por imagem em um catálogo. A aplicação combina comparação visual e filtros cadastrais para ordenar candidatos por semelhança.

[![checks](https://github.com/flaviotinococoutinho/heyface/actions/workflows/checks.yml/badge.svg)](https://github.com/flaviotinococoutinho/heyface/actions/workflows/checks.yml)

![Heyface](web/public/brand/heyface.png)

## Cenários de uso

| Quero testar | O que o Heyface entrega |
| --- | --- |
| Localizar uma pessoa em um catálogo autorizado | Busca por rosto combinada com nome, cidade, estado e data de nascimento |
| Comparar animais conhecidos | Candidatos da mesma espécie, com padrões globais e opção de fusão calibrada |
| Incluir busca visual em outro produto | API documentada, envio binário e cliente Dart para integração com Flutter |

A tela inicial guia o primeiro teste com dois cadastros fictícios. Depois, o [roteiro de piloto](docs/pilot.md) ajuda a avaliar a aplicação com fotos diferentes e tarefas reais. O score organiza candidatos; a conferência da identidade continua sendo uma decisão de quem conhece o contexto.

## Executar o primeiro teste

Use Docker com Compose v2 e containers Linux. O primeiro build baixa dependências e pesos verificados por SHA-256. Reserve acesso à internet, cerca de 10 GB livres, 4 CPUs e 6 GB de memória disponíveis para o Docker.

A configuração usa CPU. Os ambientes previstos são Linux amd64 ou arm64, macOS com Docker Desktop ou Colima, e Windows com Docker Desktop e WSL2. As dependências PHP, Python e Node são instaladas nas imagens dos containers.

Clone o repositório e entre na pasta:

```sh
git clone https://github.com/flaviotinococoutinho/heyface.git
cd heyface
```

**macOS e Linux**

```sh
./heyface try
```

**Windows, PowerShell**

```powershell
.\heyface.ps1 try
```

Também dá para abrir `Iniciar.command` no macOS ou `Iniciar.bat` no Windows. Se a política local bloquear scripts PowerShell, use o `.bat`; ele aplica a opção apenas àquele processo.

`try` prepara o ambiente, cadastra os exemplos e mostra a chave local. Abra **http://localhost:8088**, clique em **Conectar acesso** e cole a chave. Escolha **Testar com uma pessoa** ou **Testar com um animal** e faça a busca. Os exemplos têm nomes e dados fictícios. A busca pela mesma imagem verifica a integração; não mede acurácia.

Para iniciar sem preparar exemplos, use `./heyface up`. Para consultar a chave novamente, use `./heyface token`. No Windows, use os mesmos comandos com `.\heyface.ps1`.

Você pode repetir `up` sem recriar credenciais, cadastros ou calibrações. Para alterar a porta, edite `.env`. Só o servidor web é publicado, em `127.0.0.1`; os serviços internos usam uma rede Docker isolada.

## Recursos e limites

- Cadastro de pessoas com nome, sexo informado, data de nascimento, estado e cidade. Busca textual e por imagem, com filtros aplicados antes da comparação vetorial.
- Dois métodos humanos, FaceNet e SFace, com espaços vetoriais separados. O cadastro guarda ambos em uma operação. Os cinco pontos detectados do rosto são metadados; não são os eixos do embedding.
- Cadastro e busca de animais por espécie, com representação global DINOv2. A variante de fusão combina similaridade global e correspondências locais SIFT após calibração própria.
- Laravel + Octane/Swoole como gateway, casos de uso pequenos, credenciais com escopos, isolamento por espaço de trabalho, limites compartilhados em Redis e respostas em português/inglês.
- React + TypeScript, sem páginas Blade. Interface responsiva, envio de imagem, filtros, resultados, cadastro, consulta dos registros e exclusão.
- Multipart binário com metadados JSON, preservado do cliente até o Python. Base64 continua disponível para compatibilidade. A API não devolve imagens nem vetores brutos nas consultas.
- Contrato OpenAPI 3.1.2, erros Problem Details por negociação, descoberta de limites/permissões e identificação de requisições.
- Cliente Dart com tipos de cadastro/consulta, upload por stream, progresso, cancelamento e leitura de `Retry-After`.
- Scripts de teste, diagnóstico de busca, calibração offline e backup com hashes.

O score ordena candidatos e **não confirma a identidade**. O sexo e os demais dados cadastrais são informados pelo responsável; não são inferidos da foto. Imagens enviadas são decodificadas em memória. Vetores, pontos, descritores locais e metadados persistem no volume do Qdrant.

## Comandos do dia a dia

| Comando | Uso |
| --- | --- |
| `./heyface try` | Preparar o ambiente e os exemplos para o primeiro teste |
| `./heyface up` | Preparar e subir todo o ambiente |
| `./heyface init` | Criar a configuração local, sem iniciar a aplicação |
| `./heyface status` | Consultar o estado dos serviços |
| `./heyface logs vision` | Ver as últimas mensagens de um serviço |
| `./heyface test` | Rodar lint/testes Python e testes PHP em containers |
| `./heyface smoke` | Verificar o fluxo real, incluindo isolamento e os três extratores |
| `./heyface contract` | Validar respostas reais contra o contrato e comparar tamanhos de envio |
| `./heyface client-test` | Rodar análise e testes do cliente Dart em Docker |
| `./heyface client-smoke` | Preparar exemplos e testar o cliente Dart contra a API local |
| `./heyface demo` | Cadastrar novamente os dois exemplos, sem duplicá-los |
| `./heyface benchmark` | Comparar HNSW com busca exata usando vetores sintéticos |
| `./heyface backup` | Salvar snapshots, configuração e calibrações localmente |
| `./heyface stop` | Parar os containers, preservando volumes |

No Windows, troque `./heyface` por `.\heyface.ps1`. `token` exibe uma credencial local: não copie a saída para issues ou commits.

## Organização

```text
services/gateway/app/   Access, People, Animals, Recognition, Vision, Http
services/vision/app/    people, animals, retrieval, domain, media
web/src/               interface, cliente HTTP, componentes e traduções
sdk/dart/              cliente para o próximo aplicativo Flutter
models/manifest.json   versões, origens e checksums dos artefatos
scripts/               preparação e operações locais
```

- [Roteiro para testar aplicabilidade](docs/pilot.md)
- [Contrato e exemplos da API](docs/api.md)
- [OpenAPI para ferramentas de integração](services/gateway/resources/contracts/openapi.json)
- [Guia para Flutter](docs/flutter.md)
- [Decisão de transporte: multipart, protobuf e gRPC](docs/decisions/001-image-transport.md)
- [Arquitetura e decisões](docs/architecture.md)
- [Reconhecimento, animais e calibração](docs/recognition.md)
- [Operação, backup e diagnóstico](docs/operations.md)
- [Convenções para evolução](CONTRIBUTING.md)

Qdrant oferece busca HNSW com filtros de payload e vetores nomeados. O benchmark do projeto mede latência e recall do índice no seu ambiente. A configuração local não inclui replicação nem alta disponibilidade.

