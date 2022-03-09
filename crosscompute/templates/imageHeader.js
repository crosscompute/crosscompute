function refreshImageOutput(elementId, dataUri) {
  const element = document.getElementById(elementId);
  element.src = dataUri + '?' + Date.now();
}
