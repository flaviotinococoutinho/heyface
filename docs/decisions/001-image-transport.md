# Imagem binária em HTTP e contrato OpenAPI

Status: adotada. Contrato público: 1.1.0, sob `/api/v1`.

## Contexto

A consulta envia uma foto JPEG/PNG e poucos campos. React já consome a API e Flutter será o próximo cliente. O caminho anterior convertia o arquivo multipart em base64 no gateway, acrescentando representação textual e cópias sem melhorar a imagem.

## Decisão

Usar `multipart/form-data` com `image` binária e `metadata` como objeto JSON serializado em um campo textual UTF-8. O PHP abre o arquivo temporário como stream e o encaminha ao Python com o mesmo envelope. A decodificação do transporte termina no adapter Python; reconhecimento recebe bytes e parâmetros validados.

A API continua aceitando JSON/base64 e os campos multipart anteriores. Não há uma migração obrigatória de clientes existentes. Novos clientes negociam erros `application/problem+json`, enquanto clientes que pedem JSON recebem o envelope anterior.

O contrato público usa [OpenAPI 3.1.2](https://spec.openapis.org/oas/v3.1.2.html), com schemas dos parâmetros obtidos dos mesmos tipos usados pelo serviço. O arquivo é versionado, servido pelo gateway e comparado com respostas reais. O SDK Dart é pequeno e mantido explicitamente; não depende da saída de um gerador nem afirma compatibilidade automática com todos os geradores OpenAPI.

## Alternativas

| Transporte | Custo para este fluxo | Quando reavaliar |
| --- | --- | --- |
| Multipart binário + JSON | Foto sem expansão base64; suporte HTTP direto em web, PHP, Python e Dart | Escolha atual para foto por consulta |
| JSON + base64 | Base64 ocupa `4 × ceil(bytes / 3)` caracteres, além do envelope; exige codificação e decodificação | Compatibilidade com integrações existentes |
| Protobuf em HTTP/gRPC | Campo `bytes` transmite a mesma foto; exige serialização/toolchain próprios | Mensagens estruturadas numerosas, contratos RPC entre serviços |
| gRPC streaming | Bom encaixe para fluxos contínuos, com nova infraestrutura de cliente/proxy | Vídeo, lotes contínuos ou streaming bidirecional medido |
| Upload direto com URL assinada | Separa transferência e processamento, mas adiciona objeto temporário, expiração e controle de acesso | Arquivos grandes, retomada de upload ou processamento assíncrono |

Protobuf é uma codificação de mensagens, não um compressor de JPEG/PNG. Seu [campo bytes](https://protobuf.dev/programming-guides/encoding/#length-types) não remove os bytes da imagem. Para navegador, [gRPC-Web](https://grpc.io/docs/platforms/web/basics/) também envolve diferenças de transporte e proxy. Esses custos não trazem um ganho demonstrado ao fluxo atual de uma foto limitada a 5 MiB.

## Consequências verificáveis

`./heyface contract` compara os corpos HTTP reais produzidos pelo cliente de teste para os dois assets de exemplo. O relatório local informa os bytes JSON/base64 e multipart. Essa medição é de volume transferido, sem alegar redução igual de latência ou consumo de memória.

O cliente Dart usa [`AbortableMultipartRequest`](https://pub.dev/documentation/http/latest/http/AbortableMultipartRequest-class.html), stream com tamanho conhecido e transporte injetável. Cancelar não desfaz inferência ou escrita já aceita no servidor. Os erros seguem [Problem Details, RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html), negociados pelo cabeçalho `Accept`.

O proxy pode rejeitar a chamada antes de chegar ao gateway. Por isso os clientes preservam o status HTTP mesmo quando o corpo é HTML, e não pressupõem que toda falha é JSON. Não há endpoint protobuf anunciado sem implementação.
