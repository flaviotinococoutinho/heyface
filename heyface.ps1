param([string]$Task = "up", [Parameter(ValueFromRemainingArguments=$true)][string[]]$Rest)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Invoke-Docker { & docker @args; if ($LASTEXITCODE -ne 0) { throw "Docker failed ($LASTEXITCODE)" } }
switch ($Task) {
    { $_ -in "init", "up" } {
        Invoke-Docker run --rm -v "${PSScriptRoot}:/workspace" -w /workspace python:3.12-slim-bookworm python scripts/bootstrap.py
        if ($Task -eq "up") {
            Invoke-Docker build --target runtime -t heyface/gateway:local services/gateway
            Invoke-Docker build --target runtime -t heyface/vision:local services/vision
            Invoke-Docker build -t heyface/web:local web
            Invoke-Docker compose up -d --no-build --wait --wait-timeout 300
            Write-Host "Heyface is ready. Default URL: http://localhost:8088. Access key: .secrets/demo-token.txt"
        }
    }
    "stop" { Invoke-Docker compose stop }
    "status" { Invoke-Docker compose ps }
    "logs" { Invoke-Docker compose logs --tail=100 @Rest }
    "token" { Get-Content .secrets/demo-token.txt }
    "test" {
        Invoke-Docker build --target test -t heyface/vision-tests:local services/vision
        Invoke-Docker compose -f compose.yaml -f compose.test.yaml --profile test run --rm vision-tests
        Invoke-Docker build --target test -t heyface/gateway-tests:local services/gateway
        Invoke-Docker compose -f compose.yaml -f compose.test.yaml --profile test run --rm gateway-tests
    }
    { $_ -in "demo", "smoke", "benchmark", "backup", "calibrate", "score-pairs" } {
        Invoke-Docker compose -f compose.yaml -f compose.test.yaml --profile test run --rm tools $Task @Rest
    }
    default { throw "Use up, init, stop, status, logs, token, test, demo, smoke, benchmark, backup, calibrate or score-pairs." }
}
