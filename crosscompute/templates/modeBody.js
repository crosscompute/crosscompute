{% if mode_name == 'input' %}
document.getElementById('_run').onclick = async () => {
  const dataById = {};
  for (const x of document.getElementsByClassName('_input')) {
    const { view: viewName, variable: variableId } = x.dataset;
    dataById[variableId] = GET_DATA_BY_VIEW_NAME[viewName](x);
  }
  const uri = '{{ ROOT_URI }}{{ automation_definition.uri }}.json';
  const response = await fetch(uri, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(dataById)});
  const d = await response.json();
  location = '{{ ROOT_URI }}{{ automation_definition.uri }}/r/' + d['run_id'] + '/' + d['mode_code']{% if for_embed %} + '?_embed'{% endif %};
};
const GET_DATA_BY_VIEW_NAME = {};
{% else %}
const functionsByVariableId = {};
function registerElement(variableId, refreshElement) {
  if (functionsByVariableId[variableId] === undefined) {
    functionsByVariableId[variableId] = [];
  }
  functionsByVariableId[variableId].push(refreshElement);
}
function refreshVariable(variableId) {
  const fs = functionsByVariableId[variableId] || [];
  for (const f of fs) {
    f();
  }
}
{% if mode_name == 'log' %}
registerElement('return_code', function() {
  location = location.href.slice(0, -1) + 'o';
});
{% endif %}
{% endif %}
