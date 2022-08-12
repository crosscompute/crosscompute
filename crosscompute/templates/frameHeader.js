async function refreshFrame(elementId, dataUri) {
  const response = await fetch(dataUri);
  const { status } = response;
  if (status != 200) {
    throw { status };
  }
  let uri = await response.text();
  const element = document.getElementById(elementId);
  element.src = uri;
}
