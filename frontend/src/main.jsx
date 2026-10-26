import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const STATUS = {
  ALERT: { label: 'DRIVER ALERT', code: 'NOMINAL', className: 'good' },
  'POSSIBLE DROWSINESS': { label: 'FATIGUE WARNING', code: 'CAUTION', className: 'warn' },
  'HIGH DROWSINESS RISK': { label: 'HIGH RISK', code: 'PULL OVER', className: 'danger' },
  'TRACKING UNAVAILABLE': { label: 'NO DRIVER LOCK', code: 'SIGNAL LOST', className: 'offline' },
};

function App() {
  const video = useRef(null);
  const camera = useRef(null);
  const canvas = useRef(document.createElement('canvas'));
  const nightMode = useRef(false);
  const audio = useRef(null);
  const voice = useRef(null);
  const [status, setStatus] = useState('READY');
  const [night, setNight] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [history, setHistory] = useState([]);
  const [page, setPage] = useState('monitor');
  const [booting, setBooting] = useState(true);
  const [metrics, setMetrics] = useState({ tracking: 'offline', ear: '—', perclos: '—', closureSeconds: 0 });

  useEffect(() => {
    const timer = setTimeout(() => setBooting(false), 5000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const updateFullscreen = () => setFullscreen(document.fullscreenElement === camera.current);
    document.addEventListener('fullscreenchange', updateFullscreen);
    return () => document.removeEventListener('fullscreenchange', updateFullscreen);
  }, []);

  useEffect(() => {
    if (!soundEnabled || !['POSSIBLE DROWSINESS', 'HIGH DROWSINESS RISK'].includes(status)) return;
    const beep = () => {
      const context = audio.current;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const highRisk = status === 'HIGH DROWSINESS RISK';
      oscillator.type = highRisk ? 'square' : 'sine';
      oscillator.frequency.value = highRisk ? 2800 : 900;
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(highRisk ? 0.3 : 0.14, context.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + (highRisk ? 0.42 : 0.22));
      oscillator.connect(gain).connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + (highRisk ? 0.43 : 0.23));
    };
    beep();
    if (status === 'HIGH DROWSINESS RISK') {
      const timer = setInterval(beep, 600);
      return () => clearInterval(timer);
    }
  }, [status, soundEnabled]);

  useEffect(() => {
    if (!soundEnabled) return;
    const files = { 'POSSIBLE DROWSINESS': 'possible_drowsiness.mp3', 'HIGH DROWSINESS RISK': 'high_risk.mp3', 'TRACKING UNAVAILABLE': 'tracking_lost.mp3' };
    const file = files[status];
    if (!file) return;
    voice.current?.pause();
    voice.current = new Audio(`/voices/${file}`);
    voice.current.volume = 0.85;
    voice.current.play().catch(() => {});
  }, [status, soundEnabled]);

  useEffect(() => {
    if (page !== 'monitor' || booting) return undefined;
    let socket;
    let stream;
    let active = true;
    let awaitingResult = false;
    navigator.mediaDevices.getUserMedia({ video: true }).then(cameraStream => {
      stream = cameraStream;
      if (!active) {
        cameraStream.getTracks().forEach(track => track.stop());
        return;
      }
      video.current.srcObject = cameraStream;
      socket = new WebSocket('ws://localhost:8000/ws/monitor');
      socket.onopen = () => {
        setStatus('ALERT');
        socket.frameTimer = setInterval(() => {
          if (socket.readyState !== WebSocket.OPEN || !video.current.videoWidth || awaitingResult) return;
          canvas.current.width = 480;
          canvas.current.height = Math.round(480 * video.current.videoHeight / video.current.videoWidth);
          canvas.current.getContext('2d').drawImage(video.current, 0, 0, canvas.current.width, canvas.current.height);
          awaitingResult = true;
          socket.send(JSON.stringify({ frame: canvas.current.toDataURL('image/jpeg', 0.65), nightMode: nightMode.current }));
        }, 67);
      };
      socket.onmessage = event => {
        awaitingResult = false;
        const next = JSON.parse(event.data);
        setMetrics(next);
        setStatus(next.status || 'ALERT');
        setHistory(items => [...items.slice(-899), next]);
      };
    }).catch(() => setStatus('CAMERA ERROR'));
    return () => {
      active = false;
      clearInterval(socket?.frameTimer);
      socket?.close();
      stream?.getTracks().forEach(track => track.stop());
      if (video.current) video.current.srcObject = null;
    };
  }, [page, booting]);

  const toggleSound = async () => {
    audio.current ??= new AudioContext();
    await audio.current.resume();
    setSoundEnabled(enabled => !enabled);
  };
  const toggleNight = () => { nightMode.current = !nightMode.current; setNight(nightMode.current); };
  const toggleFullscreen = async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await camera.current?.requestFullscreen();
  };
  const state = STATUS[status] || { label: status, code: 'SYSTEM', className: 'offline' };
  const perclos = Number(metrics.perclos) || 0;
  const downloadReport = () => {
    window.print();
  };

  if (booting) return <BootScreen />;

  const warnings = history.filter(item => item.status !== 'ALERT').length;
  const highRisk = history.filter(item => item.status === 'HIGH DROWSINESS RISK').length;
  const averagePerclos = history.length ? history.reduce((sum, item) => sum + (Number(item.perclos) || 0), 0) / history.length : 0;
  const averageBlinkRate = history.length ? history.reduce((sum, item) => sum + (Number(item.blinkRate) || 0), 0) / history.length : 0;
  const gazeCounts = history.reduce((counts, item) => ({ ...counts, [item.gaze || 'UNKNOWN']: (counts[item.gaze || 'UNKNOWN'] || 0) + 1 }), {});

  if (page === 'analytics') return <main className="analytics-page">
    <header><div className="brand"><img className="brand-logo" src="/LOGO%20(1).png" alt="FatigueWatch logo" /><div><b>FATIGUEWATCH</b><small>SESSION ANALYTICS</small></div></div><button onClick={() => setPage('monitor')}>← LIVE MONITOR</button></header>
    <section className="hero"><div><span className="eyebrow">SESSION PERFORMANCE</span><h1>DATA <em>INSIGHT.</em></h1></div><button className="print-button" onClick={downloadReport}>PRINT / SAVE PDF</button></section>
    <section className="stats-grid"><Stat label="SAMPLES" value={history.length} /><Stat label="FATIGUE EVENTS" value={warnings} /><Stat label="HIGH-RISK SAMPLES" value={highRisk} /><Stat label="AVG PERCLOS" value={`${averagePerclos.toFixed(1)}%`} /><Stat label="AVG BLINK RATE" value={`${averageBlinkRate.toFixed(1)}/min`} /><Stat label="CENTER GAZE" value={gazeCounts.CENTER || 0} /></section>
    <section className="analytics-panels"><article className="panel analytics-card"><h2>GAZE DISTRIBUTION</h2>{Object.entries(gazeCounts).map(([label, count]) => <div className="stat-row" key={label}><span>{label}</span><b>{count}</b><i style={{ width: `${history.length ? count / history.length * 100 : 0}%` }} /></div>)}</article><article className="panel analytics-card"><h2>RECENT EVENTS</h2>{history.slice(-8).reverse().map((item, index) => <div className="event-row" key={`${item.timestamp}-${index}`}><span>{new Date(item.timestamp).toLocaleTimeString()}</span><b>{item.status}</b><small>PERCLOS {item.perclos}% · GAZE {item.gaze}</small></div>)}</article></section>
    <footer><span>FATIGUEWATCH // SESSION REPORT</span><span>PRINT DIALOG CAN SAVE THIS PAGE AS PDF</span></footer>
  </main>;

  return <main>
    <header><div className="brand"><img className="brand-logo" src="/LOGO%20(1).png" alt="FatigueWatch logo" /><div><b>FATIGUEWATCH</b><small>DRIVER TELEMETRY SYSTEM</small></div></div><div className="header-data"><span><i /> SYSTEM ONLINE</span><span>CAM 01</span><span>AI CORE</span><button onClick={() => setPage('analytics')}>ANALYTICS</button></div></header>
    <section className="hero"><div><span className="eyebrow">REAL-TIME COCKPIT MONITORING</span><h1>DRIVE <em>SHARP.</em></h1></div><div className="lap-chip"><small>ACTIVE PROFILE</small><b>DRIVER 01</b></div></section>
    <section className="dashboard">
      {metrics.yawn && <div className="yawn-alert" role="status">⚠ YAWN DETECTED</div>}
      <div ref={camera} className={`camera panel ${night ? 'night' : ''}`}><video ref={video} autoPlay muted playsInline /><div className="scanline" /><div className="reticle"><span /><span /><span /><span /></div><div className="camera-top"><span>● LIVE FEED</span><span>480P / AI TRACKING</span></div><div className="glass-data"><div><small>DRIVER STATE</small><b className={state.className}>{state.label}</b></div><div><small>FATIGUE</small><b>{Math.round(perclos)}%</b></div><div><small>EYE CLOSURE</small><b>{metrics.closureSeconds ?? 0}s</b></div><div><small>EYE OPENNESS</small><b>{metrics.ear ?? '—'}</b></div></div><div className="camera-bottom"><span>FACE LOCK <b>{metrics.tracking}</b></span><div className="camera-actions"><button onClick={toggleNight}>{night ? '☀ DAY MODE' : '◐ NIGHT MODE'}</button><button onClick={toggleFullscreen}>{fullscreen ? '↙ EXIT FULLSCREEN' : '⛶ FULLSCREEN'}</button></div></div></div>
      <aside className={`status-panel panel ${state.className}`}><div className="status-head"><small>DRIVER CONDITION</small><span>{state.code}</span></div><div className="gauge"><div className="gauge-ring" style={{ '--load': Math.min(perclos, 100) }}><b>{Math.round(perclos)}</b><small>% LOAD</small></div></div><strong>{state.label}</strong><p>{metrics.lowLight ? 'LOW LIGHT COMPENSATION ACTIVE' : 'OPTICAL SIGNAL STABLE'}</p><div className="controls"><button className={soundEnabled ? 'active' : ''} onClick={toggleSound}>{soundEnabled ? '🔊 ALERT AUDIO ON' : '🔇 ENABLE AUDIO'}</button><button className="stop" onClick={() => setStatus('STOPPED')}>■ END SESSION</button></div></aside>
    </section>
    <section className="telemetry"><Metric number="01" label="EYE OPENNESS" value={metrics.ear ?? '—'} unit="EAR" progress={Math.min((Number(metrics.ear) || 0) * 300, 100)} /><Metric number="02" label="FATIGUE LOAD" value={metrics.perclos ?? '—'} unit="% / 30S" progress={perclos} /><Metric number="03" label="BLINK RATE" value={metrics.blinkRate ?? '—'} unit="/ MIN" progress={Math.min((Number(metrics.blinkRate) || 0) * 2, 100)} /><Metric number="04" label="GAZE" value={metrics.gaze || '—'} unit={metrics.yawn ? 'YAWN DETECTED' : 'VISION'} progress={metrics.gaze === 'CENTER' ? 100 : 35} compact /></section>
    <div className="report-action"><button onClick={downloadReport} disabled={!history.length}>DOWNLOAD SESSION REPORT</button></div>
    <footer><span>FATIGUEWATCH // DRIVER SAFETY INTERFACE</span><span>NOT A MEDICAL OR SAFETY CERTIFICATION DEVICE</span></footer>
  </main>;
}

function Metric({ number, label, value, unit, progress, compact }) {
  return <article className="metric panel"><div className="metric-head"><span>{number}</span><small>{label}</small></div><strong className={compact ? 'compact' : ''}>{value}</strong><span className="unit">{unit}</span><div className="bar"><i style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }} /></div></article>;
}

function Stat({ label, value }) { return <article className="panel stat-card"><small>{label}</small><strong>{value}</strong></article>; }

function BootScreen() {
  return <main className="boot-screen"><div className="boot-core"><img src="/LOGO%20(1).png" alt="FatigueWatch logo" /><div className="boot-ring ring-one" /><div className="boot-ring ring-two" /><div className="boot-ring ring-three" /></div><h1>FATIGUE<em>WATCH</em></h1><p>INITIALIZING DRIVER TELEMETRY SYSTEM</p><div className="boot-progress"><i /></div><div className="boot-status"><span>● SYSTEM STARTUP</span><span>CAMERA / AI CORE / AUDIO</span></div></main>;
}

createRoot(document.getElementById('root')).render(<App />);
