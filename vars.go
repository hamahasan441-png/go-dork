package main

import (
	"net/http"
	"sync"
	"time"
)

var (
	query, engine, proxy string
	headers              customHeaders
	silent               bool
	page                 int
	timeout              int
	delay                int

	queries []string
	client  = http.Client{
		Timeout: 30 * time.Second,
	}
	wg sync.WaitGroup
)
