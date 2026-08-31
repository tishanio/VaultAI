# NPM Wrapper Script
# This script works around a broken npm-prefix.js installation
# Usage: .\npm-wrapper.ps1 <npm-command> [args...]

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

$npmCliPath = "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"

if (-not (Test-Path $npmCliPath)) {
    Write-Host "Error: npm-cli.js not found at $npmCliPath" -ForegroundColor Red
    exit 1
}

& node $npmCliPath @Arguments
exit $LASTEXITCODE
