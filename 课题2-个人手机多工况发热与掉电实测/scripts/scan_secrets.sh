#!/usr/bin/env bash
# 课题2 · 并入已有仓库后的提交前敏感串扫描
# 用法（在仓库任意位置均可）：
#   bash 课题2/scripts/scan_secrets.sh          # 默认只扫 课题2/ 子目录
#   bash 课题2/scripts/scan_secrets.sh --all    # 全仓库扫描（含既有课题内容）
# 期望：各扫描段无命中，图片 EXIF 全为 0
#
# 说明：扫描式全部为「通用形态」，不含任何具体 SSID / 地名 / 设备名明文，
#       避免扫描规则本身成为泄露源。替换用的明文映射表仅存于本地工具，不入库。
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "✗ 当前不在 git 仓库中。请先 clone 或 cd 到已有仓库再运行。" >&2
  exit 1
}
SUB="$(cd "$(dirname "$0")/.." && pwd)"
REL="${SUB#"$REPO_ROOT"/}"
cd "$REPO_ROOT"

if [ "${1:-}" = "--all" ]; then
  SCOPE=(-- .)
  echo "范围：全仓库（含课题10 等既有内容）"
else
  SCOPE=(-- "$REL")
  echo "范围：仅 $REL/（既有课题内容不改动、不重扫）"
fi
echo "仓库根：$REPO_ROOT"
echo

echo "=== 1/3 标识 / 地理 / 水印残留（通用形态）==="
# Wi-Fi 后跟 6+ 字符具体名称（避开占位符 <Wi-Fi_SSID>）
# 「市级地名 + 院校/餐饮具体名」= 未泛化的地址结构；不用「区·」，避免误伤「摄像头区·屏幕面」
# 防伪(码) + 10 位以上大写字母数字串 = 水印防伪码（含裸码形式）
# 设备名称后跟未打码的字母数字串 = 设备名残留
git grep -nEi \
  'Wi-Fi [A-Za-z0-9_-]{6,}|市[^,]{0,10}(学院|饭堂|职业学院)|防伪(码)?[[:space:]]*[A-Z0-9]{10,}|设备名称[[:space:]]*[:：][[:space:]]*[A-Za-z0-9_-]{2,}' \
  "${SCOPE[@]}" || true

echo "=== 2/3 疑似明文值（只查值形态，不查标签词，避免「IMEI（已打码）」误报）==="
# 15 位连续数字 = IMEI；14~20 位连续十六进制 = MEID / 序列号
# 上限 20 位可避开 32 位截图文件名 hash 与 64 位 SHA256 校验值（二者非敏感）
git grep -nE \
  '(^|[^0-9])[0-9]{15}([^0-9]|$)|(^|[^0-9A-Fa-f])[0-9A-Fa-f]{14,20}([^0-9A-Fa-f]|$)' \
  "${SCOPE[@]}" || true

echo "=== 3/3 密钥形态 ==="
git grep -nEi \
  'sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|github[_]pat[_]|token[[:space:]]*=|password[[:space:]]*=|api[_-]?key[[:space:]]*=|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY' \
  "${SCOPE[@]}" || true

echo
echo "=== 附加 A：未脱敏素材是否被误加入 ==="
git ls-files -- "$REL" | grep -E '原图|原版|仓库版|未打码|进行中|勿提交|文档包\.zip|旧档_废弃|^\.env|\.token$|\.pem$|\.key$' || true

echo "=== 附加 B：本次 add 是否触碰了既有课题内容 ==="
git diff --cached --name-only -- . ":(exclude)$REL" | sed 's/^/  ⚠ /' || true

echo "=== 附加 C：图片 EXIF ==="
python3 - "$REL/evidence" <<'PY'
from PIL import Image
import glob, sys, os
d = sys.argv[1]
files = sorted(glob.glob(os.path.join(d, '*.jpg')) + glob.glob(os.path.join(d, '*.png')))
bad = 0
for p in files:
    n = len(Image.open(p).getexif())
    print(f'  {p}: EXIF键数={n}')
    if n: bad += 1
print('  ✗ 存在未清空元数据' if bad else '  ✓ 全部为 0')
if not files:
    print('  ⚠ 未找到图片，请确认 evidence/ 是否完整')
PY

echo
echo "若各扫描段均无输出、附加 A/B 无 ⚠、附加 C 显示 ✓，即可 git commit。"
echo "任何命中都先停下处理——公开仓 push 后无法收回。"
