FROM maven:3.9-eclipse-temurin-17 AS build

WORKDIR /workspace
COPY pom.xml ./
RUN mvn -B -DskipTests dependency:go-offline

COPY src ./src
RUN cp src/main/resources/application-example.yml src/main/resources/application.yml \
    && mvn -B -DskipTests package

FROM eclipse-temurin:17-jre

RUN useradd --system --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=build /workspace/target/*.jar /app/app.jar

USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
