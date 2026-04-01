package main

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"testing"
)

// mockTransport is a custom http.RoundTripper that returns canned responses
// based on the requested URL. This allows testing search() end-to-end without
// making real network calls.
type mockTransport struct {
	handler func(req *http.Request) (*http.Response, error)
}

func (m *mockTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	return m.handler(req)
}

// setMockTransport installs a mock transport on the global client and returns
// a cleanup function that restores the original transport.
func setMockTransport(handler func(req *http.Request) (*http.Response, error)) func() {
	orig := client.Transport
	client.Transport = &mockTransport{handler: handler}
	return func() { client.Transport = orig }
}

func mockResponseWithBody(body string) *http.Response {
	return &http.Response{
		StatusCode: 200,
		Body:       io.NopCloser(strings.NewReader(body)),
		Header:     make(http.Header),
	}
}

// captureStdout runs fn while capturing stdout and returns the captured output.
func captureStdout(t *testing.T, fn func()) string {
	t.Helper()
	old := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("failed to create pipe: %v", err)
	}
	os.Stdout = w

	fn()

	w.Close()
	os.Stdout = old

	var buf bytes.Buffer
	if _, err := buf.ReadFrom(r); err != nil {
		t.Fatalf("failed to read captured stdout: %v", err)
	}
	return buf.String()
}

// ---------------------------------------------------------------------------
// End-to-end search() tests — these actually call search() instead of manually
// calling get() + parser() separately.
// ---------------------------------------------------------------------------

func TestSearchE2E_Google(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.String(), "google.com/search") {
			t.Errorf("unexpected URL: %s", req.URL)
		}
		body := `"><a href="/url?q=https://example.com&amp;sa=U&amp;">R</a>`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://example.com") {
		t.Errorf("expected output to contain 'https://example.com', got: %s", output)
	}
}

func TestSearchE2E_Shodan(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.String(), "shodan.io/search") {
			t.Errorf("unexpected URL: %s", req.URL)
		}
		// Shodan results are IPs, not full URLs, so they break iterPage
		body := `"><a href="/host/192.168.1.1">192.168.1.1</a>`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "shodan", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
}

func TestSearchE2E_Bing(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.String(), "bing.com/search") {
			t.Errorf("unexpected URL: %s", req.URL)
		}
		body := `</li><li class="b_algo"><h2><a href="https://bing-result.com" h="ID=SERP,test">`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "bing", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://bing-result.com") {
		t.Errorf("expected bing result URL in output, got: %s", output)
	}
}

func TestSearchE2E_Duck(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.String(), "duckduckgo.com") {
			t.Errorf("unexpected URL: %s", req.URL)
		}
		body := `class="result__a" href="https://duck-result.com">`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "duck", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://duck-result.com") {
		t.Errorf("expected duck result URL in output, got: %s", output)
	}
}

func TestSearchE2E_Yahoo(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.String(), "yahoo.com/search") {
			t.Errorf("unexpected URL: %s", req.URL)
		}
		body := `class="ac-algo fz-l ac-21th lh-24" href="https://yahoo-result.com" target="`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "yahoo", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://yahoo-result.com") {
		t.Errorf("expected yahoo result URL in output, got: %s", output)
	}
}

func TestSearchE2E_Ask(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		if !strings.Contains(req.URL.String(), "ask.com/web") {
			t.Errorf("unexpected URL: %s", req.URL)
		}
		body := `target="_blank" href='https://ask-result.com' data-unified=`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "ask", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://ask-result.com") {
		t.Errorf("expected ask result URL in output, got: %s", output)
	}
}

// ---------------------------------------------------------------------------
// Multi-page pagination test
// ---------------------------------------------------------------------------

