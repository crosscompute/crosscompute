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
  window.location = '{{ ROOT_URI }}{{ automation_definition.uri }}/r/' + d['id'] + '/o';
};
const GET_DATA_BY_VIEW_NAME = {};
{% elif mode_name == 'output' %}
const functionsByVariableId = {};
function registerElement(variableId, refreshElement) {
  if (functionsByVariableId[variableId] === undefined) {
    functionsByVariableId[variableId] = [];
  }
  functionsByVariableId[variableId].push(refreshElement);
}
function refreshVariable(variableId) {
  for (const f of functionsByVariableId[variableId]) {
    f();
  }
}
{% endif %}
