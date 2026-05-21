$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== ОБЩАЯ ИНФОРМАЦИЯ О ДИСКЕ C:\ ===" -ForegroundColor Green
$disk = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'"
$sizeGB = [math]::Round($disk.Size / 1GB, 2)
$freeGB = [math]::Round($disk.FreeSpace / 1GB, 2)
$usedGB = [math]::Round(($disk.Size - $disk.FreeSpace) / 1GB, 2)
Write-Host "Всего: $sizeGB GB"
Write-Host "Свободно: $freeGB GB"
Write-Host "Занято: $usedGB GB"
Write-Host ""

Write-Host "=== РАЗМЕРЫ КОРНЕВЫХ ПАПОК C:\ ===" -ForegroundColor Green
$rootFolders = Get-ChildItem C:\ -Directory
$results = @()
foreach ($folder in $rootFolders) {
    $bytes = (Get-ChildItem $folder.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $gb = [math]::Round($bytes / 1GB, 2)
    $results += [PSCustomObject]@{ Folder = $folder.Name; SizeGB = $gb; Path = $folder.FullName }
}
$results | Sort-Object SizeGB -Descending | Format-Table -AutoSize

Write-Host "=== СИСТЕМНЫЕ ВРЕМЕННЫЕ ПАПКИ ===" -ForegroundColor Yellow
$systemTemps = @(
    'C:\Windows\Temp',
    'C:\Windows\SoftwareDistribution\Download',
    'C:\Windows\Logs',
    'C:\Windows\Prefetch',
    'C:\ProgramData\Package Cache'
)
foreach ($path in $systemTemps) {
    if (Test-Path $path) {
        $bytes = (Get-ChildItem $path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $mb = [math]::Round($bytes / 1MB, 1)
        Write-Host "$mb MB - $path"
    }
}
Write-Host ""

Write-Host "=== ПОЛЬЗОВАТЕЛЬСКИЕ ПРОФИЛИ ===" -ForegroundColor Yellow
$users = Get-ChildItem 'C:\Users' -Directory
foreach ($user in $users) {
    $profileBytes = (Get-ChildItem $user.FullName -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $gb = [math]::Round($profileBytes / 1GB, 2)
    Write-Host "$gb GB - $($user.Name)"
}
Write-Host ""

Write-Host "=== СИСТЕМНЫЕ ФАЙЛЫ ===" -ForegroundColor Cyan
$sysFiles = @('C:\pagefile.sys', 'C:\hiberfil.sys', 'C:\swapfile.sys')
foreach ($file in $sysFiles) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length
        Write-Host "$([math]::Round($size / 1GB, 2)) GB - $file"
    }
}
Write-Host ""

Write-Host "=== КОРЗИНА ===" -ForegroundColor Cyan
$recycleBin = (Get-ChildItem 'C:\`$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "$([math]::Round($recycleBin / 1MB, 1)) MB в Корзине"
Write-Host ""

Write-Host "=== ПРОВЕРКА Downloads / Documents у пользователей ===" -ForegroundColor Magenta
foreach ($user in $users) {
    $downloads = Join-Path $user.FullName 'Downloads'
    $documents = Join-Path $user.FullName 'Documents'
    if (Test-Path $downloads) {
        $dBytes = (Get-ChildItem $downloads -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        Write-Host "$([math]::Round($dBytes / 1MB, 1)) MB Downloads\$($user.Name)"
    }
    if (Test-Path $documents) {
        $docBytes = (Get-ChildItem $documents -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        Write-Host "$([math]::Round($docBytes / 1MB, 1)) MB Documents\$($user.Name)"
    }
}