func TestSearchE2E_MultiPage(t *testing.T) {
	pages := 0
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		pages++
		body := fmt.Sprintf(`"><a href="/url?q=https://result-page%d.com&amp;sa=U&amp;">R</a>`, pages)
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 3}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if pages != 3 {
		t.Errorf("expected 3 page requests, got %d", pages)
	}
	for i := 1; i <= 3; i++ {
		expected := fmt.Sprintf("https://result-page%d.com", i)
		if !strings.Contains(output, expected) {
			t.Errorf("expected output to contain '%s'", expected)
		}
	}
}

// ---------------------------------------------------------------------------
// Google page number formatting: should append "0" (page 1 → "10")
// ---------------------------------------------------------------------------

func TestSearchE2E_GooglePageFormatting(t *testing.T) {
	var requestedURL string
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		requestedURL = req.URL.String()
		return mockResponseWithBody("no results"), nil
	})
	defer cleanup()

	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 1}
		opt.search()
	})

	if !strings.Contains(requestedURL, "start=10") {
		t.Errorf("expected Google start=10, got URL: %s", requestedURL)
	}
}

// ---------------------------------------------------------------------------
// Bing page number formatting: should append "1" (page 1 → "11")
// ---------------------------------------------------------------------------

func TestSearchE2E_BingPageFormatting(t *testing.T) {
	var requestedURL string
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		requestedURL = req.URL.String()
		return mockResponseWithBody("no results"), nil
	})
	defer cleanup()

	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "bing", Page: 1}
		opt.search()
	})

	if !strings.Contains(requestedURL, "first=11") {
		t.Errorf("expected Bing first=11, got URL: %s", requestedURL)
	}
}

// ---------------------------------------------------------------------------
// Yahoo page number formatting: should append "1"
// ---------------------------------------------------------------------------

func TestSearchE2E_YahooPageFormatting(t *testing.T) {
	var requestedURL string
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		requestedURL = req.URL.String()
		return mockResponseWithBody("no results"), nil
	})
	defer cleanup()

	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "yahoo", Page: 1}
		opt.search()
	})

	if !strings.Contains(requestedURL, "b=11") {
		t.Errorf("expected Yahoo b=11, got URL: %s", requestedURL)
	}
}

// ---------------------------------------------------------------------------
// search() with empty response (no matches) should succeed
// ---------------------------------------------------------------------------

func TestSearchE2E_NoResults(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		return mockResponseWithBody("<html>no results</html>"), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if strings.TrimSpace(output) != "" {
		t.Errorf("expected no output, got: %s", output)
	}
}

// ---------------------------------------------------------------------------
// search() with invalid URL-encoded result triggers QueryUnescape error
// ---------------------------------------------------------------------------

func TestSearchE2E_InvalidURLEncoding(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		// %ZZ is invalid percent-encoding that will cause QueryUnescape to fail
		body := `"><a href="/url?q=%ZZinvalid&amp;sa=U&amp;">R</a>`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 1}
		fatal, err = opt.search()
	})

	if err == nil {
		t.Error("expected error for invalid URL encoding")
	}
	if fatal {
		t.Error("expected fatal=false for unescape error")
	}
}

// ---------------------------------------------------------------------------
// search() breaks iterPage when extracted result is not a valid URL
// ---------------------------------------------------------------------------

func TestSearchE2E_BreaksOnNonURL(t *testing.T) {
	pages := 0
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		pages++
		// Return a result that is not a valid URL (no scheme/host)
		body := `"><a href="/url?q=not-a-url&amp;sa=U&amp;">R</a>`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 3}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	// Should break out of page loop after first page finds a non-URL
	if pages != 1 {
		t.Errorf("expected 1 page request (break on non-URL), got %d", pages)
	}
}

// ---------------------------------------------------------------------------
// search() with delay between pages
// ---------------------------------------------------------------------------

func TestSearchE2E_WithDelay(t *testing.T) {
	pages := 0
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		pages++
		body := fmt.Sprintf(`"><a href="/url?q=https://result%d.com&amp;sa=U&amp;">R</a>`, pages)
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	_ = captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 2, Delay: 1} // 1ms delay
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if pages != 2 {
		t.Errorf("expected 2 page requests, got %d", pages)
	}
}

