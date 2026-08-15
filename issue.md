# Code Review & Improvement Issues — autochattiktok

> **Tanggal Review:** 15 Agustus 2026
> **Status Codebase:** Fungsional, sudah bisa di-deploy dan berjalan. Review ini mengidentifikasi area perbaikan untuk stabilitas, keamanan, dan maintainability.
> **Cara Pakai:** Setiap issue di bawah bisa dikerjakan secara independen. Pilih satu, kerjakan, buat PR, lalu lanjut ke berikutnya.

---

## Daftar Issues

| No | Prioritas | Area | Judul Issue |
|----|-----------|------|-------------|
| 1 | 🔴 Critical | Security | Gemini API Key terekspos di URL query parameter |
| 2 | 🔴 Critical | Bug | Port mapping tidak konsisten antara Dockerfile dan docker-compose |
| 3 | 🔴 Critical | Reliability | Tidak ada validasi pengiriman — bot menganggap sukses tanpa verifikasi |
| 4 | 🟡 High | Bug | `do_human_delay` dipakai di `ginee_navigation.py` tapi tidak di-import |
| 5 | 🟡 High | Reliability | Network creation docker-compose `external: true` bisa gagal di fresh deploy |
| 6 | 🟡 High | Reliability | `bot_state` global mutable — tidak thread-safe dengan health server |
| 7 | 🟡 High | Observability | Health endpoint tidak melaporkan status bot yang sebenarnya |
| 8 | 🟡 High | Reliability | Tidak ada exponential backoff pada browser loop error |
| 9 | 🟡 High | Data | Unanswered file grow tanpa batas — tidak ada rotasi log |
| 10 | 🟡 High | AI | System prompt tidak menyertakan info store/channel yang sedang diproses |
| 11 | 🟠 Medium | Performance | httpx Client dibuat ulang setiap kali AI call — seharusnya reuse session |
| 12 | 🟠 Medium | Bug | `MAX_DAILY_REPLIES` default tidak konsisten antara config.py dan .env.example |
| 13 | 🟠 Medium | Code Quality | `_last_unreplied_filter_check_time` global mutable di `ginee_browser.py` |
| 14 | 🟠 Medium | Reliability | Tidak ada retry/recovery untuk kasus DOM stale setelah klik conversation |
| 15 | 🟠 Medium | Testing | Test file `test_ai_engine.py` menulis ke `/tmp` — tidak portable untuk Windows runner |
| 16 | 🟢 Low | Code Quality | `selectors.py` import `re` tapi tidak digunakan |
| 17 | 🟢 Low | Code Quality | `ginee_navigation.py` memiliki fungsi `open_unreplied_tab` yang tidak dipakai |
| 18 | 🟢 Low | UX | `DEFAULT_REPLY` di config tidak pernah digunakan di alur manapun |
| 19 | 🟢 Low | Documentation | README belum mencantumkan prasyarat Docker dan Python |
| 20 | 🟢 Low | CI/CD | Workflow CI/CD tidak memvalidasi YAML syntax docker-compose |

---

## Detail Issues

---

### Issue #1: 🔴 Gemini API Key terekspos di URL query parameter

**File:** `bot/ai_engine.py` baris 115
**Masalah:**
API key Gemini dikirim sebagai query parameter di URL (`?key=...`). Ini berarti API key bisa muncul di access log, browser history, proxy log, dan error traces.

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Cari fungsi `call_gemini` (sekitar baris 114)
3. Ubah URL agar tidak mengandung key:
```python
# SEBELUM (baris 115):
url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

# SESUDAH:
url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
```
4. Update `client.post()` call untuk menyertakan `headers=headers`
5. Jalankan test: `python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Pastikan tidak ada API key yang muncul di log output.

---

### Issue #2: 🔴 Port mapping tidak konsisten antara Dockerfile dan docker-compose

**File:** `bot/Dockerfile` baris 28 dan `docker-compose.yml` baris 13-16
**Masalah:**
- Dockerfile EXPOSE: `6080`, `8080`, `5900`
- docker-compose maps: `6085:6080`, `7085:8080`, `5905:5900`
- AGENTS.md dan README menuliskan port: `6085`, `7085`, `5905`

Port internal ini sudah benar dan konsisten. Namun, README perlu menambahkan penjelasan bahwa port **internal** container berbeda dari port **host**.

**Langkah Perbaikan:**
1. Buka `README.md`
2. Di bagian "Informasi Port Service", tambahkan penjelasan:
```markdown
## Informasi Port Service

