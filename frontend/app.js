(function () {
  const promptEl = document.getElementById('prompt');
  const runBtn = document.getElementById('run-agent');
  const statusEl = document.getElementById('status');
  const outputSection = document.getElementById('output-section');
  const responseEl = document.getElementById('response');
  const stepsSection = document.getElementById('steps-section');
  const stepsEl = document.getElementById('steps');

  function setStatus(msg) {
    statusEl.textContent = msg;
  }

  function getBaseUrl() {
    const base = document.querySelector('base');
    if (base && base.href) return base.href.replace(/\/$/, '');
    return '';
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
        responseEl.className = 'response';
        responseEl.textContent = data.response || '';
        outputSection.hidden = false;
        if (data.steps && data.steps.length) {
          stepsEl.innerHTML = '';
          data.steps.forEach(function (s, i) {
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
          stepsSection.hidden = false;
        }
        setStatus('Done.');
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

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }
})();
