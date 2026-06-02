import React, { useState } from 'react';
import styles from './Step1UrlInput.module.css';

export default function Step1UrlInput({ onConfigured }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPrompt, setShowPrompt] = useState(false);

  // Normalize inputs to ensure strings match backend assumptions
  const cleanUrlParam = (target) => {
    if (!target.startsWith('http://') && !target.startsWith('https://')) {
      return `https://${target}`;
    }
    return target;
  };

  // Stage 1: Form interception & Cache Validation
  const handlePreFlightCheck = async (e) => {
    e.preventDefault();
    if (!url) return;
    setLoading(true);
    setShowPrompt(false);

    try {
      const normalizedUrl = cleanUrlParam(url);
      const res = await fetch(`http://127.0.0.1:8000/api/check-cache?url=${encodeURIComponent(normalizedUrl)}`);
      
      if (res.ok) {
        const data = await res.json();
        if (data.exists) {
          // Cache found on disk! Intercept and show the choices
          setShowPrompt(true);
          setLoading(false);
          return;
        }
      }
      
      // No cache trace found on disk. Proceed straight to automated background crawl.
      await executeCrawlSequence(normalizedUrl, false);
    } catch (err) {
      // Fallback insurance: run a standard non-forced scrape if checking drops
      await executeCrawlSequence(cleanUrlParam(url), false);
    }
  };

  // Stage 2: Fire payload configs over to FastAPI
  const executeCrawlSequence = async (targetUrl, forceRescrapeFlag) => {
    setLoading(true);
    setShowPrompt(false);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/start-crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          url: targetUrl,
          force_rescrape: forceRescrapeFlag 
        })
      });
      
      if (res.ok) {
        onConfigured(targetUrl);
      } else {
        alert('Backend engine rejected initial scan request parameters.');
        setLoading(false);
      }
    } catch (err) {
      alert('Could not establish contact with your FastAPI server.');
      setLoading(false);
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h1 className={styles.title}>Pipeline Analysis Bench</h1>
        <p className={styles.subtitle}>Provide an e-commerce retail store URL target to profile its design aesthetic mapping parameters.</p>
      </div>
      
      <form onSubmit={handlePreFlightCheck} className={styles.form}>
        <input
          type="url"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setShowPrompt(false);
          }}
          placeholder="https://example-fashion-store.com"
          disabled={loading || showPrompt}
          className={styles.input}
          required
        />
        <button type="submit" disabled={loading || showPrompt} className={styles.button}>
          {loading ? 'Scheduling Process...' : 'Launch Crawler Pipeline'}
        </button>
      </form>

      {/* --- USER INTERCEPTOR CHOICE PANEL --- */}
      {showPrompt && (
        <div style={{ marginTop: '22px', textAlign: 'left', background: '#fffbeb', padding: '16px', borderRadius: '10px', border: '1px solid #fde68a' }}>
          <h4 style={{ margin: '0 0 6px 0', color: '#b45309', fontSize: '15px', fontWeight: '600' }}>
            ⚠️ Existing Brand Profile Discovered
          </h4>
          <p style={{ margin: '0 0 16px 0', color: '#78350f', fontSize: '13px', lineHeight: '1.4' }}>
            A local database profile already exists for this URL. Would you like to wipe storage records and force a fresh re-scrape, or instantly use the cached profile data?
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={() => {
                const normalizedUrl = cleanUrlParam(url);
                // Wipes any existing session flag so Step 2 forces the 1-minute progress bar
                sessionStorage.removeItem(`progress_done_${normalizedUrl}`);
                executeCrawlSequence(normalizedUrl, true);
              }}
              style={{ background: '#d97706', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
            >
              🔄 Force Full Remake
            </button>
            
            <button 
              onClick={() => {
                const normalizedUrl = cleanUrlParam(url);
                // Pre-emptively flag this URL as completed so Step 2 skips the progress bar completely
                sessionStorage.setItem(`progress_done_${normalizedUrl}`, 'true');
                onConfigured(normalizedUrl);
              }}
              style={{ background: '#fef3c7', color: '#92400e', border: '1px solid #fcd34d', padding: '8px 16px', borderRadius: '6px', fontWeight: '600', fontSize: '13px', cursor: 'pointer' }}
            >
              ✅ Use Existing Profile
            </button>
          </div>
        </div>
      )}
    </div>
  );
}