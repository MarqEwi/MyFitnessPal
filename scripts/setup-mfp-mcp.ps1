# Einrichtung von mfp-mcp (MyFitnessPal MCP-Server) fuer Claude Code unter Windows.
# Jeder Schritt wird geprueft; bei einem Fehler bricht das Skript mit Hinweis ab.
# Aufruf im Repo-Ordner:  .\scripts\setup-mfp-mcp.ps1  [-SkipAuth] [-AutoRefresh] [-Username MarqEwi]

param(
    [string]$Username = "MarqEwi",
    [switch]$SkipAuth,
    [switch]$AutoRefresh
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Package  = "mfp-mcp==0.3.0"
$Py       = "3.12"   # lxml 5.x (Abhaengigkeit) hat keine fertigen Pakete fuer Python 3.13+/3.14
$FromSpec = if ($AutoRefresh) { "mfp-mcp[autorefresh]==0.3.0" } else { $Package }

function Step($n, $text) { Write-Host "`n== Schritt $n : $text ==" -ForegroundColor Cyan }
function Ok($text)   { Write-Host "  [OK] $text" -ForegroundColor Green }
function Fail($text) { Write-Host "  [FEHLER] $text" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- 1. Python + uv
Step 1 "Python 3.10+ und uv pruefen"
$py = $null
foreach ($cmd in @("py -3", "python")) {
    try {
        $v = & ([scriptblock]::Create("$cmd --version")) 2>&1
        if ($v -match "Python (\d+)\.(\d+)") {
            if ([int]$Matches[1] -gt 3 -or ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10)) { $py = "$cmd ($v)"; break }
        }
    } catch {}
}
if ($py) { Ok "Python gefunden: $py" } else { Write-Host "  [INFO] Kein Python >= 3.10 im PATH; uv installiert bei Bedarf selbst eines." }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "  uv fehlt. Installation..."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
    } else {
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Fail "uv ist nach der Installation nicht im PATH. Neues PowerShell-Fenster oeffnen und Skript erneut starten." }
}
Ok ("uv " + (uv --version))
# Claude Code CLI: erst PATH, dann bekannte Installationsorte, sonst Installation anbieten
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    foreach ($cand in @("$env:USERPROFILE\.local\bin", "$env:APPDATA\npm", "$env:LOCALAPPDATA\Programs\claude")) {
        if ((Test-Path "$cand\claude.exe") -or (Test-Path "$cand\claude.cmd")) { $env:Path = "$cand;$env:Path"; break }
    }
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "  Claude Code CLI ('claude') nicht gefunden. Offizieller Installer: irm https://claude.ai/install.ps1 | iex" -ForegroundColor Yellow
    if ((Read-Host "  Jetzt installieren? [j/N]") -match '^[jJyY]') {
        irm https://claude.ai/install.ps1 | iex
        $env:Path = "$env:USERPROFILE\.local\bin;" + [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    }
}
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) { Fail "Claude Code CLI ('claude') nicht verfuegbar. Installieren mit:  irm https://claude.ai/install.ps1 | iex  , dann neues PowerShell-Fenster oeffnen und Skript erneut starten." }
Ok ("Claude Code " + (claude --version))

# ---------------------------------------------------------------- 2. mfp-mcp installieren
Step 2 "mfp-mcp installieren und starten"
$help = uvx --python $Py --from $FromSpec mfp-mcp --help 2>&1
if ($LASTEXITCODE -ne 0 -or ($help -notmatch "auth")) { Fail "uvx --python $Py --from $FromSpec mfp-mcp --help schlug fehl:`n$help" }
Ok "uvx mfp-mcp startet (Version 0.3.0, Python $Py)"
if ($AutoRefresh) {
    uvx --python $Py --from $FromSpec playwright install chromium
    if ($LASTEXITCODE -ne 0) { Fail "playwright install chromium schlug fehl" }
    Ok "Chromium fuer Auto-Refresh installiert"
}

# ---------------------------------------------------------------- 3. Cookie
Step 3 "Session-Cookie aus Chrome hinterlegen"
$cookiePath = uv run --quiet --python $Py --with $Package python -c "from myfitnesspal_mcp import config; print(config.cookies_path())"
if (-not $SkipAuth) {
    Write-Host @"
  1. In Chrome auf https://www.myfitnesspal.com einloggen.
  2. F12 -> Application -> Storage -> Cookies -> https://www.myfitnesspal.com
  3. Wert von  __Secure-next-auth.session-token  kopieren.
  4. Unten bei 'Paste cookie' einfuegen (Rechtsklick), Enter.
     Fragt das Tool nach dem Benutzernamen: $Username
"@
    $env:MFP_USERNAME = $Username
    uvx --python $Py --from $FromSpec mfp-mcp auth
    if ($LASTEXITCODE -ne 0) { Fail "mfp-mcp auth schlug fehl. Bei 403: `$env:MFP_IMPERSONATE='chrome124' setzen, VPN aus, erneut starten." }
}
if (Test-Path $cookiePath) {
    icacls $cookiePath /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null
    Ok "Cookie gespeichert und auf Benutzer $env:USERNAME beschraenkt: $cookiePath"
} else {
    Fail "Cookie-Datei nicht gefunden: $cookiePath"
}

# ---------------------------------------------------------------- 4. In Claude Code registrieren
Step 4 "MCP-Server in Claude Code registrieren (User-Scope)"
claude mcp remove myfitnesspal -s user 2>$null | Out-Null
if ($AutoRefresh) {
    claude mcp add --scope user myfitnesspal -e "MFP_USERNAME=$Username" -- uvx --python 3.12 --from "mfp-mcp[autorefresh]" mfp-mcp
} else {
    claude mcp add --scope user myfitnesspal -e "MFP_USERNAME=$Username" -- uvx --python 3.12 mfp-mcp
}
if ($LASTEXITCODE -ne 0) { Fail "claude mcp add schlug fehl" }
$status = claude mcp get myfitnesspal 2>&1
if ($status -match "Connected") { Ok "myfitnesspal: Connected" } else { Write-Host $status; Fail "Server nicht verbunden" }

# ---------------------------------------------------------------- 5. Skill kopieren
Step 5 "Skill /mahlzeit installieren"
$skillDir = Join-Path $env:USERPROFILE ".claude\skills\mahlzeit"
New-Item -ItemType Directory -Force $skillDir | Out-Null
Copy-Item (Join-Path $RepoRoot "skills\mahlzeit\SKILL.md") (Join-Path $skillDir "SKILL.md") -Force
Ok "SKILL.md nach $skillDir kopiert (in neuer Claude-Sitzung als /mahlzeit verfuegbar)"

# ---------------------------------------------------------------- 6. Lesetest
Step 6 "Lesetest: Tagebuch heute und gestern"
uv run --python $Py --with $Package python (Join-Path $RepoRoot "scripts\mfp_smoke_test.py")
if ($LASTEXITCODE -ne 0) { Fail "Lesetest meldet Fehler (siehe oben). Details: docs/mfp-tools.md, Abschnitt 6." }
Ok "Lesetest bestanden."
Write-Host "`nNaechster Schritt (Schreibtest, fragt vor dem Schreiben):"
Write-Host "  uv run --python 3.12 --with $Package python scripts\mfp_smoke_test.py --write"
Write-Host "  uv run --python 3.12 --with $Package python scripts\mfp_smoke_test.py --custom-food"
