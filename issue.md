# Code Review & Improvement Issues — autochattiktok

> **Tanggal Review:** 15 Agustus 2026
> **Status Codebase:** Fungsional, sudah bisa di-deploy dan berjalan. Review ini mengidentifikasi area perbaikan untuk stabilitas, keamanan, dan maintainability.
> **Cara Pakai:** Setiap issue di bawah bisa dikerjakan secara independen. Pilih satu, kerjakan, buat PR, lalu lanjut ke berikutnya.

---

## Daftar Issues

| No | Prioritas | Area | Judul Issue |
|----|-----------|------|-------------|
| **21** | **🔴 Critical** | **Architecture** | **Bot standby pada "Semua Pesan" — risiko membalas chat yang sudah ditangani** |
| **22** | **🔴 Critical** | **Architecture** | **Parser fail-open: bubble tak dikenali dianggap buyer** |
| **23** | **🔴 Critical** | **AI Safety** | **Static AUTO_REPLIES bypass guardrail AI (stok, garansi)** |
| **24** | **🟡 High** | **Reliability** | **Cache preliminary menahan retry hingga 24 jam** |
| **25** | **🟡 High** | **DevOps** | **Fresh production deployment berjalan DRY_RUN=true** |
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

### Issue #21: 🔴 Bot standby pada "Semua Pesan" — risiko membalas chat yang sudah ditangani

**File:** `bot/ginee_browser.py` baris 155-190
**Status Verifikasi:** ✅ Dikonfirmasi terhadap kode aktual