| Service | Port Host | Port Internal Container |
|---------|-----------|------------------------|
| noVNC Web Interface | `6085` | `6080` |
| Health API Status | `7085` | `8080` |
| VNC Direct Port | `5905` | `5900` |
```
3. Ini bukan bug kritis, tapi membingungkan saat debugging. Pastikan dokumentasi jelas.

**Verifikasi:** Baca README dan pastikan port mapping sudah jelas.

---

### Issue #3: 🔴 Tidak ada validasi pengiriman — bot menganggap sukses tanpa verifikasi bubble

**File:** `bot/ginee_sender.py` baris 56-67
**Masalah:**
Setelah klik tombol kirim, bot hanya mengecek apakah ada notifikasi error. Tapi **tidak memverifikasi** apakah bubble balasan seller benar-benar muncul di panel chat. Ini berarti:
- Jika jaringan lambat, bot menganggap sukses padahal pesan belum terkirim
- Jika ada error non-notifikasi, pesan hilang tanpa jejak

**Langkah Perbaikan:**
1. Buka `bot/ginee_sender.py`
2. Setelah pengecekan error notification (baris 58-64), tambahkan verifikasi bubble:
```python
        # Verify outgoing bubble appeared
        try:
            # Cek apakah bubble seller baru muncul dengan teks yang sama
            from bot.ginee_parser import parse_chat_messages
            verify_msgs = await parse_chat_messages(page)
            if verify_msgs:
                last = verify_msgs[-1]
                if last.direction == "seller" and reply_text[:50] in last.text:
                    log.info("Reply verified: outgoing bubble confirmed")
                    return True
            log.warning("Reply verification: outgoing bubble not confirmed, treating as uncertain success")
        except Exception as e:
            log.warning("Reply verification failed: %s", e)
```
3. Jalankan test: `python -m unittest bot/tests/test_ginee_sender.py`

**Verifikasi:** Jalankan dengan DRY_RUN=false di staging dan pastikan log menunjukkan "Reply verified".

---

### Issue #4: 🟡 `do_human_delay` dipakai di `ginee_navigation.py` tapi tidak di-import

**File:** `bot/ginee_navigation.py` baris 108
**Masalah:**
Fungsi `auto_login_ginee` menggunakan `do_human_delay(page, ...)` di baris 108, 117, 124, tapi `do_human_delay` tidak ada di daftar import file ini. Kode hanya berjalan karena fungsi ini jarang terpanggil (hanya saat login page terdeteksi). Ketika terpanggil, akan `NameError`.

**Langkah Perbaikan:**
1. Buka `bot/ginee_navigation.py`
2. Tambahkan import di bagian atas file (setelah baris 5):
```python
from bot.utils import do_human_delay
```
3. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Cari semua penggunaan `do_human_delay` di `ginee_navigation.py` dan pastikan tidak ada NameError.

---

### Issue #5: 🟡 Network docker-compose `external: true` bisa gagal di fresh deploy

**File:** `docker-compose.yml` baris 23-26
**Masalah:**
```yaml
networks:
  default:
    name: autochat_default
    external: true
```
Docker network `autochat_default` harus sudah ada sebelum `docker compose up`. Pada fresh server atau Windows staging, network ini belum tentu ada sehingga deploy gagal.

**Langkah Perbaikan:**
1. Buka `docker-compose.yml`
2. Ganti konfigurasi network:
```yaml
# SEBELUM:
networks:
  default:
    name: autochat_default
    external: true

# SESUDAH — buat network otomatis jika belum ada:
networks:
  default:
    name: autochat_default
