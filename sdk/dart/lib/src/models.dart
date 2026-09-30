typedef JsonObject = Map<String, Object?>;

final class SearchDefaults {
  static const limit = 10;
  static const pageSize = 25;
  static const candidateLimit = 40;
  static const hnswEf = 128;
}

enum HumanMethod { facenet, sface }

enum AnimalMethod { dinov2, wildfusion }

enum RegisteredSex { female, male, other, unspecified }

final class RecordId {
  RecordId(this.value) {
    if (!_format.hasMatch(value)) {
      throw ArgumentError.value(value, 'id', 'Expected a UUID.');
    }
  }
  static final _format = RegExp(
    r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
  );
  final String value;
}

final class PersonDetails {
  const PersonDetails({
    required this.name,
    required this.birthDate,
    required this.state,
    required this.city,
    required this.consent,
    this.sex = RegisteredSex.unspecified,
  });
  final String name;

  /// Calendar date in YYYY-MM-DD, without timezone conversion.
  final String birthDate;
  final String state;
  final String city;
  final bool consent;
  final RegisteredSex sex;
  JsonObject toJson() => {
    'name': name,
    'birth_date': birthDate,
    'state': state,
    'city': city,
    'sex': sex.name,
    'consent': consent,
  };
}

final class PeopleFilters {
  const PeopleFilters({
    this.name,
    this.sex,
    this.birthDate,
    this.birthDateFrom,
    this.birthDateTo,
    this.state,
    this.city,
  });
  final String? name, birthDate, birthDateFrom, birthDateTo, state, city;
  final RegisteredSex? sex;
  JsonObject toJson() => {
    if (name != null) 'name': name,
    if (sex != null) 'sex': sex!.name,
    if (birthDate != null) 'birth_date': birthDate,
    if (birthDateFrom != null) 'birth_date_from': birthDateFrom,
    if (birthDateTo != null) 'birth_date_to': birthDateTo,
    if (state != null) 'state': state,
    if (city != null) 'city': city,
  };
}

final class PeopleQuery {
  const PeopleQuery({
    this.method = HumanMethod.facenet,
    this.filters = const PeopleFilters(),
    this.limit = SearchDefaults.limit,
    this.exact = false,
    this.hnswEf = SearchDefaults.hnswEf,
    this.minScore,
  });
  final HumanMethod method;
  final PeopleFilters filters;
  final int limit, hnswEf;
  final bool exact;
  final double? minScore;
  JsonObject toJson() => {
    'method': method.name,
    'filters': filters.toJson(),
    'limit': limit,
    'exact': exact,
    'hnsw_ef': hnswEf,
    if (minScore != null) 'min_score': minScore,
  };
}

final class AnimalDetails {
  const AnimalDetails({
    required this.name,
    required this.species,
    required this.consent,
    this.sex = RegisteredSex.unspecified,
    this.breed = '',
    this.color = '',
    this.pattern = '',
  });
  final String name, species, breed, color, pattern;
  final bool consent;
  final RegisteredSex sex;
  JsonObject toJson() => {
    'name': name,
    'species': species,
    'consent': consent,
    'sex': sex.name,
    'breed': breed,
    'color': color,
    'pattern': pattern,
  };
}

final class AnimalQuery {
  const AnimalQuery({
    required this.species,
    required this.singleSubjectConfirmed,
    this.method = AnimalMethod.dinov2,
    this.limit = SearchDefaults.limit,
    this.candidateLimit = SearchDefaults.candidateLimit,
    this.exact = false,
    this.hnswEf = SearchDefaults.hnswEf,
  });
  final String species;
  final bool singleSubjectConfirmed, exact;
  final AnimalMethod method;
  final int limit, candidateLimit, hnswEf;
  JsonObject toJson() => {
    'species': species,
    'single_subject_confirmed': singleSubjectConfirmed,
    'method': method.name,
    'limit': limit,
    'candidate_limit': candidateLimit,
    'exact': exact,
    'hnsw_ef': hnswEf,
  };
}

final class PersonRecord {
  PersonRecord.fromJson(JsonObject json)
    : id = RecordId(json['id'] as String),
      name = json['name'] as String,
      birthDate = json['birth_date'] as String,
      state = json['state'] as String,
      city = json['city'] as String,
      sex = json['sex'] as String,
      face = Map.unmodifiable(json['face'] as JsonObject);
  final RecordId id;
  final String name, birthDate, state, city, sex;
  final JsonObject face;
}

final class AnimalRecord {
  AnimalRecord.fromJson(JsonObject json)
    : id = RecordId(json['id'] as String),
      name = json['name'] as String,
      species = json['species'] as String,
      representation = Map.unmodifiable(json['representation'] as JsonObject);
  final RecordId id;
  final String name, species;
  final JsonObject representation;
}

final class Candidate<T> {
  const Candidate({required this.record, required this.score, this.distance});
  final T record;
  final double score;
  final double? distance;
}

final class PeopleMatches {
  PeopleMatches.fromJson(JsonObject json)
    : matches = List.unmodifiable(
        (json['matches'] as List<Object?>).map((item) {
          final match = item as JsonObject;
          return Candidate(
            record: PersonRecord.fromJson(match['person'] as JsonObject),
            score: (match['score'] as num).toDouble(),
            distance: (match['distance'] as num).toDouble(),
          );
        }),
      ),
      mode = json['mode'] as String,
      face = Map.unmodifiable(json['face'] as JsonObject),
      timing = Map.unmodifiable(json['timing_ms'] as JsonObject);
  final List<Candidate<PersonRecord>> matches;
  final String mode;
  final JsonObject face, timing;
}

final class AnimalMatches {
  AnimalMatches.fromJson(JsonObject json)
    : matches = List.unmodifiable(
        (json['matches'] as List<Object?>).map((item) {
          final match = item as JsonObject;
          return Candidate(
            record: AnimalRecord.fromJson(match['animal'] as JsonObject),
            score: (match['score'] as num).toDouble(),
          );
        }),
      ),
      method = json['method'] as String,
      calibrated = json['calibrated'] as bool;
  final List<Candidate<AnimalRecord>> matches;
  final String method;
  final bool calibrated;
}

final class PeoplePage {
  PeoplePage.fromJson(JsonObject json)
    : items = List.unmodifiable(
        (json['items'] as List<Object?>).map(
          (item) => PersonRecord.fromJson(item as JsonObject),
        ),
      ),
      nextCursor = json['next_cursor'] as String?;
  final List<PersonRecord> items;
  final String? nextCursor;
}

final class Capabilities {
  Capabilities.fromJson(JsonObject json)
    : maxImageBytes = json['max_image_bytes'] as int,
      maxMetadataBytes = json['max_metadata_bytes'] as int,
      permissions = Set.unmodifiable(
        (json['permissions'] as List<Object?>).cast<String>(),
      ),
      acceptedImageTypes = List.unmodifiable(
        (json['accepted_image_types'] as List<Object?>).cast<String>(),
      ),
      contractVersion = json['contract_version'] as String;
  final int maxImageBytes, maxMetadataBytes;
  final Set<String> permissions;
  final List<String> acceptedImageTypes;
  final String contractVersion;
}
