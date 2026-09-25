job "bridged" {
  group "web" {
    network {
      mode = "bridge"

      port "http" {
        to = 8000
      }
    }

    task "serve" {
      driver = "exec"

      config {
        command = "/usr/bin/python3"
        args    = ["local/probe.py"]
      }

      env {
        HOST_API = "https://${NOMAD_HOST_IP_http}:4646/v1/status/leader"
      }

      template {
        destination = "local/probe.py"
        data        = <<-EOT
          import http.server, ssl, threading, time, urllib.request, os
          unverified = ssl._create_unverified_context()
          def probe(url):
              try:
                  urllib.request.urlopen(url, timeout=5, context=unverified)
                  return "ok"
              except urllib.error.HTTPError:
                  return "ok"
              except Exception as error:
                  return type(error).__name__ + " " + str(error)[:120] + " " + url
          def loop():
              while True:
                  out = "egress=" + probe("https://github.com/") + "\nhost=" + probe(os.environ["HOST_API"]) + "\n"
                  with open(os.path.join(os.environ["NOMAD_ALLOC_DIR"], "data", "probe.txt"), "w") as handle:
                      handle.write(out)
                  time.sleep(3)
          threading.Thread(target=loop, daemon=True).start()
          http.server.HTTPServer(("0.0.0.0", 8000), http.server.SimpleHTTPRequestHandler).serve_forever()
        EOT
      }
    }
  }
}
