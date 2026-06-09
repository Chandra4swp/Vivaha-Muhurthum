<#
Deploy helper for Fly.io. Run after installing flyctl and logging in.
Usage:
  1. Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
  2. Login: flyctl auth login
  3. From project root run: .\deploy-fly.ps1 -AppName your-app-name -Org your-org
#>

param(
    [string]$AppName = "vivaha-muhurtham",
    [string]$Org = "personal"
)

Write-Host "Launching Fly app (interactive) for app:$AppName org:$Org"
flyctl launch --name $AppName --org $Org

Write-Host "Deploying..."
flyctl deploy --app $AppName

Write-Host "To add a custom domain use: flyctl ips check --app $AppName or see Fly docs for DNS setup."
