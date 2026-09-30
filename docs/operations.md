# Operação local

## Configuração

`./heyface init` cria `.env`, `.secrets/demo-token.txt` e `.secrets/access/keys.json`. Arquivos existentes são preservados. Não copie valores de outra instalação: cada ambiente deve ter suas próprias chaves. Se já tiver criado um `.env` vazio, preencha as variáveis obrigatórias ou preserve esse arquivo com outro nome antes de rodar `init`.

| Ajuste | Onde | Efeito |
| --- | --- | --- |
| `HTTP_PORT` | `.env` | Porta local, padrão 8088 |
| `OCTANE_WORKERS` | `.env` | Workers PHP, padrão 2 |
| `REQUESTS_PER_MINUTE` | `.env` | Limite por credencial, compartilhado em Redis |
| Limites de imagem e índice | `services/vision/app/policies.py` | Políticas operacionais explícitas |
| Dimensões e versões | `services/vision/app/domain/representations.py` | Contrato estável, exige migração se mudar |
| Credenciais/escopos | `.secrets/access/keys.json` | Registro de hashes SHA-256, tenant e capacidades |
| Calibrações | `.local/calibrations/<tenant>/<species>.json` | Curvas compatíveis com a representação |

Cada entrada do registro usa o hash SHA-256 da chave como índice, um `tenant` de 1–64 caracteres alfanuméricos/`_`/`-` e os escopos `read`, `write` e/ou `delete`. Para revogar, remova a entrada ou marque `revoked: true`. Preserve a chave em local privado. O gateway relê o registro a cada requisição; faça a substituição do arquivo de forma atômica ao automatizar mudanças. Não altere o tenant de uma chave esperando migrar cadastros: os dados permanecem no tenant original.

Depois de alterar configuração ou código, rode `./heyface up`. O build é sequencial para reduzir pico de memória e aceita Docker com builder clássico ou BuildKit. Não é necessário instalar buildx para usar os scripts.

## Recursos e concorrência

A aplicação usa CPU por padrão. O processo Python carrega os pesos uma vez. Inferências pesadas têm concorrência limitada e espera curta; quando o serviço está ocupado, a resposta é 503, sem uma fila ilimitada na memória. Mais workers Python duplicariam os pesos; meça memória e throughput antes de aumentar processos.

Redis usa política `noeviction`: perder o controle de rate limit por pressão de memória seria pior do que recusar chamadas. Falhas de armazenamento ou transporte não são tratadas como “ninguém encontrado”.

Uploads temporários do proxy e do PHP usam `/tmp` em memória (`tmpfs`). Não há persistência de imagens originais. O diretório de artefatos baixados e os vetores usam volumes nomeados do Compose. `stop` preserva esses volumes. Evite `docker compose down -v` se houver dados que precise manter.

## Backup

```sh
./heyface backup
```

O backup fica em `.local/backups/<data-id>/` e contém snapshots das duas coleções, `.env`, credenciais e calibrações. O script grava um manifesto SHA-256 e relê os arquivos para verificar os hashes. Esse diretório contém dados privados; fica fora do Git e não é enviado para outro serviço.

Os snapshots das coleções são capturados em sequência. Se precisar de um ponto consistente entre domínios, pause novas gravações no gateway antes de executar o backup. Para recuperar, use um ambiente separado e a [API de recuperação de snapshots do Qdrant](https://qdrant.tech/documentation/database-tutorials/create-snapshot/), restaure configuração e calibrações e valide os registros. Recuperar por cima da coleção ativa pode sobrescrever dados: o script não faz isso automaticamente. Hash verificado não substitui um ensaio de recuperação.

## Benchmark

```sh
./heyface benchmark --points 3000 --queries 40
```

Cria uma coleção separada `heyface_benchmark_<id>`, gera vetores normalizados com seed fixa e mede busca exata versus HNSW com diferentes valores de `hnsw_ef`. O relatório em `.local/benchmark.json` informa contagem realmente indexada, recall@10, p50 e p95. A coleção sintética é preservada para inspeção e não participa da aplicação nem do backup normal.

Recall mede sobreposição dos vizinhos aproximados com os exatos. Não mede reconhecimento facial. A distribuição sintética também não representa necessariamente os embeddings do seu acervo. Antes de decidir por outro banco ou reduzir precisão, repita o experimento com volume, seletividade dos filtros e concorrência próximos da carga real. O benchmark não escolhe parâmetros da aplicação automaticamente.

## Diagnóstico

- `./heyface status`: todos os serviços permanentes devem aparecer ativos; o serviço `models` termina com sucesso depois da verificação.
- `./heyface logs vision`: erros de pesos/checksums, incompatibilidade de coleção ou indisponibilidade do banco.
- `./heyface logs gateway`: inicialização e falhas de transporte; o modo debug permanece desligado.
- Porta ocupada: altere `HTTP_PORT` no `.env` e repita `up`.
- Build encerrado por memória: libere recursos do Docker ou aumente a memória disponível; a compilação do Swoole já usa um processo.
- Download interrompido: repita `up`. Arquivos incompletos não são promovidos a artefatos válidos.
- 409 em fusão: falta calibração compatível com o tenant, a espécie ou a versão.
- 503 ao comparar: respeite `Retry-After`; não envie uma nova rajada imediata.

A configuração é para desenvolvimento local. Exposição pública exige TLS, gestão de identidades, política de retenção, operação de backups e testes de capacidade próprios. O bind em loopback é intencional.
