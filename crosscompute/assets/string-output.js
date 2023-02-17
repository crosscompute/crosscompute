registerFunction('$variable_id', async function() {
  await refreshString('$element_id', 'textContent', '$data_uri');
});
