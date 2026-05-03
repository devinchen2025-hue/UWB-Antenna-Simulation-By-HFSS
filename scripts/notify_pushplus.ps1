param(
    [Parameter(Mandatory = $true)]
    [string]$Title,

    [Parameter(Mandatory = $true)]
    [string]$Content,

    [string]$Token = $env:PUSHPLUS_TOKEN,

    [string]$Topic = $env:PUSHPLUS_TOPIC,

    [ValidateSet("html", "json", "cloudMonitor", "jenkins", "route")]
    [string]$Template = "html",

    [string]$ApiUrl = "https://www.pushplus.plus/send"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Token)) {
    $Token = [Environment]::GetEnvironmentVariable("PUSHPLUS_TOKEN", "User")
}

if ([string]::IsNullOrWhiteSpace($Token)) {
    $Token = [Environment]::GetEnvironmentVariable("PUSHPLUS_TOKEN", "Machine")
}

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "Missing PushPlus token. Set it with: setx PUSHPLUS_TOKEN `"your-token`""
}

if ([string]::IsNullOrWhiteSpace($Topic)) {
    $Topic = [Environment]::GetEnvironmentVariable("PUSHPLUS_TOPIC", "User")
}

if ([string]::IsNullOrWhiteSpace($Topic)) {
    $Topic = [Environment]::GetEnvironmentVariable("PUSHPLUS_TOPIC", "Machine")
}

$payload = [ordered]@{
    token = $Token
    title = $Title
    content = $Content
    template = $Template
}

if (-not [string]::IsNullOrWhiteSpace($Topic)) {
    $payload.topic = $Topic
}

$json = $payload | ConvertTo-Json -Depth 4
$response = Invoke-RestMethod `
    -Method Post `
    -Uri $ApiUrl `
    -ContentType "application/json; charset=utf-8" `
    -Body $json

if ($null -eq $response.code) {
    throw "PushPlus returned an unexpected response: $($response | ConvertTo-Json -Depth 8)"
}

if ([int]$response.code -ne 200) {
    throw "PushPlus notification failed. code=$($response.code), msg=$($response.msg)"
}

Write-Host "PushPlus notification sent: $Title"
