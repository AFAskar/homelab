# Run elevated in the disposable image-build clone before generalization.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$DriverDirectory)
$ErrorActionPreference = 'Stop'
foreach ($Driver in @('viostor','vioscsi','netkvm')) {
    $Directory = Join-Path $DriverDirectory $Driver
    $Catalog = Join-Path $Directory ($Driver + '.cat')
    $Signature = Get-AuthenticodeSignature -FilePath $Catalog
    if ($Signature.Status -ne 'Valid') { throw "Invalid driver catalog: $Catalog" }
    & pnputil.exe /add-driver (Join-Path $Directory ($Driver + '.inf')) /install
    if ($LASTEXITCODE -notin @(0,3010)) { throw "Driver installation failed: $Driver ($LASTEXITCODE)" }
}
# PnP verifies the catalog's file hashes and Windows enforces kernel signatures.
# Do not disable Secure Boot or driver signature enforcement to fix Code 52.
Write-Output 'Restart the clone, attach a temporary VirtIO disk/NIC, verify device problem codes are zero, then test booting its system disk through VirtIO. Installation alone is not boot verification.'
