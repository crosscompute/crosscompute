if ('serviceWorker' in navigator && 'SyncManager' in window) {
  navigator.serviceWorker.register('/assets/service-worker.js').then(async registration => {
    console.log('Service worker registered with scope:', registration.scope);
  }).catch(error => {
    console.error('Service worker registration failed:', error);
  });
  navigator.serviceWorker.ready.then(registration => {
    return registration.sync.register('sync-messages');
  });
}
