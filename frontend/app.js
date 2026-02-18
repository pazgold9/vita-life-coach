(function () {
  const promptEl = document.getElementById('prompt');
  const runBtn = document.getElementById('run-agent');
  const statusEl = document.getElementById('status');
  const outputSection = document.getElementById('output-section');
  const responseEl = document.getElementById('response');
  const stepsSection = document.getElementById('steps-section');
  const stepsEl = document.getElementById('steps');
  const historyEl = document.getElementById('history');

  function setStatus(msg) {
    statusEl.textContent = msg;
  }

  function getBaseUrl() {
    const base = document.querySelector('base');
    if (base && base.href) return base.href.replace(/\/$/, '');
    return '';
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function renderSteps(steps) {
    stepsEl.innerHTML = '';
    if (!steps || !steps.length) return;
    steps.forEach(function (s, i) {
      const div = document.createElement('div');
      div.className = 'step';
      const promptStr = typeof s.prompt === 'object' ? JSON.stringify(s.prompt, null, 2) : String(s.prompt);
      const responseStr = typeof s.response === 'object' ? JSON.stringify(s.response, null, 2) : String(s.response);
      div.innerHTML =
        '<div class="step-header">' + escapeHtml(s.module || 'Step ' + (i + 1)) + '</div>' +
        '<div class="step-details">' +
        '<details><summary>Prompt</summary><pre>' + escapeHtml(promptStr) + '</pre></details>' +
        '<details><summary>Response</summary><pre>' + escapeHtml(responseStr) + '</pre></details>' +
        '</div>';
      stepsEl.appendChild(div);
    });
  }

  function loadHistory() {
    const base = getBaseUrl();
    const url = (base ? base + '/api/history' : '/api/history').replace(/([^:]\/)\/+/g, '$1');
    fetch(url).then(function (r) { return r.json(); }).then(function (data) {
      if (!Array.isArray(data) || !data.length) return;
      historyEl.innerHTML = data.map(function (h) {
        const date = h.created_at ? new Date(h.created_at).toLocaleString() : '';
        return '<div class="history-item">' +
          '<div class="history-date">' + escapeHtml(date) + '</div>' +
          '<div class="history-prompt">' + escapeHtml(h.prompt || '') + '</div>' +
          '<div class="history-response">' + escapeHtml((h.response || '').slice(0, 200)) + (h.response && h.response.length > 200 ? '…' : '') + '</div>' +
          '</div>';
      }).join('');
    }).catch(function () {});
  }

  runBtn.addEventListener('click', async function () {
    const text = (promptEl.value || '').trim();
    if (!text) {
      setStatus('Please enter a prompt.');
      return;
    }
    runBtn.disabled = true;
    setStatus('Running agent…');
    outputSection.hidden = true;
    stepsSection.hidden = true;

    try {
      const base = getBaseUrl();
      const url = (base ? base + '/api/execute' : '/api/execute').replace(/([^:]\/)\/+/g, '$1');
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: text }),
      });
      const data = await res.json();

      if (data.status === 'ok') {
        promptEl.value = '';

        responseEl.className = 'response';
        responseEl.textContent = data.response || '';
        outputSection.hidden = false;

        if (data.steps && data.steps.length) {
          renderSteps(data.steps);
          stepsSection.hidden = false;
        }
        setStatus('Done (' + (data.steps ? data.steps.length : 0) + ' steps).');
        loadHistory();
      } else {
        const errMsg = data.error || 'Unknown error';
        setStatus('Error');
        responseEl.textContent = errMsg;
        responseEl.className = 'response response-error';
        outputSection.hidden = false;
      }
    } catch (err) {
      setStatus('Request failed: ' + err.message);
    } finally {
      runBtn.disabled = false;
    }
  });

  loadHistory();
})();
