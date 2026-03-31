package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestGet_BasicRequest(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("<html>search results</html>"))
	}))
	defer ts.Close()

	opt := &options{
		Query:  "test",
		Engine: "google",
	}
	body := opt.get(ts.URL)
	if body != "<html>search results</html>" {
		t.Errorf("unexpected body: %s", body)
	}
}

func TestGet_CustomHeaders(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Custom") != "test-value" {
			t.Errorf("expected X-Custom header, got '%s'", r.Header.Get("X-Custom"))
		}
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	opt := &options{
		Query:   "test",
		Engine:  "google",
		Headers: []string{"X-Custom:test-value"},
	}
	body := opt.get(ts.URL)
	if body != "ok" {
		t.Errorf("unexpected body: %s", body)
	}
}

func TestGet_MultipleHeaders(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Accept") != "text/html" {
			t.Errorf("expected Accept header 'text/html', got '%s'", r.Header.Get("Accept"))
		}
		if r.Header.Get("X-Token") != "abc123" {
			t.Errorf("expected X-Token header 'abc123', got '%s'", r.Header.Get("X-Token"))
		}
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	opt := &options{
		Query:   "test",
		Engine:  "google",
		Headers: []string{"Accept:text/html", "X-Token:abc123"},
	}
	body := opt.get(ts.URL)
	if body != "ok" {
		t.Errorf("unexpected body: %s", body)
	}
}

func TestGet_InvalidHeaderSkipped(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	opt := &options{
		Query:   "test",
		Engine:  "google",
		Headers: []string{"no-colon-header", "Valid:header"},
	}
	body := opt.get(ts.URL)
	if body != "ok" {
		t.Errorf("unexpected body: %s", body)
	}
}

func TestGet_EmptyResponse(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(""))
	}))
	defer ts.Close()

	opt := &options{
		Query:  "test",
		Engine: "google",
	}
	body := opt.get(ts.URL)
	if body != "" {
		t.Errorf("expected empty body, got '%s'", body)
	}
}

func TestGet_LargeResponse(t *testing.T) {
	largeBody := make([]byte, 10000)
	for i := range largeBody {
		largeBody[i] = 'a'
	}
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write(largeBody)
	}))
	defer ts.Close()

	opt := &options{
		Query:  "test",
		Engine: "google",
	}
	body := opt.get(ts.URL)
	if len(body) != 10000 {
		t.Errorf("expected 10000 bytes, got %d", len(body))
	}
}

func TestGet_MethodIsGET(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("expected GET method, got %s", r.Method)
		}
		w.Write([]byte("ok"))
	}))
	defer ts.Close()

	opt := &options{
		Query:  "test",
		Engine: "google",
	}
	opt.get(ts.URL)
}
