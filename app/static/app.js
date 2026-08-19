/* eslint-disable */
'use strict';

const landing = document.querySelector('.landing');
const resultPage = document.querySelector('.result-page');
if (landing)    initLanding();
if (resultPage) initResult();

// ───────────────────────────── LANDING ─────────────────────────────

function initLanding() {
  const $schemaGrid = document.getElementById('schema-grid');
  const $customBuilder = document.getElementById('custom-builder');
  const $customFields = document.getElementById('custom-fields');
  const $customFieldsJson = document.getElementById('custom-fields-json');
  const $schemaKey = document.getElementById('schema-key');
  const $fileInput = document.getElementById('file-input');
  const $dropTitle = document.getElementById('drop-title');
  const $form = document.getElementById('upload-form');
  const $submitBtn = document.getElementById('submit-btn');
  const $addField = document.getElementById('add-field');

  // ── Schema picker ──
  function onSchemaChange() {
    const checked = $schemaGrid.querySelector('input[name="schema"]:checked');
    if (!checked) return;
    const value = checked.value;
    $schemaKey.value = value;
    if (value === 'custom') {
      $customBuilder.hidden = false;
      if ($customFields.children.length === 0) addCustomField();
    } else {
      $customBuilder.hidden = true;
    }
  }
  $schemaGrid.addEventListener('change', onSchemaChange);
  onSchemaChange();

  // ── Custom field rows ──
  function addCustomField() {
    const row = document.createElement('div');
    row.className = 'custom-field-row';
    row.innerHTML = `
      <input type="text" class="cf-name" placeholder="field_name" />
      <select class="cf-type">
        <option value="string">string</option>
        <option value="number">number</option>
        <option value="integer">integer</option>
        <option value="boolean">boolean</option>
        <option value="date">date</option>
        <option value="list-string">list of strings</option>
      </select>
      <input type="text" class="cf-desc" placeholder="what to look for…" />
      <button type="button" class="custom-field-remove" title="Remove field">×</button>
    `;
    row.querySelector('.custom-field-remove').addEventListener('click', () => row.remove());
    $customFields.appendChild(row);
  }
  $addField.addEventListener('click', addCustomField);

  // ── File picker UX ──
  $fileInput.addEventListener('change', () => {
    const file = $fileInput.files?.[0];
    if (file) $dropTitle.textContent = file.name;
  });

  // ── Submit ──
  $form.addEventListener('submit', (e) => {
    const file = $fileInput.files?.[0];
    if (!file) {
      e.preventDefault();
      return;
    }

    if ($schemaKey.value === 'custom') {
      const rows = $customFields.querySelectorAll('.custom-field-row');
      const fields = [];
      rows.forEach((r) => {
        const name = r.querySelector('.cf-name').value.trim();
        const type = r.querySelector('.cf-type').value;
        const desc = r.querySelector('.cf-desc').value.trim();
        if (name) fields.push({ name, type, description: desc });
      });
      if (fields.length === 0) {
        alert('Add at least one custom field.');
        e.preventDefault();
        return;
      }
      $customFieldsJson.value = JSON.stringify(fields);
    }

    $submitBtn.disabled = true;
    $submitBtn.textContent = 'Extracting… (10-30s)';
  });
}

// ───────────────────────────── RESULT ─────────────────────────────

