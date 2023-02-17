registerFunction('$variable_id', async function() {
  await refreshJson('$variable_id', '$data_uri');
});
