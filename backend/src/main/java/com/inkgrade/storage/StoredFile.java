package com.inkgrade.storage;

public record StoredFile(String relativePath, String originalName, String contentType) {
}