// ---------------------------------------------------------------------------
// search() with query containing special characters (URL encoding)
// ---------------------------------------------------------------------------

func TestSearchE2E_SpecialCharsInQuery(t *testing.T) {
	var requestedURL string
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		requestedURL = req.URL.String()
		return mockResponseWithBody("no results"), nil
	})
	defer cleanup()

	_ = captureStdout(t, func() {
		opt := &options{Query: "site:example.com inurl:admin", Engine: "google", Page: 1}
		opt.search()
	})

	if !strings.Contains(requestedURL, "site%3Aexample.com") {
		t.Errorf("expected URL-encoded query in URL, got: %s", requestedURL)
	}
}

// ---------------------------------------------------------------------------
// search() with Duck DuckGo alternate capture group
// ---------------------------------------------------------------------------

func TestSearchE2E_DuckAlternateCapture(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		// Uses the //duckduckgo.com/l/ variant
		body := `<a rel="nofollow" href="//duckduckgo.com/l/?kh=-1&amp;uddg=https%3A%2F%2Fduck-alt.com">link</a>`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "duck", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://duck-alt.com") {
		t.Errorf("expected duck alternate result URL in output, got: %s", output)
	}
}

// ---------------------------------------------------------------------------
// search() with multiple results on one page
// ---------------------------------------------------------------------------

func TestSearchE2E_MultipleResultsOnePage(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		body := `"><a href="/url?q=https://result1.com&amp;sa=U&amp;">R1</a>` +
			`"><a href="/url?q=https://result2.com&amp;sa=U&amp;">R2</a>` +
			`"><a href="/url?q=https://result3.com&amp;sa=U&amp;">R3</a>`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	lines := strings.Split(strings.TrimSpace(output), "\n")
	if len(lines) != 3 {
		t.Errorf("expected 3 result lines, got %d: %s", len(lines), output)
	}
}

// ---------------------------------------------------------------------------
// search() Google with updated yuRUbf class pattern
// ---------------------------------------------------------------------------

func TestSearchE2E_GoogleYuRUbfPattern(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		body := `class="yuRUbf"><a href="https://new-google-result.com" data-test`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "google", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if !strings.Contains(output, "https://new-google-result.com") {
		t.Errorf("expected yuRUbf pattern result in output, got: %s", output)
	}
}

// ---------------------------------------------------------------------------
// search() with all capture groups empty (should skip result)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// search() with all capture groups empty (should skip result via continue)
// ---------------------------------------------------------------------------

func TestSearchE2E_EmptyCaptureGroupsContinue(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		// DuckDuckGo regex has two alternation capture groups.
		// If a match occurs but the captured URL is empty, it should continue.
		// This HTML will match the first alternative but with an empty URL in group 1.
		body := `<a rel="nofollow" href="//duckduckgo.com/l/?kh=-1&amp;uddg=">empty</a>` +
			`class="result__a" href="https://valid-result.com">`
		return mockResponseWithBody(body), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "duck", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	// The empty capture group should be skipped, but the valid result should be output
	if !strings.Contains(output, "https://valid-result.com") {
		t.Errorf("expected valid result in output, got: %s", output)
	}
}

func TestSearchE2E_EmptyCaptureGroupsSkipped(t *testing.T) {
	cleanup := setMockTransport(func(req *http.Request) (*http.Response, error) {
		// For duck engine, both capture groups can potentially match but be empty
		// Return HTML that doesn't yield useful URLs
		return mockResponseWithBody("<html>no matching patterns here</html>"), nil
	})
	defer cleanup()

	var fatal bool
	var err error
	output := captureStdout(t, func() {
		opt := &options{Query: "test", Engine: "duck", Page: 1}
		fatal, err = opt.search()
	})

	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fatal {
		t.Error("expected fatal=false")
	}
	if strings.TrimSpace(output) != "" {
		t.Errorf("expected no output, got: %s", output)
	}
}
