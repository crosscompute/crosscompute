(async function () {
  const l = await refreshString('$element_id', 'value', '$data_uri');
  if (l) {
    l.disabled = false;
  }
})();
