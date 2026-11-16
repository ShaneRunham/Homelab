#!/usr/bin/env bash
# homelab-doctor: one health check for the PC and homelab.
# Part 1 reads the Discord bot's live problem list (collect.py problems(), written every minute).
# Part 2 runs the checks the bot doesn't: the "Gotchas" in ~/CLAUDE.md and patches that updates undo.
# Read-only, no sudo. Exit code = number of BAD lines.

bad=0
ok()   { printf '  \e[32mOK\e[0m    %s\n' "$*"; }
warn() { printf '  \e[33mWARN\e[0m  %s\n' "$*"; }
fail() { printf '  \e[31mBAD\e[0m   %s\n' "$*"; bad=$((bad+1)); }

echo "== Bot's live problems (containers, services, Kuma, backup, disks, SATA, kernel default, expiries, heartbeat)"
state=~/homelab/home-assistant/config/homelab-state.json
if [[ ! -r $state ]]; then
  fail "can't read $state: is homelab-bot running?"
else
  python3 - "$state" <<'EOF' || bad=$((bad+1))
import json, sys, time
s = json.load(open(sys.argv[1]))
age = time.time() - s.get("updated", 0)
if age > 300:
    print(f"  \033[31mBAD\033[0m   bot last reported {age/60:.0f} min ago (systemctl --user status homelab-bot)")
    sys.exit(1)
probs = s.get("problems") or {}
if not probs:
    print(f"  \033[32mOK\033[0m    no problems (reported {age:.0f} s ago)")
for k, v in probs.items():
    print(f"  \033[31mBAD\033[0m   [{k}] {v}")
sys.exit(1 if probs else 0)
EOF
fi

echo "== Kernel and desktop"
k=$(uname -r)
if rpm -q "kernel-modules-$k" >/dev/null 2>&1; then ok "kernel $k has kernel-modules"
else fail "kernel $k has no kernel-modules package: install kernel kernel-modules kernel-modules-extra for it"; fi
lsmod | grep -q '^amdgpu' && ok "amdgpu loaded" || fail "amdgpu not loaded (GPU driver missing)"
[[ -e /sys/class/net/wlp3s0 ]] && ok "Wi-Fi wlp3s0 present" || fail "Wi-Fi wlp3s0 missing (services use 192.168.0.10)"
cs=$(journalctl -b -q --no-pager -g 'CS has been rejected' 2>/dev/null | wc -l)
[[ $cs -eq 0 ]] && ok "no Plasma 'CS has been rejected' errors this boot" \
  || fail "$cs 'CS has been rejected' errors this boot: kernel $k crashes Plasma, go back to 7.2.15 (see ~/CLAUDE.md)"

echo "== Hardware open items"
aer=$(grep -oP 'TOTAL_ERR_COR \K\d+' /sys/bus/pci/devices/0000:03:00.0/aer_dev_correctable 2>/dev/null)
if [[ -z $aer ]]; then warn "can't read the Wi-Fi card's PCIe error count"
elif [[ $aer -eq 0 ]]; then ok "Wi-Fi card PCIe errors: 0 this boot"
else warn "Wi-Fi card PCIe errors: $aer this boot (pcie_aspm=off should keep this at 0)"; fi
lpm=$(cat /sys/class/scsi_host/host4/link_power_management_policy 2>/dev/null)
echo "  info  boot SSD link power policy (host4): ${lpm:-?}"
prev=$(ls -1 ~/.local/state/blackbox/*.log 2>/dev/null | sort | tail -2 | head -1)
cur=$(ls -1 ~/.local/state/blackbox/*.log 2>/dev/null | sort | tail -1)
if [[ -n $prev && $prev != "$cur" ]]; then
  grep -q 'STOP clean shutdown' "$prev" && ok "last session shut down cleanly" \
    || warn "last session ($(basename "$prev" .log)) ended without a clean shutdown: freeze or power loss, run 'blackbox'"
fi

echo "== Sunshine"
bin=$(readlink -f "$(command -v sunshine)" 2>/dev/null)
getcap "$bin" 2>/dev/null | grep -q cap_sys_admin && ok "cap_sys_admin set" \
  || fail "Sunshine lost cap_sys_admin (dnf upgrade): sudo ~/homelab/streaming/install.sh"
grep -qE '^\s*capture\s*=\s*kms' ~/.config/sunshine/sunshine.conf 2>/dev/null && ok "capture = kms" \
  || fail "sunshine.conf lacks 'capture = kms' (portal capture stalls at startup)"

echo "== Patches that updates undo"
oi=$(ls ~/.local/share/pipx/venvs/open-interpreter/lib/python*/site-packages/interpreter/core/llm/run_text_llm.py 2>/dev/null | head -1)
if [[ -z $oi ]]; then warn "Open Interpreter not found"
elif [[ ! -e $oi.orig ]]; then warn "Open Interpreter parser: no .orig, patch state unknown (pipx reinstall?)"
elif cmp -s "$oi" "$oi.orig"; then fail "Open Interpreter parser patch undone (pipx upgrade): code blocks will be cut off"
else ok "Open Interpreter parser patch in place"; fi

echo "== Git (uncommitted changes)"
for r in ~/homelab ~/tv-launcher; do
  n=$(git -C "$r" status --porcelain 2>/dev/null | wc -l)
  [[ $n -eq 0 ]] && ok "${r/#$HOME/\~} clean" || warn "${r/#$HOME/\~}: $n uncommitted file(s) (nightly catch-up at 03:20)"
done

echo
[[ $bad -eq 0 ]] && echo "All clear." || echo "$bad problem(s)."
exit $bad
