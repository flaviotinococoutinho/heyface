import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';
import 'models.dart';
import 'transport.dart';

typedef AccessTokenProvider = FutureOr<String> Function();
typedef UploadProgress = void Function(int sent, int total);

final class HeyfaceClient {
  HeyfaceClient({
    required Uri baseUri,
    required AccessTokenProvider tokenProvider,
    this.locale = 'pt-BR',
    this.timeout = UploadPolicy.requestTimeout,
    http.Client? transport,
    bool allowInsecureLocalhost = false,
  }) : _base = _validateBase(baseUri, allowInsecureLocalhost),
       _tokenProvider = tokenProvider,
       _http = transport ?? http.Client(),
       _ownsTransport = transport == null;
  final Uri _base;
  final AccessTokenProvider _tokenProvider;
  final http.Client _http;
  final bool _ownsTransport;
  final String locale;
  final Duration timeout;

  static Uri _validateBase(Uri uri, bool allowLocal) {
    const localHosts = {'localhost', '127.0.0.1', '::1', '10.0.2.2'};
    final local =
        allowLocal && uri.scheme == 'http' && localHosts.contains(uri.host);
    if ((!local && uri.scheme != 'https') ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        !uri.path.endsWith('/api/v1/')) {
      throw ArgumentError(
        'Use an HTTPS base URI ending in /api/v1/. Local HTTP needs allowInsecureLocalhost.',
      );
    }
    return uri;
  }

  Future<Capabilities> capabilities({
    RequestCancellation? cancellation,
  }) async => Capabilities.fromJson(
    await _get('capabilities', cancellation: cancellation),
  );
  Future<JsonObject> methods({RequestCancellation? cancellation}) =>
      _get('methods', cancellation: cancellation);
  Future<JsonObject> readiness({RequestCancellation? cancellation}) =>
      _get('health/ready', cancellation: cancellation);

  Future<PersonRecord> enrollPerson({
    required RecordId id,
    required PersonDetails person,
    required ImageUpload image,
    RequestCancellation? cancellation,
    UploadProgress? onProgress,
  }) async {
    final result = await _upload(
      'people',
      {'person_id': id.value, 'person': person.toJson()},
      image,
      cancellation,
      onProgress,
    );
    return PersonRecord.fromJson(result['person'] as JsonObject);
  }

  Future<PeopleMatches> searchPeople({
    required ImageUpload image,
    PeopleQuery query = const PeopleQuery(),
    RequestCancellation? cancellation,
    UploadProgress? onProgress,
  }) async => PeopleMatches.fromJson(
    await _upload('search', query.toJson(), image, cancellation, onProgress),
  );

  Future<JsonObject> analyzeFace({
    required ImageUpload image,
    RequestCancellation? cancellation,
  }) async =>
      (await _upload('faces/analyze', {}, image, cancellation, null))['face']
          as JsonObject;

  Future<PeoplePage> listPeople({
    PeopleFilters filters = const PeopleFilters(),
    int limit = SearchDefaults.pageSize,
    String? cursor,
    RequestCancellation? cancellation,
  }) async {
    final query = filters.toJson().map(
      (key, value) => MapEntry(key, value.toString()),
    )..['limit'] = '$limit';
    if (cursor != null) query['cursor'] = cursor;
    return PeoplePage.fromJson(
      await _get('people', query: query, cancellation: cancellation),
    );
  }

  Future<PersonRecord> getPerson(
    RecordId id, {
    RequestCancellation? cancellation,
  }) async => PersonRecord.fromJson(
    (await _get('people/${id.value}', cancellation: cancellation))['person']
        as JsonObject,
  );
  Future<void> removePerson(RecordId id, {RequestCancellation? cancellation}) =>
      _delete('people/${id.value}', cancellation);

  Future<AnimalRecord> enrollAnimal({
    required RecordId id,
    required AnimalDetails animal,
    required bool singleSubjectConfirmed,
    required ImageUpload image,
    RequestCancellation? cancellation,
    UploadProgress? onProgress,
  }) async {
    final result = await _upload(
      'animals',
      {
        'animal_id': id.value,
        'animal': animal.toJson(),
        'single_subject_confirmed': singleSubjectConfirmed,
      },
      image,
      cancellation,
      onProgress,
    );
    return AnimalRecord.fromJson(result['animal'] as JsonObject);
  }

  Future<AnimalMatches> searchAnimals({
    required ImageUpload image,
    required AnimalQuery query,
    RequestCancellation? cancellation,
    UploadProgress? onProgress,
  }) async => AnimalMatches.fromJson(
    await _upload(
      'animals/search',
      query.toJson(),
      image,
      cancellation,
      onProgress,
    ),
  );
  Future<void> removeAnimal(RecordId id, {RequestCancellation? cancellation}) =>
      _delete('animals/${id.value}', cancellation);

