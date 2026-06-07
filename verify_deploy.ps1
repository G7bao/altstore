Start-Sleep -Seconds 20
$url = "https://g7bao.github.io/altstore/ma1plus.json"
Write-Host "Checking: $url"
try {
    $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 15
    Write-Host "Status: $($r.StatusCode)"
    Write-Host "Size: $($r.Content.Length) bytes"
    $j = $r.Content | ConvertFrom-Json
    Write-Host "Source Name: $($j.name)"
    Write-Host "Identifier: $($j.identifier)"
    Write-Host "Apps: $($j.apps.Count)"
    Write-Host "News: $($j.news.Count)"
    Write-Host ""
    Write-Host "LIVE URL: $url"
    Write-Host "DEPLOYMENT SUCCESSFUL"
} catch {
    Write-Host "Not ready yet: $($_.Exception.Message)"
    Write-Host "GitHub Pages may need another minute to deploy. Try the URL manually."
}
