$ErrorActionPreference = "Stop"

# Run from backend folder. This script preserves the existing database volume.
$backend = (Get-Location).Path
if (!(Test-Path (Join-Path $backend "docker-compose.yml")) -or !(Test-Path (Join-Path $backend "migrations\versions"))) {
    throw "Backend klasöründe çalıştır. docker-compose.yml veya migrations\versions bulunamadı."
}
$repo = (& git -C $backend rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) { throw "Git deposu bulunamadı." }

$canonicalRel = "backend/migrations/versions/2d87a7f6bfdf_initial_schema.py"
$canonical = (& git -C $repo show "origin/security/backend-hardening:$canonicalRel" 2>&1 | Out-String)
if ($LASTEXITCODE -ne 0 -or !$canonical.StartsWith('"""initial schema')) {
    throw "Doğru migration origin/security/backend-hardening dalından alınamadı. Hiçbir dosya değiştirilmedi."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $repo ".repair-backup-$stamp"
New-Item -ItemType Directory -Path $backup | Out-Null

$versions = Join-Path $backend "migrations\versions"
$oldMigration = Join-Path $versions "25b2c2624266_initial_schema.py"
$newMigration = Join-Path $versions "2d87a7f6bfdf_initial_schema.py"

if (Test-Path $oldMigration) {
    Copy-Item $oldMigration (Join-Path $backup "25b2c2624266_initial_schema.py")
    Move-Item $oldMigration (Join-Path $backup "25b2c2624266_initial_schema.py.original")
}
if (Test-Path $newMigration) {
    Copy-Item $newMigration (Join-Path $backup "2d87a7f6bfdf_initial_schema.py.before")
}
Set-Content -Path $newMigration -Value $canonical -Encoding utf8

$composePath = Join-Path $backend "docker-compose.yml"
$compose = Get-Content $composePath -Raw
$composeBefore = $compose
$compose = $compose.Replace('"127.0.0.1:16379:6379"', '"127.0.0.1:3307:3306"')
$compose = $compose.Replace('REDIS_URL: redis://:${REDIS_PASSWORD:-change-me-local-only}@redis:6379/0',
                            'REDIS_URL: redis://:${REDIS_PASSWORD:-avatar-test-only}@redis:6379/0')
if ($compose -eq $composeBefore) {
    Write-Host "Compose dosyasında beklenen hatalı port satırı bulunamadı; migration düzeltmesi yapıldı, compose değiştirilmedi." -ForegroundColor Yellow
} else {
    Copy-Item $composePath (Join-Path $backup "docker-compose.yml.before")
    Set-Content -Path $composePath -Value $compose -Encoding utf8
}

Write-Host "`nDosyalar güncellendi. Yedek: $backup" -ForegroundColor Green
Write-Host "Mevcut veritabanı volume'una dokunulmadı; migration çalıştırılmadı." -ForegroundColor Yellow
Write-Host "`nŞimdi API imajını yeniden oluşturup servisleri güncelle:"
Write-Host "docker compose up -d --build api"
Write-Host "`nArdından migration sürümünü kontrol et:"
Write-Host "docker compose exec api alembic current"
