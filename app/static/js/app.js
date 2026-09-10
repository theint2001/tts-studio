// TTS Studio - Pure British English Speech Synthesis
(function () {
  'use strict';

  // British English Voice Catalog
  const VOICES = [
    { id: 'en-GB-SoniaNeural', name: 'Sonia', gender: 'Female', desc: 'Warm, natural, clear' },
    { id: 'en-GB-RyanNeural', name: 'Ryan', gender: 'Male', desc: 'Clear, engaging' },
    { id: 'en-GB-LibbyNeural', name: 'Libby', gender: 'Female', desc: 'Bright, friendly' },
    { id: 'en-GB-ThomasNeural', name: 'Thomas', gender: 'Male', desc: 'Deep, authoritative' }
  ];

  // State
  let selectedVoiceId = 'en-GB-SoniaNeural';
  let activeAudioUrl = null;
  let activeAudioFilename = null;
  let isGeneratingSpeech = false;

  // DOM Elements - Script & Voice
  const narrationText = document.getElementById('narration-text');
  const btnClearText = document.getElementById('btn-clear-text');
  const statChars = document.getElementById('stat-chars');
  const statWords = document.getElementById('stat-words');
  const statDuration = document.getElementById('stat-duration');
  const audioTotalBadge = document.getElementById('audio-total-badge');

  const voiceCards = document.querySelectorAll('.voice-card');
  const rateSlider = document.getElementById('rate-slider');
  const pitchSlider = document.getElementById('pitch-slider');
  const rateDisplay = document.getElementById('rate-display');
  const pitchDisplay = document.getElementById('pitch-display');
  const btnSynthesize = document.getElementById('btn-synthesize');
  const btnSynthesizeText = document.getElementById('btn-synthesize-text');

  // DOM Elements - Audio Preview
  const mainAudio = document.getElementById('main-audio');
  const btnPlayPause = document.getElementById('btn-play-pause');
  const iconPlaySvg = document.getElementById('icon-play-svg');
  const iconPauseSvg = document.getElementById('icon-pause-svg');
  const timeDisplayCurrent = document.getElementById('time-display-current');
  const timeDisplayTotal = document.getElementById('time-display-total');
  const volumeSlider = document.getElementById('volume-slider');
  const btnDownloadMp3 = document.getElementById('btn-download-mp3');
  const waveformVisualizer = document.getElementById('waveform-visualizer');

  // Error Banner
  const ttsErrorBanner = document.getElementById('tts-error-banner');
  const ttsErrorMessage = document.getElementById('tts-error-message');
  const btnDismissTtsError = document.getElementById('btn-dismiss-tts-error');

  // Toast Notification
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const borderCls = type === 'error' ? 'border-rose-300' :
                      type === 'success' ? 'border-emerald-300' : 'border-blue-300';
    const textCls = type === 'error' ? 'text-rose-700' :
                    type === 'success' ? 'text-emerald-700' : 'text-blue-700';

    toast.className = `p-3 rounded-xl bg-white ${borderCls} border shadow-lg flex items-center justify-between gap-3 text-xs font-medium ${textCls} pointer-events-auto transition-all duration-300 transform translate-y-2 opacity-0`;
    toast.innerHTML = `
      <div class="flex items-center gap-2">
        <span class="w-2 h-2 rounded-full ${type === 'error' ? 'bg-rose-500' : type === 'success' ? 'bg-emerald-500' : 'bg-blue-500'} shrink-0"></span>
        <span>${message}</span>
      </div>
      <button class="text-slate-400 hover:text-slate-600 cursor-pointer p-0.5" onclick="this.parentElement.remove()">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    });

    setTimeout(() => {
      toast.classList.add('opacity-0', 'translate-y-1');
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function showTtsError(msg) {
    if (ttsErrorMessage) ttsErrorMessage.textContent = msg;
    if (ttsErrorBanner) {
      ttsErrorBanner.classList.remove('hidden');
      ttsErrorBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    showToast(msg, 'error');
  }

  function hideTtsError() {
    if (ttsErrorBanner) ttsErrorBanner.classList.add('hidden');
  }

  if (btnDismissTtsError) {
    btnDismissTtsError.addEventListener('click', hideTtsError);
  }

  // 1. Script Stats Calculator
  function updateScriptStats() {
    const text = narrationText.value.trim();
    const chars = text.length;
    const words = text ? text.split(/\s+/).length : 0;
    // Estimate: ~150 words per minute for natural speech
    const durationSeconds = Math.max(1, Math.round((words / 150) * 60));

    statChars.textContent = chars.toString();
    statWords.textContent = words.toString();
    statDuration.textContent = formatTime(durationSeconds);
  }

  narrationText.addEventListener('input', updateScriptStats);

  btnClearText.addEventListener('click', () => {
    narrationText.value = '';
    updateScriptStats();
    hideTtsError();
    narrationText.focus();
  });

  // 2. Voice Selection Card Click
  voiceCards.forEach(card => {
    card.addEventListener('click', () => {
      voiceCards.forEach(c => {
        c.classList.remove('border-blue-600', 'bg-blue-50/30', 'border-2');
        c.classList.add('border-slate-200', 'bg-white', 'border');
        const ind = c.querySelector('.radio-indicator');
        if (ind) {
          ind.className = 'radio-indicator absolute top-2 right-2 w-3.5 h-3.5 rounded-full border-2 border-slate-300 bg-white';
          ind.innerHTML = '';
        }
      });

      card.classList.remove('border-slate-200', 'bg-white', 'border');
      card.classList.add('border-blue-600', 'bg-blue-50/30', 'border-2');
      const activeRadio = card.querySelector('.radio-indicator');
      if (activeRadio) {
        activeRadio.className = 'radio-indicator absolute top-2 right-2 w-3.5 h-3.5 rounded-full border-2 border-blue-600 bg-blue-600 flex items-center justify-center';
        activeRadio.innerHTML = '<div class="w-1.5 h-1.5 rounded-full bg-white"></div>';
      }

      selectedVoiceId = card.dataset.voice;
      const voiceObj = VOICES.find(v => v.id === selectedVoiceId);
      if (voiceObj) {
        showToast(`Selected voice: ${voiceObj.name} (${voiceObj.gender})`, 'info');
      }
    });
  });

  // 3. Sliders Tuning
  rateSlider.addEventListener('input', () => {
    const val = parseInt(rateSlider.value);
    const multiplier = (1 + val / 100).toFixed(1);
    rateDisplay.textContent = `${multiplier}x`;
  });

  pitchSlider.addEventListener('input', () => {
    const val = parseInt(pitchSlider.value);
    const sign = val > 0 ? '+' : '';
    pitchDisplay.textContent = val === 0 ? '0 Hz' : `${sign}${val} Hz`;
  });

  // 4. Generate Speech Flow
  btnSynthesize.addEventListener('click', async () => {
    hideTtsError();
    const text = narrationText.value.trim();
    if (!text) {
      showTtsError('Please enter text to synthesize');
      narrationText.focus();
      return;
    }

    const rateVal = parseInt(rateSlider.value);
    const pitchVal = parseInt(pitchSlider.value);
    const rateStr = rateVal >= 0 ? `+${rateVal}%` : `${rateVal}%`;
    const pitchStr = pitchVal >= 0 ? `+${pitchVal}Hz` : `${pitchVal}Hz`;

    isGeneratingSpeech = true;
    btnSynthesize.disabled = true;
    btnSynthesizeText.textContent = 'Generating Speech...';

    try {
      const response = await fetch('/api/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          voice_id: selectedVoiceId,
          rate: rateStr,
          pitch: pitchStr,
          title: text.slice(0, 30)
        })
      });

      const resData = await response.json();
      if (!response.ok) {
        throw new Error(resData.detail || 'Synthesis failed');
      }

      const voiceObj = VOICES.find(v => v.id === selectedVoiceId) || { name: 'Sonia' };

      activeAudioUrl = resData.data.audio_url;
      activeAudioFilename = resData.data.filename;

      mainAudio.src = activeAudioUrl;
      mainAudio.load();

      btnDownloadMp3.href = `${activeAudioUrl}?download=true`;
      btnDownloadMp3.download = `British_${voiceObj.name}_Speech.mp3`;

      showToast(`Speech generated successfully with ${voiceObj.name}!`, 'success');
      loadHistory();

      // Play audio automatically
      mainAudio.play().catch(() => {});

    } catch (err) {
      showTtsError(err.message || 'Error communicating with TTS server');
    } finally {
      isGeneratingSpeech = false;
      btnSynthesize.disabled = false;
      btnSynthesizeText.textContent = 'Generate Speech';
    }
  });

  // 5. Audio Player Controls
  btnPlayPause.addEventListener('click', () => {
    if (!mainAudio.src) {
      showToast('Generate speech first to preview audio', 'info');
      return;
    }

    if (mainAudio.paused) {
      mainAudio.play();
    } else {
      mainAudio.pause();
    }
  });

  mainAudio.addEventListener('play', () => {
    iconPlaySvg.classList.add('hidden');
    iconPauseSvg.classList.remove('hidden');
    if (waveformVisualizer) waveformVisualizer.classList.add('playing');
  });

  mainAudio.addEventListener('pause', () => {
    iconPlaySvg.classList.remove('hidden');
    iconPauseSvg.classList.add('hidden');
    if (waveformVisualizer) waveformVisualizer.classList.remove('playing');
  });

  mainAudio.addEventListener('ended', () => {
    iconPlaySvg.classList.remove('hidden');
    iconPauseSvg.classList.add('hidden');
    if (waveformVisualizer) waveformVisualizer.classList.remove('playing');
    timeDisplayCurrent.textContent = '0:00';
  });

  mainAudio.addEventListener('timeupdate', () => {
    timeDisplayCurrent.textContent = formatTime(mainAudio.currentTime);
    if (waveformVisualizer && mainAudio.duration) {
      const pct = mainAudio.currentTime / mainAudio.duration;
      const bars = waveformVisualizer.querySelectorAll('.wave-bar');
      const activeCount = Math.floor(pct * bars.length);
      bars.forEach((bar, idx) => {
        if (idx <= activeCount) {
          bar.classList.add('active');
        } else {
          bar.classList.remove('active');
        }
      });
    }
  });

  mainAudio.addEventListener('loadedmetadata', () => {
    const durStr = formatTime(mainAudio.duration);
    timeDisplayTotal.textContent = durStr;
    audioTotalBadge.textContent = durStr;
  });

  volumeSlider.addEventListener('input', () => {
    mainAudio.volume = volumeSlider.value / 100;
  });

  // 6. History Manager
  async function loadHistory() {
    try {
      const res = await fetch('/api/history?limit=10');
      if (!res.ok) return;
      const data = await res.json();
      const items = data.history || [];
      const historyList = document.getElementById('history-list');
      if (!historyList) return;

      if (items.length === 0) {
        historyList.innerHTML = `
          <div class="py-8 text-center text-xs text-slate-400 flex flex-col items-center justify-center gap-1.5">
            <svg class="w-7 h-7 text-slate-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
            <span>No recordings yet. Click <strong>Generate Speech</strong> to create audio.</span>
          </div>
        `;
        return;
      }

      // Preload latest item into audio player if not currently loaded
      if (!activeAudioFilename && items.length > 0) {
        const latest = items[0];
        activeAudioFilename = latest.audio_filename;
        activeAudioUrl = latest.audio_url;
        mainAudio.src = activeAudioUrl;
        mainAudio.load();
        btnDownloadMp3.href = `${activeAudioUrl}?download=true`;
        btnDownloadMp3.download = `British_${latest.voice_name || 'speech'}.mp3`;
      }

      historyList.innerHTML = items.map(item => `
        <div class="p-3 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs transition flex items-center justify-between gap-3 shadow-2xs group" data-id="${item.id}">
          <div class="flex items-center gap-3 min-w-0">
            <button class="history-play-btn w-8 h-8 rounded-full bg-blue-50 hover:bg-blue-600 text-blue-600 hover:text-white flex items-center justify-center shrink-0 transition cursor-pointer" title="Play audio" data-url="${item.audio_url}" data-fn="${item.audio_filename}" data-title="${item.title || 'Audio'}">
              <svg class="w-3.5 h-3.5 ml-0.5 fill-current" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </button>
            <div class="min-w-0 truncate">
              <h4 class="text-xs font-semibold text-slate-900 truncate">${item.title || item.text_preview || 'Audio Narration'}</h4>
              <p class="text-[10px] text-slate-400 mt-0.5">${item.voice_name || (item.voice_id ? item.voice_id.split('-')[2] : 'Sonia')} • ${item.created_at || 'Recently'}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <a href="${item.audio_url}?download=true" download="narration.mp3" class="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-blue-600 text-xs font-medium flex items-center gap-1 transition shadow-2xs">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>MP3</span>
            </a>
            <button class="history-del-btn p-1.5 text-slate-400 hover:text-rose-500 cursor-pointer transition rounded-md hover:bg-rose-50" title="Delete record" data-id="${item.id}">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      `).join('');

      // Wire history play buttons
      historyList.querySelectorAll('.history-play-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const url = btn.dataset.url;
          const fn = btn.dataset.fn;
          activeAudioUrl = url;
          activeAudioFilename = fn;
          mainAudio.src = url;
          mainAudio.load();
          btnDownloadMp3.href = `${url}?download=true`;
          mainAudio.play().catch(() => {});
          showToast(`Playing: ${btn.dataset.title}`, 'info');
        });
      });

      // Wire history delete buttons
      historyList.querySelectorAll('.history-del-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          await fetch(`/api/history/${id}`, { method: 'DELETE' });
          loadHistory();
        });
      });

    } catch (e) {
      console.warn('Could not load history:', e);
    }
  }

  // Initial setup
  updateScriptStats();
  loadHistory();

})();
