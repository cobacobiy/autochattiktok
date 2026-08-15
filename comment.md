# Code Review: PR #2 — Fix: Implement Code Review Improvements

> **Tanggal Review:** 15 Agustus 2026
> **PR Link:** https://github.com/cobacobiy/autochattiktok/pull/2
> **Verdict:** ⚠️ **Ada 8 temuan yang perlu diperbaiki sebelum merge.**
> **Cara Pakai:** Setiap temuan di bawah bisa dikerjakan secara independen. Kerjakan langsung di branch `fix/code-review-issues`, commit, push, lalu review ulang.

---

## Ringkasan Temuan

| No | Severity | File | Masalah |
|----|----------|------|---------|
| 1 | 🔴 Bug | `bot/ai_engine.py` | `DEFAULT_REPLY` dikirim untuk kasus TIDAK_TAHU — ini bisa menyebabkan bot mengirim jawaban generik ke pembeli |
| 2 | 🔴 Bug | `bot/ai_engine.py` | `_http_client` module-level bisa leak/hang — tidak ada graceful close |
| 3 | 🔴 Bug | `bot/ai_engine.py` | `os.makedirs` crash saat `UNANSWERED_PATH` tidak punya parent directory |
| 4 | 🟡 Bug | `bot/ginee_sender.py` | Verifikasi bubble pakai `import` di dalam fungsi — kurang efisien dan test log warning |
| 5 | 🟡 Bug | `bot/browser_loop.py` | `bot_state.last_error` tidak pernah di-set walaupun field sudah ada |
| 6 | 🟡 Code Quality | `bot/ginee_navigation.py` | Baris kosong berlebihan di akhir file setelah hapus `open_unreplied_tab` |
| 7 | 🟡 Test | `bot/tests/test_ai_engine.py` | Test tidak memverifikasi bahwa `log_unanswered_question` benar-benar terpanggil saat DEFAULT_REPLY dikembalikan |
| 8 | 🟢 Code Quality | `bot/state.py` | Trailing whitespace pada baris 17 dan 23 |

---

## Detail Temuan & Langkah Perbaikan

---

### Temuan #1: 🔴 `DEFAULT_REPLY` dikirim ke pembeli saat AI gagal — ini bisa berbahaya