**Masalah:**
Desain awal (`AGENTS.md` aturan #1) mengharuskan bot hanya memproses percakapan dari filter `Belum Dibalas`. Namun di implementasi saat ini:
- Mode standby utama adalah `Semua Pesan` (baris 180-186).
- Filter `Belum Dibalas` hanya dicek sekali setiap 15 menit (baris 173).
- Di siklus biasa (setiap 8 detik), bot memproses **semua** conversation di view `Semua Pesan`.

**Dampak Konkret:**
Jika CS manusia sedang aktif membalas buyer di Ginee, bot tetap membaca conversation itu di `Semua Pesan` dan berpotensi mengirimkan balasan ganda / bertabrakan.

**Bukti di Kode:**
```python
# ginee_browser.py baris 184-186
else:
    # Regular standby cycle on "Semua Pesan"
    processed_p2 = await _process_conversations_in_current_view(page)
```

**Langkah Perbaikan:**
1. Buka `bot/ginee_browser.py`
2. Di fungsi `process_unreplied_chats`, ubah logika utama agar **selalu** menggunakan filter `Belum Dibalas` sebagai sumber data:
```python
async def process_unreplied_chats(page) -> int:
    """Process chats: Always work from 'Belum Dibalas' filter only."""

    if bot_state.daily_reply_counter >= MAX_DAILY_REPLIES:
        log.warning("Daily reply limit reached (%d)", MAX_DAILY_REPLIES)
        return 0

    now = time.time()

    # --- Scheduled Check: Ensure Unified Layout only once every hour (3600s) ---
    if now - bot_state.last_layout_check >= 3600 or bot_state.last_layout_check == 0.0:
        log.info("--- Hourly layout refresh check ---")
        await ensure_unified_chat_layout(page)
        bot_state.last_layout_check = now

    # Selalu bekerja dari filter "Belum Dibalas"
    filter_ok = await select_filter_unreplied(page)
    if not filter_ok:
        log.warning("Failed to select 'Belum Dibalas' filter — skipping this cycle")
        return 0

    total_processed = await _process_conversations_in_current_view(page)

    log.debug("Completed processing cycle on 'Belum Dibalas' filter. Processed: %d", total_processed)
    return total_processed
```
3. Hapus import `select_filter_semua_pesan` dan konstanta `UNREPLIED_CHECK_INTERVAL_SECONDS` jika tidak lagi digunakan.
4. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:**
- Pastikan log hanya menunjukkan aktivitas pada filter `Belum Dibalas`.
- Minta CS manusia membalas satu conversation, pastikan bot **tidak** ikut membalas.

---

### Issue #22: 🔴 Parser fail-open: bubble tak dikenali dianggap buyer

**File:** `bot/ginee_parser.py` baris 153-160 dan `bot/ginee_navigation.py` baris 192
**Status Verifikasi:** ✅ Dikonfirmasi terhadap kode aktual

**Masalah:**
Ada dua titik kegagalan yang memperbesar risiko salah balas:

**A. Direction fallback ke "buyer"** (ginee_parser.py baris 159-160):
```python
else:
    direction = "buyer"  # <-- Bubble tak dikenali = buyer
```
Jika DOM Ginee berubah (misalnya style CSS baru), semua bubble seller, system, dan bot auto-reply akan diidentifikasi sebagai "buyer". Bot kemudian akan membalas pesan-pesan itu karena menganggapnya sebagai pertanyaan pembeli.

**B. Filter gagal tidak diperiksa** (ginee_browser.py baris 175-176):
```python
await select_filter_unreplied(page)  # bisa return False
processed_p1 = await _process_conversations_in_current_view(page)  # tetap dijalankan
```
`select_filter_unreplied` bisa return `False` (filter gagal diklik), tapi conversation tetap diproses di view apapun yang kebetulan aktif.

**Langkah Perbaikan (2 bagian):**

**Bagian A — Ubah default direction ke "unknown":**
1. Buka `bot/ginee_parser.py`
2. Ubah baris 159-160:
```python
# SEBELUM:
else:
    direction = "buyer"

# SESUDAH:
else:
    direction = "unknown"
```
3. Buka `bot/ginee_browser.py`
4. Di `_process_conversations_in_current_view`, setelah strip auto_reply (baris 68-70), tambahkan pengecekan unknown:
```python
# Setelah strip auto_reply
# Cek apakah ada terlalu banyak bubble "unknown" (indikasi DOM berubah)
unknown_count = sum(1 for m in messages if m.direction == "unknown")
if unknown_count > len(messages) * 0.5:
    log.warning("More than 50%% messages are 'unknown' direction — DOM may have changed. Skipping.")
    bot_state.replied_cache[prelim_hash] = time.time()
    continue
```

**Bagian B — Cek return value filter:**
1. Di `process_unreplied_chats`, cek return value sebelum memproses (sudah termasuk di fix Issue #21).
2. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:**
- Jalankan bot dan cari di log apakah ada message dengan `direction=unknown`.
- Jika ada banyak `unknown`, itu menandakan selector CSS perlu diupdate.

---

### Issue #23: 🔴 Static AUTO_REPLIES bypass guardrail AI (stok, garansi)

**File:** `bot/config.py` baris 56-63 dan `bot/ai_engine.py` baris 44-62, 203-207
**Status Verifikasi:** ✅ Dikonfirmasi terhadap kode aktual

**Masalah:**
System prompt AI di baris 111-113 secara tegas melarang:
> "Jangan pernah memberikan janji stok, harga, resi, atau garansi jika tidak tertulis di Knowledge Base."

Namun `AUTO_REPLIES` di `config.py` baris 56-63 **langsung menjawab**:
```python
AUTO_REPLIES = {
    "stok": "Stok produk masih tersedia, silakan diorder kak!",
    "garansi": "Produk bergaransi sesuai syarat dan ketentuan garansi toko kami.",
    # ...
}
```

Dan di `ai_engine.py` baris 203-207, static reply dicek **SEBELUM** AI:
```python
static_reply = get_auto_reply(buyer_message)
if static_reply:
    log.info("Matched static reply from knowledge base")
    return static_reply  # <-- Langsung return, AI tidak pernah dipanggil
```

Ini berarti jika buyer bertanya "stok ada ga?", bot langsung menjanjikan stok tersedia **tanpa mengecek** apakah benar stok tersedia menurut Knowledge Base. Sama untuk garansi.

Masalah kedua: `get_auto_reply` di baris 50-51 melakukan substring match `if key in msg`, sehingga keyword lama dalam riwayat chat juga bisa memicu. Contoh: buyer pernah bilang "stok habis ya" di awal, lalu bertanya soal lain, tapi bot tetap match keyword "stok".

**Langkah Perbaikan:**
1. Buka `bot/config.py`
2. **Hapus seluruh dictionary `AUTO_REPLIES`** atau kosongkan:
```python
# SEBELUM:
AUTO_REPLIES = {
    "harga": "Harga sudah tertera...",
    "stok": "Stok produk masih tersedia...",
    # ...
}

# SESUDAH:
AUTO_REPLIES = {}  # Semua jawaban sekarang melewati AI + Knowledge Base
```
3. **Pindahkan** isi jawaban yang masih relevan ke file `store_knowledge.txt` sebagai entri Knowledge Base:
```
T: berapa harganya / harga produk
J: Harga sudah tertera di halaman produk. Silakan cek produk kami ya kak 😊

T: ongkir / ongkos kirim berapa
J: Ongkir dihitung otomatis oleh sistem sesuai dengan alamat lokasi pengiriman.

T: kirim dari mana / pengiriman dari mana
J: Pengiriman dilakukan dari Penjaringan, Jakarta Utara.
```
4. **JANGAN** memindahkan jawaban stok dan garansi ke Knowledge Base kecuali memang bisa dijamin kebenarannya.
5. Buka `bot/ai_engine.py`
6. Hapus import `AUTO_REPLIES` di baris 19 dan hapus/sederhanakan fungsi `get_auto_reply` (baris 44-62).
7. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:**
- Kirim chat "stok ada ga?" dan pastikan bot merespons berdasarkan Knowledge Base atau mengembalikan TIDAK_TAHU (bukan hardcoded).
- Pastikan tidak ada lagi jawaban yang muncul tanpa melalui pengecekan Knowledge Base.

---

### Issue #24: 🟡 Cache preliminary menahan retry hingga 24 jam

**File:** `bot/ginee_browser.py` baris 65, 74, 83, 91, 100, 126, 136 dan `bot/config.py` baris 48
**Status Verifikasi:** ✅ Dikonfirmasi terhadap kode aktual

**Masalah:**
Setiap kali conversation gagal diproses (karena alasan apapun: DOM belum render, AI kosong, skip, dll), `prelim_hash` selalu dimasukkan ke cache:
```python
bot_state.replied_cache[prelim_hash] = time.time()
```

Cache ini expired setelah `CACHE_EXPIRY_SECONDS = 86400` (24 jam, baris 48 config.py). Artinya:
- Jika AI sementara down → conversation di-cache → buyer harus menunggu 24 jam sebelum bot mencoba ulang.
- Jika DOM lambat render → parse return kosong → conversation di-cache 24 jam.
- Sebaliknya, cache **hanya ada di memory** (Python dict) → restart bot menghilangkan seluruh deduplikasi → bot bisa membalas ulang semua conversation yang pernah dibalas sebelum restart.

**Langkah Perbaikan:**
1. Buka `bot/ginee_browser.py`
2. Bedakan cache untuk "sudah berhasil dibalas" dan "gagal diproses":
   - **Sukses**: gunakan `CACHE_EXPIRY_SECONDS` (24 jam) → ini memang benar.
   - **Gagal sementara** (AI error, DOM kosong, no messages): gunakan expiry pendek, misalnya 5 menit (300 detik).
```python
# Tambahkan konstanta di atas file
FAILED_CACHE_EXPIRY = 300  # 5 menit untuk kegagalan sementara

# Untuk kasus gagal (DOM kosong, AI empty, dll), ganti:
# SEBELUM:
bot_state.replied_cache[prelim_hash] = time.time()

# SESUDAH:
bot_state.replied_cache[prelim_hash] = time.time() - (CACHE_EXPIRY_SECONDS - FAILED_CACHE_EXPIRY)
```
Trik ini membuat hash akan "expired" 5 menit lagi, bukan 24 jam lagi, karena `cleanup_expired_cache` mengecek `now - timestamp > CACHE_EXPIRY_SECONDS`.

3. Baris yang **HARUS TETAP** menggunakan cache normal (24 jam): hanya baris 142-143 (setelah send berhasil).

4. Baris yang harus menggunakan cache pendek (5 menit):
   - Baris 65 (no messages after retries)
   - Baris 74 (all auto-replies)
   - Baris 83 (last msg not buyer)
   - Baris 91 (skip rule)
   - Baris 126 (AI empty)
   - Baris 136 (seller replied since snapshot)
   
   Catatan: baris 100 (dedup key match) harus tetap 24 jam karena ini berarti conversation **sudah pernah dijawab**.

5. Jalankan test: `python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:**
- Matikan Ollama, kirim chat pembeli, lihat log bahwa conversation di-skip.
- Nyalakan kembali Ollama, tunggu 5 menit.
- Pastikan bot **mencoba ulang** menjawab conversation tersebut tanpa harus restart.

---

### Issue #25: 🟡 Fresh production deployment berjalan DRY_RUN=true

**File:** `.github/workflows/ci-cd.yml` baris 188-189 dan `.env.example` baris 6
**Status Verifikasi:** ✅ Dikonfirmasi terhadap kode aktual

**Masalah:**
Alur CI/CD production (baris 188-189):
```bash
if [ ! -f ".env" ]; then
    cp .env.example .env
fi
```

File `.env.example` baris 6:
```
DRY_RUN=true
```

CI/CD **hanya** menginjeksi `GINEE_USERNAME` dan `GINEE_PASSWORD` via `sed` (baris 193-198). Tidak ada injeksi `DRY_RUN=false`. Artinya jika `.env` belum ada (server baru, volume terhapus, atau perpindahan path), bot production berjalan dalam **mode simulasi** tanpa benar-benar mengirim pesan.

**Dampak Konkret:**
- Bot terlihat "running" dan "healthy" di dashboard, tapi tidak mengirim satupun balasan.
- Sulit dideteksi karena log tetap menunjukkan aktivitas normal (hanya tidak ada actual send).

**Langkah Perbaikan:**
1. Buka `.github/workflows/ci-cd.yml`
2. Di bagian deploy production (setelah baris 198), tambahkan injeksi DRY_RUN:
```yaml
          # Force DRY_RUN=false for production
          sed -i "s/^DRY_RUN=.*/DRY_RUN=false/" .env
```
3. Di bagian deploy-preview (staging Windows), **jangan** tambahkan ini — staging memang harus DRY_RUN=true untuk keamanan.
4. Jalankan: `docker compose config` untuk validasi syntax.

**Verifikasi:**
- Hapus file `.env` di server production.
- Trigger deploy via push ke main.
- SSH ke server dan cek: `grep DRY_RUN .env` → harus menunjukkan `DRY_RUN=false`.

---

## Urutan Pengerjaan yang Disarankan

Untuk efisiensi, kerjakan dalam urutan berikut:

### Batch 0 — Arsitektur & Safety (PRIORITAS TERTINGGI — kerjakan sebelum semua batch lain)
- [ ] Issue #21 — Ubah mode standby ke "Belum Dibalas" only
- [ ] Issue #22 — Ubah default direction ke "unknown", cek return value filter
- [ ] Issue #23 — Hapus hardcoded AUTO_REPLIES, pindahkan ke Knowledge Base
- [ ] Issue #25 — Injeksi DRY_RUN=false di CI/CD production
- [ ] Issue #24 — Bedakan cache expiry untuk sukses vs gagal sementara

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

## Catatan untuk Junior Programmer / AI Executor

> **⚠️ PENTING:** Jangan kerjakan lebih dari satu issue dalam satu PR. Kerjakan satu issue, buat PR, minta review, merge, lalu lanjut ke berikutnya.

> **⚠️ PENTING:** Batch 0 harus dikerjakan secara berurutan (Issue #21 dulu, baru #22, dst.) karena ada dependensi antar issue.

> **⚠️ PENTING:** Setelah setiap perubahan, WAJIB jalankan `python -m unittest discover -s bot/tests -p "test_*.py"` dan pastikan semua test lulus sebelum commit.

> **⚠️ PENTING:** Issue #1, #4, #6, #7, #8, #9, #10, #11, #12, #13, #14 pada issue.md asli sudah dikerjakan di commit sebelumnya. Verifikasi dulu status masing-masing sebelum mengerjakan ulang.

---

## Referensi

- Repo sumber arsitektur: <https://github.com/cobacobiy/autochat>
- Aplikasi target: <https://chat.ginee.com/>
- Dokumentasi Playwright Python: <https://playwright.dev/python/docs/intro>



