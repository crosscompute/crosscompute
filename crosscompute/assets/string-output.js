registerFunction('$variable_id', async function({v}) {
  await refreshString('$element_id', 'textContent', '$data_uri', v);
});
