# Preparar a integração com Flutter

A API já tem um [cliente Dart](../sdk/dart) com upload binário por stream, resultados tipados, cancelamento e erros estruturados. Ele não depende de widgets nem de `dart:io`; o app escolhe como abrir a imagem e obter a credencial. O exemplo de terminal usa `dart:io` apenas para ler arquivos locais.

## Testar sem instalar Flutter

Na raiz do projeto:

```sh
./heyface up
./heyface client-test
./heyface client-smoke
```

`client-test` roda formatação, análise estática e testes no SDK Dart em Docker. `client-smoke` prepara os dois cadastros fictícios e executa uma busca real pelo cliente. Esses checks validam o cliente e a API; não substituem a futura validação em Android/iOS.

O exemplo completo fica em [sdk/dart/example/search.dart](../sdk/dart/example/search.dart). Ele lê a chave do arquivo local, sem incluí-la no código ou em argumentos de processo.

## Adicionar ao aplicativo

Enquanto o app estiver no mesmo checkout, adicione uma dependência de caminho no `pubspec.yaml` e ajuste o caminho à localização dele:

```yaml
dependencies:
  heyface_client:
    path: ../sdk/dart
```

Em outro repositório, fixe uma revisão Git testada em vez de acompanhar `main` automaticamente. O pacote não é publicado no pub.dev.

Crie uma instância de `HeyfaceClient` por sessão e reutilize a conexão. O construtor recebe `baseUri`, `tokenProvider` e, opcionalmente, um `http.Client`. O `tokenProvider` é chamado em cada operação: a camada de acesso do app pode renovar a credencial sem reconstruir o cliente.

```dart
final api = HeyfaceClient(
  baseUri: Uri.parse('https://seu-ambiente.example/api/v1/'),
  tokenProvider: access.currentToken,
  locale: 'pt-BR',
);

final cancellation = RequestCancellation();
final result = await api.searchPeople(
  image: ImageUpload.stream(
    length: await selectedImage.length(),
    type: ImageType.jpeg,
    openStream: selectedImage.openRead,
  ),
  query: const PeopleQuery(
    method: HumanMethod.sface,
    filters: PeopleFilters(city: 'Vitória'),
  ),
  cancellation: cancellation,
  onProgress: (sent, total) => uploadProgress.value = sent / total,
);
```

`selectedImage` e `access` pertencem ao app. `openStream` deve abrir um stream novo a cada tentativa e entregar exatamente o tamanho declarado. `onProgress` mede os bytes da imagem entregues ao transporte, sem contar o envelope; 100% não significa que a comparação terminou. O helper `ImageUpload.bytes` atende arquivos já em memória, incluindo Flutter web.

## Fluxo de tela

1. Obtenha a credencial e consulte `capabilities()`. Use `permissions`, `acceptedImageTypes` e `maxImageBytes` para habilitar ações e validar a escolha da foto.
2. Selecione uma foto com um único rosto. Para animais, peça o recorte e a confirmação de um único indivíduo e informe a espécie.
3. Mostre o progresso do envio e depois o estado de comparação. Mantenha o cancelamento disponível.
4. Mostre os candidatos na ordem recebida. O score é uma medida de similaridade, sem a apresentação de uma certeza percentual de identidade.
5. Ao sair da tela, chame `cancellation.cancel()`. Ao encerrar a sessão, chame `api.close()` se o transporte pertence ao cliente.

O cancelamento interrompe a chamada do cliente. Uma inferência ou escrita que já chegou ao servidor pode terminar. Ao repetir um cadastro, preserve o UUID gerado no app: o mesmo UUID substitui o registro naquele espaço de trabalho. Não gere um UUID novo automaticamente a cada falha de rede.

O cliente oferece `enrollPerson`, `searchPeople`, `getPerson`, `listPeople`, `removePerson`, `analyzeFace`, `enrollAnimal`, `searchAnimals`, `removeAnimal`, `capabilities`, `methods` e `readiness`.

## Erros, rede e credenciais

`HeyfaceException` contém `status`, `code`, `message`, `requestId`, `retryAfter` e `canRetry`. Ele também entende o envelope anterior de erros e falhas HTML de proxy. Cancelamento usa `RequestAbortedException`, da biblioteca HTTP; falhas de conexão continuam sendo erros de transporte. O cliente não repete uploads automaticamente.

Para 429/503, respeite `retryAfter` quando presente, limite o número de tentativas e inclua um pequeno atraso aleatório. A decisão de repetir pertence ao caso de uso do app. Um timeout de cadastro deve levar à consulta do UUID antes de uma nova escrita.

A chave local de demonstração serve ao ambiente local. Não a embuta em um APK. A distribuição do aplicativo precisa conectar `tokenProvider` ao acesso do usuário e guardar a credencial fora do código. O gateway atual trabalha com chaves provisionadas e escopos; ainda não oferece login de usuário, OAuth ou renovação automática.

## Endereços de desenvolvimento

| Execução | Base da API |
| --- | --- |
| Navegador no computador | `http://localhost:8088/api/v1/` |
| Simulador iOS no mesmo Mac | `http://localhost:8088/api/v1/` |
| Emulador Android | `http://10.0.2.2:8088/api/v1/` |
| Aparelho físico | Endpoint HTTPS alcançável pelo aparelho |

HTTP local exige `allowInsecureLocalhost: true` no cliente. Essa exceção aceita apenas loopback e o alias do emulador Android; não libera servidores HTTP remotos. O Compose mantém a porta em `127.0.0.1`. Para um aparelho físico, use um ambiente HTTPS configurado para o piloto.

No Android, declare a permissão de internet. Se o ambiente exigir exceção para tráfego local sem TLS, mantenha-a na configuração de depuração. Consulte as instruções de [rede do Flutter](https://docs.flutter.dev/cookbook/networking/fetch-data), a [política de rede iOS/Android](https://docs.flutter.dev/release/breaking-changes/network-policy-ios-android) e o [alias de rede do emulador Android](https://developer.android.com/studio/run/emulator-networking). Nenhuma dessas configurações de app é aplicada por este repositório.
