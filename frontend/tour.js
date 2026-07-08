'use strict';
/* Guided product tour for CAMP 2.0.
   Drives the real app — loads sample COs, runs the mapping, opens a cell's
   explanation — so a first-time viewer feels personally walked through it.
   Depends on globals defined in app.js (runMapping, closeDrawer). */
(function () {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  const SAMPLE = [
    'Apply data structures and algorithms to solve computational problems efficiently.',
    'Analyze the time complexity and space complexity of algorithms.',
    'Design and develop a software system using modern engineering tools.',
    'Communicate technical results effectively through reports and presentations.',
  ];

  // ---- actions the tour performs on the real app -------------------------
  function fillSample() {
    const code = document.getElementById('courseCode');
    const title = document.getElementById('courseTitle');
    const cos = document.getElementById('cosInput');
    if (code && !code.value) code.value = '21CS42';
    if (title && !title.value) title.value = 'Data Structures & Algorithms';
    if (cos) cos.value = SAMPLE.join('\n');
  }
  async function runMap() {
    if (typeof window.runMapping === 'function') await window.runMapping();
    else document.getElementById('mapBtn')?.click();
    await wait(150);
  }
  function openStrongCell() {
    const cell = document.querySelector('#matrix .cell.lvl-3')
      || document.querySelector('#matrix .cell.lvl-2');
    if (cell) cell.click();
  }
  function closeDrawerSafe() {
    if (typeof window.closeDrawer === 'function') window.closeDrawer();
    else {
      document.getElementById('drawer')?.setAttribute('hidden', '');
      document.getElementById('scrim')?.setAttribute('hidden', '');
    }
  }

  // ---- steps -------------------------------------------------------------
  const STEPS = [
    { center: true, title: 'Welcome to CAMP 2.0 👋',
      body: "In about 30 seconds I'll show you how CAMP turns Course Outcomes into an audit-ready CO–PO matrix. Click <b>Next</b> to begin." },
    { target: '#cosInput', title: '1 · Enter Course Outcomes',
      body: "Type your outcomes here, one per line. I've loaded a few real examples for you.",
      before: () => fillSample() },
    { target: '#mapBtn', title: '2 · Run the engine',
      body: 'Press <b>Map to POs</b> and the deterministic CSAS engine scores every CO against all 12 Program Outcomes — no AI black box, and the same result every time.' },
    { target: '#matrixWrap', title: '3 · Your CO–PO matrix',
      body: 'Each cell is a strength from <b>0 to 3</b>, colour-coded. Rows are your COs; columns are PO1–PO12.',
      before: async () => { await runMap(); } },
    { target: '#drawer', pad: 0, title: "4 · See the 'why'",
      body: 'Click any cell for the full breakdown — semantic score, lexical affinity, Bloom gate, and a plain-English reason. This is what makes the matrix defensible in an audit.',
      before: async () => { openStrongCell(); await wait(260); } },
    { target: '.bloom-badge', title: '5 · Bloom-aware',
      body: 'Every CO’s Bloom level (Remember → Create) shapes how strongly it can map to higher-order outcomes.',
      before: () => closeDrawerSafe() },
    { target: '#exportBtn', title: '6 · Export the report',
      body: 'Download an accreditation-ready <b>DOCX</b> — the matrix plus a justification appendix for every cell.' },
    { target: '.saved-bar', title: '7 · Save & reload',
      body: 'Save a course and pull it back anytime from this dropdown.' },
    { center: true, title: "That's the whole flow 🎉",
      body: "Now it's yours to explore. Replay this tour anytime with the <b>✨ Tour</b> button up top." },
  ];

  // ---- engine ------------------------------------------------------------
  let els = null, current = 0, active = false;

  function build() {
    const blocker = document.createElement('div'); blocker.id = 'tourBlocker';
    const spot = document.createElement('div'); spot.id = 'tourSpotlight';
    const pop = document.createElement('div'); pop.id = 'tourPop';
    pop.innerHTML =
      '<div class="tour-progress"><span class="tour-dot"></span><span class="tour-count"></span></div>' +
      '<h3 class="tour-title"></h3><p class="tour-body"></p>' +
      '<div class="tour-controls"><button class="tour-skip">Skip tour</button>' +
      '<div class="tour-nav"><button class="tour-back">Back</button>' +
      '<button class="tour-next">Next</button></div></div>';
    document.body.append(blocker, spot, pop);
    els = {
      blocker, spot, pop,
      count: pop.querySelector('.tour-count'), title: pop.querySelector('.tour-title'),
      body: pop.querySelector('.tour-body'), back: pop.querySelector('.tour-back'),
      next: pop.querySelector('.tour-next'), skip: pop.querySelector('.tour-skip'),
    };
    els.next.addEventListener('click', next);
    els.back.addEventListener('click', back);
    els.skip.addEventListener('click', end);
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', reposition);
  }

  function positionSpot(rect, pad) {
    if (!rect) { els.spot.classList.add('spot-none'); return; }
    els.spot.classList.remove('spot-none');
    els.spot.style.left = (rect.left - pad) + 'px';
    els.spot.style.top = (rect.top - pad) + 'px';
    els.spot.style.width = (rect.width + pad * 2) + 'px';
    els.spot.style.height = (rect.height + pad * 2) + 'px';
  }

  function positionPop(rect) {
    const pop = els.pop, gap = 14, m = 12, vw = innerWidth, vh = innerHeight;
    pop.style.visibility = 'hidden';
    const pw = pop.offsetWidth, ph = pop.offsetHeight;
    let left, top;
    if (!rect) { left = (vw - pw) / 2; top = (vh - ph) / 2; }
    else {
      const s = { below: vh - rect.bottom, above: rect.top, right: vw - rect.right, left: rect.left };
      const pos = s.below >= ph + gap ? 'below' : s.above >= ph + gap ? 'above'
        : s.right >= pw + gap ? 'right' : s.left >= pw + gap ? 'left' : 'below';
      if (pos === 'below') { top = rect.bottom + gap; left = rect.left; }
      else if (pos === 'above') { top = rect.top - ph - gap; left = rect.left; }
      else if (pos === 'right') { left = rect.right + gap; top = rect.top; }
      else { left = rect.left - pw - gap; top = rect.top; }
      left = Math.max(m, Math.min(left, vw - pw - m));
      top = Math.max(m, Math.min(top, vh - ph - m));
    }
    pop.style.left = left + 'px'; pop.style.top = top + 'px';
    pop.style.visibility = 'visible';
  }

  let lastRect = null;
  function reposition() {
    const step = STEPS[current];
    const t = step && step.target ? document.querySelector(step.target) : null;
    lastRect = t ? t.getBoundingClientRect() : null;
    positionSpot(lastRect, step ? (step.pad ?? 8) : 8);
    positionPop(lastRect);
  }

  async function showStep(i) {
    const step = STEPS[i]; current = i;
    if (step.before) { try { await step.before(); } catch (e) { /* keep going */ } }

    let target = step.target ? document.querySelector(step.target) : null;
    if (step.target) {
      // treat as hidden if missing, [hidden], or zero-size — but NOT via offsetParent
      // (fixed-position elements like the drawer always report offsetParent === null)
      const r = target && target.getBoundingClientRect();
      const invisible = !target || target.hasAttribute('hidden') || (r.width === 0 && r.height === 0);
      if (invisible) return next();
    }
    if (target) { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); await wait(320); }

    lastRect = target ? target.getBoundingClientRect() : null;
    els.count.textContent = 'Step ' + (i + 1) + ' of ' + STEPS.length;
    els.title.textContent = step.title;
    els.body.innerHTML = step.body;
    els.back.style.visibility = i === 0 ? 'hidden' : 'visible';
    els.next.textContent = i === STEPS.length - 1 ? 'Finish' : 'Next';
    positionSpot(lastRect, step.pad ?? 8);
    positionPop(lastRect);
  }

  function next() { if (current < STEPS.length - 1) showStep(current + 1); else end(); }
  function back() { if (current > 0) showStep(current - 1); }
  function onKey(e) {
    if (!active) return;
    if (e.key === 'Escape') end();
    else if (e.key === 'ArrowRight') next();
    else if (e.key === 'ArrowLeft') back();
  }

  function end() {
    active = false;
    window.removeEventListener('keydown', onKey);
    window.removeEventListener('resize', reposition);
    [els?.blocker, els?.spot, els?.pop].forEach((n) => n && n.remove());
    els = null;
    localStorage.setItem('camp-tour-done', '1');
    // clean ?tour=1 so a refresh doesn't re-trigger
    if (new URLSearchParams(location.search).get('tour')) {
      history.replaceState(null, '', location.pathname);
    }
  }

  function start() {
    if (active) return;
    active = true; current = 0;
    build();
    showStep(0);
  }
  window.startCampTour = start;

  function maybeAutoStart() {
    const forced = new URLSearchParams(location.search).get('tour') === '1';
    if (forced || !localStorage.getItem('camp-tour-done')) setTimeout(start, 600);
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('tourBtn')?.addEventListener('click', start);
  });
  window.addEventListener('load', maybeAutoStart);
})();
