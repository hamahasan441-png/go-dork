package main

import (
	"testing"
)

func TestCustomHeaders_String_Empty(t *testing.T) {
	h := customHeaders{}
	if s := h.String(); s != "" {
		t.Errorf("expected empty string, got '%s'", s)
	}
}

func TestCustomHeaders_String_Single(t *testing.T) {
	h := customHeaders{"Authorization: Bearer token"}
	expected := "Authorization: Bearer token"
	if s := h.String(); s != expected {
		t.Errorf("expected '%s', got '%s'", expected, s)
	}
}

func TestCustomHeaders_String_Multiple(t *testing.T) {
	h := customHeaders{"Accept: text/html", "X-Custom: value"}
	expected := "Accept: text/html, X-Custom: value"
	if s := h.String(); s != expected {
		t.Errorf("expected '%s', got '%s'", expected, s)
	}
}

func TestCustomHeaders_Set_Single(t *testing.T) {
	var h customHeaders
	err := h.Set("Content-Type: application/json")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(h) != 1 {
		t.Fatalf("expected 1 header, got %d", len(h))
	}
	if h[0] != "Content-Type: application/json" {
		t.Errorf("unexpected header: '%s'", h[0])
	}
}

func TestCustomHeaders_Set_Multiple(t *testing.T) {
	var h customHeaders
	_ = h.Set("Header1: val1")
	_ = h.Set("Header2: val2")
	_ = h.Set("Header3: val3")
	if len(h) != 3 {
		t.Fatalf("expected 3 headers, got %d", len(h))
	}
}

func TestCustomHeaders_Set_ReturnsNil(t *testing.T) {
	var h customHeaders
	err := h.Set("any value")
	if err != nil {
		t.Errorf("Set should always return nil, got: %v", err)
	}
}

func TestCustomHeaders_Set_EmptyValue(t *testing.T) {
	var h customHeaders
	_ = h.Set("")
	if len(h) != 1 {
		t.Fatalf("expected 1 header (even empty), got %d", len(h))
	}
}