function initResult() {
  const extractionId = resultPage.dataset.extractionId;
  const $tree = document.getElementById('data-tree');
  const $saveBtn = document.getElementById('save-btn');
  const $deleteBtn = document.getElementById('delete-btn');
  const raw = document.getElementById('extracted-data').textContent;

  let data;
  try {
    data = JSON.parse(raw || '{}');
  } catch {
    data = {};
  }

  let dirty = false;
  function markDirty() {
    dirty = true;
    $saveBtn.disabled = false;
  }

  function setValue(path, value) {
    const keys = path.split('.');
    let cursor = data;
    for (let i = 0; i < keys.length - 1; i++) {
      const k = keys[i];
      if (cursor[k] == null) cursor[k] = {};
      cursor = cursor[k];
    }
    cursor[keys[keys.length - 1]] = value;
  }

  // ── Render ──
  function render() {
    $tree.innerHTML = '';
    $tree.appendChild(renderObject('', data));
  }

  function renderObject(prefix, obj) {
    const wrap = document.createElement('div');
    wrap.className = 'dt-block';
    if (obj == null || typeof obj !== 'object' || Array.isArray(obj)) {
      // Shouldn't happen at top level, but be defensive
      wrap.textContent = String(obj);
      return wrap;
    }

    for (const [key, value] of Object.entries(obj)) {
      const path = prefix ? `${prefix}.${key}` : key;

      if (Array.isArray(value)) {
        // Array section
        const section = document.createElement('div');
        section.className = 'dt-block';
        const label = document.createElement('div');
        label.className = 'dt-key';
        label.textContent = `${prettify(key)} (${value.length})`;
        section.appendChild(label);

        if (value.every((v) => typeof v !== 'object' || v == null)) {
          // Scalar list — render as chips
          const list = document.createElement('div');
          list.className = 'dt-scalar-list';
          value.forEach((v) => {
            const chip = document.createElement('span');
            chip.className = 'dt-chip';
            chip.textContent = v == null ? '—' : String(v);
            list.appendChild(chip);
          });
          section.appendChild(list);
        } else {
          const list = document.createElement('div');
          list.className = 'dt-list';
          value.forEach((item, idx) => {
            const card = document.createElement('div');
            card.className = 'dt-list-item';
            const lbl = document.createElement('div');
            lbl.className = 'dt-index';
            lbl.textContent = `#${idx + 1}`;
            card.appendChild(lbl);
            if (item != null && typeof item === 'object') {
              card.appendChild(renderObject(`${path}.${idx}`, item));
            } else {
              const v = document.createElement('div');
              v.className = 'dt-value';
              v.textContent = item == null ? '—' : String(item);
              card.appendChild(v);
            }
            list.appendChild(card);
          });
          section.appendChild(list);
        }
        wrap.appendChild(section);
      } else if (value != null && typeof value === 'object') {
        // Nested object — render label + sub-tree
        const section = document.createElement('div');
        section.className = 'dt-block';
        const label = document.createElement('div');
        label.className = 'dt-key';
        label.textContent = prettify(key);
        section.appendChild(label);
        section.appendChild(renderObject(path, value));
        wrap.appendChild(section);
      } else {
        // Scalar — editable row
        const row = document.createElement('div');
        row.className = 'dt-row';
        const lbl = document.createElement('div');
        lbl.className = 'dt-label';
        lbl.textContent = prettify(key);
        row.appendChild(lbl);

        const vWrap = document.createElement('div');
        vWrap.className = 'dt-value' + (value == null ? ' null' : '');

        const useTextarea = typeof value === 'string' && value.length > 80;
        const input = document.createElement(useTextarea ? 'textarea' : 'input');
        if (!useTextarea) input.type = inferInputType(value);
        if (useTextarea) {
          input.rows = Math.min(6, Math.ceil(String(value).length / 80) || 1);
        }
        input.value = value == null ? '' : String(value);
        input.placeholder = value == null ? '(null)' : '';
        input.addEventListener('input', () => {
          markDirty();
          input.classList.add('dirty');
          const raw = input.value;
          const t = inputCoerce(raw, value);
          setValue(path, t);
          vWrap.classList.toggle('null', t == null && raw === '');
        });
        vWrap.appendChild(input);
        row.appendChild(vWrap);
        wrap.appendChild(row);
      }
    }
    return wrap;
  }

  function prettify(key) {
    return String(key).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function inferInputType(value) {
    if (typeof value === 'number') return 'number';
    if (typeof value === 'boolean') return 'text';
    if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) return 'date';
    return 'text';
  }

  function inputCoerce(raw, original) {
    if (raw === '' || raw === null) return null;
    // Preserve original type when possible
    if (typeof original === 'number') {
      const n = parseFloat(raw);
      return Number.isFinite(n) ? n : raw;
    }
    if (typeof original === 'boolean') {
      const lower = raw.trim().toLowerCase();
      if (['true', '1', 'yes'].includes(lower)) return true;
      if (['false', '0', 'no'].includes(lower)) return false;
    }
    return raw;
  }

  render();

  // ── Save ──
  $saveBtn.addEventListener('click', async () => {
    if (!dirty) return;
    $saveBtn.disabled = true;
    $saveBtn.textContent = 'Saving…';
    try {
      const r = await fetch(`/result/${extractionId}/save`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ data }),
      });
      if (!r.ok) throw new Error(await r.text().catch(() => 'Save failed'));
      $saveBtn.textContent = '✓ Saved';
      dirty = false;
      setTimeout(() => {
        $saveBtn.textContent = 'Save edits';
        $saveBtn.disabled = true;
      }, 1500);
      // Clear dirty styling
      document.querySelectorAll('.dt-value input.dirty, .dt-value textarea.dirty').forEach((el) => {
        el.classList.remove('dirty');
      });
    } catch (err) {
      alert('Failed to save: ' + (err.message || err));
      $saveBtn.textContent = 'Save edits';
      $saveBtn.disabled = false;
    }
  });

  // ── Delete ──
  $deleteBtn.addEventListener('click', async () => {
    if (!confirm('Delete this extraction permanently?')) return;
    const r = await fetch(`/result/${extractionId}`, { method: 'DELETE' });
    if (r.ok) window.location.href = '/';
    else alert('Delete failed');
  });
}
