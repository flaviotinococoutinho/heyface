# API pública

Base: `http://localhost:8088/api/v1`. Todos os endpoints, exceto `health/live` e `openapi.json`, exigem `Authorization: Bearer <chave>`. `Accept-Language: pt-BR` ou `en` controla as mensagens. `X-Tenant-Id` recebido do cliente não determina o espaço de trabalho.

| Método | Caminho | Escopo | Resultado |
| --- | --- | --- | --- |
| GET | `/openapi.json` | público | Contrato OpenAPI versionado |
| GET | `/capabilities` | read | Limites, formatos e permissões desta chave |
| GET | `/health/live` | público | Processo do gateway ativo |
| GET | `/health/ready` | read | Python e coleções disponíveis |
| GET | `/methods` | read | Métodos, dimensões e requisitos |
| POST | `/people` | write | Cadastro/atualização pelo UUID fornecido, HTTP 201 |
| GET | `/people` | read | Lista filtrada, com paginação por cursor |
| GET | `/people/{uuid}` | read | Dados e observação facial |
| DELETE | `/people/{uuid}` | delete | Exclui ponto e vetores, HTTP 204 |
| POST | `/search` | read | Candidatos humanos ordenados por similaridade |
| POST | `/faces/analyze` | read | Caixa, cinco pontos e qualidade da observação |
| POST | `/animals` | write | Cadastro/atualização do animal, HTTP 201 |
| POST | `/animals/search` | read | Candidatos da mesma espécie |
| DELETE | `/animals/{uuid}` | delete | Exclui o cadastro do animal, HTTP 204 |

## Contrato verificável

O [arquivo OpenAPI](../services/gateway/resources/contracts/openapi.json) é servido em `/api/v1/openapi.json`. A versão do contrato é independente da URL da API: `1.1.0` acrescenta o envelope de upload, capacidades e negociação de erros sem remover contratos anteriores.

Os schemas de entrada são gerados a partir dos tipos usados pelo Python. Rode `./heyface contract-build` ao alterá-los e versione o resultado. `./heyface test` detecta divergência entre tipos e contrato; `./heyface contract` valida respostas reais das operações e grava `.local/contract-report.json`.

## Envio recomendado de imagem

Use multipart com **duas partes**: arquivo `image` e campo textual `metadata`, contendo um objeto JSON serializado. Não misture `metadata` com campos de topo antigos. O arquivo segue binário do cliente ao PHP e do PHP ao Python.

```sh
TOKEN="$(./heyface token)"
curl --fail-with-body http://localhost:8088/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Accept: application/problem+json, application/json' \
  -H 'Accept-Language: pt-BR' \
  -F 'image=@web/public/brand/heyface.png;type=image/png' \
  -F 'metadata={"method":"sface","filters":{"city":"Vitória"},"limit":10}'
```

Esse comando é um exemplo interativo. Em scripts ou clientes, leia a credencial de um arquivo/provedor e passe-a em memória, sem registrar o cabeçalho ou a linha de comando.

`metadata` aceita até 64 KiB em UTF-8. JPEG/PNG são limitados a 5 MiB e 16 milhões de pixels. O corpo HTTP completo aceita até 8 MiB. O cliente define o boundary multipart; não configure manualmente um `Content-Type` sem boundary. Nome de arquivo e MIME declarados não substituem a validação do conteúdo.

Por compatibilidade também são aceitos:

1. JSON: campo `image_base64` com base64 puro ou data URI de JPEG/PNG, junto aos parâmetros da operação.
2. Multipart anterior: `image` com arquivo e os parâmetros nos campos de topo.
3. Multipart anterior: `image_base64` textual e os parâmetros nos campos de topo.

Objetos como `person`, `animal` e `filters` são JSON serializado nos campos textuais do multipart anterior. O base64 tem limite de 7 milhões de caracteres. Mais de uma fonte de imagem, mais de um rosto ou detecção insuficiente geram erro explícito.

JPEG/PNG já chegam codificados. Protobuf pode transportar bytes, mas não comprime a foto por definição. A [decisão de transporte](decisions/001-image-transport.md) explica a escolha e quando reavaliar gRPC ou upload direto.

## Cadastro de pessoa

No envelope recomendado, coloque `person_id` e `person` dentro de `metadata`, deixando a foto em `image`. O exemplo abaixo mostra o multipart anterior, que continua aceito.

Prefira enviar um UUID criado pelo cliente. Na ausência, o gateway gera um UUID novo para manter a compatibilidade; uma repetição sem esse identificador pode criar outro cadastro. Repetir o cadastro com o mesmo UUID e a mesma credencial substitui o registro dentro daquele espaço de trabalho, sem duplicá-lo. Os dois extratores precisam concluir antes de persistir.

```sh
TOKEN="$(./heyface token)"
curl --fail-with-body http://localhost:8088/api/v1/people \
  -H "Authorization: Bearer $TOKEN" \
  -F 'person_id=1d4fa779-962e-4b5b-b88e-8a8f8d6093b5' \
  -F 'person={"name":"Alex Exemplo","sex":"unspecified","birth_date":"1990-05-18","state":"ES","city":"Vitória","consent":true}' \
  -F 'image=@web/public/brand/heyface.png'
```

