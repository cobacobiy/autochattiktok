# Ginee Chat Auto-Reply AI Bot (`autochattiktok`)

Aplikasi balasan otomatis berbasis AI untuk [Ginee Chat](https://chat.ginee.com/) dengan arsitektur Playwright Python, noVNC manual login, guardrail AI, dan logging komprehensif.

## Fitur Utama

- **Navigasi Antrean Unreplied**: Hanya memproses percakapan yang belum dibalas (`Belum Dibalas` / `Unreplied`).
- **Deduplikasi & Race Protection**: Menjamin maksimal 1 balasan per percakapan pembeli.
- **Support AI Multi-Provider**: Menggunakan Ollama (default), Google Gemini, atau Anthropic Claude.
- **Safety Mode (`DRY_RUN=true`)**: Bot secara default hanya melakukan prediksi & pembuatan draft tanpa menekan tombol kirim.
- **Port Kustom**: Port disesuaikan agar tidak bentrok dengan aplikasi sebelumnya.

## Informasi Port Service

- **noVNC Web Interface**: `http://localhost:6085`
- **VNC Direct Port**: `5905`
- **Health API Status**: `http://localhost:7085`

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
Untuk mendaftarkan runner otomatis pada server production:
1. Dapatkan token runner di `GitHub -> Settings -> Actions -> Runners -> New self-hosted runner`.
2. Jalankan script setup runner:
```bash
./scripts/setup_github_runner.sh <YOUR_RUNNER_TOKEN>
```

### 5. Menjalankan Unit Test
```bash
python -m unittest discover -s bot/tests -p "test_*.py"
```

## Lisensi & Atribusi
Arsitektur aplikasi dipicu oleh dan diadaptasi dari repository [`cobacobiy/autochat`](https://github.com/cobacobiy/autochat).
