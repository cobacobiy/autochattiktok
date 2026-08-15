# Ginee Chat Auto-Reply AI Bot (`autochattiktok`)

Aplikasi balasan otomatis berbasis AI untuk [Ginee Chat](https://chat.ginee.com/) dengan arsitektur Playwright Python, noVNC manual login, guardrail AI, dan logging komprehensif.

## Fitur Utama

- **Navigasi Antrean Unreplied**: Hanya memproses percakapan yang belum dibalas (`Belum Dibalas` / `Unreplied`).
- **Deduplikasi & Race Protection**: Menjamin maksimal 1 balasan per percakapan pembeli.
- **Support AI Multi-Provider**: Menggunakan Ollama (default), Google Gemini, atau Anthropic Claude.
- **Safety Mode (`DRY_RUN=true`)**: Bot secara default hanya melakukan prediksi & pembuatan draft tanpa menekan tombol kirim.
- **Port Kustom**: Port disesuaikan agar tidak bentrok dengan aplikasi sebelumnya.

## Informasi Port Service

| Service | Port Host | Port Internal Container |
|---------|-----------|------------------------|
| noVNC Web Interface | `6085` | `6080` |
| Health API Status | `7085` | `8080` |
| VNC Direct Port | `5905` | `5900` |

## Prasyarat

- **Docker** >= 20.10 dan **Docker Compose** v2
- **Python** >= 3.11 (untuk development/testing lokal)
- **Git** untuk clone repository
- **Koneksi Internet** untuk mengunduh image dan dependency

## Panduan Penggunaan

### 1. Setup Environment
Salin `.env.example` ke `.env`:
```bash
cp .env.example .env
```

### 2. Jalankan via Docker Compose
```bash
docker compose up -d --build
```

### 3. Login Manual via noVNC
Buka browser dan akses `http://localhost:6085`. Selesaikan proses login akun Ginee secara manual. Sesi login akan tersimpan otomatis di persistent profile `/data/ginee-profile`.

### 4. Setup GitHub Actions Self-Hosted Runner (CI/CD)
Untuk mendaftarkan runner otomatis pada server/mesin local:

**Linux / Server Production:**
1. Dapatkan token runner di `GitHub -> Settings -> Actions -> Runners -> New self-hosted runner`.
2. Jalankan script setup runner:
```bash
./scripts/setup_github_runner.sh <YOUR_RUNNER_TOKEN>
```

**Windows Host (Netbird Network - Staging):**

*Jika menggunakan Command Prompt (CMD):*
Ketik `powershell` terlebih dahulu untuk masuk ke mode PowerShell, atau jalankan langsung:
```cmd
curl -o setup_github_runner.ps1 https://raw.githubusercontent.com/cobacobiy/autochattiktok/main/scripts/setup_github_runner.ps1
powershell -ExecutionPolicy Bypass -File .\setup_github_runner.ps1 -RunnerToken "<YOUR_RUNNER_TOKEN>"
```

*Jika menggunakan PowerShell (Run as Administrator):*
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/cobacobiy/autochattiktok/main/scripts/setup_github_runner.ps1 -OutFile setup_github_runner.ps1
powershell -ExecutionPolicy Bypass -File .\setup_github_runner.ps1 -RunnerToken "<YOUR_RUNNER_TOKEN>"
```
*Catatan Netbird:* Pastikan service Netbird terhubung (`netbird status`). Runner Windows secara otomatis akan mendapat label `self-hosted,windows,staging,test,netbird,autochattiktok`.

### 5. Menjalankan Unit Test
```bash
python -m unittest discover -s bot/tests -p "test_*.py"
```

## Lisensi & Atribusi
Arsitektur aplikasi dipicu oleh dan diadaptasi dari repository [`cobacobiy/autochat`](https://github.com/cobacobiy/autochat).
