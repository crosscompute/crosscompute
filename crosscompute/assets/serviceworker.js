const dbPromise = indexedDB.open('failed-requests', 1);

dbPromise.onupgradeneeded = event => {
    const db = event.target.result;
    db.createObjectStore('requests', { autoIncrement: true });
};


self.addEventListener('install', event => {
//    event.waitUntil(
//        openCacheForCurrentURL().then(cache => {
//            return cache.addAll([
//            ]);
//        }));
});

self.addEventListener('fetch', async event => {
    const SUBMIT_URL = `${event.request.referrer}.json`
    if (event.request.url.includes(SUBMIT_URL)) {
        event.respondWith(
            fetch(event.request.clone()).catch(async (error) => {
                if (error instanceof TypeError) {
                    await storeFailedRequest(event.request);

                    return new Response("Offline mode: Failed to fetch due to no connectivity");

                    // await saveFormDataToCache(event.request)
                }}));
    }
//     else {
//        event.respondWith(fetch(event.request));
//    }
});


async function storeFailedRequest(request) {
    const clonedRequest = request.clone();
    const streamChunks = [];

    const reader = clonedRequest.body.getReader();
    while (true) {
        const { done, value } = await reader.read();
        if (done) {
            break;
        }
        streamChunks.push(value);
    }

    // Store the captured request body in IndexedDB or another storage mechanism

    const db = dbPromise.result;
    const tx = db.transaction('requests', 'readwrite');
    const store = tx.objectStore('requests');
    store.add({
        url: request.url,
        method: request.method,
        body: streamChunks
    });
    return tx.complete;
}

self.addEventListener('sync', event => {
    if (event.tag === 'data-sync') {
        event.waitUntil(processFailedRequests());
    }
});

function processFailedRequests() {
    let db = dbPromise.result;
    let tx = db.transaction('requests', 'readwrite');
    let store = tx.objectStore('requests');

    let request = store.getAll()

    request.onsuccess = function() {
        if (request.result !== undefined) {
            request.result.forEach((r) => {
                const body = new Blob(r.body);

                // Now you can use 'body' in your fetch request
                fetch(r.url, {
                    method: r.method,
                    body: body
                })
                .then(response => {
                    // Handle response
                    console.log(response)
                })
                .catch(error => {
                    console.log(error)
                });
                    console.log("Request", r);
            })
        } else {
            console.log("No pending requests");
        }
    };

    store.clear();

    return tx.complete;
}

self.addEventListener('push', event => {
    
});
