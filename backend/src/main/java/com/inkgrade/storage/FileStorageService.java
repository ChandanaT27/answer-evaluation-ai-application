package com.inkgrade.storage;

import com.inkgrade.config.AppProperties;
import com.inkgrade.exception.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Map;
import java.util.UUID;

/** Stores uploads outside the web root under random names after extension + magic-byte validation. */
@Service
public class FileStorageService {
    private static final Map<String, String> EXT_TYPES = Map.of(
            "pdf", "application/pdf", "png", "image/png", "jpg", "image/jpeg", "jpeg", "image/jpeg",
            "bmp", "image/bmp", "tif", "image/tiff", "tiff", "image/tiff", "txt", "text/plain");

    private final Path root;

    public FileStorageService(AppProperties props) throws IOException {
        this.root = Path.of(props.storage().root()).toAbsolutePath().normalize();
        Files.createDirectories(root);
    }

    public StoredFile store(MultipartFile file, String category) {
        if (file == null || file.isEmpty()) {
            throw ApiException.badRequest("Uploaded file is empty");
        }
        String original = sanitize(file.getOriginalFilename());
        String ext = extension(original);
        if (!EXT_TYPES.containsKey(ext)) {
            throw ApiException.badRequest("Unsupported file type. Allowed: " + String.join(", ", EXT_TYPES.keySet()));
        }
        try {
            byte[] head;
            try (InputStream in = file.getInputStream()) {
                head = in.readNBytes(4096);
            }
            if (!contentMatches(ext, head)) {
                throw ApiException.badRequest("File content does not match its extension");
            }
            String cat = category.replaceAll("[^a-z0-9_-]", "");
            Path dir = root.resolve(cat).normalize();
            Files.createDirectories(dir);
            String name = UUID.randomUUID() + "." + ext;
            Path target = dir.resolve(name).normalize();
            if (!target.startsWith(root)) {
                throw ApiException.badRequest("Invalid storage path");
            }
            try (InputStream in = file.getInputStream()) {
                Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
            }
            return new StoredFile(cat + "/" + name, original, EXT_TYPES.get(ext));
        } catch (IOException e) {
            throw new ApiException(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR, "Could not store file");
        }
    }

    public Path resolve(String relativePath) {
        Path p = root.resolve(relativePath).normalize();
        if (!p.startsWith(root) || !Files.isRegularFile(p)) {
            throw ApiException.notFound("File");
        }
        return p;
    }

    public void deleteQuietly(String relativePath) {
        if (relativePath == null) return;
        try {
            Path p = root.resolve(relativePath).normalize();
            if (p.startsWith(root)) Files.deleteIfExists(p);
        } catch (IOException ignored) {
            // best effort
        }
    }

    public static String contentTypeFor(String path) {
        return EXT_TYPES.getOrDefault(extension(path), "application/octet-stream");
    }

    static String sanitize(String name) {
        if (name == null || name.isBlank()) return "upload";
        String base = name.replace('\\', '/');
        base = base.substring(base.lastIndexOf('/') + 1);
        base = base.replaceAll("[^A-Za-z0-9._ -]", "_");
        return base.length() > 120 ? base.substring(base.length() - 120) : base;
    }

    static String extension(String name) {
        int i = name.lastIndexOf('.');
        return i < 0 ? "" : name.substring(i + 1).toLowerCase();
    }

    static boolean contentMatches(String ext, byte[] h) {
        return switch (ext) {
            case "pdf" -> startsWith(h, '%', 'P', 'D', 'F');
            case "png" -> startsWith(h, 0x89, 'P', 'N', 'G');
            case "jpg", "jpeg" -> startsWith(h, 0xFF, 0xD8, 0xFF);
            case "bmp" -> startsWith(h, 'B', 'M');
            case "tif", "tiff" -> startsWith(h, 'I', 'I', 42, 0) || startsWith(h, 'M', 'M', 0, 42);
            case "txt" -> isText(h);
            default -> false;
        };
    }

    private static boolean startsWith(byte[] h, int... sig) {
        if (h.length < sig.length) return false;
        for (int i = 0; i < sig.length; i++) {
            if ((h[i] & 0xFF) != sig[i]) return false;
        }
        return true;
    }

    private static boolean isText(byte[] h) {
        for (byte b : h) {
            if (b == 0) return false;
        }
        try {
            // a 4096-byte cut may split a multibyte char; tolerate by trimming up to 3 trailing bytes
            for (int trim = 0; trim <= 3 && trim < h.length; trim++) {
                try {
                    StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                            .decode(ByteBuffer.wrap(h, 0, h.length - trim));
                    return true;
                } catch (CharacterCodingException ignored) {
                    // try shorter
                }
            }
            return false;
        } catch (RuntimeException e) {
            return false;
        }
    }
}
