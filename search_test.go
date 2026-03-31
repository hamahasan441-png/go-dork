package main

import (
	"bytes"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

// ---------------------------------------------------------------------------
// search() — using httptest for HTTP mocking
// ---------------------------------------------------------------------------

func TestSearch_GoogleEngine(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `"><a href="/url?q=https://result1.com&amp;sa=U&amp;">R1</a>"><a href="/url?q=https://result2.com&amp;sa=U&amp;">R2</a>`)
	}))
	defer ts.Close()

	// Override the search to use our test server by testing the search method
	// We need to manually call get and parser since search constructs URLs internally
	opt := &options{
		Query:  "test",
		Engine: "google",
		Page:   1,
	}
	body := opt.get(ts.URL)
	pattern := `"><a href="\/url\?q=(.*?)&amp;sa=U&amp;`
	result := parser(body, pattern)
	if len(result) != 2 {
		t.Fatalf("expected 2 Google results, got %d", len(result))
	}
	if result[0][1] != "https://result1.com" {
		t.Errorf("expected 'https://result1.com', got '%s'", result[0][1])
	}
}

func TestSearch_ShodanEngine(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `"><a href="/host/192.168.1.1">192.168.1.1</a>"><a href="/host/10.0.0.1">10.0.0.1</a>`)
	}))
	defer ts.Close()

	opt := &options{Query: "test", Engine: "shodan", Page: 1}
	body := opt.get(ts.URL)
	pattern := `\"><a href=\"/host/(.*?)\">`
	result := parser(body, pattern)
	if len(result) != 2 {
		t.Fatalf("expected 2 Shodan results, got %d", len(result))
	}
	if result[0][1] != "192.168.1.1" {
		t.Errorf("expected '192.168.1.1', got '%s'", result[0][1])
	}
}

func TestSearch_BingEngine(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `</li><li class="b_algo"><h2><a href="https://bing-result.com" h="ID=SERP,test">`)
	}))
	defer ts.Close()

	opt := &options{Query: "test", Engine: "bing", Page: 1}
	body := opt.get(ts.URL)
	pattern := `</li><li class=\"b_algo\"><h2><a href=\"(.*?)\" h=\"ID=SERP,`
	result := parser(body, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Bing result, got %d", len(result))
	}
	if result[0][1] != "https://bing-result.com" {
		t.Errorf("expected 'https://bing-result.com', got '%s'", result[0][1])
	}
}

func TestSearch_DuckEngine(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`<a rel="nofollow" href="//duckduckgo.com/l/?kh=-1&amp;uddg=https%3A%2F%2Fduck-result.com">`))
	}))
	defer ts.Close()

	opt := &options{Query: "test", Engine: "duck", Page: 1}
	body := opt.get(ts.URL)
	pattern := `<a rel=\"nofollow\" href=\"//duckduckgo.com/l/\?kh=-1&amp;uddg=(.*?)\">`
	result := parser(body, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Duck result, got %d", len(result))
	}
}

func TestSearch_YahooEngine(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `" ac-algo fz-l ac-21th lh-24" href="https://yahoo-result.com" referrerpolicy="origin`)
	}))
	defer ts.Close()

	opt := &options{Query: "test", Engine: "yahoo", Page: 1}
	body := opt.get(ts.URL)
	pattern := `" ac-algo fz-l ac-21th lh-24" href="(.*?)" referrerpolicy="origin`
	result := parser(body, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Yahoo result, got %d", len(result))
	}
}

func TestSearch_AskEngine(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, `target="_blank" href='https://ask-result.com' data-unified=`)
	}))
	defer ts.Close()

	opt := &options{Query: "test", Engine: "ask", Page: 1}
	body := opt.get(ts.URL)
	pattern := `target="_blank" href='(.*?)' data-unified=`
	result := parser(body, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Ask result, got %d", len(result))
	}
}

func TestSearch_UnknownEngine(t *testing.T) {
	opt := &options{
		Query:  "test",
		Engine: "nonexistent",
		Page:   1,
	}
	fatal, err := opt.search()
	if !fatal {
		t.Error("expected fatal=true for unknown engine")
	}
	if err == nil {
		t.Error("expected error for unknown engine")
	}
	if err.Error() != "engine not found! Please choose one available" {
		t.Errorf("unexpected error message: %s", err.Error())
	}
}