```
3. Atau, jika memang perlu share network dengan project `autochat`, tambahkan perintah di CI/CD dan README:
```bash
docker network create autochat_default 2>/dev/null || true
```
4. Jalankan: `docker compose config` untuk validasi syntax.

**Verifikasi:** Pada server bersih, jalankan `docker compose up -d --build` tanpa membuat network terlebih dahulu — harus berhasil.

---

### Issue #6: 🟡 `bot_state` global mutable — tidak thread-safe dengan health server

**File:** `bot/state.py` dan `bot/health.py`
**Masalah:**
`bot_state` adalah singleton global yang diakses oleh:
- Main async loop (baca/tulis di thread utama)
- Health HTTP server (baca di thread daemon terpisah)

Tidak ada lock/synchronization. Di Python CPython GIL melindungi simple reads, tapi ini bukan jaminan formal dan bisa menghasilkan data tidak konsisten.

**Langkah Perbaikan:**
1. Buka `bot/state.py`
2. Tambahkan threading lock:
```python
import threading

# Di dalam class BotState, tambahkan:
_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

def snapshot(self) -> dict:
    """Thread-safe snapshot for health endpoint."""
    with self._lock:
        return {
            "daily_reply_counter": self.daily_reply_counter,
            "daily_skip_count": self.daily_skip_count,
            "daily_unanswered_count": self.daily_unanswered_count,
            "daily_ai_replied_count": self.daily_ai_replied_count,
            "cache_size": len(self.replied_cache),
            "knowledge_loaded": bool(self.knowledge_base),
            "knowledge_entries": len(self.knowledge_answers),
        }
```
3. Buka `bot/health.py` dan gunakan `bot_state.snapshot()` di `do_GET`.
4. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Health endpoint tetap mengembalikan JSON yang valid.

---

### Issue #7: 🟡 Health endpoint tidak melaporkan status bot yang sebenarnya

**File:** `bot/health.py`
**Masalah:**
Health endpoint selalu mengembalikan `"status": "ok"` tanpa memperhatikan apakah:
- Bot sedang menunggu login (`waiting_login`)
- Browser sudah crash / restart cycle
- Ada error berulang

**Langkah Perbaikan:**
1. Buka `bot/state.py`
2. Tambahkan field status:
```python
bot_status: str = "starting"  # starting, waiting_login, running, error
last_error: str = ""
last_successful_cycle: float = 0.0
```
3. Buka `bot/browser_loop.py`:
   - Set `bot_state.bot_status = "running"` setelah login berhasil dan loop aktif
   - Set `bot_state.bot_status = "waiting_login"` ketika `check_login_status` return False
   - Set `bot_state.bot_status = "error"` di exception handler
   - Update `bot_state.last_successful_cycle = time.time()` setiap sukses process
4. Buka `bot/health.py` dan gunakan `bot_state.bot_status` sebagai value `"status"`.
5. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Curl `http://localhost:7085` dan lihat status berubah sesuai kondisi bot.

---

### Issue #8: 🟡 Tidak ada exponential backoff pada browser loop error

**File:** `bot/browser_loop.py` baris 118-120
**Masalah:**
```python
except Exception as e:
    log.error("Unhandled error in browser loop: %s", e, exc_info=True)
    await asyncio.sleep(10)  # selalu 10 detik
```
Jika error berulang (misalnya Ginee down), bot akan terus retry setiap 10 detik tanpa backoff. Ini bisa menyebabkan rate limiting atau log spam.

**Langkah Perbaikan:**
1. Buka `bot/browser_loop.py`
2. Tambahkan counter error dan backoff:
```python
async def run_browser_loop():
    load_knowledge_base()
    consecutive_errors = 0

    while True:
        # ... existing code ...
        try:
            # ... existing browser session code ...
            consecutive_errors = 0  # reset on success
        except Exception as e:
            consecutive_errors += 1
            backoff = min(10 * (2 ** consecutive_errors), 300)  # max 5 menit
            log.error("Unhandled error (attempt %d, backoff %ds): %s", consecutive_errors, backoff, e, exc_info=True)
            await asyncio.sleep(backoff)
```
3. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Simulasikan error berturut-turut dan pastikan interval sleep meningkat.

---

### Issue #9: 🟡 Unanswered file grow tanpa batas — tidak ada rotasi

