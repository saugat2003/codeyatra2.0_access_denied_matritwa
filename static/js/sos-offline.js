/**
 * SOS Emergency — Offline-First Module
 * ─────────────────────────────────────
 * Handles one-tap SOS triggering, GPS capture, IndexedDB persistence
 * and background sync when connectivity is restored.
 *
 * Public API (attached to `window.SOS`):
 *   SOS.trigger(motherId, { note, riskLevel }) → Promise<result>
 *   SOS.syncQueue()                            → Promise<{synced, failed}>
 *   SOS.getPendingCount()                      → Promise<number>
 *   SOS.getQueue()                             → Promise<record[]>
 *   SOS.clearSynced()                          → Promise<void>
 */

(() => {
  "use strict";

  // ── Configuration ──────────────────────────────────────────────

  const DB_NAME    = "matritwa_sos";
  const DB_VERSION = 1;
  const STORE_NAME = "sos_queue";

  const API_CREATE = "/api/sos/";
  const API_SYNC   = "/api/sos/sync/";

  const GPS_TIMEOUT     = 10_000;   // 10 s
  const GPS_MAX_AGE     = 60_000;   // accept cached position ≤60 s
  const SYNC_INTERVAL   = 30_000;   // auto-retry every 30 s

  // ── IndexedDB helpers ──────────────────────────────────────────

  /** Open (or create) the SOS IndexedDB database. */
  function openDB() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);

      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: "offline_id" });
          store.createIndex("status", "sync_status", { unique: false });
          store.createIndex("mother", "mother_id",    { unique: false });
        }
      };

      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => reject(req.error);
    });
  }

  /** Save or update a record in the queue store. */
  async function dbPut(record) {
    const db    = await openDB();
    const tx    = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    store.put(record);
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onerror    = () => { db.close(); reject(tx.error); };
    });
  }

  /** Get all records with sync_status === "pending". */
  async function dbGetPending() {
    const db    = await openDB();
    const tx    = db.transaction(STORE_NAME, "readonly");
    const idx   = tx.objectStore(STORE_NAME).index("status");
    const req   = idx.getAll("pending");
    return new Promise((resolve, reject) => {
      req.onsuccess = () => { db.close(); resolve(req.result); };
      req.onerror   = () => { db.close(); reject(req.error); };
    });
  }

  /** Get ALL records (pending + synced). */
  async function dbGetAll() {
    const db    = await openDB();
    const tx    = db.transaction(STORE_NAME, "readonly");
    const req   = tx.objectStore(STORE_NAME).getAll();
    return new Promise((resolve, reject) => {
      req.onsuccess = () => { db.close(); resolve(req.result); };
      req.onerror   = () => { db.close(); reject(req.error); };
    });
  }

  /** Delete all records whose sync_status === "synced". */
  async function dbClearSynced() {
    const db    = await openDB();
    const tx    = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const idx   = store.index("status");
    const req   = idx.openCursor("synced");

    req.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      }
    };

    return new Promise((resolve, reject) => {
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onerror    = () => { db.close(); reject(tx.error); };
    });
  }

  // ── GPS helper ─────────────────────────────────────────────────

  /**
   * Attempt to get the device's current GPS position.
   * Returns { latitude, longitude } or { latitude: null, longitude: null }
   * if unavailable or timed out.
   */
  function getPosition() {
    return new Promise((resolve) => {
      if (!navigator.geolocation) {
        return resolve({ latitude: null, longitude: null });
      }
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          resolve({
            latitude:  pos.coords.latitude.toFixed(6),
            longitude: pos.coords.longitude.toFixed(6),
          }),
        () => resolve({ latitude: null, longitude: null }),
        { enableHighAccuracy: true, timeout: GPS_TIMEOUT, maximumAge: GPS_MAX_AGE },
      );
    });
  }

  // ── Network helpers ────────────────────────────────────────────

  function isOnline() {
    return navigator.onLine;
  }

  /** POST JSON to a URL. Returns { ok, data } or { ok: false, error }. */
  async function postJSON(url, body) {
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",            // send session cookie
        body: JSON.stringify(body),
      });
      const data = await resp.json();
      return { ok: resp.ok, data };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  }

  // ── Core: trigger ──────────────────────────────────────────────

  /**
   * One-tap SOS trigger.
   *
   * 1. Captures GPS (best-effort).
   * 2. Creates a local IndexedDB record (instant, works offline).
   * 3. If online, attempts to push to server immediately.
   * 4. Returns a result object.
   *
   * @param {number} motherId – MotherProfile PK
   * @param {object} opts
   * @param {string} [opts.note]      – free-text
   * @param {string} [opts.riskLevel] – CRITICAL | HIGH | MODERATE | LOW
   * @returns {Promise<{ offlineId, synced, serverData? }>}
   */
  async function trigger(motherId, { note = "", riskLevel = "" } = {}) {
    const offlineId  = crypto.randomUUID();
    const triggeredAt = new Date().toISOString();
    const { latitude, longitude } = await getPosition();

    const record = {
      offline_id:   offlineId,
      mother_id:    motherId,
      latitude,
      longitude,
      note,
      risk_level:   riskLevel,
      triggered_at: triggeredAt,
      sync_status:  "pending",   // IndexedDB-only field
    };

    // Persist locally first (offline-safe)
    await dbPut(record);

    // Attempt immediate server push
    if (isOnline()) {
      const { ok, data } = await postJSON(API_CREATE, record);
      if (ok) {
        record.sync_status  = "synced";
        record.server_id    = data.sos?.id;
        await dbPut(record);
        return { offlineId, synced: true, serverData: data.sos };
      }
    }

    // Offline or server unreachable — queued for later sync
    return { offlineId, synced: false };
  }

  // ── Core: sync queue ───────────────────────────────────────────

  /**
   * Push all pending records to the server in one bulk request.
   *
   * Idempotent: duplicate offline_ids are handled server-side.
   * @returns {Promise<{ synced: number, failed: number }>}
   */
  async function syncQueue() {
    const pending = await dbGetPending();
    if (pending.length === 0) return { synced: 0, failed: 0 };

    if (!isOnline()) return { synced: 0, failed: pending.length };

    const { ok, data } = await postJSON(API_SYNC, { records: pending });
    if (!ok) return { synced: 0, failed: pending.length };

    let synced = 0;
    let failed = 0;

    for (const result of (data.results || [])) {
      const rec = pending[result.index];
      if (result.ok && rec) {
        rec.sync_status = "synced";
        rec.server_id   = result.id;
        await dbPut(rec);
        synced++;
      } else {
        failed++;
      }
    }

    return { synced, failed };
  }

  // ── Auto-sync on connectivity change ──────────────────────────

  let _syncTimer = null;

  function _startAutoSync() {
    // Sync when browser reports online
    window.addEventListener("online", () => {
      syncQueue().catch(console.error);
    });

    // Periodic retry (covers edge cases where 'online' fires too early)
    _syncTimer = setInterval(async () => {
      if (isOnline()) {
        const pending = await dbGetPending();
        if (pending.length > 0) syncQueue().catch(console.error);
      }
    }, SYNC_INTERVAL);
  }

  _startAutoSync();

  // ── Pending badge helper ───────────────────────────────────────

  /**
   * Update a DOM element's text with the pending-sync count.
   * Call this on page load and after trigger / sync.
   *
   * @param {string} selector – CSS selector of the badge element
   */
  async function updateBadge(selector) {
    const el = document.querySelector(selector);
    if (!el) return;
    const count = await getPendingCount();
    el.textContent = count;
    el.style.display = count > 0 ? "inline-flex" : "none";
  }

  async function getPendingCount() {
    const pending = await dbGetPending();
    return pending.length;
  }

  // ── Public API ─────────────────────────────────────────────────

  window.SOS = {
    trigger,
    syncQueue,
    getPendingCount,
    getQueue:     dbGetAll,
    clearSynced:  dbClearSynced,
    updateBadge,
  };
})();
