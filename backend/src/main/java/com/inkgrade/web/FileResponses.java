package com.inkgrade.web;

import com.inkgrade.storage.FileStorageService;
import org.springframework.core.io.PathResource;
import org.springframework.core.io.Resource;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import java.nio.file.Path;

final class FileResponses {
    private FileResponses() {}

    static ResponseEntity<Resource> inline(Path path, String name) {
        String type = FileStorageService.contentTypeFor(path.getFileName().toString());
        String filename = name == null ? path.getFileName().toString() : name;
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(type))
                .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.inline().filename(filename).build().toString())
                .header("X-Content-Type-Options", "nosniff")
                .body(new PathResource(path));
    }
}
