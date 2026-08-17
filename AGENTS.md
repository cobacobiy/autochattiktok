# AGENTS.md — autochattiktok

## Role & Scope
You are an automation and AI developer assistant working on **autochattiktok** (Ginee Chat Auto-Reply AI Bot).
This application provides intelligent automated responses for Ginee Chat (`chat.ginee.com`), handling multi-channel TikTok/Shopee customer support with guardrails and safety controls.

## Tech Stack & Port Mappings
- **Language & Engine**: Python, Playwright.
- **Key Libraries**: `httpx` (HTTP client), `tenacity` (retry decorator).
- **AI Providers**: Ollama (default: `qwen2.5:3b`), Google Gemini, Anthropic Claude.
- **Port Allocation**:
  - **noVNC Web UI**: `http://localhost:6085`
  - **VNC Direct Port**: `5905`
  - **Health API Status**: `http://localhost:7085`
- **Session Data**: Persistent browser profile stored in `/data/ginee-profile`.

## Key Environment Variables
- `GINEE_CHAT_URL` — Target URL Ginee Chat (default: `https://chat.ginee.com/`).
- `DRY_RUN` — Safety mode, default `true`. Set `false` hanya di production.
- `BROWSER_LIFETIME` — Waktu hidup browser sebelum restart otomatis (default: `21600` detik / 6 jam).
- `KNOWLEDGE_PATH` — Path file knowledge base (default: `/app/store_knowledge.txt`).
- `UNANSWERED_PATH` — Path file pencatatan pertanyaan tak terjawab (default: `/app/unanswered_questions.txt`).
- `DEFAULT_REPLY` — Fallback reply jika AI tidak menghasilkan jawaban.
- `POLL_INTERVAL` — Interval polling percakapan dalam detik (default: `8`, minimum: `3`).
- `MAX_DAILY_REPLIES` — Batas maksimum balasan per hari (default: `5000`).
- **Hardcoded Config**: `SKIP_MESSAGES` (set pesan yang di-skip, e.g. "ok", "makasih") dan `ADMIN_KEYWORDS` (keyword yang memerlukan penanganan admin, e.g. "gojek", "grab", "sameday") didefinisikan di `bot/config.py`.

## Critical Operational Rules
1. **Chat Queue & Standby Mode (`Semua Pesan` / `Belum Dibalas`)**:
   - Primary CS standby mode operates on the `Semua Pesan` (All Messages) filter to handle incoming customer threads continuously.
   - Periodically checks the `Belum Dibalas` (Unreplied) filter (every 15 minutes) before returning to `Semua Pesan`.
2. **Race Protection & Deduplication**:
   - Maintain state locks to guarantee at most 1 reply per buyer thread across iterations.
3. **Safety Mode (`DRY_RUN`)**:
   - Default to `DRY_RUN=true` when developing or testing. In dry run mode, generate draft predictions without clicking the send button.
4. **Port Separation**:
   - Always verify ports (`6085`, `5905`, `7085`) to avoid conflicts with other auto-reply bot instances on the host system.
5. **Environment Configuration (`.env` / `.env.example`)**:
   - For Docker Compose operations, always ensure a `.env` or `.env.example` file containing required credentials and environment variables is created and maintained.
   - Never hardcode sensitive credentials directly inside `docker-compose.yml`.
6. **DOM Selectors & Fragility**:
   - Prefer robust, immutable IDs (e.g., `#account`, `#password`) over fragile attributes (e.g., `placeholder*='Email'`) that can fail due to case-sensitivity or i18n changes.
   - Throttle aggressive UI recovery actions (like layout refreshes) to run maximally once per hour to prevent infinite loops when the upstream DOM changes unexpectedly.
7. **Trailing Auto-Replies**:
   - When parsing chat threads, strip trailing `auto_reply` messages (e.g., "[Balasan Otomatis Ginee]") from the end of the conversation history. This ensures the bot evaluates and responds to the *actual* last message from the buyer, rather than falsely aborting because a system/seller auto-reply was sent.
8. **Environment Infrastructure Policy**:
   - **Coding Device (Local)**: This local machine is strictly for **coding, development, and unit testing**.
   - **Staging Environment (Windows)**: Code pushed to a Pull Request deploys to **Staging Windows** (`[self-hosted, windows]`).
   - **Production Environment (Server 226 Linux)**: Code merged into `main` automatically deploys to **Production Linux Server 226** (`[self-hosted, 226node2]`).
   - **Multiplatform Docker & Credentials**: Always use Docker Compose for multiplatform deployments across Linux and Windows. Maintain secrets strictly in `.env` created from `.env.example`. Never hardcode sensitive credentials inside `docker-compose.yml` or source code.
9. **MANDATORY PRE-PUSH UNIT TESTING**:
   - **NEVER** commit or push code to GitHub without first running and verifying the unit test suite:
     ```bash
     .venv/bin/python -m unittest discover -s bot/tests -p "test_*.py"
     ```
   - Pushing code with failing unit tests is **STRICTLY PROHIBITED**.

10. **Frontend Modularization & File Editing Policy**:
    - **No Monolithic HTML**: Do NOT bundle HTML, CSS, and JavaScript together inside a single monolithic `index.html` file. Always modularize web assets into separate files (`index.html`, `style.css`, and `app.js`).
    - **No Python One-Liner Overwriting**: NEVER use inline Python script commands in terminal (`python3 -c 'html_content = ...'`) to write or replace HTML/code files. Always edit files directly using proper file writing/editing tools.

## Verification & Testing Workflows
- **Run Unit Tests (MANDATORY BEFORE PUSH)**:
  Before committing or pushing changes, execute the test suite:
  ```bash
  .venv/bin/python -m unittest discover -s bot/tests -p "test_*.py"
  ```
- **Run Container**:
  Ensure `.env` exists with all credentials before launching Docker Compose:
  ```bash
  cp -n .env.example .env
  docker compose up -d --build
  ```
- **Health Check**:
  Verify bot status via `curl http://localhost:7085`.
