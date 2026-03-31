package main

import (
	"testing"
)

func TestParser_WithMatches(t *testing.T) {
	html := `"><a href="/url?q=https://example.com&amp;sa=U&amp;">Example</a>` +
		`"><a href="/url?q=https://other.com&amp;sa=U&amp;">Other</a>`
	pattern := `"><a href="\/url\?q=(.*?)&amp;sa=U&amp;`

	result := parser(html, pattern)
	if len(result) < 2 {
		t.Fatalf("expected at least 2 matches, got %d", len(result))
	}
	if result[0][1] != "https://example.com" {
		t.Errorf("expected first match to be 'https://example.com', got '%s'", result[0][1])
	}
	if result[1][1] != "https://other.com" {
		t.Errorf("expected second match to be 'https://other.com', got '%s'", result[1][1])
	}
}

func TestParser_SingleMatch(t *testing.T) {
	html := `<a href="/host/1.2.3.4">`
	pattern := `<a href="/host/(.*?)">`

	result := parser(html, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 match, got %d", len(result))
	}
	if result[0][1] != "1.2.3.4" {
		t.Errorf("expected '1.2.3.4', got '%s'", result[0][1])
	}
}

func TestParser_ComplexPattern(t *testing.T) {
	html := `<a rel="nofollow" href="//duckduckgo.com/l/?kh=-1&amp;uddg=https%3A%2F%2Fexample.com">`
	pattern := `<a rel="nofollow" href="//duckduckgo.com/l/\?kh=-1&amp;uddg=(.*?)">`

	result := parser(html, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 match, got %d", len(result))
	}
	if result[0][1] != "https%3A%2F%2Fexample.com" {
		t.Errorf("expected encoded URL, got '%s'", result[0][1])
	}
}

func TestParser_MultipleCaptures(t *testing.T) {
	html := `Name: John, Age: 30, Name: Jane, Age: 25`
	pattern := `Name: (.*?), Age: (\d+)`

	result := parser(html, pattern)
	if len(result) != 2 {
		t.Fatalf("expected 2 matches, got %d", len(result))
	}
	if result[0][1] != "John" || result[0][2] != "30" {
		t.Errorf("unexpected first match: %v", result[0])
	}
	if result[1][1] != "Jane" || result[1][2] != "25" {
		t.Errorf("unexpected second match: %v", result[1])
	}
}

func TestParser_NoMatches(t *testing.T) {
	html := `<html><body>No search results here</body></html>`
	pattern := `<a href="/host/(.*?)">`

	result := parser(html, pattern)
	if len(result) != 0 {
		t.Errorf("expected 0 matches, got %d", len(result))
	}
}

func TestParser_EmptyHTML(t *testing.T) {
	result := parser("", `<a href="(.*?)">`)
	if len(result) != 0 {
		t.Errorf("expected 0 matches for empty HTML, got %d", len(result))
	}
}

func TestParser_EmptyPattern(t *testing.T) {
	result := parser("<html>test</html>", ``)
	if result == nil {
		t.Error("expected non-nil result for empty pattern")
	}
}

func TestParser_GooglePattern_NoResults(t *testing.T) {
	html := `<html><body>Your search did not match any documents</body></html>`
	pattern := `"><a href="\/url\?q=(.*?)&amp;sa=U&amp;`
	result := parser(html, pattern)
	if len(result) != 0 {
		t.Errorf("expected 0 matches for no-result Google page, got %d", len(result))
	}
}

func TestParser_BingPattern(t *testing.T) {
	html := `</li><li class="b_algo"><h2><a href="https://example.com" h="ID=SERP,test">`
	pattern := `</li><li class=\"b_algo\"><h2><a href=\"(.*?)\" h=\"ID=SERP,`
	result := parser(html, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Bing match, got %d", len(result))
	}
	if result[0][1] != "https://example.com" {
		t.Errorf("expected 'https://example.com', got '%s'", result[0][1])
	}
}

func TestParser_YahooPattern(t *testing.T) {
	html := `" ac-algo fz-l ac-21th lh-24" href="https://yahoo-result.com" referrerpolicy="origin`
	pattern := `" ac-algo fz-l ac-21th lh-24" href="(.*?)" referrerpolicy="origin`
	result := parser(html, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Yahoo match, got %d", len(result))
	}
	if result[0][1] != "https://yahoo-result.com" {
		t.Errorf("expected 'https://yahoo-result.com', got '%s'", result[0][1])
	}
}

func TestParser_AskPattern(t *testing.T) {
	html := `target="_blank" href='https://ask-result.com' data-unified=`
	pattern := `target="_blank" href='(.*?)' data-unified=`
	result := parser(html, pattern)
	if len(result) != 1 {
		t.Fatalf("expected 1 Ask match, got %d", len(result))
	}
	if result[0][1] != "https://ask-result.com" {
		t.Errorf("expected 'https://ask-result.com', got '%s'", result[0][1])
	}
}
