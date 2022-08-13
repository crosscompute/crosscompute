async function refreshFrame(elementId, dataUri) {
  let response = await fetch(dataUri);
  let { status } = response;
  if (status != 200) {
    throw { status };
  }
  const frameUri = await response.text();
  const element = document.getElementById(elementId);
  element.src = frameUri;
}
