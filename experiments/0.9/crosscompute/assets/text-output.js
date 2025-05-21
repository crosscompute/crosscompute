registerFunction('{{ variable_id }}', async function({v}) {
  await refreshText('{{ element_id }}', '{{ data_uri }}', v);
});
{% if is_big_data %}
refreshVariable('{{ variable_id }}');
{% endif %}
