import 'dart:async';

final class UploadPolicy {
  static const maxImageBytes = 5 * 1024 * 1024;
  static const maxMetadataBytes = 64 * 1024;
  static const requestTimeout = Duration(seconds: 60);
}

enum ImageType {
  jpeg('image/jpeg', 'image.jpg'),
  png('image/png', 'image.png');

  const ImageType(this.mediaType, this.filename);
  final String mediaType;
  final String filename;
}

/// The stream factory opens a fresh stream for each explicit attempt.
final class ImageUpload {
  ImageUpload.stream({
    required this.length,
    required this.type,
    required this.openStream,
  }) {
    if (length < 1 || length > UploadPolicy.maxImageBytes) {
      throw ArgumentError.value(
        length,
        'length',
        'Image must contain 1–5242880 bytes.',
      );
    }
  }

  factory ImageUpload.bytes(List<int> bytes, ImageType type) {
    final content = List<int>.unmodifiable(bytes);
    return ImageUpload.stream(
      length: content.length,
      type: type,
      openStream: () => Stream.value(content),
    );
  }

  final int length;
  final ImageType type;
  final Stream<List<int>> Function() openStream;
}

final class RequestCancellation {
  final _signal = Completer<void>();
  Future<void> get whenCancelled => _signal.future;
  bool get isCancelled => _signal.isCompleted;
  void cancel() {
    if (!_signal.isCompleted) _signal.complete();
  }
}

final class HeyfaceException implements Exception {
  const HeyfaceException({
    required this.status,
    required this.code,
    required this.message,
    this.requestId,
    this.retryAfter,
  });
  final int status;
  final String code;
  final String message;
  final String? requestId;
  final Duration? retryAfter;
  bool get canRetry =>
      status == 429 || status == 502 || status == 503 || status == 504;
  @override
  String toString() => 'HeyfaceException($status, $code): $message';
}
