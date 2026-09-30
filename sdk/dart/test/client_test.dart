import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:heyface_client/heyface_client.dart';
import 'package:http/http.dart' as http;
import 'package:test/test.dart';

final class RecordingClient extends http.BaseClient {
  RecordingClient(this.respond);
  final http.StreamedResponse Function(http.BaseRequest, List<int>) respond;
  int calls = 0;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    calls++;
    final bytes = await request.finalize().toBytes();
    return respond(request, bytes);
  }
}

http.StreamedResponse response(
  JsonObject body, {
  int status = 200,
  Map<String, String> headers = const {},
}) => http.StreamedResponse(
  Stream.value(utf8.encode(jsonEncode(body))),
  status,
  headers: headers,
);

HeyfaceClient client(
  http.Client transport, {
  AccessTokenProvider? tokenProvider,
  Duration timeout = const Duration(seconds: 2),
}) => HeyfaceClient(
  baseUri: Uri.parse('https://heyface.example/api/v1/'),
  tokenProvider: tokenProvider ?? () => 'test-access',
  transport: transport,
  timeout: timeout,
);

void main() {
  test(
    'multipart keeps binary image and JSON metadata, without base64',
    () async {
      final bytes = [0, 255, 128, 42, 1];
      final progress = <int>[];
      final transport = RecordingClient((request, body) {
        final multipart = request as http.MultipartRequest;
        expect(request.url.path, '/api/v1/search');
        expect(request.headers['Authorization'], 'Bearer test-access');
        expect(request.headers['Accept'], contains('application/problem+json'));
        expect(request.followRedirects, isFalse);
        expect(jsonDecode(multipart.fields['metadata']!), {
          'method': 'sface',
          'filters': {'city': 'Vitória'},
          'limit': 10,
          'exact': false,
          'hnsw_ef': 128,
        });
        expect(multipart.fields, isNot(contains('image_base64')));
        expect(body, containsAllInOrder(bytes));
        return response({
          'matches': [],
          'mode': 'approximate',
          'face': {},
          'timing_ms': {'inference': 1, 'search': 2},
        });
      });
      final result = await client(transport).searchPeople(
        image: ImageUpload.bytes(bytes, ImageType.png),
        query: const PeopleQuery(
          method: HumanMethod.sface,
          filters: PeopleFilters(city: 'Vitória'),
        ),
        onProgress: (sent, total) {
          progress.add(sent);
          expect(total, bytes.length);
        },
      );
      expect(result.matches, isEmpty);
      expect(progress.last, bytes.length);
      expect(transport.calls, 1);
    },
  );

  test(
    'problem details preserve code, trace and retry delay without automatic retries',
    () async {
      final transport = RecordingClient(
        (_, _) => response(
          {'code': 'vision_busy', 'detail': 'Aguarde.'},
          status: 503,
          headers: {'retry-after': '2', 'x-request-id': 'trace-id'},
        ),
      );
      await expectLater(
        client(transport).capabilities(),
        throwsA(
          isA<HeyfaceException>()
              .having((e) => e.code, 'code', 'vision_busy')
              .having((e) => e.requestId, 'trace', 'trace-id')
              .having((e) => e.retryAfter, 'delay', const Duration(seconds: 2))
              .having((e) => e.canRetry, 'retryable', true),
        ),
      );
      expect(transport.calls, 1);
    },
  );

  test('proxy HTML errors still produce a useful status', () async {
    final transport = RecordingClient(
      (_, _) => http.StreamedResponse(
        Stream.value(utf8.encode('<html>Too large</html>')),
        413,
      ),
    );
    await expectLater(
      client(transport).capabilities(),
      throwsA(isA<HeyfaceException>().having((e) => e.status, 'status', 413)),
    );
  });

  test('credentials are obtained for each operation', () async {
    var identity = 0;
    final transport = RecordingClient((request, _) {
      expect(request.headers['Authorization'], 'Bearer key-$identity');
      return response({'methods': []});
    });
    final api = client(transport, tokenProvider: () => 'key-${++identity}');
    await api.methods();
    await api.methods();
    expect(identity, 2);
  });

  test('already cancelled requests do not upload', () async {
    final transport = RecordingClient((_, _) => response({}));
    final cancellation = RequestCancellation()..cancel();
    await expectLater(
      client(transport).capabilities(cancellation: cancellation),
      throwsA(isA<http.RequestAbortedException>()),
    );
    expect(transport.calls, 0);
  });

  test('cancellation aborts an active native HTTP request', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final entered = Completer<void>();
    server.listen((request) {
      if (!entered.isCompleted) entered.complete();
    });
    final api = HeyfaceClient(
      baseUri: Uri.parse('http://127.0.0.1:${server.port}/api/v1/'),
      tokenProvider: () => 'test-access',
      allowInsecureLocalhost: true,
    );
    final cancellation = RequestCancellation();
    try {
      final pending = api.capabilities(cancellation: cancellation);
      final expectation = expectLater(
        pending,
        throwsA(isA<http.RequestAbortedException>()),
      );
      await entered.future.timeout(const Duration(seconds: 2));
      cancellation.cancel();
      await expectation.timeout(const Duration(seconds: 2));
    } finally {
      api.close();
      await server.close(force: true);
    }
  });

  test(
    'timeout includes credential lookup and prevents a later upload',
    () async {
      final token = Completer<String>();
      final transport = RecordingClient((_, _) => response({}));
      final api = client(
        transport,
        tokenProvider: () => token.future,
        timeout: const Duration(milliseconds: 20),
      );
      await expectLater(api.capabilities(), throwsA(isA<TimeoutException>()));
      token.complete('too-late');
      await Future<void>.delayed(Duration.zero);
      expect(transport.calls, 0);
    },
  );

  test(
    'invalid stream length is rejected before treating an upload as complete',
    () async {
      final transport = RecordingClient((_, _) => response({}));
      final image = ImageUpload.stream(
        length: 2,
        type: ImageType.jpeg,
        openStream: () => Stream.value([1]),
      );
      await expectLater(
        client(transport).searchPeople(image: image),
        throwsA(isA<StateError>()),
      );
    },
  );

  test(
    'remote cleartext transport and invalid record identifiers are rejected',
    () {
      expect(
        () => HeyfaceClient(
          baseUri: Uri.parse('http://remote.example/api/v1/'),
          tokenProvider: () => 'key',
          allowInsecureLocalhost: true,
        ),
        throwsArgumentError,
      );
      expect(() => RecordId('../other'), throwsArgumentError);
      expect(() => ImageUpload.bytes([], ImageType.png), throwsArgumentError);
    },
  );

  test(
    '204 deletion is accepted with the supplied stable identifier',
    () async {
      final id = RecordId('03d0916b-d4e8-413c-bb97-d52c99baf60d');
      final transport = RecordingClient((request, _) {
        expect(request.method, 'DELETE');
        expect(request.url.path, '/api/v1/animals/${id.value}');
        return http.StreamedResponse(const Stream.empty(), 204);
      });
      await client(transport).removeAnimal(id);
    },
  );
}
