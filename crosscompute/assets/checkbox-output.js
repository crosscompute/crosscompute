registerFunction('$variable_id', async function({v, c}) {
  await refreshCheckbox('$element_id', '$data_uri', v, c);
});
