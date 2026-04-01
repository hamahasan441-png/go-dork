package main

import (
	"fmt"
	"io"
	"math"
	"net/http"
	"strings"
	"time"

	log "github.com/projectdiscovery/gologger"
	"ktbs.dev/mubeng/pkg/mubeng"
)

const maxRetries = 3

func (opt *options) get(url string) string {
	var lastErr error
	for attempt := 0; attempt < maxRetries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(math.Pow(2, float64(attempt))) * time.Second
			log.Info().Msgf("Retry %d/%d after %v for %s", attempt, maxRetries-1, backoff, url)
			time.Sleep(backoff)
		}

		body, err := opt.doRequest(url)
		if err != nil {
			lastErr = err
			continue
		}
		return body
	}

	log.Warning().Msgf("All %d attempts failed for %s: %v", maxRetries, url, lastErr)
	return ""
}

func (opt *options) doRequest(url string) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", fmt.Errorf("creating request: %w", err)
	}

	for _, h := range opt.Headers {
		parts := strings.SplitN(h, ":", 2)
		if len(parts) != 2 {
			continue
		}
		req.Header.Set(parts[0], parts[1])
	}

	if opt.Proxy != "" {
		client.Transport, err = mubeng.Transport(opt.Proxy)
		if err != nil {
			return "", fmt.Errorf("setting up proxy: %w", err)
		}

		req.Header.Add("Connection", "close")
	}

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("executing request: %w", err)
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("reading response body: %w", err)
	}
	return string(data), nil
}
