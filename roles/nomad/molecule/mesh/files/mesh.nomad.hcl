job "mesh" {
  group "web" {
    network {
      mode = "bridge"

      port "http" {
        static = 18080
        to     = 8080
      }
    }

    service {
      name     = "web"
      port     = "8080"
      provider = "consul"

      connect {
        sidecar_service {}
      }
    }

    task "web" {
      driver = "docker"

      config {
        image   = "probe:local"
        command = "/bin/busybox"
        args    = ["httpd", "-f", "-p", "0.0.0.0:8080", "-h", "/local"]
      }

      template {
        data        = "hello through the mesh\n"
        destination = "local/index.html"
      }
    }
  }

  group "caller" {
    network {
      mode = "bridge"
    }

    service {
      name     = "caller"
      provider = "consul"

      connect {
        sidecar_service {
          proxy {
            upstreams {
              destination_name = "web"
              local_bind_port  = 9090
            }
          }
        }
      }
    }

    task "caller" {
      driver = "docker"

      config {
        image   = "probe:local"
        command = "/bin/busybox"
        args    = ["sh", "-c", "while true; do /bin/busybox wget -q -O /alloc/data/out.txt http://127.0.0.1:9090/; /bin/busybox sleep 2; done"]
      }
    }
  }
}
