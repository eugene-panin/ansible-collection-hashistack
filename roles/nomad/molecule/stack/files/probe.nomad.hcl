job "probe" {
  group "probe" {
    service {
      name     = "probe"
      provider = "consul"
    }

    task "probe" {
      driver = "raw_exec"

      config {
        command = "/bin/sleep"
        args    = ["3600"]
      }

      consul {}

      vault {}

      template {
        data        = <<-EOT
          consul={{ key "probe" }}
          vault={{ with secret "secret/data/probe" }}{{ .Data.data.value }}{{ end }}
        EOT
        destination = "local/out.txt"
      }
    }
  }
}