**File:** [bot/ai_engine.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/ai_engine.py#L211-L228)
**Masalah:**
Sebelum PR ini, ketika AI mengembalikan `TIDAK_TAHU` atau respons terlalu panjang, bot mengembalikan string kosong `""` dan **tidak mengirim pesan apapun** ke pembeli. Ini adalah perilaku yang aman.

Sekarang, bot mengembalikan `DEFAULT_REPLY` ("Ada yang bisa dibantu?") yang akan **benar-benar dikirim ke pembeli**. Ini berarti:
- Pertanyaan "Berapa berat paket ini?" → AI gagal menjawab → bot mengirim "Ada yang bisa dibantu?" — **tidak relevan dan membingungkan**
- Setiap pertanyaan yang AI tidak tahu jawabannya, pembeli tetap menerima respons generik

Ini bertentangan dengan prinsip keselamatan di `issue.md` bagian "Implementasi pengiriman aman" yang menyatakan: *"Jika output TIDAK_TAHU, kosong, terlalu panjang... jangan kirim."*

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Di baris 217, kembalikan ke string kosong:
```python
# SEBELUM (baris 217):
        return DEFAULT_REPLY

# SESUDAH:
        return ""
```
3. Di baris 228, lakukan hal yang sama:
```python
# SEBELUM (baris 228):
        return DEFAULT_REPLY

# SESUDAH:
        return ""
```
4. Buka `bot/tests/test_ai_engine.py`
5. Ubah kembali assertion di baris 48:
```python
# SEBELUM:
        self.assertEqual(reply, ai_engine.DEFAULT_REPLY)
# SESUDAH:
        self.assertEqual(reply, "")
```
6. Ubah kembali assertion di baris 62:
```python
# SEBELUM:
        self.assertEqual(reply, ai_engine.DEFAULT_REPLY)
# SESUDAH:
        self.assertEqual(reply, "")
```
7. Jika memang ingin menggunakan `DEFAULT_REPLY`, seharusnya hanya digunakan di **skenario yang benar-benar aman** (misalnya ketika pembeli hanya bilang "halo" tanpa pertanyaan spesifik). Untuk itu, buat logic baru yang terpisah.
8. Jalankan test: `.venv/bin/python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Test harus lulus dan bot tidak mengirim jawaban generik untuk pertanyaan yang AI gagal jawab.

---

### Temuan #2: 🔴 `_http_client` module-level tidak pernah ditutup

**File:** [bot/ai_engine.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/ai_engine.py#L32) baris 32
**Masalah:**
```python
_http_client = httpx.Client(timeout=120.0)
```
Client ini dibuat di module level dan tidak pernah di-close. Walaupun Python akan membersihkannya saat exit, jika modul di-reload (misalnya saat testing atau hot reload), koneksi lama akan terbuang tanpa ditutup.

Selain itu, `_http_client` juga rentan terhadap **stale connection** jika koneksi ke server AI terputus lama — httpx `Client` tidak otomatis reconnect.

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Ganti client creation di baris 32 dengan lazy initialization dan retry-safe pattern:
```python
# SEBELUM (baris 32):
_http_client = httpx.Client(timeout=120.0)

# SESUDAH:
_http_client: httpx.Client | None = None

def _get_http_client() -> httpx.Client:
    """Get or create reusable httpx client."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.Client(timeout=120.0)
    return _http_client
```
3. Ganti semua `_http_client.post(...)` di `call_ollama`, `call_gemini`, `call_claude` menjadi `_get_http_client().post(...)`.

   Contoh di `call_ollama` (baris 116):
```python
# SEBELUM:
    resp = _http_client.post(url, json=payload)
# SESUDAH:
    resp = _get_http_client().post(url, json=payload)
```
   Lakukan hal yang sama di baris 135 (`call_gemini`) dan baris 166 (`call_claude`).
4. Jalankan test: `.venv/bin/python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Test harus lulus, dan jika client tertutup secara tidak sengaja, ia akan dibuat ulang otomatis.

---

### Temuan #3: 🔴 `os.makedirs` crash saat `UNANSWERED_PATH` tidak punya parent directory

**File:** [bot/ai_engine.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/ai_engine.py#L64) baris 64
**Masalah:**
```python
os.makedirs(os.path.dirname(UNANSWERED_PATH), exist_ok=True)
```
Jika `UNANSWERED_PATH` adalah path tanpa directory (misalnya `"unanswered_questions.txt"` — hanya nama file), maka `os.path.dirname()` mengembalikan string kosong `""`. Lalu `os.makedirs("")` akan **raise `FileNotFoundError`** di beberapa OS, menyebabkan seluruh fungsi `log_unanswered_question` gagal.

**Langkah Perbaikan:**
1. Buka `bot/ai_engine.py`
2. Ubah baris 64 untuk menambah guard:
```python
# SEBELUM (baris 64):
        os.makedirs(os.path.dirname(UNANSWERED_PATH), exist_ok=True)

# SESUDAH:
        parent_dir = os.path.dirname(UNANSWERED_PATH)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
```
3. Jalankan test: `.venv/bin/python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Test harus lulus. Coba tes manual dengan `UNANSWERED_PATH=unanswered_questions.txt` (tanpa path).

---

### Temuan #4: 🟡 Import di dalam fungsi `send_ginee_reply`

**File:** [bot/ginee_sender.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/ginee_sender.py#L68) baris 68
**Masalah:**
```python
        # Verify outgoing bubble appeared
        try:
            from bot.ginee_parser import parse_chat_messages  # <-- import di dalam fungsi
```
Import di dalam fungsi tidak efisien karena dieksekusi setiap kali fungsi dipanggil. Selain itu, test `test_send_production_success` mengeluarkan warning `Reply verification failed: 'MagicMock' object can't be awaited` karena `parse_chat_messages` tidak di-mock dengan benar.

**Langkah Perbaikan:**
1. Buka `bot/ginee_sender.py`
2. Pindahkan import ke bagian atas file (setelah baris 6):
```python
# Tambahkan di bagian import atas (setelah baris 6):
from bot.ginee_parser import parse_chat_messages
```
3. Hapus baris 68 (`from bot.ginee_parser import parse_chat_messages` di dalam fungsi).
4. Buka `bot/tests/test_ginee_sender.py`
5. Di test `test_send_production_success` (baris 36-61), tambahkan patch untuk `parse_chat_messages`:
```python
    @patch("bot.ginee_sender.parse_chat_messages")
    @patch("bot.ginee_sender.first_visible")
    def test_send_production_success(self, mock_first_visible, mock_parse):
        async def run_test():
            page = MagicMock()
            page.wait_for_timeout = AsyncMock()
            page.keyboard.insert_text = AsyncMock()
            input_loc = AsyncMock()
            input_loc.evaluate = AsyncMock(return_value="div")

            send_btn = AsyncMock()
            send_btn.click = AsyncMock()

            # Simulate verified seller bubble
            from bot.ginee_parser import ChatMessage
            mock_parse.return_value = [
                ChatMessage(message_id=None, text="Halo kak", direction="seller")
            ]

            mock_first_visible.side_effect = [
                (input_loc, "input"),
                (send_btn, "button"),
                (None, None),
            ]

            with patch("bot.ginee_sender.DRY_RUN", False):
                result = await ginee_sender.send_ginee_reply(page, "Halo kak")
                self.assertTrue(result)
                send_btn.click.assert_called_once()

        import asyncio
        asyncio.run(run_test())
```
6. Jalankan test: `.venv/bin/python -m unittest bot/tests/test_ginee_sender.py`

**Verifikasi:** Test harus lulus tanpa warning `MagicMock object can't be awaited`.

---

### Temuan #5: 🟡 `bot_state.last_error` tidak pernah di-set

**File:** [bot/browser_loop.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/browser_loop.py#L125-L130) baris 125-130
**Masalah:**
Field `last_error` ditambahkan di `state.py` dan dikembalikan di `snapshot()`, tapi **tidak pernah di-set di manapun**. Artinya health endpoint selalu mengembalikan `"last_error": ""` walaupun ada error.

**Langkah Perbaikan:**
1. Buka `bot/browser_loop.py`
2. Di baris 126, setelah `bot_state.bot_status = "error"`, tambahkan set `last_error`:
```python
# SEBELUM (baris 125-130):
            except Exception as e:
                bot_state.bot_status = "error"
                consecutive_errors += 1

# SESUDAH:
            except Exception as e:
                bot_state.bot_status = "error"
                bot_state.last_error = str(e)[:200]
                consecutive_errors += 1
```
3. Juga reset `last_error` saat sukses (di sekitar baris 113-114):
```python
# Setelah bot_state.last_successful_cycle = time.time():
                    bot_state.last_error = ""
```
4. Jalankan test: `.venv/bin/python -m unittest discover -s bot/tests -p "test_*.py"`

**Verifikasi:** Curl health endpoint setelah error terjadi dan pastikan `last_error` terisi.

---

### Temuan #6: 🟡 Baris kosong berlebihan di akhir `ginee_navigation.py`

**File:** [bot/ginee_navigation.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/ginee_navigation.py#L203-L208) baris 203-208
**Masalah:**
Setelah menghapus fungsi `open_unreplied_tab`, ada 5 baris kosong tersisa di akhir file (baris 204-208). PEP 8 menganjurkan tepat 1 baris kosong di akhir file.

**Langkah Perbaikan:**
1. Buka `bot/ginee_navigation.py`
2. Hapus baris kosong berlebihan di akhir file (baris 204-208).
3. File harus berakhir di:
```python
async def select_filter_semua_pesan(page) -> bool:
    """Switch dropdown filter specifically to 'Semua Pesan' / 'All Message'."""
    return await select_filter_option(page, ["Semua Pesan", "All Message", "All"])
```
   Diikuti **tepat 1 baris kosong**.
4. Jalankan lint: `.venv/bin/python -m ruff check bot/ginee_navigation.py`

**Verifikasi:** Tidak ada trailing whitespace atau baris kosong berlebihan.

---

### Temuan #7: 🟡 Test tidak memverifikasi bahwa unanswered question di-log saat DEFAULT_REPLY

**File:** [bot/tests/test_ai_engine.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/tests/test_ai_engine.py#L39-L65)
**Masalah:**
Test `test_generate_ai_reply_tidak_tahu` dan `test_generate_ai_reply_too_long` hanya mengecek return value tapi **tidak memverifikasi** bahwa:
1. `log_unanswered_question` benar-benar dipanggil
2. File unanswered benar-benar tertulis

Ini penting karena fungsi log bisa saja gagal silently di future refactoring.

**Langkah Perbaikan:**
1. Buka `bot/tests/test_ai_engine.py`
2. Di test `test_generate_ai_reply_tidak_tahu` (baris 39-51), tambahkan assertion bahwa file unanswered tertulis:
```python
    @patch("bot.ai_engine.call_ollama")
    def test_generate_ai_reply_tidak_tahu(self, mock_call):
        mock_call.return_value = "TIDAK_TAHU"
        test_path = os.path.join(tempfile.gettempdir(), "test_unanswered_tt.txt")
        ai_engine.UNANSWERED_PATH = test_path
        if os.path.exists(test_path):
            os.remove(test_path)

        reply = ai_engine.generate_ai_reply("Berapa berat paket ini?", "hash_tt", "store:tiktok")
        self.assertEqual(reply, "")

        # Verifikasi unanswered question tercatat
        self.assertTrue(os.path.exists(test_path), "Unanswered file should be created")
        with open(test_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("TIDAK_TAHU", content)
            self.assertIn("Berapa berat paket ini?", content)

        if os.path.exists(test_path):
            os.remove(test_path)
```
3. Lakukan hal yang sama untuk `test_generate_ai_reply_too_long`: tambahkan verifikasi file unanswered dan cek reason `TOO_LONG`.
4. Jalankan test: `.venv/bin/python -m unittest bot/tests/test_ai_engine.py`

**Verifikasi:** Test harus lulus dan memverifikasi bahwa file unanswered benar-benar ditulis.

---

### Temuan #8: 🟢 Trailing whitespace di `bot/state.py`

**File:** [bot/state.py](file:///home/cacyos/Downloads/github/autochattiktok/bot/state.py#L17) baris 17 dan 23
**Masalah:**
Baris 17 dan 23 memiliki trailing whitespace (spasi di akhir baris kosong). Ini akan ditangkap oleh linter.

**Langkah Perbaikan:**
1. Buka `bot/state.py`
2. Hapus trailing whitespace di baris 17 (baris kosong setelah `knowledge_answers`) dan baris 23 (baris kosong setelah `last_unreplied_filter_check`).
3. Jalankan lint: `.venv/bin/python -m ruff check bot/state.py`

**Verifikasi:** Tidak ada trailing whitespace warning.

---

## Urutan Pengerjaan yang Disarankan

### 🔥 Harus diperbaiki sebelum merge:
- [ ] Temuan #1 — Revert `DEFAULT_REPLY` → kembalikan ke `""` (paling penting untuk keselamatan bot)
- [ ] Temuan #3 — Guard `os.makedirs` untuk path tanpa directory
- [ ] Temuan #2 — Lazy init `_http_client` agar tidak stale/leak

### ⚡ Sebaiknya diperbaiki sebelum merge:
- [ ] Temuan #5 — Set `bot_state.last_error`
- [ ] Temuan #4 — Pindahkan import ke top-level dan fix test mock
- [ ] Temuan #7 — Tambah assertion unanswered file di test

### 🧹 Bisa di-merge dulu, diperbaiki kemudian:
- [ ] Temuan #6 — Hapus baris kosong berlebihan
- [ ] Temuan #8 — Hapus trailing whitespace

---

## Catatan Positif ✅

Beberapa hal yang sudah dikerjakan dengan **baik** di PR ini:
- ✅ Gemini API key sudah dipindahkan ke header `x-goog-api-key` — benar dan aman
- ✅ Exponential backoff di browser loop sudah diimplementasi dengan benar
- ✅ Thread-safe snapshot di `BotState` menggunakan `threading.Lock` — pattern yang tepat
- ✅ DOM retry loop di `ginee_browser.py` — pragmatis dan efektif
- ✅ File rotation untuk unanswered file — approach yang benar
- ✅ Store/channel context di AI prompt — meningkatkan relevansi jawaban AI
- ✅ Docker network tanpa `external: true` — deployment lebih robust
- ✅ Test path portabel dengan `tempfile.gettempdir()` — cross-platform ready