func TestSearch_EmptyResults(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprint(w, "<html><body>No results found</body></html>")
	}))
	defer ts.Close()

	// Test that parser returns empty when no matches (after our fix)
	body := (&options{}).get(ts.URL)
	pattern := `"><a href="\/url\?q=(.*?)&amp;sa=U&amp;`
	result := parser(body, pattern)
	if len(result) != 0 {
		t.Errorf("expected 0 results for no-match page, got %d", len(result))
	}
}

func TestSearch_EmptyHTMLResponse(t *testing.T) {
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(""))
	}))
	defer ts.Close()

	body := (&options{}).get(ts.URL)
	pattern := `"><a href="\/url\?q=(.*?)&amp;sa=U&amp;`
	result := parser(body, pattern)
	if len(result) != 0 {
		t.Errorf("expected 0 results for empty response, got %d", len(result))
	}
}

// ---------------------------------------------------------------------------
// showBanner()
// ---------------------------------------------------------------------------

func TestShowBanner(t *testing.T) {
	// Capture stderr output
	oldStderr := os.Stderr
	r, w, _ := os.Pipe()
	os.Stderr = w

	showBanner()

	w.Close()
	os.Stderr = oldStderr

	var buf bytes.Buffer
	buf.ReadFrom(r)
	output := buf.String()

	if output == "" {
		t.Error("expected showBanner to write to stderr")
	}
	if len(output) < 10 {
		t.Error("expected banner to have meaningful content")
	}
}

// ---------------------------------------------------------------------------
// isStdin() — tests for stdin detection
// ---------------------------------------------------------------------------

func TestIsStdin_NormalExecution(t *testing.T) {
	// When running tests, stdin is typically not a pipe
	result := isStdin()
	if result {
		t.Error("expected isStdin to be false when running as a test")
	}
}

// ---------------------------------------------------------------------------
// Additional isURL edge cases
// ---------------------------------------------------------------------------

func TestIsURL_IPv4Address(t *testing.T) {
	if !isURL("http://192.168.1.1/path") {
		t.Error("expected URL with IPv4 to be valid")
	}
}

func TestIsURL_IPv6Address(t *testing.T) {
	if !isURL("http://[::1]/path") {
		t.Error("expected URL with IPv6 to be valid")
	}
}

func TestIsURL_WithQueryAndFragment(t *testing.T) {
	if !isURL("https://example.com/page?q=test#section") {
		t.Error("expected URL with query and fragment to be valid")
	}
}

func TestIsURL_UserInfo(t *testing.T) {
	if !isURL("https://user:pass@example.com/path") {
		t.Error("expected URL with user info to be valid")
	}
}

func TestIsURL_SpacesInvalid(t *testing.T) {
	if isURL("http://example .com") {
		t.Error("expected URL with space to be invalid")
	}
}

func TestIsURL_DataURI(t *testing.T) {
	if isURL("data:text/html,<h1>test</h1>") {
		t.Error("expected data URI to be invalid (no host)")
	}
}

// ---------------------------------------------------------------------------
// options struct comprehensive tests
// ---------------------------------------------------------------------------

func TestOptionsStruct_AllFields(t *testing.T) {
	opts := options{
		Query:   "site:example.com inurl:admin",
		Engine:  "bing",
		Proxy:   "socks5://127.0.0.1:9050",
		Page:    5,
		Headers: []string{"Authorization: Bearer token", "X-Custom: value"},
	}

	if opts.Query != "site:example.com inurl:admin" {
		t.Errorf("unexpected Query: %s", opts.Query)
	}
	if opts.Engine != "bing" {
		t.Errorf("unexpected Engine: %s", opts.Engine)
	}
	if opts.Proxy != "socks5://127.0.0.1:9050" {
		t.Errorf("unexpected Proxy: %s", opts.Proxy)
	}
	if opts.Page != 5 {
		t.Errorf("unexpected Page: %d", opts.Page)
	}
	if len(opts.Headers) != 2 {
		t.Errorf("expected 2 headers, got %d", len(opts.Headers))
	}
}

func TestOptionsStruct_EmptyHeaders(t *testing.T) {
	opts := options{
		Query:   "test",
		Engine:  "google",
		Page:    1,
		Headers: []string{},
	}
	if len(opts.Headers) != 0 {
		t.Errorf("expected 0 headers, got %d", len(opts.Headers))
	}
}

func TestOptionsStruct_NilHeaders(t *testing.T) {
	opts := options{
		Query:  "test",
		Engine: "google",
		Page:   1,
	}
	if opts.Headers != nil {
		t.Error("expected nil Headers by default")
	}
}
