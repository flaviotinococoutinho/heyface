# Heyface

Um ambiente local para cadastrar pessoas e animais e buscar imagens parecidas. PHP cuida do acesso; Python cuida das imagens; Qdrant guarda os vetores e os dados usados nos filtros.

![Heyface](web/public/brand/heyface.png)

## Começar

Você precisa do **Docker com Compose v2 ou superior**, usando containers Linux. Não precisa instalar PHP, Python, Node ou extensões na máquina. O primeiro build baixa dependências e os pesos verificados por SHA-256; reserve internet, alguns minutos e cerca de 10 GB livres. A configuração usa CPU e funciona em Linux amd64/arm64, macOS com Docker Desktop/Colima e Windows com Docker Desktop + WSL2. Reserve 4 CPUs e 6 GB de memória disponíveis para o Docker.

**macOS e Linux**

```sh
./heyface up
./heyface demo
./heyface token
```

**Windows — PowerShell**

```powershell
.\heyface.ps1 up
.\heyface.ps1 demo
.\heyface.ps1 token
```

Também dá para abrir `Iniciar.command` no macOS ou `Iniciar.bat` no Windows. Se a política local bloquear scripts PowerShell, use o `.bat`; ele aplica a opção apenas àquele processo.

Abra **http://localhost:8088**, clique em **Conectar acesso** e cole a chave exibida por `token`. Em **Usar exemplo**, escolha a imagem da pessoa ou do animal cadastrado pelo comando `demo`. Os exemplos têm nomes e dados fictícios. A busca pela mesma imagem verifica a integração; não mede acurácia.

`up` pode ser repetido. Ele preserva credenciais, cadastros e calibrações. A porta pode ser alterada em `.env`. Só o servidor web é publicado, em `127.0.0.1`; os serviços internos usam uma rede Docker isolada.

## O que tem aqui

- Cadastro de pessoas com nome, sexo informado, data de nascimento, estado e cidade. Busca textual e por imagem, com filtros aplicados antes da comparação vetorial.
- Dois métodos humanos, FaceNet e SFace, com espaços vetoriais separados. O cadastro guarda ambos em uma operação. Os cinco pontos detectados do rosto são metadados; não são os eixos do embedding.
- Cadastro e busca de animais por espécie, com representação global DINOv2. A variante de fusão combina similaridade global e correspondências locais SIFT após calibração própria.
- Laravel + Octane/Swoole como gateway, casos de uso pequenos, credenciais com escopos, isolamento por espaço de trabalho, limites compartilhados em Redis e respostas em português/inglês.
- React + TypeScript, sem páginas Blade. Interface responsiva, envio de imagem, filtros, resultados, cadastro, consulta dos registros e exclusão.
- JSON com base64 e multipart com arquivo **ou** base64. A API não devolve imagens nem vetores brutos nas consultas.
- Scripts de teste, diagnóstico de busca, calibração offline e backup com hashes.

O score ordena candidatos e **não confirma a identidade**. O sexo e os demais dados cadastrais são informados pelo responsável; não são inferidos da foto. Imagens enviadas são decodificadas em memória. Vetores, pontos, descritores locais e metadados persistem no volume do Qdrant.

## Comandos do dia a dia

| Comando | Uso |
| --- | --- |
| `./heyface up` | Preparar e subir todo o ambiente |
| `./heyface init` | Criar a configuração local, sem iniciar a aplicação |
| `./heyface status` | Consultar o estado dos serviços |
| `./heyface logs vision` | Ver as últimas mensagens de um serviço |
| `./heyface test` | Rodar lint/testes Python e testes PHP em containers |
| `./heyface smoke` | Verificar o fluxo real, incluindo isolamento e os três extratores |
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
models/manifest.json   versões, origens e checksums dos artefatos
scripts/               preparação e operações locais
```

- [Contrato da API](docs/api.md)
- [Arquitetura e decisões](docs/architecture.md)
- [Reconhecimento, animais e calibração](docs/recognition.md)
- [Operação, backup e diagnóstico](docs/operations.md)
- [Convenções para evolução](CONTRIBUTING.md)

Qdrant foi escolhido pela busca HNSW com filtros de payload e vetores nomeados. Não existe um banco que vença todos os cenários: o benchmark daqui mede latência e recall do índice no seu ambiente, sem alegar superioridade sobre outros bancos. A configuração local não inclui replicação nem alta disponibilidade.
