/**
 * ==============================================================================
 * MONITORING SYSTEM - INTERACTIVE AUTOMATED DEMO TOUR ENGINE
 * Architecture: Clean Inline SVG Icons + Spotlight Overlay + Typewriter Effect
 * ==============================================================================
 */

(function() {
  'use strict';

  // Crisp High-Resolution Inline SVG Icons (Never Corrupts to '?' or '??')
  const ICONS = {
    rocket: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.63 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 7.39a15.05 15.05 0 01-2.064-2.064"/></svg>',
    chart: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>',
    search: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>',
    switchView: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>',
    matrix: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>',
    document: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
    exportXls: '<svg class="tour-svg-icon" style="width:18px;height:18px;color:#059669;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>',
    
    // Feature Icons
    folder: '<svg class="tour-svg-icon" style="width:14px;height:14px;color:#2563eb;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>',
    git: '<svg class="tour-svg-icon" style="width:14px;height:14px;color:#4f46e5;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>',
    gapChart: '<svg class="tour-svg-icon" style="width:14px;height:14px;color:#059669;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"/></svg>',
    shield: '<svg class="tour-svg-icon" style="width:14px;height:14px;color:#7c3aed;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>',

    // Controls Icons
    close: '<svg style="width:16px;height:16px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"/></svg>',
    forward: '<svg style="width:13px;height:13px;margin-right:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 5l7 7-7 7M5 5l7 7-7 7"/></svg>',
    pause: '<svg style="width:13px;height:13px;margin-right:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M10 9v6m4-6v6"/></svg>',
    play: '<svg style="width:13px;height:13px;margin-right:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/></svg>',
    arrowLeft: '<svg style="width:13px;height:13px;margin-right:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M15 19l-7-7 7-7"/></svg>',
    arrowRight: '<svg style="width:13px;height:13px;margin-left:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5l7 7-7 7"/></svg>',
    check: '<svg style="width:14px;height:14px;margin-left:4px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>',
    target: '<svg style="width:16px;height:16px;margin-right:6px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" stroke-width="2"></circle><circle cx="12" cy="12" r="5" stroke-width="2"></circle><circle cx="12" cy="12" r="1.5" fill="currentColor"></circle></svg>'
  };

  // Tour Steps Configuration
  const TOUR_STEPS = [
    {
      stepNumber: 1,
      target: null, // Centered Modal
      icon: ICONS.rocket,
      badge: "Sistem Overview",
      title: "Selamat Datang di Monitoring System",
      subtitle: "Platform Kontrol & Audit Dokumen Rekayasa Sipil Terpadu",
      text: "Monitoring System adalah platform enterprise terintegrasi yang dirancang khusus untuk memonitor, menstandarisasi rekayasa, dan mengaudit kepatuhan 3.000+ dokumen teknis pada 150 proyek infrastruktur sipil strategis nasional (Jalan Tol, Jembatan Bentang Panjang, Pelabuhan, Bendungan, hingga Jalur LRT).",
      features: [
        { icon: ICONS.folder, title: "Single Source of Truth", desc: "Repositori terpusat 20 jenis dokumen teknis sipil." },
        { icon: ICONS.git, title: "Version Control Ketat", desc: "Pelacakan riwayat revisi Rev 0 Draft s/d Rev 6 As-Built." },
        { icon: ICONS.gapChart, title: "Real-Time Gap Analysis", desc: "Deteksi instan dokumen tertunda & progres fisik proyek." },
        { icon: ICONS.shield, title: "Kepatuhan & Audit Trail", desc: "Pencatatan permanen 2.500+ log aktivitas pengguna." }
      ]
    },
    {
      stepNumber: 2,
      target: ".iatf-stats-grid",
      icon: ICONS.chart,
      badge: "KPI & Statistik",
      title: "Panel Ringkasan Portofolio Proyek",
      subtitle: "Dashboard Eksekutif & Monitoring Status Real-Time",
      text: "Panel ini menyajikan ringkasan eksekutif tingkat tinggi seluruh portofolio proyek: memantau 150 Total Proyek, 45 Proyek Selesai (100% dokumen lengkap), 85 Proyek Sedang Berjalan (On Progress), serta deteksi dini 20 Proyek Tertunda (Hold & Canceled) untuk mitigasi risiko keterlambatan proyek."
    },
    {
      stepNumber: 3,
      target: 'input[placeholder*="Cari proyek"], .iatf-filter-grid',
      icon: ICONS.search,
      badge: "Navigasi Cepat",
      title: "Pencarian Instan & Filter Multi-Kriteria",
      subtitle: "Pencarian Berkecepatan Tinggi & Filter Dinamis",
      text: "Temukan proyek yang diinginkan dalam hitungan detik menggunakan pencarian cerdas (cukup tekan shortcut keyboard '/') berdasarkan I-Code, Nama Item, No Part, atau PIC Lapangan. Anda juga dapat memfilter proyek menurut Customer, Status Pengerjaan, dan Departemen Pelaksana."
    },
    {
      stepNumber: 4,
      target: ".iatf-segmented-control",
      icon: ICONS.switchView,
      badge: "Mode Tampilan",
      title: "Switcher Mode Tampilan: Tabel vs Matriks",
      subtitle: "Fleksibilitas Kerja Dua Dimensi",
      text: "Sistem menghadirkan dua sudut pandang navigasi yang fleksibel: Tampilan 'Tabel Standar' untuk operasional administratif dan manajemen detail per proyek, serta 'Matriks Dokumen Proyek' untuk visualisasi menyeluruh seluruh dokumen teknis lintas proyek dalam satu layar kerja."
    },
    {
      stepNumber: 5,
      target: ".iatf-matrix-wrapper, .iatf-matrix-table",
      icon: ICONS.matrix,
      actionBefore: function() {
        const matrixBtn = Array.from(document.querySelectorAll('.iatf-seg-btn')).find(b => b.textContent.includes('Matriks'));
        if (matrixBtn && !matrixBtn.classList.contains('active')) {
          matrixBtn.click();
        }
      },
      badge: "Audit Kelengkapan",
      title: "Matriks Kepatuhan 20 Jenis Dokumen Teknis",
      subtitle: "Audit Gap Analysis & Kepatuhan Standar Teknis Sipil",
      text: "Inilah keunggulan utama sistem: Matriks interaktif 20 kategori dokumen rekayasa sipil (DED, As-Built, BoQ, Soil Test, AMDAL, RKS, Uji Tarik Baja, hingga Sertifikat Laik Fungsi). Indikator hijau menandakan dokumen terverifikasi beserta jumlah revisinya, sedangkan strip abu-abu memperlihatkan gap dokumen yang belum terpenuhi."
    },
    {
      stepNumber: 6,
      target: "table tbody tr:first-child",
      icon: ICONS.document,
      actionBefore: function() {
        const tableBtn = Array.from(document.querySelectorAll('.iatf-seg-btn')).find(b => b.textContent.includes('Tabel'));
        if (tableBtn && !tableBtn.classList.contains('active')) {
          tableBtn.click();
        }
      },
      badge: "Version Control",
      title: "Multi-Stage Version Control & Akses Dokumen PDF",
      subtitle: "Pelacakan Riwayat Perubahan & Pratinjau Dokumen",
      text: "Setiap dokumen memiliki riwayat version control otomatis dari Rev 0 (Draft) hingga Rev 6 (As-Built). Tim teknis dan auditor dapat meninjau catatan revisi, riwayat batch unggahan, serta membuka pratinjau dokumen PDF secara instan langsung di peramban tanpa perlu mengunduh file secara manual."
    },
    {
      stepNumber: 7,
      target: ".iatf-export-btn",
      icon: ICONS.exportXls,
      badge: "Laporan & Kepatuhan",
      title: "Ekspor Laporan Excel & Audit Trail Compliance",
      subtitle: "Pelaporan Eksekutif & Kepatuhan Tata Kelola",
      text: "Hasilkan laporan audit kelengkapan matriks dalam format spreadsheet Excel (.xlsx) siap pakai hanya dengan satu klik. Seluruh aktivitas pembuatan proyek, unggahan dokumen, revisi, dan perubahan status tercatat secara permanen dalam sistem Audit Log untuk transparansi penuh dan kepatuhan standar industri."
    }
  ];

  // State Management
  let currentStepIdx = 0;
  let isTourActive = false;
  let isTyping = false;
  let isPaused = false;
  let typewriterTimer = null;
  let countdownTimer = null;
  let countdownProgressInterval = null;
  let remainingCountdownMs = 6000;
  const TOTAL_COUNTDOWN_MS = 6000;

  // DOM Elements
  let overlayEl = null;
  let spotlightEl = null;
  let calloutCardEl = null;
  let launcherBtnEl = null;

  function initTourDOM() {
    if (document.getElementById('tour-overlay-container')) return;

    overlayEl = document.createElement('div');
    overlayEl.id = 'tour-overlay-container';
    overlayEl.style.display = 'none';

    spotlightEl = document.createElement('div');
    spotlightEl.id = 'tour-spotlight-box';
    spotlightEl.className = 'hidden-spotlight';
    overlayEl.appendChild(spotlightEl);

    calloutCardEl = document.createElement('div');
    calloutCardEl.id = 'tour-callout-card';
    overlayEl.appendChild(calloutCardEl);

    document.body.appendChild(overlayEl);

    if (!document.getElementById('tour-launcher-btn')) {
      launcherBtnEl = document.createElement('button');
      launcherBtnEl.id = 'tour-launcher-btn';
      launcherBtnEl.type = 'button';
      launcherBtnEl.innerHTML = `
        <span class="tour-pulse-dot"></span>
        ${ICONS.target}
        <span>Panduan & Demo Tour</span>
      `;
      launcherBtnEl.title = 'Mulai Ulang Panduan Demo Interaktif';
      launcherBtnEl.onclick = function() {
        startTour(0);
      };
      document.body.appendChild(launcherBtnEl);
    }

    window.addEventListener('resize', handleWindowResizeOrScroll);
    window.addEventListener('scroll', handleWindowResizeOrScroll, true);
    window.addEventListener('keydown', handleKeyNavigation);
  }

  function handleKeyNavigation(e) {
    if (!isTourActive) return;
    if (e.key === 'Escape') {
      stopTour();
    } else if (e.key === 'ArrowRight') {
      nextStep();
    } else if (e.key === 'ArrowLeft') {
      prevStep();
    } else if (e.key === ' ') {
      e.preventDefault();
      togglePause();
    }
  }

  function handleWindowResizeOrScroll() {
    if (!isTourActive) return;
    const step = TOUR_STEPS[currentStepIdx];
    if (step && step.target) {
      positionSpotlightAndCallout(step.target);
    }
  }

  function startTour(stepIndex) {
    initTourDOM();
    isTourActive = true;
    overlayEl.style.display = 'block';
    currentStepIdx = stepIndex || 0;
    renderStep(currentStepIdx);
  }

  function stopTour() {
    isTourActive = false;
    clearAllTimers();
    if (overlayEl) {
      overlayEl.style.display = 'none';
    }
    if (spotlightEl) {
      spotlightEl.className = 'hidden-spotlight';
    }
  }

  function clearAllTimers() {
    if (typewriterTimer) clearInterval(typewriterTimer);
    if (countdownTimer) clearTimeout(countdownTimer);
    if (countdownProgressInterval) clearInterval(countdownProgressInterval);
    typewriterTimer = null;
    countdownTimer = null;
    countdownProgressInterval = null;
    isTyping = false;
  }

  function renderStep(idx) {
    clearAllTimers();
    isPaused = false;
    remainingCountdownMs = TOTAL_COUNTDOWN_MS;

    const step = TOUR_STEPS[idx];
    if (!step) {
      stopTour();
      return;
    }

    if (typeof step.actionBefore === 'function') {
      try {
        step.actionBefore();
      } catch (err) {
        console.warn('Action before step error:', err);
      }
    }

    setTimeout(() => {
      buildStepHTML(step);
      startTypewriter(step.text, () => {
        startCountdownTimer();
      });

      if (step.target) {
        positionSpotlightAndCallout(step.target);
      } else {
        spotlightEl.className = 'hidden-spotlight';
        calloutCardEl.className = 'tour-modal-mode';
        calloutCardEl.style.top = '50%';
        calloutCardEl.style.left = '50%';
      }
    }, 180);
  }

  function buildStepHTML(step) {
    const totalSteps = TOUR_STEPS.length;
    const isFirst = step.stepNumber === 1;
    const isLast = step.stepNumber === totalSteps;

    let featuresHTML = '';
    if (step.features && step.features.length) {
      featuresHTML = `
        <div class="tour-feature-grid">
          ${step.features.map(f => `
            <div class="tour-feature-card">
              <div class="tour-feature-card-title">
                <span class="tour-feature-icon-badge">${f.icon}</span>
                <span>${f.title}</span>
              </div>
              <div class="tour-feature-card-desc">${f.desc}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    calloutCardEl.innerHTML = `
      <div class="tour-card-header">
        <div style="display:flex;align-items:center;gap:10px;">
          <span class="tour-card-badge">${step.badge}</span>
          <span class="tour-card-steps-count">Langkah ${step.stepNumber} dari ${totalSteps}</span>
        </div>
        <button type="button" class="tour-card-close" id="tour-close-btn" title="Tutup Tour (Esc)">${ICONS.close}</button>
      </div>

      <div class="tour-card-body">
        <h3 class="tour-step-title">
          <span class="tour-title-icon">${step.icon}</span>
          <span>${step.title}</span>
        </h3>
        <div class="tour-step-subtitle">${step.subtitle}</div>
        <div class="tour-step-text-wrapper" id="tour-typewriter-container" title="Klik untuk menampilkan teks lengkap langsung">
          <span id="tour-text-target"></span><span class="tour-typing-cursor" id="tour-cursor"></span>
        </div>
        ${featuresHTML}

        <div class="tour-countdown-container" id="tour-countdown-box" style="display:none;">
          <div class="tour-countdown-bar-wrap">
            <div class="tour-countdown-bar-fill" id="tour-progress-bar"></div>
          </div>
          <div class="tour-countdown-label" id="tour-countdown-label">Lanjut otomatis dalam 6s...</div>
        </div>
      </div>

      <div class="tour-card-footer">
        <div class="tour-footer-left">
          <button type="button" class="tour-btn tour-btn-ghost" id="tour-skip-btn">Tutup</button>
          <button type="button" class="tour-btn tour-btn-ghost" id="tour-skip-type-btn" style="color:#2563eb;font-weight:700;">
            ${ICONS.forward}
            <span>Tampilkan Lengkap</span>
          </button>
        </div>
        <div class="tour-footer-right">
          <button type="button" class="tour-btn tour-btn-ghost" id="tour-pause-btn" style="display:none;" title="Jeda / Lanjutkan Auto-Play">
            ${ICONS.pause}
            <span>Jeda</span>
          </button>
          <button type="button" class="tour-btn tour-btn-secondary" id="tour-prev-btn" ${isFirst ? 'disabled' : ''}>
            ${ICONS.arrowLeft}
            <span>Kembali</span>
          </button>
          <button type="button" class="tour-btn tour-btn-primary" id="tour-next-btn">
            <span>${isLast ? 'Selesai' : 'Berikutnya'}</span>
            ${isLast ? ICONS.check : ICONS.arrowRight}
          </button>
        </div>
      </div>
    `;

    document.getElementById('tour-close-btn').onclick = stopTour;
    document.getElementById('tour-skip-btn').onclick = stopTour;
    document.getElementById('tour-prev-btn').onclick = prevStep;
    document.getElementById('tour-next-btn').onclick = nextStep;

    const skipTypeBtn = document.getElementById('tour-skip-type-btn');
    if (skipTypeBtn) {
      skipTypeBtn.onclick = function() {
        finishTypewriterImmediately(step.text);
      };
    }

    const typewriterBox = document.getElementById('tour-typewriter-container');
    if (typewriterBox) {
      typewriterBox.onclick = function() {
        finishTypewriterImmediately(step.text);
      };
    }

    const pauseBtn = document.getElementById('tour-pause-btn');
    if (pauseBtn) {
      pauseBtn.onclick = togglePause;
    }
  }

  function startTypewriter(fullText, onComplete) {
    const textTarget = document.getElementById('tour-text-target');
    const cursor = document.getElementById('tour-cursor');
    if (!textTarget) return;

    textTarget.textContent = '';
    if (cursor) cursor.style.display = 'inline-block';
    isTyping = true;

    let charIdx = 0;
    const speedMs = 18;

    typewriterTimer = setInterval(() => {
      if (charIdx < fullText.length) {
        textTarget.textContent += fullText.charAt(charIdx);
        charIdx++;
      } else {
        clearInterval(typewriterTimer);
        typewriterTimer = null;
        isTyping = false;
        if (cursor) cursor.style.display = 'none';
        hideSkipTypeButton();
        if (typeof onComplete === 'function') onComplete();
      }
    }, speedMs);
  }

  function finishTypewriterImmediately(fullText) {
    if (!isTyping) return;
    if (typewriterTimer) clearInterval(typewriterTimer);
    typewriterTimer = null;
    isTyping = false;

    const textTarget = document.getElementById('tour-text-target');
    const cursor = document.getElementById('tour-cursor');
    if (textTarget) textTarget.textContent = fullText;
    if (cursor) cursor.style.display = 'none';

    hideSkipTypeButton();
    startCountdownTimer();
  }

  function hideSkipTypeButton() {
    const btn = document.getElementById('tour-skip-type-btn');
    if (btn) btn.style.display = 'none';
    const pauseBtn = document.getElementById('tour-pause-btn');
    if (pauseBtn) pauseBtn.style.display = 'inline-flex';
  }

  function startCountdownTimer() {
    const countdownBox = document.getElementById('tour-countdown-box');
    const progressBar = document.getElementById('tour-progress-bar');
    const label = document.getElementById('tour-countdown-label');
    const pauseBtn = document.getElementById('tour-pause-btn');

    if (!countdownBox || !progressBar) return;
    countdownBox.style.display = 'flex';
    if (pauseBtn) pauseBtn.style.display = 'inline-flex';

    let elapsedMs = 0;
    const intervalMs = 100;

    countdownProgressInterval = setInterval(() => {
      if (isPaused) return;

      elapsedMs += intervalMs;
      const progressPercent = Math.min(100, (elapsedMs / TOTAL_COUNTDOWN_MS) * 100);
      progressBar.style.width = progressPercent + '%';

      const secLeft = Math.ceil((TOTAL_COUNTDOWN_MS - elapsedMs) / 1000);
      if (label) label.textContent = `Lanjut otomatis dalam ${Math.max(1, secLeft)}s...`;

      if (elapsedMs >= TOTAL_COUNTDOWN_MS) {
        clearInterval(countdownProgressInterval);
        countdownProgressInterval = null;
        nextStep();
      }
    }, intervalMs);
  }

  function togglePause() {
    isPaused = !isPaused;
    const pauseBtn = document.getElementById('tour-pause-btn');
    const label = document.getElementById('tour-countdown-label');
    if (pauseBtn) {
      pauseBtn.innerHTML = isPaused ? `${ICONS.play}<span>Lanjut</span>` : `${ICONS.pause}<span>Jeda</span>`;
      pauseBtn.title = isPaused ? 'Lanjutkan countdown' : 'Jeda countdown';
    }
    if (label && isPaused) {
      label.textContent = 'Countdown dijeda';
    }
  }

  function nextStep() {
    if (currentStepIdx < TOUR_STEPS.length - 1) {
      currentStepIdx++;
      renderStep(currentStepIdx);
    } else {
      stopTour();
      if (window.showToast) {
        window.showToast("Demo Tour Selesai! Klik tombol 'Panduan & Demo Tour' di pojok kanan bawah jika ingin memutar kembali.", "success");
      }
    }
  }

  function prevStep() {
    if (currentStepIdx > 0) {
      currentStepIdx--;
      renderStep(currentStepIdx);
    }
  }

  function positionSpotlightAndCallout(selector) {
    const targetEl = document.querySelector(selector);
    if (!targetEl) {
      spotlightEl.className = 'hidden-spotlight';
      calloutCardEl.className = 'tour-modal-mode';
      calloutCardEl.style.top = '50%';
      calloutCardEl.style.left = '50%';
      return;
    }

    calloutCardEl.className = '';
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });

    setTimeout(() => {
      const rect = targetEl.getBoundingClientRect();
      const pad = 12;

      const spotTop = Math.max(0, rect.top - pad);
      const spotLeft = Math.max(0, rect.left - pad);
      const spotWidth = Math.min(window.innerWidth - spotLeft, rect.width + (pad * 2));
      const spotHeight = Math.min(window.innerHeight - spotTop, rect.height + (pad * 2));

      spotlightEl.className = '';
      spotlightEl.style.top = spotTop + 'px';
      spotlightEl.style.left = spotLeft + 'px';
      spotlightEl.style.width = spotWidth + 'px';
      spotlightEl.style.height = spotHeight + 'px';

      const cardRect = calloutCardEl.getBoundingClientRect();
      const cardWidth = cardRect.width || 520;
      const cardHeight = cardRect.height || 340;

      let topPos = 0;
      let leftPos = 0;

      const spaceBelow = window.innerHeight - (rect.bottom + pad + 15);
      const spaceAbove = rect.top - pad - 15;

      if (spaceBelow >= cardHeight || spaceBelow >= spaceAbove) {
        topPos = rect.bottom + pad + 14;
      } else {
        topPos = Math.max(16, rect.top - pad - cardHeight - 14);
      }

      topPos = Math.max(16, Math.min(topPos, window.innerHeight - cardHeight - 16));

      leftPos = rect.left + (rect.width / 2) - (cardWidth / 2);
      leftPos = Math.max(16, Math.min(leftPos, window.innerWidth - cardWidth - 16));

      calloutCardEl.style.top = topPos + 'px';
      calloutCardEl.style.left = leftPos + 'px';
      calloutCardEl.style.transform = 'none';
    }, 220);
  }

  function setupAutoTrigger() {
    let checkAttempts = 0;
    const maxAttempts = 50;

    const checkInterval = setInterval(() => {
      checkAttempts++;
      const hasDashboard = document.querySelector('.iatf-stats-grid') || 
                           document.querySelector('h1') || 
                           document.querySelector('.iatf-toolbar-card');

      if (hasDashboard) {
        clearInterval(checkInterval);
        setTimeout(() => {
          console.log('[Tour] Starting automated demo tour on page entry...');
          startTour(0);
        }, 1100);
      } else if (checkAttempts >= maxAttempts) {
        clearInterval(checkInterval);
        startTour(0);
      }
    }, 200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initTourDOM();
      setupAutoTrigger();
    });
  } else {
    initTourDOM();
    setupAutoTrigger();
  }

  window.IATFTour = {
    start: startTour,
    stop: stopTour,
    next: nextStep,
    prev: prevStep
  };

})();