`sex` aceita `female`, `male`, `other` ou `unspecified`. A data de nascimento deve ficar entre 1900 e hoje. Campos extras são rejeitados. `consent: true` registra a declaração do responsável; o sistema não verifica a autorização fora da aplicação.

## Busca por imagem

```sh
curl --fail-with-body http://localhost:8088/api/v1/search \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Accept-Language: pt-BR' \
  -F 'image=@web/public/brand/heyface.png' \
  -F 'method=sface' \
  -F 'filters={"name":"alex","state":"ES","city":"vitoria"}' \
  -F 'limit=10' -F 'exact=false'
```

O corpo JSON equivalente:

```json
{
  "image_base64": "<base64 da imagem>",
  "method": "facenet",
  "filters": {"state": "ES", "birth_date_from": "1980-01-01", "birth_date_to": "2000-12-31"},
  "limit": 10,
  "exact": false,
  "hnsw_ef": 128
}
```

`method`: `facenet` ou `sface`. `limit`: 1–50. `hnsw_ef`: 32–1024. `min_score`, opcional, é um corte de similaridade de -1 a 1; escolha-o com validação local, não como um percentual universal.

O resultado contém `matches`, `face`, `metric`, `mode` e `timing_ms`. Cada correspondência traz `person`, `score` e `distance`. A ordenação é decrescente por score. Nenhuma falha de armazenamento vira uma lista vazia.

Os filtros aceitam nome, sexo, data exata ou intervalo de nascimento, estado e cidade. Nome é comparado por palavras completas normalizadas: caixa, espaços e acentos são normalizados, mas não há substring ou distância de edição. As palavras fornecidas precisam existir no cadastro. Estado/cidade também têm comparação sem acentos e sem distinção de caixa.

## Consulta cadastral

```sh
curl --fail-with-body -G http://localhost:8088/api/v1/people \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode 'name=alex' --data-urlencode 'city=Vitória' \
  --data-urlencode 'limit=25'
```

A resposta traz `items` e `next_cursor`. Passe o cursor opaco na próxima consulta com os mesmos filtros. A lista não promete ordem alfabética; sua ordem é a do armazenamento. `limit` vai de 1 a 100.

## Animais

```sh
curl --fail-with-body http://localhost:8088/api/v1/animals \
  -H "Authorization: Bearer $TOKEN" \
  -F 'animal_id=e188ef24-b09e-43b9-9f09-d4075a57ddbd' \
  -F 'animal={"name":"Luna Exemplo","species":"cat","sex":"unspecified","breed":"","color":"tabby","pattern":"stripes","consent":true}' \
  -F 'single_subject_confirmed=true' -F 'image=@web/public/brand/animal.png'
```

A busca recebe `image_base64` ou arquivo, `species`, `single_subject_confirmed: true`, `method: dinov2` ou `wildfusion`, `limit` de 1 a 20 e `candidate_limit` de 20 a 100, usado na fusão. A espécie é um identificador de 2–64 caracteres, como `cat`, `dog` ou `whale-shark`.

O serviço não detecta automaticamente a espécie nem garante que há um único animal no crop. A confirmação é fornecida pelo responsável. A fusão retorna HTTP 409 enquanto não houver calibração compatível com espécie, tenant e versão da representação. Veja [o processo de calibração](recognition.md).

## Falhas e acesso

Clientes novos devem enviar `Accept: application/problem+json, application/json`. Falhas do gateway passam a usar Problem Details (RFC 9457):

```json
{
  "type": "urn:heyface:problem:vision_busy",
  "title": "Service Unavailable",
  "status": 503,
  "detail": "O processamento está ocupado. Tente novamente em instantes.",
  "instance": "urn:uuid:fdc00956-152c-4c0c-9c48-1ae0503b1049",
  "code": "vision_busy",
  "request_id": "fdc00956-152c-4c0c-9c48-1ae0503b1049"
}
```

`code` é estável para lógica do cliente. `detail` respeita `Accept-Language`; `title` é a frase padrão do status HTTP. `request_id` corresponde a `X-Request-Id`, criado pelo gateway e encaminhado ao serviço interno. Respostas incluem `Cache-Control: no-store` e variam por idioma e formato aceito.

Quem envia `Accept: application/json`, ou não negocia Problem Details explicitamente, continua recebendo `{"error":{"code":"...","message":"..."}}`.

Casos principais: 401 sem acesso, 403 sem escopo, 404 inexistente naquele espaço de trabalho, 409 calibração ausente/incompatível, 413 corpo grande, 415 formato de transporte/imagem incompatível, 422 entrada inválida, 429 limite de requisições e 503 serviço ocupado/indisponível. Respostas 503 incluem `Retry-After`; o limitador do gateway também fornece espera em 429.

Os limites do proxy podem responder antes do gateway, inclusive com corpo HTML e sem identificador da aplicação. O cliente deve preservar e tratar o status HTTP mesmo quando o corpo não for JSON.

A API não faz repetição automática de uploads. Cancelamento do cliente não desfaz uma operação já aceita. Reuse o mesmo UUID ao conferir ou repetir um cadastro. `GET /capabilities` informa limites e permissões efetivos da chave; o [guia Flutter](flutter.md) aplica essas regras no cliente Dart.
