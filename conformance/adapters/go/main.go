// Adapter: teambition/rrule-go. Reads one JSON case per line on stdin,
// writes one result per line on stdout. See conformance/PROTOCOL.md.
//
//	go build -o rrulego_adapter .
//	python3 conformance/score.py -- /path/to/rrulego_adapter
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/teambition/rrule-go"
)

const layout = "20060102T150405"

type input struct {
	ID      string `json:"id"`
	RRule   string `json:"rrule"`
	DTStart string `json:"dtstart"`
	Limit   int    `json:"limit"`
}

// Emitted as a map so that an empty occurrence list still serialises as
// "occurrences":[] and is never confused with a refusal.
func emit(id string, occ []string, err error) []byte {
	m := map[string]interface{}{"id": id}
	if err != nil {
		m["error"] = err.Error()
	} else {
		m["occurrences"] = occ
	}
	b, _ := json.Marshal(m)
	return b
}

// All cases are floating local time; UTC is used as a fixed-offset clock so
// that no tz database enters the answer.
func expand(c input) (occ []string, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("panic: %v", r)
		}
	}()
	dt, err := time.ParseInLocation(layout, c.DTStart, time.UTC)
	if err != nil {
		return nil, err
	}
	opt, err := rrule.StrToROptionInLocation(c.RRule, time.UTC)
	if err != nil {
		return nil, err
	}
	opt.Dtstart = dt
	r, err := rrule.NewRRule(*opt)
	if err != nil {
		return nil, err
	}
	next := r.Iterator()
	occ = []string{}
	for len(occ) < c.Limit {
		t, ok := next()
		if !ok {
			break
		}
		occ = append(occ, t.Format(layout))
	}
	return occ, nil
}

func main() {
	in := bufio.NewScanner(os.Stdin)
	in.Buffer(make([]byte, 0, 1<<20), 1<<20)
	out := bufio.NewWriter(os.Stdout)
	defer out.Flush()
	for in.Scan() {
		line := in.Bytes()
		if len(line) == 0 {
			continue
		}
		var c input
		if err := json.Unmarshal(line, &c); err != nil {
			continue
		}
		occ, err := expand(c)
		out.Write(emit(c.ID, occ, err))
		out.WriteByte('\n')
	}
}
