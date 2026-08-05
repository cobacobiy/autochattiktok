# Implementasi Auto-Reply AI untuk Ginee Chat

## Ringkasan

Buat aplikasi di folder ini dengan pola arsitektur dari [`cobacobiy/autochat`](https://github.com/cobacobiy/autochat), tetapi target browsernya adalah [Ginee Chat](https://chat.ginee.com/), bukan Shopee Seller Centre.

Bot harus membuka Ginee Chat dengan Playwright, memakai sesi login yang disimpan, mencari percakapan **Belum Dibalas/Belum Dibaca**, membaca pesan terakhir pembeli, membuat jawaban berdasarkan `store_knowledge.txt`, lalu mengirim jawaban satu kali. Kasus yang tidak aman atau tidak diketahui harus dilewati dan dicatat untuk admin.

> Catatan riset (5 Agustus 2026): panduan ini dibuat dari upstream commit `e7cbc8bab59d426ab03a7e5fe9d8f1896879d3cb` dan halaman/bundle publik Ginee Chat. DOM percakapan Ginee berada di balik login sehingga selector produksi harus dikonfirmasi menggunakan akun uji pada tahap discovery. Jangan memasukkan cookie, token, HTML berisi data pembeli, atau kredensial ke Git.

## Keputusan desain

- Pertahankan modul generik upstream: konfigurasi, state/cache, knowledge base, AI engine, health endpoint, logging, Docker/VNC, retry, dan graceful shutdown.
- Ganti seluruh adapter Shopee dengan adapter Ginee. Jangan menambahkan kondisi Ginee ke file `shopee_browser.py` yang besar.
- Gunakan UI Ginee yang sudah mengagregasi banyak marketplace. Identitas unik percakapan minimal harus mencakup `store + channel/platform + buyer/conversation`, bukan username saja.
- Login dilakukan manual melalui browser/noVNC dan disimpan dalam persistent profile. Jangan mengotomatisasi OTP, CAPTCHA, atau mengambil token internal.
- Mulai dengan mode aman `DRY_RUN=true`: baca pesan dan hasilkan draft/log tanpa mengirim.
- Jangan mengandalkan class CSS hasil build sebagai selector utama. Prioritas selector: `data-*` stabil, role/accessible name, placeholder/teks terjemahan, lalu fallback posisi.
- Jangan memanggil API privat Ginee yang ditemukan dari bundle. Gunakan browser UI kecuali tersedia API resmi dan izin tertulis.
- Ginee sendiri menampilkan fitur **Balasan Otomatis/Auto Reply**. Sebelum memakai bot eksternal, periksa apakah fitur native sudah memenuhi kebutuhan serta cek syarat layanan dan kebijakan marketplace yang terhubung.

## Target struktur folder

```text
autochattiktok/
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── store_knowledge.txt
├── unanswered_questions.txt
├── bot/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── state.py
│   ├── knowledge.py
│   ├── ai_engine.py
│   ├── browser_loop.py
│   ├── ginee_browser.py
│   ├── ginee_navigation.py
│   ├── ginee_parser.py
│   ├── ginee_sender.py
│   ├── selectors.py
│   ├── health.py
│   ├── utils.py
│   ├── Dockerfile
│   ├── supervisord.conf
│   ├── requirements.txt
│   └── tests/
│       ├── fixtures/
│       │   ├── conversation_list.html
│       │   └── conversation_detail.html
│       ├── test_ginee_parser.py
│       ├── test_ginee_sender.py
│       ├── test_ai_engine.py
│       ├── test_knowledge.py
│       └── test_config.py
└── logs/                         # diabaikan Git
```

## Langkah implementasi

### 1. Jadikan upstream sebagai referensi, bukan salinan buta

1. Salin modul yang platform-agnostic dari upstream: `ai_engine.py`, `knowledge.py`, `state.py`, `health.py`, `utils.py`, setup logging, Dockerfile, supervisor, dan test yang relevan.
2. Port dan rapikan `browser_loop.py`; ubah nama/konstanta Shopee menjadi Ginee.
3. Jangan membawa `shopee_browser.py`, `chat_navigation.py`, `chat_parser.py`, `chat_sender.py`, serta JS selector Shopee sebagai implementasi Ginee.
4. Tambahkan atribusi/referensi upstream dan pertahankan lisensi upstream bila tersedia. Jika lisensinya tidak jelas, minta izin pemilik sebelum mendistribusikan kode hasil salinan.

### 2. Buat konfigurasi Ginee

Isi `.env.example`:

```env
GINEE_CHAT_URL=https://chat.ginee.com/
PROFILE_DIR=/data/ginee-profile
HEADLESS=false
DRY_RUN=true
POLL_INTERVAL=8
BROWSER_LIFETIME=21600
MAX_DAILY_REPLIES=500
MAX_CACHE_SIZE=1000
LOG_DIR=/data/logs
LOG_FORMAT=text
KNOWLEDGE_PATH=/app/store_knowledge.txt
UNANSWERED_PATH=/app/unanswered_questions.txt

AI_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:3b
# GEMINI_API_KEY=
# ANTHROPIC_API_KEY=
```

Di `config.py`:

- ganti `SHOPEE_CHAT_URL` menjadi `GINEE_CHAT_URL`;
- ganti default profile `/data/shopee-profile` menjadi `/data/ginee-profile`;
- tambahkan parsing boolean yang ketat untuk `DRY_RUN` dan `HEADLESS`;
- validasi angka: interval minimal 3 detik, limit harian positif, dan panjang jawaban maksimal 1.000 karakter (UI publik Ginee menyebut batas ini; gunakan batas internal lebih rendah, misalnya 600, agar aman);
- jangan sediakan `GINEE_USERNAME`/`GINEE_PASSWORD`; sesi login manual lebih aman untuk OTP/CAPTCHA.

### 3. Discovery DOM dengan akun uji

Jalankan browser headful dan login manual. Gunakan akun/toko staging atau percakapan uji, bukan pembeli nyata.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r bot/requirements.txt
playwright install chromium
DRY_RUN=true HEADLESS=false python -m bot.main
```

Setelah login, dokumentasikan locator berikut di `bot/selectors.py`:

| Elemen | Kandidat berbasis UI publik | Yang harus diverifikasi |
|---|---|---|
| Root aplikasi | `#root` | root sudah selesai loading, bukan spinner |
| Tab antrean | teks `Belum Dibalas` / `Unreplied`; fallback `Belum Dibaca` / `Unread` | tab aktif dan jumlah item |
| Daftar percakapan | region/list di panel kiri | satu item, badge unread/unreplied, store/channel, buyer, preview |
| Panel pesan | region tengah setelah item diklik | container scroll dan bubble pesan |
| Input | placeholder `Masukkan pesan...` / `Type a message...` | `textarea`, input, atau `contenteditable` |
| Tombol kirim | `button` bernama `Kirim` / `Send` | enabled hanya ketika ada teks |
| Status gagal | `Gagal mengirim pesan` / `Failed to send message` | retry tidak membuat duplikat |
| Keadaan kosong | `Belum ada pesan` / `No messages` | tidak dianggap error |

Simpan snapshot HTML yang sudah disanitasi ke `bot/tests/fixtures/`. Hapus nama, isi chat, nomor pesanan, alamat, URL gambar, token, dan atribut identitas. Ambil screenshot hanya ke `logs/`, jangan commit.

Jalankan halaman dengan locale Indonesia dan Inggris untuk memastikan fallback bahasa. Periksa juga apakah daftar memakai virtual scrolling; jika ya, proses hanya elemen yang sedang terlihat dan gunakan ID/metadata percakapan, bukan index baris.

### 4. Pusatkan selector

Buat `selectors.py` yang menyimpan beberapa kandidat per elemen. Contoh bentuk API:

```python
UNREPLIED_TAB = [
    {"role": "tab", "name": re.compile(r"Belum Dibalas|Unreplied", re.I)},
    {"text": re.compile(r"Belum Dibalas|Unreplied", re.I)},
]

MESSAGE_INPUT = [
    "textarea[placeholder*='Masukkan pesan']",
    "textarea[placeholder*='Type a message']",
    "[contenteditable='true'][role='textbox']",
]
```

Tambahkan helper `first_visible(page_or_scope, candidates)`. Setiap selector fallback harus mencatat selector mana yang berhasil. Jika selector utama gagal berulang kali, simpan diagnostic screenshot/HTML tersanitasi dan hentikan pengiriman, bukan mengklik elemen acak.

### 5. Implementasi navigasi dan autentikasi

Di `ginee_navigation.py`:

1. Buka `GINEE_CHAT_URL` dan tunggu `domcontentloaded` serta hilangnya loading wrapper.
2. Deteksi redirect/login Accounts berdasarkan URL dan keberadaan form login.
3. Jika logout, log instruksi login manual dan tunggu sampai root Ginee Chat muncul. Timeout sebaiknya 10 menit lalu restart browser secara bersih.
4. Buka tab `Belum Dibalas`. Jika tidak tersedia, gunakan `Belum Dibaca`; jangan memproses `Semua Pesan` secara default.
5. Tangani status paket habis, toko belum terhubung/tidak terotorisasi, modal error, network error, dan halaman kosong sebagai kondisi `PAUSED`, bukan loop klik.
6. Jangan klik menu **Balasan Otomatis**; itu fitur native Ginee, bukan inbox percakapan.

State login harus bertahan lewat persistent context. Pastikan profile tidak pernah dimount ke dua container secara bersamaan.

### 6. Implementasi pembacaan antrean

Di `ginee_browser.py`, buat model data:

```python
@dataclass
class ConversationSummary:
    conversation_id: str
    buyer_name: str
    store_name: str
    channel: str
    preview: str
    unread: bool
    unreplied: bool

@dataclass
class ChatMessage:
    message_id: str | None
    text: str
    direction: Literal["buyer", "seller", "system", "unknown"]
    sent_at: str | None
```

Alurnya:

1. Ambil maksimal 5 percakapan teratas yang `unreplied=true`.
2. Bangun `conversation_id` dari atribut stabil DOM. Jika tidak ada, hash gabungan `store|channel|buyer`, tetapi log bahwa ini fallback.
3. Klik satu item, tunggu header/panel berubah ke percakapan tersebut, lalu tunggu pesan stabil.
4. Baca maksimal 10 pesan terakhir untuk konteks AI.
5. Tentukan arah pesan dari atribut/struktur DOM yang terverifikasi. Posisi bubble kiri/kanan hanya fallback terakhir.
6. Abaikan system notification, gambar/sticker tanpa caption, pesan unsupported, pesan kosong, dan acknowledgment seperti `ok`, `sip`, `terima kasih`.
7. Proses hanya jika pesan terakhir adalah dari buyer. Jika arah `unknown`, jangan kirim.

Jangan memakai preview sidebar sebagai isi final jika panel detail tersedia; preview boleh dipakai hanya untuk deduplikasi awal.

### 7. Deduplikasi dan race-condition

Key cache harus berupa:

```text
sha256(store_name | channel | conversation_id | last_buyer_message_id_or_normalized_text)
```

Sebelum AI dipanggil dan sekali lagi sebelum klik kirim:

- pastikan percakapan/header masih sama;
- baca ulang pesan terakhir;
- pastikan belum ada balasan seller/admin sejak snapshot pertama;
- pastikan key belum pernah sukses dikirim;
- pastikan limit harian belum tercapai.

Status cache minimal: `seen`, `drafted`, `sent`, `skipped`, `failed`. Hanya `sent` yang dihitung sebagai reply. Jangan menandai sukses hanya karena tombol/Enter sudah ditekan; verifikasi bubble outgoing muncul dengan teks yang sama atau input kosong **dan** tidak ada status gagal.

### 8. Integrasi AI dan knowledge base

Pertahankan dukungan Ollama/Gemini/Claude dari upstream. System prompt harus menyatakan:

- jawab sebagai CS toko secara singkat dan sopan;
- hanya gunakan fakta dari knowledge base dan konteks chat;
- jangan mengarang stok, harga, status pesanan, ongkir, nomor resi, promo, atau kebijakan;
- jangan meminta password, OTP, data kartu, atau data sensitif;
- bila tidak yakin keluarkan token persis `TIDAK_TAHU`;
- keluarkan jawaban saja, tanpa label `Jawaban:`;
- maksimal 600 karakter.

Format awal `store_knowledge.txt` boleh tetap `pertanyaan | jawaban`. Tambahkan bagian kebijakan eskalasi. Jika output `TIDAK_TAHU`, kosong, terlalu panjang, mengandung pola prompt leakage, atau bertentangan dengan kebijakan, jangan kirim dan tulis JSON Lines ke `unanswered_questions.txt` dengan waktu, hash conversation, store/channel, dan pertanyaan; jangan menyimpan PII yang tidak diperlukan.

### 9. Implementasi pengiriman aman

Di `ginee_sender.py`:

1. Cari input hanya di dalam panel percakapan aktif.
2. Klik/focus lalu isi teks dengan API Playwright (`fill` untuk textarea; keyboard untuk contenteditable).
3. Di `DRY_RUN`, log `would_send` dan berhenti di sini.
4. Di mode produksi, prioritaskan tombol `Kirim/Send`; gunakan Enter hanya setelah perilakunya diverifikasi. Bundle publik menyatakan Enter mengirim dan Shift+Enter membuat baris baru, tetapi tetap uji pada akun staging.
5. Setelah kirim, tunggu bubble seller yang cocok dan periksa `Failed to send message/Gagal mengirim pesan`.
6. Jika hasil ambigu, beri status `failed_unknown`; jangan retry otomatis pada siklus yang sama karena berisiko mengirim dua kali.
7. Tambahkan lock tunggal agar hanya satu pengiriman aktif dalam satu instance.

### 10. Browser loop dan pemulihan

Adaptasi loop upstream:

- polling awal 8–15 detik dengan jitter kecil;
- reload knowledge base berkala;
- bersihkan cache setelah 24 jam dan batasi ukurannya;
- restart context setiap 6 jam;
- heartbeat serta daily report;
- health endpoint memberi status `starting`, `waiting_login`, `ready`, `paused`, atau `degraded`;
- exponential backoff untuk network/Ginee error;
- pause minimal beberapa menit bila CAPTCHA/challenge atau rate limit muncul;
- jangan mencoba menyembunyikan automasi atau melewati CAPTCHA. Minta intervensi operator melalui noVNC.

### 11. Docker dan operasi

Ubah nama service dan volume upstream:

```yaml
services:
  ginee-bot:
    build: ./bot
    container_name: ginee-bot
    shm_size: 2gb
    restart: unless-stopped
    env_file: .env
    volumes:
      - ginee-profile:/data/ginee-profile
      - ./logs:/data/logs
      - ./store_knowledge.txt:/app/store_knowledge.txt:ro
      - ./unanswered_questions.txt:/app/unanswered_questions.txt
    ports:
      - "6080:6080" # noVNC/login manual
      - "7080:8080" # health

volumes:
  ginee-profile:
```

Mulai satu instance dahulu. Untuk banyak akun Ginee, setiap container wajib memiliki profile, log, port, dan unanswered file berbeda. Jangan menjalankan dua worker untuk profile atau inbox yang sama.

### 12. Test

Unit test wajib:

- parser membedakan buyer/seller/system dari fixture;
- parser tidak menganggap posisi sebagai seller jika ada atribut direction eksplisit;
- tab memilih `Belum Dibalas`, lalu fallback `Belum Dibaca`;
- ack, gambar tanpa teks, unsupported, dan system message dilewati;
- cache key berbeda untuk store/channel berbeda walau buyer dan teks sama;
- `TIDAK_TAHU` dicatat dan tidak dikirim;
- dry-run tidak menekan Enter/tombol;
- sender mendeteksi send success, send failure, dan hasil ambigu;
- pesan buyer baru yang masuk saat AI berjalan membatalkan draft lama;
- balasan admin yang masuk saat AI berjalan mencegah bot mengirim;
- limit harian, cache expiry, dan hot reload knowledge bekerja.

Test manual staging:

1. Login manual dan restart container; sesi tetap aktif.
2. Kirim pertanyaan FAQ dari akun marketplace uji; tepat satu draft tercipta dalam dry-run.
3. Aktifkan pengiriman untuk satu toko uji; tepat satu balasan muncul.
4. Kirim `ok`; bot tidak membalas.
5. Kirim pertanyaan di luar knowledge; tidak ada balasan dan ada entry unanswered.
6. Balas manual saat AI sedang memproses; bot membatalkan kirim.
7. Putuskan jaringan dan pulihkan; tidak ada duplikasi.
8. Ubah bahasa Indonesia/Inggris; navigasi dan input tetap ditemukan.
9. Uji dua store/channel dengan buyer bernama sama; cache tidak bentrok.
10. Logout/expire session; status berubah ke `waiting_login`, tanpa percobaan login otomatis.

## Urutan milestone

- [ ] **M0 — Legal dan akses:** konfirmasi izin automasi, buat akun/toko uji, nilai fitur Auto Reply native Ginee.
- [ ] **M1 — Scaffold:** port modul generik, konfigurasi Ginee, Docker/noVNC, health endpoint.
- [ ] **M2 — DOM discovery:** dokumentasikan locator, buat fixture tersanitasi, dukung ID/EN.
- [ ] **M3 — Read-only:** navigasi antrean dan parser berjalan stabil dengan `DRY_RUN=true` selama minimal 24 jam.
- [ ] **M4 — AI draft:** knowledge base, guardrail, unanswered logger, deduplikasi, race checks.
- [ ] **M5 — Send staging:** kirim ke percakapan uji, verifikasi hasil, failure handling tanpa retry ganda.
- [ ] **M6 — Pilot:** satu toko, allowlist, jam operasi terbatas, limit 20 balasan/hari, review manusia harian.
- [ ] **M7 — Production:** naikkan limit bertahap setelah audit log dan tingkat kesalahan memenuhi target.

## Definition of Done

- [ ] Tidak ada nama variabel, URL, profile, container, atau selector Shopee tersisa di jalur runtime.
- [ ] Semua selector Ginee terpusat dan diverifikasi pada UI login aktual, bukan hanya dari bundle publik.
- [ ] Bot hanya memproses percakapan buyer yang belum dibalas.
- [ ] Tidak pernah mengirim ketika direction, conversation identity, atau hasil pengiriman ambigu.
- [ ] Satu pesan buyer menghasilkan maksimal satu balasan walau restart/network error terjadi.
- [ ] Balasan manual admin menang terhadap draft bot.
- [ ] `DRY_RUN=true` menjadi default.
- [ ] Kredensial, cookie, token, profile, screenshot, log PII, dan `.env` tidak masuk Git.
- [ ] Unit test, lint, dan test manual staging lulus.
- [ ] README menjelaskan login manual, noVNC, knowledge base, dry-run, aktivasi produksi, rollback, serta risiko kebijakan.

## Referensi

- Repo sumber arsitektur: <https://github.com/cobacobiy/autochat>
- Aplikasi target: <https://chat.ginee.com/>
- Dokumentasi Playwright Python: <https://playwright.dev/python/docs/intro>

