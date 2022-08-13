registerElement('$variable_id', async function () {
  try {
    await refreshString('$element_id', 'textContent', '$data_uri');
  } catch {
  }
});
