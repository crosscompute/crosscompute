const dbp = indexedDB.open('failed-requests', 1);

dbp.onupgradeneeded = event => {
  const db = event.target.result;
  db.createObjectStore('requests', { autoIncrement: true });
};

self.addEventListener('install', event => {
// TODO: Cache assets for offline loading
});

self.addEventListener('fetch', async event => {
  if (event.request.url === `${event.request.referrer}.json`) {
    event.respondWith(
      fetch(event.request.clone()).catch(async (e) => {
        if (e instanceof TypeError) {
          await storeFailedRequest(event.request);
          return new Response('fetch postponed');
        }
      })
    );
  }
});

async function storeFailedRequest(request) {
  const clonedRequest = request.clone();
  const streamChunks = [];
  const reader = clonedRequest.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    streamChunks.push(value);
  }
  const db = dbPromise.result;
  const tx = db.transaction('requests', 'readwrite');
  const store = tx.objectStore('requests');
  store.add({
    url: request.url,
    method: request.method,
    body: streamChunks});
  return tx.complete;
}

self.addEventListener('sync', event => {
  if (event.tag === 'sync-messages') {
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
        fetch(r.url, {
          method: r.method,
          body: new Blob(r.body)})
        .then(response => {
          // TODO: Handle response
          console.log(response);
        })
        .catch(e => {
          console.log(e);
        });
      })
    }
  };
  store.clear();
  return tx.complete;
}

// self.addEventListener('push', event => {});
