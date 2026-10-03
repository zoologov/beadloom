plugins {
    kotlin("jvm") version "2.0.21"
    application
}

group = "org.example"
version = "0.9.0"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}

application {
    mainClass.set("org.example.orchard.routing.MainKt")
}

tasks.test {
    useJUnitPlatform()
}
