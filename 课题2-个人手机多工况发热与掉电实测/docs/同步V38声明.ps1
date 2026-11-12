$ErrorActionPreference = 'Stop'
$root = ((& git rev-parse --show-toplevel) | Select-Object -First 1).ToString().Trim()
if (-not $root) { throw '当前目录不在 git 仓库中，请 cd 到 keti2-repo 后重试' }
$sub = Get-ChildItem -LiteralPath $root -Directory | Where-Object { $_.Name -like '课题2*' } | Select-Object -First 1
if (-not $sub) { throw '未找到课题2 子目录' }
$subPath = $sub.FullName
$utf8 = New-Object System.Text.UTF8Encoding($false)
$marker = 'V38 口径更正'
$pointer = '> **V38 口径更正（2026-11-08）**：按考核要求，CSV 校园点位列已写回「深圳城市职业学院」，`raw_data/` 为同版原始数据表，`evidence/` 新增 7 张本人现场同框照脱敏版（正脸保留、地址行与防伪码遮盖、EXIF 清零）。本文下文的「点位已泛化」「无正面人脸」「3 张 JPG」等表述为历史快照，以 `docs/课题2_V38_变更说明_校名写回与同框照入库.md` 为准。'

function Insert-AfterFirst($file, $text) {
  if (-not (Test-Path -LiteralPath $file)) { Write-Host ('SKIP  ' + $file); return }
  $s = [IO.File]::ReadAllText($file, [Text.Encoding]::UTF8)
  if ($s.Contains($marker)) { Write-Host ('ALREADY  ' + (Split-Path $file -Leaf)); return }
  $nl = if ($s.Contains("`r`n")) { "`r`n" } else { "`n" }
  $L = $s -split "\r?\n"
  $out = @($L[0], '', $text, '') + @($L[1..($L.Count-1)])
  [IO.File]::WriteAllText($file, ($out -join $nl), $utf8)
  Write-Host ('OK  ' + (Split-Path $file -Leaf))
}
Insert-AfterFirst (Join-Path $subPath 'README.md') $pointer
Insert-AfterFirst (Join-Path $subPath 'evidence\隐私处置对照表.md') $pointer

$rf = Join-Path $root 'README.md'
$bullet = '- 补记（V38）：按考核要求补入 `raw_data/` 原始数据表与 7 张本人现场同框照脱敏版；CSV 点位列写回「深圳城市职业学院」、补录 P01 六行逐点时间 10:30~10:55；隐私声明同步见课题2 子目录 `docs/课题2_V38_变更说明_校名写回与同框照入库.md`'
if (-not (Test-Path -LiteralPath $rf)) { Write-Host 'SKIP  根 README.md 不存在' }
else {
  $s = [IO.File]::ReadAllText($rf, [Text.Encoding]::UTF8)
  if ($s.Contains('补记（V38）')) { Write-Host 'ALREADY  根 README 更新日志' }
  else {
    $nl = if ($s.Contains("`r`n")) { "`r`n" } else { "`n" }
    $L = $s -split "\r?\n"
    $idx = -1
    for ($i = 0; $i -lt $L.Count; $i++) { if ($L[$i] -match '^\s*#{1,3}\s*2026-11-08') { $idx = $i; break } }; if ($idx -lt 0) { for ($i = 0; $i -lt $L.Count; $i++) { if ($L[$i] -match '2026-11-08') { $idx = $i; break } } }
    if ($idx -lt 0) { Write-Host 'WARN  根 README 未找到 2026-11-08 锚点，未改动' }
    elseif ($idx + 1 -ge $L.Count) { Write-Host 'WARN  锚点在文件末尾，未改动' }
    else {
      $out = @($L[0..$idx]) + @($bullet) + @($L[($idx+1)..($L.Count-1)])
      [IO.File]::WriteAllText($rf, ($out -join $nl), $utf8)
      Write-Host 'OK  根 README 更新日志'
    }
  }
}
Write-Host 'DONE'