**File:** `bot/ai_engine.py` fungsi `log_unanswered_question`
**Masalah:**
File `unanswered_questions.txt` hanya di-append terus tanpa batasan ukuran. Dalam jangka panjang bisa menghabiskan disk space.

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Tambahkan pengecekan ukuran file sebelum menulis:
```python
import shutil

MAX_UNANSWERED_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def log_unanswered_question(question, conversation_hash="", store_channel="", reason="TIDAK_TAHU"):
    try:
        # Rotate file jika sudah terlalu besar
        if os.path.exists(UNANSWERED_PATH):
            size = os.path.getsize(UNANSWERED_PATH)
            if size > MAX_UNANSWERED_FILE_SIZE:
                backup = UNANSWERED_PATH + ".old"
                shutil.move(UNANSWERED_PATH, backup)
                log.info("Rotated unanswered file (%d bytes) to %s", size, backup)

        # ... sisanya sama seperti sekarang ...
```
3. Jalankan test: `python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Buat file unanswered > 10MB dan pastikan di-rotate otomatis.

---

### Issue #10: 🟡 System prompt AI tidak menyertakan info store/channel

**File:** `bot/ai_engine.py` fungsi `_build_system_prompt` dan `generate_ai_reply`
**Masalah:**
System prompt yang dikirim ke AI tidak menyebutkan toko mana yang sedang dibalas. Jika bot menangani multi-store, AI tidak tahu konteks toko sehingga bisa memberikan jawaban yang tidak relevan.

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Ubah signature `_build_system_prompt` agar menerima `store_channel`:
```python
def _build_system_prompt(store_channel: str = "") -> str:
    # ... kode existing ...
    store_info = f"\nAnda sedang menjawab chat untuk toko: {store_channel}\n" if store_channel else ""
    return (
        "Anda adalah Customer Service resmi toko online di Ginee Chat.\n"
        f"{store_info}"
        # ... sisanya sama ...
    )
```
3. Update pemanggilan `_build_system_prompt()` di `call_ollama`, `call_gemini`, `call_claude` untuk meneruskan parameter `store_channel`.
4. Ini memerlukan perubahan signature fungsi-fungsi AI call. Alternatif lebih mudah: simpan `store_channel` di variabel modul/state sebelum memanggil AI.
5. Jalankan test: `python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Periksa log AI call dan pastikan store info muncul di prompt.

---

### Issue #11: 🟠 httpx Client dibuat ulang setiap kali AI call

**File:** `bot/ai_engine.py` baris 102, 121, 153
**Masalah:**
Setiap call ke Ollama/Gemini/Claude membuat `httpx.Client()` baru. Ini berarti TCP connection tidak di-reuse dan ada overhead setup koneksi setiap kali.

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Buat modul-level client yang reusable:
```python
# Di bagian atas file, setelah import:
_http_client = httpx.Client(timeout=120.0)
```
3. Ganti semua `with httpx.Client(timeout=120.0) as client:` menjadi langsung pakai `_http_client`:
```python
# SEBELUM:
with httpx.Client(timeout=120.0) as client:
    resp = client.post(url, json=payload)

# SESUDAH:
resp = _http_client.post(url, json=payload)
```
4. Lakukan untuk ketiga fungsi: `call_ollama`, `call_gemini`, `call_claude`.
5. Jalankan test: `python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Bot tetap berfungsi normal. Perhatikan log untuk error koneksi yang mungkin muncul karena connection reuse.

---

### Issue #12: 🟠 `MAX_DAILY_REPLIES` default tidak konsisten

**File:** `bot/config.py` baris 26 dan `.env.example` baris 9
**Masalah:**
- `config.py`: `MAX_DAILY_REPLIES = max(1, int(os.getenv("MAX_DAILY_REPLIES", "500")))`
- `AGENTS.md`: menyebut default `5000`
- `.env.example`: `MAX_DAILY_REPLIES=500`

Ini membingungkan karena AGENTS.md bilang 5000, tapi kode default-nya 500.

**Langkah Perbaikan:**
1. Tentukan mana yang benar: 500 atau 5000
2. Jika 500 yang benar, update `AGENTS.md` baris yang menyebut "default: `5000`" menjadi "default: `500`"
3. Jika 5000 yang benar, update `config.py` baris 26 dan `.env.example` baris 9
4. Pastikan semua 3 file konsisten.

**Verifikasi:** Grep `MAX_DAILY_REPLIES` di seluruh project dan pastikan semua default value sama.

---

### Issue #13: 🟠 Global mutable `_last_unreplied_filter_check_time`

**File:** `bot/ginee_browser.py` baris 27, 138, 148, 153
**Masalah:**
```python
_last_unreplied_filter_check_time = 0.0
# ...
global _last_unreplied_filter_check_time
```
Variabel global mutable ini seharusnya dikelola di `BotState` agar lebih terstruktur dan testable.

**Langkah Perbaikan:**
1. Buka `bot/state.py` dan tambahkan field baru:
```python
last_unreplied_filter_check: float = 0.0
```
2. Buka `bot/ginee_browser.py`:
   - Hapus baris `_last_unreplied_filter_check_time = 0.0`
   - Hapus `global _last_unreplied_filter_check_time`
   - Ganti semua referensi `_last_unreplied_filter_check_time` dengan `bot_state.last_unreplied_filter_check`
3. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Bot tetap menjalankan cek filter "Belum Dibalas" setiap 15 menit.

---

### Issue #14: 🟠 Tidak ada retry/recovery untuk DOM stale setelah klik conversation

**File:** `bot/ginee_browser.py` baris 53-56
**Masalah:**
Setelah klik conversation item, bot langsung `parse_chat_messages`. Jika DOM belum ter-render (loading lambat), parse bisa return kosong dan conversation di-skip.

**Langkah Perbaikan:**
1. Buka `bot/ginee_browser.py`
2. Setelah `await conv.element.click(force=True)` (baris 53), tambahkan retry sederhana:
```python
if conv.element:
    await conv.element.click(force=True)
    await do_human_delay(page, min_ms=1500, max_ms=3000)

