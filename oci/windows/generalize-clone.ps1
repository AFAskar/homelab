# Destructive to the disposable build clone only. Never run on the source VM.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][guid]$ExpectedCloneUUID,
    [Parameter(Mandatory=$true)][guid]$SourceUUID,
    [Parameter(Mandatory=$true)][string]$SourceAccount,
    [Parameter(Mandatory=$true)][SecureString]$LabPassword
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Actual = [guid](Get-CimInstance Win32_ComputerSystemProduct).UUID
if ($Actual -ne $ExpectedCloneUUID -or $Actual -eq $SourceUUID) { throw 'Refusing: source/clone UUID guard failed' }
if ([Security.Principal.WindowsIdentity]::GetCurrent().User.Value -notmatch '-500$') { throw 'Use the clone built-in administrator after verifying access' }
if (-not (Confirm-SecureBootUEFI) -or -not (Get-Tpm).TpmReady) { throw 'Secure Boot and ready TPM required' }
if ((Get-CimInstance Win32_OperatingSystem).Caption -notmatch 'Windows 11') { throw 'Windows 11 required' }
if ((Get-BitLockerVolume -MountPoint C:).EncryptionPercentage -ne 0) { throw 'Use a fully decrypted clone for OCI import' }
$SourceUser = Get-LocalUser -Name $SourceAccount -ErrorAction SilentlyContinue
if ($SourceUser) {
    if ($SourceUser.SID.Value -match '-500$') { throw 'Cannot delete the built-in administrator' }
    # Log out only the copied source account before unloading its copied profile.
    Get-ScheduledTask -TaskName 'MPMB*' -ErrorAction SilentlyContinue | Stop-ScheduledTask
    Get-ScheduledTask -TaskName 'MPMB*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    try { $Sessions = & quser.exe $SourceAccount 2>$null } catch { $Sessions = @() }
    foreach ($Line in ($Sessions | Select-Object -Skip 1)) {
        $Fields = ($Line.Trim().TrimStart('>') -split '\s+')
        $SessionId = if ($Fields[1] -match '^\d+$') { $Fields[1] } else { $Fields[2] }
        if ($Fields[0] -eq $SourceAccount -and $SessionId -match '^\d+$') { & logoff.exe $SessionId }
    }
    # Stop copied background workers that keep the source profile loaded.
    Get-CimInstance Win32_Process | ForEach-Object {
        try {
            $Owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwnerSid
            if ($Owner.Sid -eq $SourceUser.SID.Value) { Invoke-CimMethod -InputObject $_ -MethodName Terminate | Out-Null }
        } catch { }
    }
    Start-Sleep -Seconds 10
    $Profile = Get-CimInstance Win32_UserProfile | Where-Object { $_.SID -eq $SourceUser.SID.Value }
    if ($Profile.Loaded) { throw 'Copied source profile remains loaded; stop and inspect' }
    if ($Profile) { $Profile | Remove-CimInstance }
    Remove-LocalUser -SID $SourceUser.SID
}
if (Test-Path (Join-Path 'C:\Users' $SourceAccount)) { throw 'Copied source profile directory remains; inspect it before proceeding' }
Get-ScheduledTask -TaskName 'MPMB*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
$Winlogon = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Set-ItemProperty $Winlogon AutoAdminLogon '0'
Remove-ItemProperty $Winlogon DefaultPassword,DefaultUserName,DefaultDomainName -ErrorAction SilentlyContinue
Remove-Item HKLM:\SYSTEM\Setup\LabConfig -Recurse -Force -ErrorAction SilentlyContinue
# Stop the local SPICE helper before deleting its open temporary log.
Get-Service vdservice -ErrorAction SilentlyContinue | Set-Service -StartupType Disabled
Get-Service vdservice -ErrorAction SilentlyContinue | Stop-Service -Force
Get-Process vdagent -ErrorAction SilentlyContinue | Stop-Process -Force
foreach ($Directory in @('C:\Users\Public\Documents','C:\Users\Public\Desktop','C:\Users\Public\Downloads','C:\ProgramData\Adobe','C:\Windows\Temp')) {
    if (Test-Path $Directory) { Get-ChildItem $Directory -Force | Remove-Item -Recurse -Force -ErrorAction Stop }
}
Get-CimInstance Win32_ShadowCopy | Remove-CimInstance
Clear-RecycleBin -Force -ErrorAction SilentlyContinue
& powercfg.exe /hibernate off
if ($LASTEXITCODE) { throw 'Failed to disable hibernation in clone' }
Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' ClearPageFileAtShutdown 1
# Zero freed NTFS space without installing an additional utility. Cipher writes
# several passes; capture only after completion and a clean Sysprep shutdown.
& cipher.exe /w:C:\
if ($LASTEXITCODE) { throw 'Free-space clearing failed' }
$Directory = 'C:\Windows\Setup\Scripts'
New-Item -ItemType Directory -Path $Directory -Force | Out-Null
$Answer = Join-Path $Directory 'homelab-unattend.xml'
# The answer file is a secret in the private image. Protect it and remove cached
# copies during SetupComplete; rotate the bootstrap password after deployment.
$Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($LabPassword)
try { $Password = [Security.SecurityElement]::Escape([Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer) }
$Template = Get-Content (Join-Path $PSScriptRoot 'unattend.xml.template') -Raw
$Template.Replace('__WINLAB_PASSWORD__', $Password) | Set-Content -Path $Answer -Encoding UTF8
$Password = $null
& icacls.exe $Answer /inheritance:r /grant '*S-1-5-18:F' '*S-1-5-32-544:F' | Out-Null
if ($LASTEXITCODE) { throw 'Cannot protect the answer file' }
@'
@echo off
powershell.exe -NoProfile -Command "Remove-Item C:\Windows\Panther\unattend.xml,C:\Windows\Setup\Scripts\homelab-unattend.xml -Force -ErrorAction SilentlyContinue"
'@ | Set-Content (Join-Path $Directory 'SetupComplete.cmd') -Encoding ASCII
# SSH exists only for local image construction; OCI administration uses RDP.
# Keep the current build connection alive until Sysprep shuts the guest down.
Set-Service sshd -StartupType Disabled
Remove-Item C:\ProgramData\ssh\ssh_host_*,C:\ProgramData\ssh\administrators_authorized_keys -Force -ErrorAction SilentlyContinue
$Process = Start-Process "$env:WINDIR\System32\Sysprep\Sysprep.exe" -ArgumentList @('/generalize','/oobe','/shutdown',('/unattend:' + $Answer),'/quiet') -PassThru -Wait
if ($Process.ExitCode) { throw "Sysprep failed: $($Process.ExitCode). Inspect Panther logs through the clone console." }
