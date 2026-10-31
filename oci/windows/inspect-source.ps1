# Read-only source-image preflight. Run in the source Windows guest; no setup changes.
$ErrorActionPreference = 'Continue'
$SecureBootState = $null
try { $SecureBootState = Confirm-SecureBootUEFI } catch { $SecureBootState = $_.Exception.Message }
$Result = [ordered]@{
    OperatingSystem = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture
    Tpm = Get-Tpm | Select-Object TpmPresent,TpmReady,TpmEnabled,TpmActivated
    SecureBoot = $SecureBootState
    InstallerOverrides = Get-ItemProperty HKLM:\SYSTEM\Setup\LabConfig -ErrorAction SilentlyContinue |
        Select-Object BypassTPMCheck,BypassSecureBootCheck,BypassRAMCheck,BypassCPUCheck
    Disks = Get-Disk | Select-Object Number,PartitionStyle,BusType,Size
    Encryption = Get-BitLockerVolume -MountPoint C: -ErrorAction SilentlyContinue |
        Select-Object VolumeStatus,ProtectionStatus,EncryptionPercentage
    VirtioDrivers = Get-WindowsDriver -Online -All | Where-Object { $_.ProviderName -match 'Red Hat|VirtIO' } |
        Select-Object Driver,OriginalFileName,ProviderName,Version,ClassName
}
$Result | ConvertTo-Json -Depth 5