messages = None
for attempt in range(3):
    messages = await parse_chat_messages(page)
    if messages:
        break
    log.debug("Retry %d: waiting for messages to load...", attempt + 1)
    await page.wait_for_timeout(2000)

if not messages:
    log.info("No messages found after retries for %s", conv.conversation_id)
    bot_state.replied_cache[prelim_hash] = time.time()
    continue
```
3. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Jalankan bot dengan koneksi lambat dan pastikan parsing berhasil setelah retry.

---

### Issue #15: 🟠 Test menulis ke `/tmp` — tidak portable untuk Windows runner

**File:** `bot/tests/test_ai_engine.py` baris 22, 41, 55
**Masalah:**
Test menggunakan hardcoded path `/tmp/test_unanswered*.txt`. Pada Windows runner (staging), `/tmp` tidak ada sehingga test akan gagal.

**Langkah Perbaikan:**
1. Buka `bot/tests/test_ai_engine.py`
2. Ganti `/tmp/` dengan `tempfile.gettempdir()`:
```python
import tempfile

# SEBELUM:
test_path = "/tmp/test_unanswered.txt"

# SESUDAH:
test_path = os.path.join(tempfile.gettempdir(), "test_unanswered.txt")
```
3. Lakukan untuk semua 3 occurrences (baris 22, 41, 55).
4. Jalankan test: `python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Jalankan test di Linux dan Windows, keduanya harus lulus.

---

### Issue #16: 🟢 Import `re` tidak digunakan di `selectors.py`

**File:** `bot/selectors.py` baris 2
**Masalah:**
```python
import re  # tidak digunakan di manapun di file ini
```

**Langkah Perbaikan:**
1. Buka `bot/selectors.py`
2. Hapus baris `import re`
3. Jalankan lint: `python -m ruff check bot/selectors.py`

**Verifikasi:** `ruff check` tidak melaporkan error/warning.

---

### Issue #17: 🟢 Fungsi `open_unreplied_tab` tidak dipakai

**File:** `bot/ginee_navigation.py` baris 204-207
**Masalah:**
Fungsi `open_unreplied_tab` didefinisikan tapi tidak dipanggil dari manapun di codebase. Dead code.

**Langkah Perbaikan:**
1. Grep seluruh project: `grep -r "open_unreplied_tab" bot/`
2. Jika tidak ada pemanggil, hapus fungsi tersebut dari `ginee_navigation.py`
3. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Tidak ada error import atau test failure setelah penghapusan.

---

### Issue #18: 🟢 `DEFAULT_REPLY` tidak pernah digunakan

