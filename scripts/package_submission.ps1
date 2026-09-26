param(
    [string]$OutputPath
)

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$projectParent = Split-Path -Parent $projectRoot

if (-not $OutputPath) {
    $OutputPath = Join-Path $projectParent '2412190733干宸骅.zip'
}

$pendingChanges = & git -C $projectRoot status --porcelain
if ($LASTEXITCODE -ne 0) {
    throw '无法读取 Git 仓库状态。'
}
if ($pendingChanges) {
    throw '仓库中存在尚未提交的修改。请先提交并推送，再创建压缩包。'
}

if (Test-Path -LiteralPath $OutputPath) {
    throw "目标压缩包已经存在，请先移动或删除后重试：$OutputPath"
}

& git -C $projectRoot archive --format=zip "--output=$OutputPath" HEAD
if ($LASTEXITCODE -ne 0) {
    throw 'Git 归档失败。'
}

$archive = Get-Item -LiteralPath $OutputPath
$sizeInMegabytes = [Math]::Round($archive.Length / 1MB, 2)
if ($archive.Length -ge 200MB) {
    throw "压缩包大小为 $sizeInMegabytes MB，超过 200 MB 限制。"
}

Write-Output "已创建：$($archive.FullName)"
Write-Output "大小：$sizeInMegabytes MB"
Write-Output '压缩包只包含 Git 已提交文件，不包含 .env。'
