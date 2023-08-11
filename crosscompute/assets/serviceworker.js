const SUBMIT_URL = '/submit';
const CACHE_FORM_KEY = 'form-data';
const SERVER_URL = 'server-url'
async function openCacheForCurrentURL() {
    const formPath = self.location.href;
    const cacheName = 'cache-' + formPath;

    return await caches.open(cacheName);
}

self.addEventListener('install', event => {
    event.waitUntil(
        openCacheForCurrentURL().then(cache => {
            return cache.addAll([
            ]);
        }));
});

self.addEventListener('fetch', event => {
    if (event.request.url.includes(SUBMIT_URL)) {
        event.respondWith(
            fetch(event.request).catch(async (error) => {
                if (error instanceof TypeError) {
                    await saveFormDataToCache(event.request)
                }}));
    } else {
        event.respondWith(fetch(event.request));
    }
});

async function saveFormDataToCache(request) {
    const formData = await request.clone().formData();
    const cache = openCacheForCurrentURL();
    
    const response = new Response(JSON.stringify(formData));

    await cache.put(CACHE_FORM_KEY, response);
}

self.addEventListener('sync', event => {
    if (event.tag === 'form-sync') {
        event.waitUntil(sendFormData());
    }
});

async function sendFormData() {
    const formData = await getFormDataFromCache();
    if (formData) {
        try {
            const response = await fetch(SERVER_URL, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                // Data sent successfully, remove from cache
                await removeFormDataFromCache();
            }
        } catch (error) {
            console.error('Error sending form data:', error);
        }
    }
}

async function getFormDataFromCache() {
    const cache = await openCacheForCurrentURL();
    const cachedResponse = await cache.match(CACHE_FORM_KEY);
    if (cachedResponse) {
        return await cachedResponse.text();
    }
    return null;
}

async function removeFormDataFromCache() {
    const cache = await openCacheForCurrentURL();
    await cache.delete(CACHE_FORM_KEY);
}

self.addEventListener('push', event => {
    
});
