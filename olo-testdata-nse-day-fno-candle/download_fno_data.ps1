param(
    [string]$OutputFolder = (Join-Path $PSScriptRoot "Day_FNO\NSE"),
    [datetime]$StartDate = [datetime]::ParseExact("08-Jul-2024", "dd-MMM-yyyy", [cultureinfo]::InvariantCulture),
    [datetime]$EndDate = (Get-Date).Date
)
$ErrorActionPreference = "Stop"
$OutputFolder = [IO.Path]::GetFullPath($OutputFolder)
New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
$headers = @{ "user-agent"="Mozilla/5.0"; "referer"="https://www.nseindia.com/all-reports-derivatives"; "accept"="application/zip,*/*" }
$failed=0; $downloaded=0; $unavailable=0
for ($day=$StartDate.Date; $day -le $EndDate.Date; $day=$day.AddDays(1)) {
    if ($day.DayOfWeek -in @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday)) { continue }
    $stamp=$day.ToString("yyyyMMdd"); $name="BhavCopy_NSE_FO_0_0_0_${stamp}_F_0000.csv.zip"
    $target=Join-Path $OutputFolder $name
    if (Test-Path -LiteralPath $target) { continue }
    $temp="$target.download.zip"; $extract=Join-Path ([IO.Path]::GetTempPath()) ("nse-fno-"+[guid]::NewGuid().ToString("N"))
    $url="https://nsearchives.nseindia.com/content/fo/$name"
    try {
        Invoke-WebRequest -Uri $url -Headers $headers -OutFile $temp -TimeoutSec 45 -UseBasicParsing
        New-Item -ItemType Directory -Path $extract | Out-Null
        Expand-Archive -LiteralPath $temp -DestinationPath $extract -Force
        $csv=Get-ChildItem -LiteralPath $extract -File -Filter *.csv | Select-Object -First 1
        if (-not $csv) { throw "Archive contains no CSV" }
        $header=Get-Content -LiteralPath $csv.FullName -TotalCount 1
        if ($header -notmatch '(?i)(TckrSymb|SYMBOL)' -or $header -notmatch '(?i)(OpnPric|OPEN)') { throw "Unexpected F&O UDiFF schema" }
        Move-Item -LiteralPath $temp -Destination $target -Force; $downloaded++
        Write-Host "[OK] $name" -ForegroundColor Green
    } catch {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
        if ($_.Exception.Response.StatusCode.value__ -eq 404) { $unavailable++ } else { $failed++; Write-Warning "$name : $($_.Exception.Message)" }
    } finally { Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Milliseconds 500
}
Write-Host "Downloaded=$downloaded Unavailable=$unavailable Failed=$failed"
if ($failed) { exit 2 }
