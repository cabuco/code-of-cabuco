# ==============================================================================
# SCRIPT: Real-Time Azure Storage Mount Verification Utility
# Location: Run inside a standard user window to view active uploads live
# ==============================================================================

# Configuration Parameters
$rcloneDir  = "<path_to_your_rclone_folder>"
$driveLetter = "<desired_drive_letter>"
$sasUrl     = "<your_azure_container_sas_url>"

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " LINK FRAMEWORK: Projecting Azure Cloud Container to Windows Explorer" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " [Operational Note] Leave this prompt window minimized during use." -ForegroundColor Yellow
Write-Host " [Operational Note] Close this window or press Ctrl+C to unmount drive." -ForegroundColor Yellow

# Navigate to target RClone binary ecosystem
Set-Location -Path $rcloneDir

# Invoke native background virtual network mount string mapping parameters
& .\rclone.exe mount :azureblob: "$($driveLetter):" --azureblob-sas-url $sasUrl --vfs-cache-mode writes --network-mode
