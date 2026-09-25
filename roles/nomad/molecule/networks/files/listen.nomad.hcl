job "listen" {
  group "private" {
    network {
      port "http" {}
    }

    task "serve" {
      driver = "raw_exec"

      config {
        command = "/usr/bin/python3"
        args    = ["-m", "http.server", "${NOMAD_PORT_http}", "--bind", "${NOMAD_IP_http}"]
      }
    }
  }

  group "public" {
    network {
      port "http" {
        host_network = "public"
      }
    }

    task "serve" {
      driver = "raw_exec"

      config {
        command = "/usr/bin/python3"
        args    = ["-m", "http.server", "${NOMAD_PORT_http}", "--bind", "${NOMAD_IP_http}"]
      }
    }
  }
}
