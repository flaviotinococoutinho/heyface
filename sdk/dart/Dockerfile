FROM dart:3.13.4-sdk
WORKDIR /client
COPY pubspec.yaml pubspec.lock ./
RUN dart pub get --enforce-lockfile
COPY . .
CMD ["sh", "-c", "dart format --output=none --set-exit-if-changed lib test example && dart analyze --fatal-infos && dart test"]
