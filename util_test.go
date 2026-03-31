package main

import (
	"testing"
)

func TestIsURL_ValidHTTP(t *testing.T) {
	if !isURL("http://example.com") {
		t.Error("expected http://example.com to be a valid URL")
	}
}

func TestIsURL_ValidHTTPS(t *testing.T) {
	if !isURL("https://example.com/path?q=1") {
		t.Error("expected https URL with path/query to be valid")
	}
}

func TestIsURL_ValidWithPort(t *testing.T) {
	if !isURL("http://example.com:8080/path") {
		t.Error("expected URL with port to be valid")
	}
}

func TestIsURL_MissingScheme(t *testing.T) {
	if isURL("example.com") {
		t.Error("expected URL without scheme to be invalid")
	}
}

func TestIsURL_MissingHost(t *testing.T) {
	if isURL("http://") {
		t.Error("expected URL without host to be invalid")
	}
}

func TestIsURL_EmptyString(t *testing.T) {
	if isURL("") {
		t.Error("expected empty string to be invalid")
	}
}

func TestIsURL_RelativePath(t *testing.T) {
	if isURL("/path/to/file") {
		t.Error("expected relative path to be invalid")
	}
}

func TestIsURL_JustScheme(t *testing.T) {
	if isURL("http") {
		t.Error("expected bare scheme to be invalid")
	}
}

func TestIsURL_FTPScheme(t *testing.T) {
	if !isURL("ftp://files.example.com/file") {
		t.Error("expected ftp URL to be valid (has scheme + host)")
	}
}

func TestIsURL_ComplexPath(t *testing.T) {
	if !isURL("https://example.com/path/to/resource?key=value&other=123#fragment") {
		t.Error("expected complex URL to be valid")
	}
}

// Test options struct creation
func TestOptionsStruct(t *testing.T) {
	opts := options{
		Query:   "test query",
		Engine:  "google",
		Proxy:   "",
		Page:    1,
		Headers: []string{"X-Custom: value"},
	}

	if opts.Query != "test query" {
		t.Errorf("expected Query 'test query', got '%s'", opts.Query)
	}
	if opts.Engine != "google" {
		t.Errorf("expected Engine 'google', got '%s'", opts.Engine)
	}
	if opts.Page != 1 {
		t.Errorf("expected Page 1, got %d", opts.Page)
	}
	if len(opts.Headers) != 1 {
		t.Errorf("expected 1 header, got %d", len(opts.Headers))
	}
}

func TestOptionsStruct_Defaults(t *testing.T) {
	opts := options{}
	if opts.Query != "" {
		t.Errorf("expected empty Query, got '%s'", opts.Query)
	}
	if opts.Page != 0 {
		t.Errorf("expected zero Page, got %d", opts.Page)
	}
	if opts.Proxy != "" {
		t.Errorf("expected empty Proxy, got '%s'", opts.Proxy)
	}
}
