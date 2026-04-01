package main

import (
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
)

// ---------------------------------------------------------------------------
// get() retry logic tests
// ---------------------------------------------------------------------------

func TestGet_RetriesOnError(t *testing.T) {
	attempts := 0
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		attempts++
		if attempts < 3 {
			return nil, fmt.Errorf("temporary error attempt %d", attempts)
		}
		return &http.Response{
			StatusCode: 200,
			Body:       io.NopCloser(strings.NewReader("success after retries")),
			Header:     make(http.Header),
		}, nil
	})
	defer cleanup()

	opt := &options{Query: "test", Engine: "google"}
	body := opt.get("http://test.example.com")

	if body != "success after retries" {
		t.Errorf("expected 'success after retries', got '%s'", body)
	}
	if attempts != 3 {
		t.Errorf("expected 3 attempts, got %d", attempts)
	}
}

func TestGet_AllRetriesFail(t *testing.T) {
	attempts := 0
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		attempts++
		return nil, fmt.Errorf("persistent error")
	})
	defer cleanup()

	opt := &options{Query: "test", Engine: "google"}
	body := opt.get("http://test.example.com")

	if body != "" {
		t.Errorf("expected empty string when all retries fail, got '%s'", body)
	}
	if attempts != maxRetries {
		t.Errorf("expected %d attempts, got %d", maxRetries, attempts)
	}
}

func TestGet_SucceedsFirstAttempt(t *testing.T) {
	attempts := 0
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		attempts++
		return &http.Response{
			StatusCode: 200,
			Body:       io.NopCloser(strings.NewReader("first try")),
			Header:     make(http.Header),
		}, nil
	})
	defer cleanup()

	opt := &options{Query: "test", Engine: "google"}
	body := opt.get("http://test.example.com")

	if body != "first try" {
		t.Errorf("expected 'first try', got '%s'", body)
	}
	if attempts != 1 {
		t.Errorf("expected 1 attempt, got %d", attempts)
	}
}

// ---------------------------------------------------------------------------
// doRequest() error path tests
// ---------------------------------------------------------------------------

func TestDoRequest_InvalidURL(t *testing.T) {
	opt := &options{Query: "test", Engine: "google"}
	_, err := opt.doRequest("://invalid-url")
	if err == nil {
		t.Error("expected error for invalid URL")
	}
	if !strings.Contains(err.Error(), "creating request") {
		t.Errorf("expected 'creating request' error, got: %v", err)
	}
}

func TestDoRequest_ServerError(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		return nil, fmt.Errorf("connection refused")
	})
	defer cleanup()

	opt := &options{Query: "test", Engine: "google"}
	_, err := opt.doRequest("http://test.example.com")
	if err == nil {
		t.Error("expected error for connection failure")
	}
	if !strings.Contains(err.Error(), "executing request") {
		t.Errorf("expected 'executing request' error, got: %v", err)
	}
}

func TestDoRequest_WithHeaders(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if req.Header.Get("Authorization") != "Bearer token123" {
			t.Errorf("expected Authorization header, got '%s'", req.Header.Get("Authorization"))
		}
		if req.Header.Get("Accept-Language") != "en-US" {
			t.Errorf("expected Accept-Language header, got '%s'", req.Header.Get("Accept-Language"))
		}
		return &http.Response{
			StatusCode: 200,
			Body:       io.NopCloser(strings.NewReader("ok")),
			Header:     make(http.Header),
		}, nil
	})
	defer cleanup()

	opt := &options{
		Query:   "test",
		Engine:  "google",
		Headers: []string{"Authorization:Bearer token123", "Accept-Language:en-US"},
	}
	body, err := opt.doRequest("http://test.example.com")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if body != "ok" {
		t.Errorf("expected 'ok', got '%s'", body)
	}
}

func TestDoRequest_HeaderWithoutColon(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		// The invalid header should be skipped; check that it wasn't set
		if req.Header.Get("invalidheader") != "" {
			t.Error("invalid header should not be set")
		}
		return &http.Response{
			StatusCode: 200,
			Body:       io.NopCloser(strings.NewReader("ok")),
			Header:     make(http.Header),
		}, nil
	})
	defer cleanup()

	opt := &options{
		Query:   "test",
		Engine:  "google",
		Headers: []string{"invalidheader"},
	}
	body, err := opt.doRequest("http://test.example.com")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if body != "ok" {
		t.Errorf("expected 'ok', got '%s'", body)
	}
}

func TestDoRequest_HeaderWithColonInValue(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		// Header "Key:value:with:colons" should split as Key -> "value:with:colons"
		if req.Header.Get("Key") != "value:with:colons" {
			t.Errorf("expected 'value:with:colons', got '%s'", req.Header.Get("Key"))
		}
		return &http.Response{
			StatusCode: 200,
			Body:       io.NopCloser(strings.NewReader("ok")),
			Header:     make(http.Header),
		}, nil
	})
	defer cleanup()

	opt := &options{
		Query:   "test",
		Engine:  "google",
		Headers: []string{"Key:value:with:colons"},
	}
	body, err := opt.doRequest("http://test.example.com")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if body != "ok" {
		t.Errorf("expected 'ok', got '%s'", body)
	}
}

// ---------------------------------------------------------------------------
// doRequest() with proxy (error case: invalid proxy URL)
// ---------------------------------------------------------------------------

func TestDoRequest_InvalidProxy(t *testing.T) {
	opt := &options{
		Query:  "test",
		Engine: "google",
		Proxy:  "://invalid-proxy",
	}
	_, err := opt.doRequest("http://test.example.com")
	if err == nil {
		t.Error("expected error for invalid proxy")
	}
	if !strings.Contains(err.Error(), "setting up proxy") {
		t.Errorf("expected 'setting up proxy' error, got: %v", err)
	}
	// Restore default transport
	client.Transport = nil
}

// ---------------------------------------------------------------------------
// doRequest() with a response body that errors during read
// ---------------------------------------------------------------------------

type errorReader struct{}

func (e *errorReader) Read(p []byte) (int, error) {
	return 0, fmt.Errorf("read failure")
}
func (e *errorReader) Close() error { return nil }

func TestDoRequest_ReadBodyError(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		return &http.Response{
			StatusCode: 200,
			Body:       &errorReader{},
			Header:     make(http.Header),
		}, nil
	})
	defer cleanup()

	opt := &options{Query: "test", Engine: "google"}
	_, err := opt.doRequest("http://test.example.com")
	if err == nil {
		t.Error("expected error for body read failure")
	}
	if !strings.Contains(err.Error(), "reading response body") {
		t.Errorf("expected 'reading response body' error, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// doRequest() with a valid proxy URL (sets transport successfully)
// ---------------------------------------------------------------------------

func TestDoRequest_ValidProxy(t *testing.T) {
	origTransport := client.Transport

	opt := &options{
		Query:  "test",
		Engine: "google",
		Proxy:  "http://127.0.0.1:8080",
	}
	// This will set up the proxy transport but the actual request will fail
	// since there's no proxy running. The important thing is the proxy setup succeeds.
	_, err := opt.doRequest("http://test.example.com")
	// We expect an "executing request" error since the proxy isn't actually running
	if err == nil {
		t.Error("expected error since proxy is not running")
	}

	// Restore original transport
	client.Transport = origTransport
}

// ---------------------------------------------------------------------------
// isError() tests
// ---------------------------------------------------------------------------

func TestIsError_NilError(t *testing.T) {
	// isError with nil should be a no-op (should not panic or exit)
	isError(nil)
	// If we get here, the test passed (no panic, no exit)
}
