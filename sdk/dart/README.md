# Cliente Dart do Heyface

Cliente HTTP independente de interface, para integrar a busca visual com Flutter. Envia JPEG/PNG como bytes, com metadados JSON, usando `package:http`.

- Tipos separados para cadastro, filtros, consultas e candidatos de pessoas e animais.
- Upload por stream com tamanho conhecido, progresso e cancelamento.
- `tokenProvider` por requisição, transporte reutilizável e HTTPS por padrão.
- Problem Details, códigos estáveis, identificação da requisição e `Retry-After`.
- Sem repetição automática de escrita ou upload.

Na raiz do repositório, use `./heyface client-test` e `./heyface client-smoke`. O segundo comando prepara os exemplos e precisa do ambiente iniciado.

Veja o [guia de integração](../../docs/flutter.md), o [contrato público](../../services/gateway/resources/contracts/openapi.json) e o [exemplo executável](example/search.dart).