  Future<JsonObject> _get(
    String path, {
    Map<String, String>? query,
    RequestCancellation? cancellation,
  }) => _send(
    (abort) => http.AbortableRequest(
      'GET',
      _base.resolve(path).replace(queryParameters: query),
      abortTrigger: abort,
    ),
    cancellation,
  );
  Future<void> _delete(String path, RequestCancellation? cancellation) async {
    await _send(
      (abort) => http.AbortableRequest(
        'DELETE',
        _base.resolve(path),
        abortTrigger: abort,
      ),
      cancellation,
    );
  }

  Future<JsonObject> _upload(
    String path,
    JsonObject metadata,
    ImageUpload image,
    RequestCancellation? cancellation,
    UploadProgress? progress,
  ) {
    final encoded = jsonEncode(metadata);
    if (utf8.encode(encoded).length > UploadPolicy.maxMetadataBytes) {
      throw ArgumentError('Metadata exceeds 64 KiB.');
    }
    return _send((abort) {
      final request = http.AbortableMultipartRequest(
        'POST',
        _base.resolve(path),
        abortTrigger: abort,
      )..fields['metadata'] = encoded;
      request.files.add(
        http.MultipartFile(
          'image',
          _imageStream(image, progress),
          image.length,
          filename: image.type.filename,
          contentType: MediaType.parse(image.type.mediaType),
        ),
      );
      return request;
    }, cancellation);
  }

  Stream<List<int>> _imageStream(
    ImageUpload image,
    UploadProgress? progress,
  ) async* {
    var sent = 0;
    await for (final chunk in image.openStream()) {
      sent += chunk.length;
      if (sent > image.length) {
        throw StateError('Image stream exceeds declared length.');
      }
      progress?.call(sent, image.length);
      yield chunk;
    }
    if (sent != image.length) {
      throw StateError('Image stream does not match declared length.');
    }
  }

  Future<JsonObject> _send(
    http.BaseRequest Function(Future<void>) build,
    RequestCancellation? cancellation,
  ) async {
    final abort = Completer<void>();
    void cancel() {
      if (!abort.isCompleted) abort.complete();
    }

    cancellation?.whenCancelled.then((_) => cancel());
    if (cancellation?.isCancelled ?? false) {
      throw http.RequestAbortedException(_base);
    }
    final cancelled = abort.future.then<JsonObject>(
      (_) => throw http.RequestAbortedException(_base),
    );
    try {
      return await Future.any([_perform(build, abort), cancelled]).timeout(
        timeout,
        onTimeout: () {
          cancel();
          throw TimeoutException('Request deadline exceeded.', timeout);
        },
      );
    } finally {
      cancel();
    }
  }

  Future<JsonObject> _perform(
    http.BaseRequest Function(Future<void>) build,
    Completer<void> abort,
  ) async {
    final token = await Future<String>.sync(_tokenProvider);
    if (token.isEmpty || token.contains(RegExp(r'[\r\n]'))) {
      throw ArgumentError('Access token is invalid.');
    }
    if (abort.isCompleted) throw http.RequestAbortedException(_base);
    final request = build(abort.future)..followRedirects = false;
    request.headers.addAll({
      'Authorization': 'Bearer $token',
      'Accept': 'application/problem+json, application/json',
      'Accept-Language': locale,
    });
    final response = await _http.send(request).then(http.Response.fromStream);
    return _decode(response);
  }

  JsonObject _decode(http.Response response) {
    if (response.statusCode == 204) return {};
    JsonObject? body;
    try {
      body = jsonDecode(utf8.decode(response.bodyBytes)) as JsonObject;
    } on FormatException {
      body = null;
    } on TypeError {
      body = null;
    }
    if (response.statusCode >= 200 &&
        response.statusCode < 300 &&
        body != null) {
      return body;
    }
    final legacy = body?['error'];
    final error = legacy is JsonObject ? legacy : <String, Object?>{};
    throw HeyfaceException(
      status: response.statusCode,
      code: (body?['code'] ?? error['code'] ?? 'http_error').toString(),
      message:
          (body?['detail'] ?? error['message'] ?? 'HTTP ${response.statusCode}')
              .toString(),
      requestId: response.headers['x-request-id'],
      retryAfter: _retryAfter(response.headers['retry-after']),
    );
  }

  Duration? _retryAfter(String? value) {
    if (value == null) return null;
    final seconds = int.tryParse(value);
    if (seconds != null) return Duration(seconds: seconds < 0 ? 0 : seconds);
    try {
      final remaining = parseHttpDate(value).difference(DateTime.now().toUtc());
      return remaining.isNegative ? Duration.zero : remaining;
    } on FormatException {
      return null;
    }
  }

  /// Closes the owned transport. Injected transports remain the caller's responsibility.
  void close() {
    if (_ownsTransport) _http.close();
  }
}
