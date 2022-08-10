async registerElement('$variable_id', function () {
  try {
    await refreshString('$element_id', 'textContent', '$data_uri');
  } catch {
  }
});
