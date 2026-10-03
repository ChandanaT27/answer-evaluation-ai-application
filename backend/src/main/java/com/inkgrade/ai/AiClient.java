package com.inkgrade.ai;

import com.inkgrade.config.AppProperties;
import com.inkgrade.exception.ApiException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestClientResponseException;

import java.nio.file.Path;
import java.time.Duration;

/** HTTP client for the Python FastAPI AI service. */
@Component
public class AiClient {
    private static final Logger log = LoggerFactory.getLogger(AiClient.class);
    private final RestClient client;

    public AiClient(AppProperties props) {
        SimpleClientHttpRequestFactory f = new SimpleClientHttpRequestFactory();
        f.setConnectTimeout(Duration.ofSeconds(10));
        f.setReadTimeout(Duration.ofSeconds(props.ai().timeoutSeconds()));
        RestClient.Builder b = RestClient.builder().baseUrl(props.ai().baseUrl()).requestFactory(f);
        if (props.ai().apiKey() != null && !props.ai().apiKey().isBlank()) {
            b.defaultHeader("X-API-Key", props.ai().apiKey());
        }
        this.client = b.build();
    }

    public AiDtos.OcrResult ocr(Path file, String filename) {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new FileSystemResource(file) {
            @Override
            public String getFilename() {
                return filename;
            }
        });
        return call(() -> client.post().uri("/ocr").body(body).retrieve().body(AiDtos.OcrResult.class));
    }

    public AiDtos.EvaluateResponse evaluate(AiDtos.EvaluateRequest request) {
        return call(() -> client.post().uri("/evaluate").body(request).retrieve().body(AiDtos.EvaluateResponse.class));
    }

    private <T> T call(java.util.function.Supplier<T> s) {
        try {
            T r = s.get();
            if (r == null) throw new ApiException(HttpStatus.BAD_GATEWAY, "AI service returned an empty response");
            return r;
        } catch (RestClientResponseException e) {
            log.warn("AI service error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new ApiException(HttpStatus.BAD_GATEWAY, "AI service error: " + e.getStatusCode().value()
                    + " " + e.getResponseBodyAsString());
        } catch (RestClientException e) {
            log.warn("AI service unreachable: {}", e.getMessage());
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "AI service is unavailable");
        }
    }
}
