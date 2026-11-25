const CACHE_NAME = "myday-v1";

self.addEventListener("install", (event) => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        self.clients.claim()
    );
});

self.addEventListener("fetch", (event) => {
    // Requests will use the normal network.
});