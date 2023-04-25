{% if template_count == 1 %}
document.querySelectorAll('._continue').forEach(function (l) {
  if (!l.onclick) {
    l.onclick = runAutomation;
  }
});
{% else %}
async function showNext() {
  let newElement, isThis = false;
  if (newTemplateIndex >= 0) {
    templateIndices.push(newTemplateIndex);
  }
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
  if (newElement) {
    hideAndShow(getTemplateElement(templateIndices[templateIndices.length - 1]), newElement);
    newElement.querySelectorAll('._input').forEach(_ => show(_));
  } else if (newTemplateIndex > 0) {
    runAutomation();
  }
}
async function showPrevious() {
  const oldTemplateIndex = newTemplateIndex;
  newTemplateIndex = templateIndices.pop();
  const newElement = getTemplateElement(newTemplateIndex);
  if (newElement) {
    const oldElement = getTemplateElement(oldTemplateIndex);
    hideAndShow(oldElement, newElement);
    oldElement.querySelectorAll('._input').forEach(_ => hide(_));
  }
}
async function hideAndShow(oldElement, newElement) {
  if (oldElement) {
    hide(oldElement);
  }
  show(newElement);
  const backButton = newElement.querySelector('._back');
  if (backButton) {
    backButton.style.visibility = templateIndices.length == 0 ? 'hidden' : 'visible';
  }
}
async function hide(l) {
  l.classList.remove('_live');
}
async function show(l) {
  l.classList.add('_live');
}
const getTemplateElement = i => document.getElementById('_t' + i), templateIndices = [];
let newTemplateIndex = -1;
document.querySelectorAll('._back').forEach(function (l) {
  if (!l.onclick) {
    l.onclick = showPrevious;
  }
});
document.querySelectorAll('._continue').forEach(function (l) {
  if (!l.onclick) {
    l.onclick = showNext;
  }
});
showNext();
{% endif %}
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
  for (const x of document.getElementsByClassName('{{ "_input" if template_count == 1 else "_input _live" }}')) {
    const { view: viewName, variable: variableId } = x.dataset;
    d[variableId] = GET_DATA_BY_VIEW_NAME[viewName](x);
  }
  return d;
}
const GET_DATA_BY_VIEW_NAME = {};
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
