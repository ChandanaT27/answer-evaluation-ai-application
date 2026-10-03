FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B -DskipTests package

FROM eclipse-temurin:21-jre
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 1001 inkgrade && mkdir -p /data/uploads && chown -R inkgrade /data
WORKDIR /app
COPY --from=build /build/target/inkgrade-backend-*.jar app.jar
USER inkgrade
ENV STORAGE_ROOT=/data/uploads
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --retries=20 CMD curl -fs http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-jar", "app.jar"]
