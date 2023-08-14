if ('serviceWorker' in navigator && 'SyncManager' in window) {
  navigator.serviceWorker.register(`${window.location.origin}/a/serviceworker.js`)
        .then(async registration => {
          console.log('Service Worker registered with scope:', registration.scope);
        })
        .catch(error => {
          console.error('Service Worker registration failed:', error);
        });

//  navigator.serviceWorker.ready.then(registration => {
//    return registration.sync.register('data-sync');
//  });
}