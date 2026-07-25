package com.automation.base;

import java.io.IOException;
import java.io.InputStream;
import java.util.Locale;
import java.util.Properties;

/**
 * Splits SUT/environment binding from test data (ADR-0037 D3), structurally: two accessors,
 * {@link #env(String)} and {@link #data(String)}, so the two surfaces are distinguishable in
 * code, not just by the {@code env.}/{@code data.} key prefix the POC's flat config.properties
 * lacked.
 *
 * <p>{@code env(key)} may be overridden per-invocation with a {@code -Denv.<key>} system
 * property (e.g. {@code -Denv.headless=true}). {@code data(key)} may be overridden with an
 * environment variable named {@code TEST_DATA_<KEY>} (dots and hyphens become underscores,
 * uppercased) -- e.g. {@code data.password} is overridden by {@code TEST_DATA_PASSWORD}. This
 * is the indirection pattern real credentials would use; the committed values here are a public
 * demo site's own well-known fixture login, not a secret.
 */
public final class ConfigReader {

    private static final Properties PROPERTIES = load();

    private ConfigReader() {
    }

    private static Properties load() {
        Properties properties = new Properties();
        try (InputStream stream =
                ConfigReader.class.getClassLoader().getResourceAsStream("config.properties")) {
            if (stream == null) {
                throw new IllegalStateException("config.properties not found on the classpath");
            }
            properties.load(stream);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to load config.properties", e);
        }
        return properties;
    }

    /** Environment/SUT-binding value. Overridable with {@code -Denv.<key>}. */
    public static String env(String key) {
        String fullKey = "env." + key;
        String override = System.getProperty(fullKey);
        return override != null ? override : require(fullKey);
    }

    /** Test-data value. Overridable with env var {@code TEST_DATA_<KEY>}. */
    public static String data(String key) {
        String envVar = "TEST_DATA_" + key.toUpperCase(Locale.ROOT).replace('.', '_').replace('-', '_');
        String override = System.getenv(envVar);
        return override != null ? override : require("data." + key);
    }

    private static String require(String fullKey) {
        String value = PROPERTIES.getProperty(fullKey);
        if (value == null) {
            throw new IllegalStateException("Missing config key: " + fullKey);
        }
        return value;
    }
}
