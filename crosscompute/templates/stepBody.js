async function post(uri, d) {
  const r = await fetch(uri, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(d)});
  return await r.json();
}
function redirect(uri, d) {
  location = uri + '/r/' + d['run_id'] + '/' + d['step_code']{% if for_embed %} + '?_embed'{% endif %};
}
function getDataById() {
  const d = {};
  for (const x of document.getElementsByClassName('_input')) {
    const { view: viewName, variable: variableId } = x.dataset;
    d[variableId] = GET_DATA_BY_VIEW_NAME[viewName](x);
  }
  return d;
}
const GET_DATA_BY_VIEW_NAME = {};
{% if step_name == 'input' %}
document.getElementById('_run').onclick = async () => {
  const uri = '{{ ROOT_URI }}{{ automation_definition.uri }}';
  let d;
  try {
    d = await post(uri + '.json', getDataById());
  } catch (e) {
    console.error(e);
    return;
  }
  redirect(uri, d);
};
{% else %}
function registerElement(variableId, refreshElement) {
  if (callbacks[variableId] === undefined) {
    callbacks[variableId] = [];
  }
  callbacks[variableId].push(refreshElement);
}
{% if step_name == 'log' %}
registerElement('return_code', function() {
  location = location.href.slice(0, -1) + 'o';
});
{% endif %}
{% endif %}
