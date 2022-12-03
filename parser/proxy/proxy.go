package main


import (
  "bytes"
  "log"
  "encoding/json"
  "io/ioutil"
  "flag"
  "net/url"
  "net/http"
  "net/http/httputil"
  "time"
  "strconv"
  "fmt"
)

var new_host string
var remote = url.URL{}
var current_payload []byte

type ProxyHandler struct {
  p *httputil.ReverseProxy
}

type ResponseLog struct {
  Status_code int
  Body []byte
  Headers map[string][]string
  // cookies
}

type RequestLog struct {
  Payload string

  Protocol string
  Path string
  Method string
  Headers map[string][]string
  // cookies
}

type RecordLog struct {
  Request RequestLog
  Response ResponseLog
}


func dump_response(resp *http.Response, body []byte) {
  req := &RecordLog{
    RequestLog{string(current_payload), resp.Request.Proto, resp.Request.URL.String(), resp.Request.Method, resp.Request.Header},
    ResponseLog{resp.StatusCode, body, resp.Header},
  }
  current_payload = make([]byte, 0)
  log_obj, err := json.Marshal(req)
  if err != nil {
    panic(err)
    return
  }
  fmt.Println(string(log_obj))
}


func parse_response(resp *http.Response) (err error) {
  b, err := ioutil.ReadAll(resp.Body)

  if err != nil {
    panic(err)
    return err
  }
  err = resp.Body.Close()
  if err != nil {
    panic(err)
    return err
  }
  body := ioutil.NopCloser(bytes.NewReader(b))
  resp.Body = body
  dump_response(resp, b)
  return nil

}


func (ph *ProxyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
  b, err := ioutil.ReadAll(r.Body)

  if err != nil {
    panic(err)
    return
  }
  err = r.Body.Close()
  if err != nil {
    panic(err)
    return
  }
  body := ioutil.NopCloser(bytes.NewReader(b))
  current_payload = b
  r.Body = body
  r.Host = remote.Host
  ph.p.ServeHTTP(w, r)
}

func main() {

  host_ptr := flag.String("host", "https://example.com", "The host to forward to.")
  proxy_port := flag.Int("port", 8080, "The port to listen on.")
  flag.Parse()

  mux := http.NewServeMux()
  remote, err := url.Parse(*host_ptr)
  if err != nil {
    panic(err)
  }

  proxy := httputil.NewSingleHostReverseProxy(remote)
  proxy.ModifyResponse = parse_response
  mux.Handle("/", &ProxyHandler{proxy})
  server := &http.Server{
    Addr:       ":"+strconv.Itoa(*proxy_port),
    Handler:    mux,
    ReadTimeout: 10 * time.Second,
    WriteTimeout: 10 * time.Second,
    MaxHeaderBytes: 1 << 20,
  }
  log.Fatal(server.ListenAndServe())
}
