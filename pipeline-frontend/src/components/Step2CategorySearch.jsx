import React, { useState, useEffect, useRef } from 'react';
import ProgressBar from './ProgressBar';
import styles from './Step2CategorySearch.module.css';

export default function Step2CategorySearch({ targetUrl, onSearchComplete, onBack }) {
  // Use sessionStorage so that returning to this page for the same URL remembers it already loaded
  const [progress, setProgress] = useState(() => {
    const wasLoaded = sessionStorage.getItem(`progress_done_${targetUrl}`);
    return wasLoaded ? 100 : 0;
  }); 
  const [category, setCategory] = useState('');
  const [searching, setSearching] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [scrapingStatus, setScrapingStatus] = useState('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [generatingImage, setGeneratingImage] = useState(false);

  const pollingIntervalRef = useRef(null);

  // 1. Smooth 1-Minute Progress Bar Timer
  useEffect(() => {
    if (progress >= 100) return;

    const totalDuration = 60000; // 60 seconds
    const intervalTick = 200;    // Update every 200ms for visual smoothness
    const increment = (intervalTick / totalDuration) * 100;

    const progressTimer = setInterval(() => {
      setProgress((prevProgress) => {
        if (prevProgress >= 100) {
          clearInterval(progressTimer);
          sessionStorage.setItem(`progress_done_${targetUrl}`, 'true');
          return 100;
        }
        const nextProgress = prevProgress + increment;
        if (nextProgress >= 100) {
          sessionStorage.setItem(`progress_done_${targetUrl}`, 'true');
          return 100;
        }
        return nextProgress;
      });
    }, intervalTick);

    return () => clearInterval(progressTimer);
  }, [targetUrl, progress]);

  // 2. Background Scraper Status Polling Loop
  useEffect(() => {
    const checkInitialEngineStatus = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/status');
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'running') {
            setScrapingStatus('scraping');
            setStatusMessage(data.message);
            startPollingLoop();
          }
        }
      } catch (err) { console.error(err); }
    };
    checkInitialEngineStatus();

    return () => { if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current); };
  }, []);

  const startPollingLoop = () => {
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/status');
        if (res.ok) {
          const data = await res.json();
          setStatusMessage(data.message);
          if (data.status === 'completed') {
            clearInterval(pollingIntervalRef.current);
            setScrapingStatus('idle');
          } else if (data.status === 'failed') {
            clearInterval(pollingIntervalRef.current);
            setScrapingStatus('idle');
            alert(`Pipeline error: ${data.message}`);
          }
        }
      } catch (e) { console.error(e); }
    }, 2000);
  };

  const handleQueryLookup = async (e) => {
    e.preventDefault();
    if (progress < 100 || !category) return;
    setSearching(true);
    setSuggestions([]);

    try {
      const targetQuery = encodeURIComponent(category);
      const targetDomain = encodeURIComponent(targetUrl);

      const res = await fetch(`http://127.0.0.1:8000/api/search?query=${targetQuery}&url=${targetDomain}`);
      
      if (res.ok) {
        const responseData = await res.json();
        const payload = responseData.result;

        if (payload.type === 'suggestions') {
          setSuggestions(payload.data || []);
        } else {
          onSearchComplete(category, payload.data);
        }
      } else {
        alert('Could not safely query backend index logs.');
      }
    } catch (err) {
      alert('Could not safely query backend index.');
    } finally {
      setSearching(false);
    }
  };
  const generateImage = async (prompt) => {
  try {
    setGeneratingImage(true);

    const formData = new FormData();

    formData.append("category", prompt);

    if (selectedImage) {
      formData.append("image", selectedImage);
    }

    const res = await fetch(
      "http://127.0.0.1:8000/api/generate-image",
      {
        method: "POST",
        body: formData,
      }
    );

    if (!res.ok) {
      throw new Error("Image generation failed");
    }

    const data = await res.json();
    console.log("Full nano response:", data);

    return data;
  } finally {
    setGeneratingImage(false);
  }
};

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          {progress < 100 ? 'Analyzing Site Framework...' : 'Brand Workspace Active'}
        </h2>
        <p className={styles.urlDisplay}>{targetUrl}</p>
      </div>

      {/* Only render progress bar if it hasn't completed yet */}
      {progress < 100 && <ProgressBar percentage={Math.floor(progress)} />}

      <button
        type="button"
        onClick={onBack}
        style={{
          marginBottom: '16px',
          padding: '8px 16px',
          borderRadius: '8px',
          border: '1px solid #cbd5e1',
          background: '#ffffff',
          cursor: 'pointer'
        }}
      >
        ← Back to URL Input
      </button>

      {/* Background status notice can still subtly display if scraping is running in bg */}
      {scrapingStatus === 'scraping' && (
        <div style={{ background: '#f1f5f9', padding: '12px', borderRadius: '8px', marginBottom: '15px', color: '#475569', fontSize: '13px', textAlign: 'left', border: '1px solid #cbd5e1' }}>
          ⏳ Backend Engine Status: {statusMessage || 'Processing data streams...'}
        </div>
      )}

      <form onSubmit={handleQueryLookup} className={styles.form}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Target Search Category</label>
          <input
            type="text"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              if (suggestions.length > 0) setSuggestions([]); 
            }}
            placeholder={progress < 100 ? "Awaiting initialization..." : "e.g., Shoes, Denim"}
            /* Form inputs unlock as soon as the 1-minute progress completes, ignoring background scraper status */
            disabled={progress < 100 || searching}
            className={styles.input}
            required
          />
        </div>

        <div className={styles.fieldGroup}>
          <label className={styles.label}>Upload Image</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                setSelectedImage(e.target.files[0]);
              }
            }}
            disabled={progress < 100 || searching}
            className={styles.input}
          />

          {selectedImage && (
            <div style={{ marginTop: "10px" }}>
              <img
                src={URL.createObjectURL(selectedImage)}
                alt="Preview"
                style={{
                  maxWidth: "200px",
                  maxHeight: "200px",
                  borderRadius: "8px",
                  border: "1px solid #cbd5e1"
                }}
              />
            </div>
          )}
        </div>

        <button type="submit" disabled={progress < 100 || searching} className={styles.button}>
          {searching ? 'Querying Index Logs...' : 'Scan Matching Categories'}
        </button>
      </form>

      {/* NEW SPLIT-UI LOGIC STARTS HERE */}
      {suggestions.length > 0 && (
        <div style={{ marginTop: '22px', textAlign: 'left', background: '#f8fafc', padding: '16px', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
          
          {/* SECTION A: ACTIVE QUERY SEARCH MATCHES */}
          {suggestions.filter(item => !item.is_group_filler).length > 0 && (
            <>
              <h4 style={{ margin: '0 0 12px 0', color: '#1e293b', fontSize: '15px', fontWeight: '600' }}>
                Matching Search Results:
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '20px' }}>
                {suggestions.filter(item => !item.is_group_filler).map((item, idx) => (
                  <button
                    key={`active-${idx}`}
                    disabled={generatingImage}
                    onClick={async () => {
                      try {
                        if (!selectedImage) {
                          alert("Please upload an image first.");
                          return;
                        }
                        setCategory(item.text);

                        const nanoResponse = await generateImage(item.text);
                        console.log("Nano response:", nanoResponse);

                        onSearchComplete(
                          item.text,
                          item.prompt,
                          nanoResponse?.images || []
                        );
                      } catch (err) {
                        console.error(err);
                        alert("Failed to generate image.");
                      }
                    }}
                    style={{
                      background: item.is_exact ? '#eff6ff' : '#ffffff',
                      border: item.is_exact ? '1px solid #3b82f6' : '1px solid #cbd5e1',
                      color: item.is_exact ? '#1d4ed8' : '#334155',
                      fontWeight: item.is_exact ? '600' : '400',
                      padding: '8px 14px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.background = item.is_exact ? '#dbeafe' : '#f1f5f9'; }}
                    onMouseOut={(e) => { e.currentTarget.style.background = item.is_exact ? '#eff6ff' : '#ffffff'; }}
                  >
                    {item.is_exact ? '⭐' : '📁'}{' '}
                    {item.group ? (
                      <span style={{ background: item.is_exact ? '#3b82f6' : '#64748b', color: '#ffffff', fontSize: '11px', fontWeight: '700', padding: '2px 6px', borderRadius: '4px', marginRight: '4px', textTransform: 'uppercase' }}>
                        {item.group}
                      </span>
                    ) : null}
                    {item.text}
                  </button>
                ))}
              </div>
            </>
          )}

          {/* SECTION B: ALL OTHER CATEGORIES IN THE GROUP (SHOWN BELOW) */}
          {suggestions.filter(item => item.is_group_filler).length > 0 && (
            <>
              {suggestions.filter(item => !item.is_group_filler).length > 0 && (
                <hr style={{ border: '0', borderTop: '1px solid #e2e8f0', margin: '18px 0' }} />
              )}
              <h4 style={{ margin: '0 0 12px 0', color: '#64748b', fontSize: '13px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                All Other Discoverable Categories in ({suggestions.find(i => i.group)?.group || 'Context'}):
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                {suggestions.filter(item => item.is_group_filler).map((item, idx) => (
                  <button
                    key={`filler-${idx}`}
                    disabled={generatingImage}
                    onClick={async () => {
                      try {
                        if (!selectedImage) {
                          alert("Please upload an image first.");
                          return;
                        }
                        setCategory(item.text);

                        const nanoResponse = await generateImage(item.text);
                        console.log("Nano response:", nanoResponse);

                        onSearchComplete(
                          item.text,
                          item.prompt,
                          nanoResponse?.images || []
                        );
                      } catch (err) {
                        console.error(err);
                        alert("Failed to generate image.");
                      }
                    }}
                    style={{
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      color: '#64748b',
                      fontWeight: '400',
                      padding: '8px 14px',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      transition: 'all 0.15s ease'
                    }}
                    onMouseOver={(e) => { 
                      e.currentTarget.style.background = '#ffffff'; 
                      e.currentTarget.style.borderColor = '#cbd5e1';
                      e.currentTarget.style.color = '#334155';
                    }}
                    onMouseOut={(e) => { 
                      e.currentTarget.style.background = '#f8fafc'; 
                      e.currentTarget.style.borderColor = '#e2e8f0';
                      e.currentTarget.style.color = '#64748b';
                    }}
                  >
                    📁 {item.text}
                  </button>
                ))}
              </div>
            </>
          )}

        </div>
      )}

      
    </div>
  );
}