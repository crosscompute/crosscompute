function showNext() {
  oldTemplateIndex = newTemplateIndex;
  let newElement, isThis = false;
  while (!isThis) {
    newElement = getTemplateElement(++newTemplateIndex);
    const x = newElement?.dataset.expression;
    if (x) {
      const lines = [];
      for (const [k, v] of Object.entries(getDataById())) {
        lines.push(`const ${k} = ${JSON.stringify(v.value)};`);
      }
      isThis = Function(lines.join('\n') + `return ${x};`)();
    } else {
      isThis = true;
    }
  }
  const oldElement = getTemplateElement(oldTemplateIndex);
  if (oldElement) {
    oldElement.classList.remove('_live');
  }
  if (newElement) {
    newElement.classList.add('_live');
  } else {
    runAutomation();
  }
}
async function runAutomation() {
  const uri = '{{ root_uri }}{{ automation_definition.uri }}';
  let d;
  try {
    d = await post(uri + '.json', getDataById());
  } catch (e) {
    console.error(e);
    return;
  }
  redirect(uri, d);
}
async function post(uri, d) {
  const r = await fetch(uri, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(d)});
  return await r.json();
}
function redirect(uri, d) {
  location = uri + '/b/' + d['batch_slug'] + '/' + d['step_code']{% if for_embed %} + '?_embed'{% endif %};
}
function getDataById() {
  const d = {};
  for (const x of document.getElementsByClassName('_input')) {
    const { view: viewName, variable: variableId } = x.dataset;
    d[variableId] = GET_DATA_BY_VIEW_NAME[viewName](x);
  }
  return d;
}
const getTemplateElement = i => document.getElementById('_t' + i), GET_DATA_BY_VIEW_NAME = {};
let oldTemplateIndex, newTemplateIndex = 0;
Array.from(document.getElementsByClassName('_continue')).forEach(function (l) {
  l.onclick = showNext;
});
{% if step_name != 'input' %}
function registerFunction(variableId, f) {
  register(functions, variableId, f);
}
const functions = {};
{% if step_name == 'log' %}
registerFunction('return_code', function() {
  location = location.href.slice(0, -1) + 'o';
});
{% endif %}
{% endif %}
