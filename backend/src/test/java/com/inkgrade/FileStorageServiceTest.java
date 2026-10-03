package com.inkgrade;

import com.inkgrade.config.AppProperties;
import com.inkgrade.exception.ApiException;
import com.inkgrade.storage.FileStorageService;
import com.inkgrade.storage.StoredFile;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class FileStorageServiceTest {
    @TempDir Path dir;

    private FileStorageService svc() throws Exception {
        return new FileStorageService(new AppProperties(null, null, new AppProperties.Storage(dir.toString()), null, null, false));
    }

    @Test
    void storesValidPngWithRandomName() throws Exception {
        byte[] png = {(byte) 0x89, 'P', 'N', 'G', 1, 2, 3};
        StoredFile f = svc().store(new MockMultipartFile("file", "../../evil name.png", "image/png", png), "answer-sheets");
        assertTrue(f.relativePath().startsWith("answer-sheets/"));
        assertFalse(f.relativePath().contains(".."));
        assertFalse(f.originalName().contains("/"));
        assertTrue(Files.exists(svc().resolve(f.relativePath())));
    }

    @Test
    void rejectsDisallowedExtensionAndSpoofedContent() throws Exception {
        FileStorageService s = svc();
        assertThrows(ApiException.class, () -> s.store(new MockMultipartFile("file", "a.exe", "application/octet-stream", new byte[]{1, 2}), "x"));
        assertThrows(ApiException.class, () -> s.store(new MockMultipartFile("file", "a.png", "image/png", "not an image".getBytes()), "x"));
        assertThrows(ApiException.class, () -> s.store(new MockMultipartFile("file", "a.pdf", "application/pdf", new byte[0]), "x"));
    }

    @Test
    void resolveBlocksPathTraversal() throws Exception {
        assertThrows(ApiException.class, () -> svc().resolve("../../etc/passwd"));
    }
}
