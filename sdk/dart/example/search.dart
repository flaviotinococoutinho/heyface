import 'dart:io';
import 'package:heyface_client/heyface_client.dart';

/// Run from the repository root; no token is written to arguments or source files.
Future<void> main() async {
  final root = Directory.current.path;
  final uri = Uri.parse(
    Platform.environment['HEYFACE_API_URL'] ?? 'http://localhost:8088/api/v1/',
  );
  final photo = File('$root/web/public/brand/heyface.png');
  final api = HeyfaceClient(
    baseUri: uri,
    allowInsecureLocalhost: true,
    tokenProvider: () async =>
        (await File('$root/.secrets/demo-token.txt').readAsString()).trim(),
  );
  try {
    final limits = await api.capabilities();
    if (!limits.permissions.contains('read')) {
      throw StateError('Read permission required.');
    }
    final result = await api.searchPeople(
      image: ImageUpload.stream(
        length: await photo.length(),
        type: ImageType.png,
        openStream: photo.openRead,
      ),
      query: const PeopleQuery(method: HumanMethod.sface),
    );
    if (result.matches.isEmpty) {
      throw StateError('Prepare the examples with ./heyface demo.');
    }
    for (final match in result.matches) {
      stdout.writeln('${match.record.name}: ${match.score.toStringAsFixed(4)}');
    }
  } on HeyfaceException catch (error) {
    stderr.writeln('${error.code}: ${error.message}');
    stderr.writeln('Request: ${error.requestId ?? "unknown"}');
    exitCode = 1;
  } finally {
    api.close();
  }
}