**File:** `bot/config.py` baris 54
**Masalah:**
```python
DEFAULT_REPLY = os.getenv("DEFAULT_REPLY", "Ada yang bisa dibantu?")
```
Variabel ini di-import di `ai_engine.py` (baris 19) tapi **tidak pernah digunakan** di alur manapun. Ketika AI gagal atau return TIDAK_TAHU, bot mengembalikan string kosong `""`, bukan `DEFAULT_REPLY`.

**Langkah Perbaikan:**
Pilih salah satu:

**Opsi A — Gunakan DEFAULT_REPLY sebagai fallback:**
1. Buka `bot/ai_engine.py` fungsi `generate_ai_reply`
2. Di bagian akhir (sebelum `return ""`), tambahkan:
```python
# Jika tidak ada reply dari AI dan tidak ada static match, gunakan default
return DEFAULT_REPLY
```

**Opsi B — Hapus DEFAULT_REPLY jika memang tidak diperlukan:**
1. Hapus dari `config.py`, `.env.example`, dan import di `ai_engine.py`

**Verifikasi:** Jalankan test dan pastikan tidak ada broken import.

---

### Issue #19: 🟢 README belum mencantumkan prasyarat

**File:** `README.md`
**Masalah:**
README langsung menuju "Setup Environment" tanpa menyebutkan prasyarat seperti Docker, Docker Compose, Python versi, dll.

**Langkah Perbaikan:**
1. Buka `README.md`
2. Tambahkan bagian "Prasyarat" sebelum "Panduan Penggunaan":
```markdown
## Prasyarat

- **Docker** >= 20.10 dan **Docker Compose** v2
- **Python** >= 3.11 (untuk development/testing lokal)
- **Git** untuk clone repository
- **Koneksi Internet** untuk mengunduh image dan dependency
```

**Verifikasi:** Baca README dari perspektif developer baru.

---

### Issue #20: 🟢 CI/CD tidak memvalidasi docker-compose syntax

**File:** `.github/workflows/ci-cd.yml`
**Masalah:**
Pipeline CI hanya menjalankan lint Python dan unit test. Tidak ada validasi bahwa `docker-compose.yml` dan `Dockerfile` valid.

**Langkah Perbaikan:**
1. Buka `.github/workflows/ci-cd.yml`
2. Tambahkan step di job `validate` setelah "Jalankan Unit Tests":
```yaml
      - name: Validate Docker Compose Config
        continue-on-error: true
        run: |
          if command -v docker &> /dev/null; then
            docker compose -f docker-compose.yml config --quiet
          else
            echo "Docker not available, skipping compose validation"
          fi
```

**Verifikasi:** Push perubahan dan cek pipeline di GitHub Actions.

---

## Urutan Pengerjaan yang Disarankan

Untuk efisiensi, kerjakan dalam urutan berikut:

### Batch 1 — Quick Fixes (bisa selesai dalam 1 PR)
- [ ] Issue #4 — Import `do_human_delay` yang hilang
- [ ] Issue #16 — Hapus unused import `re`
- [ ] Issue #12 — Konsistensikan `MAX_DAILY_REPLIES`
- [ ] Issue #15 — Fix test path untuk Windows
- [ ] Issue #17 — Hapus dead code `open_unreplied_tab`

### Batch 2 — Security & Reliability
- [ ] Issue #1 — Gemini API key di header
- [ ] Issue #5 — Docker network external
- [ ] Issue #11 — Reuse httpx Client
- [ ] Issue #8 — Exponential backoff

### Batch 3 — Observability & State Management
- [ ] Issue #6 — Thread-safe bot_state
- [ ] Issue #7 — Status health endpoint
- [ ] Issue #13 — Pindahkan global ke state
- [ ] Issue #9 — Rotasi unanswered file

### Batch 4 — Feature Improvements
- [ ] Issue #3 — Verifikasi pengiriman
- [ ] Issue #10 — Store info di AI prompt
- [ ] Issue #14 — DOM retry
- [ ] Issue #18 — DEFAULT_REPLY fallback

### Batch 5 — Documentation & CI
- [ ] Issue #2 — Port mapping docs
- [ ] Issue #19 — Prasyarat README
- [ ] Issue #20 — Docker compose validation

---

## Referensi

- Repo sumber arsitektur: <https://github.com/cobacobiy/autochat>
- Aplikasi target: <https://chat.ginee.com/>
- Dokumentasi Playwright Python: <https://playwright.dev/python/docs/intro>
