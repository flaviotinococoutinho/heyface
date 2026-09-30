# API pública

Base: `http://localhost:8088/api/v1`. Todos os endpoints, exceto `health/live`, exigem `Authorization: Bearer <chave>`. `Accept-Language: pt-BR` ou `en` controla as mensagens. `X-Tenant-Id` recebido do cliente não determina o espaço de trabalho.

| Método | Caminho | Escopo | Resultado |
| --- | --- | --- | --- |
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

## Imagem

Use **uma** destas opções por chamada:

1. JSON: campo `image_base64` com base64 puro ou data URI de JPEG/PNG.
2. Multipart: campo `image` com o arquivo.
3. Multipart: campo textual `image_base64` com a codificação da imagem.

Objetos como `person`, `animal` e `filters` são JSON em um campo textual quando o transporte é multipart. Valores booleanos de topo podem ser `true`/`false`. JPEG/PNG são limitados a 5 MiB e 16 milhões de pixels; base64 tem limite próprio de 7 milhões de caracteres e o corpo HTTP de 8 MiB. Mais de um rosto, imagem sem rosto ou detecção insuficiente geram erro explícito.

## Cadastro de pessoa

O UUID vem do cliente. Repetir o cadastro com o mesmo UUID e a mesma credencial substitui o registro dentro daquele espaço de trabalho, sem duplicá-lo. Os dois extratores precisam concluir antes de persistir.

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

Erros usam `{"error":{"code":"...","message":"..."}}`, com mensagem traduzida e código estável. Casos principais: 401 sem acesso, 403 sem escopo, 404 inexistente naquele tenant, 409 calibração ausente/incompatível, 413 corpo grande, 422 entrada inválida, 429 limite de requisições e 503 serviço ocupado/indisponível. Respostas 503 do serviço de imagem incluem `Retry-After`.

O limite da imagem vale depois da decodificação também. Mensagens de validação não repetem base64 nem conteúdo da requisição. Os limites do proxy podem responder antes do gateway; nesses casos o corpo pode ser texto/HTML e o cliente trata o status.
