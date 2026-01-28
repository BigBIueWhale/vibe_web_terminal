/**
 * SessionStore — shared localStorage module for managing session IDs.
 * Exposes a global `SessionStore` object.
 */
const SessionStore = (function () {
    const STORAGE_KEY = 'vibe_sessions';

    function _load() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function _persist(sessions) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }

    /** Add a session to localStorage (idempotent). */
    function save(id) {
        const sessions = _load();
        if (sessions.some(s => s.id === id)) return;
        sessions.push({
            id: id,
            addedAt: new Date().toISOString(),
            label: id.substring(0, 8)
        });
        _persist(sessions);
    }

    /** Remove a session from localStorage. */
    function remove(id) {
        const sessions = _load().filter(s => s.id !== id);
        _persist(sessions);
    }

    /** Return all saved sessions. */
    function getAll() {
        return _load();
    }

    /**
     * POST to /sessions/status with all saved IDs, auto-prune "gone" ones.
     * Returns array of {id, addedAt, label, status, created_at}.
     */
    async function checkAll() {
        const sessions = _load();
        if (sessions.length === 0) return [];

        try {
            const response = await fetch('/sessions/status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_ids: sessions.map(s => s.id) })
            });
            if (!response.ok) return sessions;

            const data = await response.json();
            const statuses = data.sessions || {};

            // Auto-prune gone sessions
            const alive = [];
            const result = [];
            for (const s of sessions) {
                const info = statuses[s.id];
                if (info && info.status === 'gone') continue;
                alive.push(s);
                result.push({
                    ...s,
                    status: info ? info.status : 'unknown',
                    created_at: info ? info.created_at : null
                });
            }
            _persist(alive);

            // Sort: running first, then by addedAt descending
            result.sort((a, b) => {
                const aRunning = a.status === 'running' ? 0 : 1;
                const bRunning = b.status === 'running' ? 0 : 1;
                if (aRunning !== bRunning) return aRunning - bRunning;
                return new Date(b.addedAt) - new Date(a.addedAt);
            });

            return result;
        } catch (e) {
            return sessions;
        }
    }

    /** Call DELETE /session/{id} and remove from localStorage. */
    async function deleteSession(id) {
        try {
            await fetch(`/session/${id}`, { method: 'DELETE' });
        } catch (e) {
            // Ignore network errors — still remove locally
        }
        remove(id);
    }

    /** If response is 404, remove the session from localStorage. */
    function handleApiResponse(id, response) {
        if (response && response.status === 404) {
            remove(id);
        }
    }

    return {
        save: save,
        remove: remove,
        getAll: getAll,
        checkAll: checkAll,
        deleteSession: deleteSession,
        handleApiResponse: handleApiResponse
    };
})();
