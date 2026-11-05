# Run in elevated guest console during image preparation, before sysprep.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string[]]$RouterPrivateIPs,
    [Parameter(Mandatory=$true)][SecureString]$AdministratorPassword
)
$ErrorActionPreference = 'Stop'
if ((Get-CimInstance Win32_OperatingSystem).Caption -notmatch 'Windows 11') { throw 'Windows 11 required' }
if (-not (Get-Tpm).TpmPresent) { throw 'TPM is required; no bypass permitted' }
if (-not (Confirm-SecureBootUEFI)) { throw 'Enable Secure Boot in supported firmware first' }
foreach ($IP in $RouterPrivateIPs) {
    $Parsed = $null
    if (-not [Net.IPAddress]::TryParse($IP, [ref]$Parsed) -or $Parsed.AddressFamily -ne 'InterNetwork') { throw 'Router must have a private IPv4 address' }
    if ($IP -notmatch '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)') { throw 'Router source must be RFC1918' }
}
$Admin = Get-LocalUser | Where-Object { $_.SID.Value -match '-500$' }
Set-LocalUser -Name $Admin.Name -Password $AdministratorPassword
Enable-LocalUser -Name $Admin.Name
Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True -DefaultInboundAction Block
# Disable broad built-in RDP rules, then install only the router-scoped rule.
Get-NetFirewallRule -Name 'RemoteDesktop-*' -ErrorAction SilentlyContinue | Disable-NetFirewallRule
Remove-NetFirewallRule -Name 'Homelab-RDP' -ErrorAction SilentlyContinue
New-NetFirewallRule -Name 'Homelab-RDP' -DisplayName 'RDP from OCI subnet routers' -Direction Inbound -Protocol TCP -LocalPort 3389 -RemoteAddress $RouterPrivateIPs -Action Allow -Profile Any | Out-Null
Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp' -Name UserAuthentication -Value 1
Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0
Set-Service TermService -StartupType Automatic
Start-Service TermService
# Keep password in a password manager. Never put credentials into user_data, Git,
# Terraform variables or image metadata. Re-generalize and rotate after launch.
