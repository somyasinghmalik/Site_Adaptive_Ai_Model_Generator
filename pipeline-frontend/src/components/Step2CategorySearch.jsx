import React, { useState, useEffect, useRef, useCallback } from 'react';
import ProgressBar from './ProgressBar';
import styles from './Step2CategorySearch.module.css';

export default function Step2CategorySearch({ targetUrl, onSearchComplete, onBack }) {
  const [progress, setProgress] = useState(() => {
    const wasLoaded = sessionStorage.getItem(`progress_done_${targetUrl}`);
    return wasLoaded ? 100 : 0;
  });
  const [category, setCategory] = useState('');
  const [scrapingStatus, setScrapingStatus] = useState('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [frontImage, setFrontImage] = useState(null);
  const [backImage, setBackImage] = useState(null);
  const [generatingImage, setGeneratingImage] = useState(false);

  // Dropdown state
  const [allCategories, setAllCategories] = useState([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  // Track if category was picked from dropdown (enables direct Generate Images mode)
  const [selectedFromDropdown, setSelectedFromDropdown] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  const inputRef = useRef(null);
  const dropdownRef = useRef(null);
  const pollingIntervalRef = useRef(null);
  const hasFrontImage = Boolean(frontImage);

  const filteredCategories = allCategories.length === 0 ? [] : (() => {
    const q = category.trim().toLowerCase();
    if (!q) return allCategories;
    return allCategories.filter(item =>
      item.text.toLowerCase().includes(q) || item.group.toLowerCase().includes(q)
    );
  })();

  const groupedFiltered = filteredCategories.reduce((acc, item) => {
    const g = item.group || 'Other';
    if (!acc[g]) acc[g] = [];
    acc[g].push(item);
    return acc;
  }, {});

  // 1. Progress bar
  useEffect(() => {
    if (progress >= 100) return;
    const totalDuration = 60000;
    const intervalTick = 200;
    const increment = (intervalTick / totalDuration) * 100;
    const progressTimer = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) { clearInterval(progressTimer); sessionStorage.setItem(`progress_done_${targetUrl}`, 'true'); return 100; }
        const next = prev + increment;
        if (next >= 100) { sessionStorage.setItem(`progress_done_${targetUrl}`, 'true'); return 100; }
        return next;
      });
    }, intervalTick);
    return () => clearInterval(progressTimer);
  }, [targetUrl, progress]);

  // 2. Fetch all categories once progress hits 100
  const fetchAllCategories = useCallback(async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/categories?url=${encodeURIComponent(targetUrl)}`);
      if (res.ok) {
        const data = await res.json();
        setAllCategories(data.categories || []);
      }
    } catch (err) {
      console.error('Category fetch failed:', err);
    }
  }, [targetUrl]);

  useEffect(() => {
    if (progress >= 100) fetchAllCategories();
  }, [progress, fetchAllCategories]);

  // 3. Background scraper polling
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
          if (data.status === 'completed') { clearInterval(pollingIntervalRef.current); setScrapingStatus('idle'); }
          else if (data.status === 'failed') { clearInterval(pollingIntervalRef.current); setScrapingStatus('idle'); alert(`Pipeline error: ${data.message}`); }
        }
      } catch (e) { console.error(e); }
    }, 2000);
  };

  // 4. Click-outside closes dropdown
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // 5. Input handlers — typing clears the dropdown selection
  const handleCategoryChange = (e) => {
    setCategory(e.target.value);
    setActiveIndex(-1);
    setSelectedFromDropdown(false);
    setSelectedItem(null);
    setDropdownOpen(true);
  };

  const handleInputFocus = () => {
    if (allCategories.length > 0) setDropdownOpen(true);
  };

  const handleKeyDown = (e) => {
    if (!dropdownOpen || filteredCategories.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(i => Math.min(i + 1, filteredCategories.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      const selected = filteredCategories[activeIndex];
      handleDropdownSelect(selected);
    } else if (e.key === 'Escape') {
      setDropdownOpen(false);
      setActiveIndex(-1);
    }
  };

  // Picking from dropdown sets selectedFromDropdown = true → button becomes "Generate Images"
  const handleDropdownSelect = (item) => {
    setCategory(item.text);
    setSelectedFromDropdown(true);
    setSelectedItem(item);
    setDropdownOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  };

  // 6. Submit — two modes depending on how category was set
  const handleQueryLookup = async (e) => {
    e.preventDefault();

    if (!selectedItem?.prompt) {
      alert("Please select a category.");
      return;
    }

    if (!frontImage) {
      alert("Please upload the front image first.");
      return;
    }

    try {
      setGeneratingImage(true);

      const dispatchResponse = await generateImage(selectedItem.text);

      if (!dispatchResponse?.trackers?.length) {
        throw new Error("No prediction IDs returned");
      }

      const images = await waitForImages(dispatchResponse.trackers);

      onSearchComplete(
        selectedItem.text,
        selectedItem.prompt,
        images
      );
    } catch (err) {
      console.error(err);
      alert("Failed to generate image.");
    } finally {
      setGeneratingImage(false);
    }
  };

  // 7. Image generation
  const generateImage = async (prompt) => {
    const formData = new FormData();
    formData.append("category", prompt);
    if (frontImage) formData.append("front_image", frontImage);
    if (backImage) formData.append("back_image", backImage);
    const res = await fetch("http://127.0.0.1:8000/api/generate-image", { method: "POST", body: formData });
    if (!res.ok) throw new Error("Image generation failed");
    return await res.json();
  };

  const waitForImages = async (trackers) => {
    const ids = trackers.map(t => t.prediction_id);
    while (true) {
      const res = await fetch("http://127.0.0.1:8000/api/prediction-status", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prediction_ids: ids })
      });
      const data = await res.json();
      if (data.completed) return data.images;
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  };


  // Shared eye SVG
  const EyeIcon = () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  );

  // Shared eye button style object
  const eyeBtnStyle = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
    width: '22px', height: '22px', borderRadius: '5px', flexShrink: 0,
    color: '#94a3b8', cursor: 'pointer', transition: 'background 0.1s, color 0.1s',
    marginLeft: '2px', background: 'transparent',
  };

  // Submit button label + style derived from current mode
  
  const isSubmitBusy = generatingImage;

  let flatIndex = -1;

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          {progress < 100 ? 'Analyzing Site Framework...' : 'Brand Workspace Active'}
        </h2>
        <p className={styles.urlDisplay}>{targetUrl}</p>
      </div>

      {progress < 100 && <ProgressBar percentage={Math.floor(progress)} />}

      <button type="button" onClick={onBack} className={styles.backButton}>
        ← Back to URL Input
      </button>

      {scrapingStatus === 'scraping' && (
        <div className={styles.statusNotice}>
          ⏳ Backend Engine Status: {statusMessage || 'Processing data streams...'}
        </div>
      )}

      <form onSubmit={handleQueryLookup} className={styles.form}>
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Target Search Category</label>

          <div ref={dropdownRef} style={{ position: 'relative' }}>
            {/* Input row */}
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <input
                ref={inputRef}
                type="text"
                value={category}
                onChange={handleCategoryChange}
                onFocus={handleInputFocus}
                onKeyDown={handleKeyDown}
                placeholder={progress < 100 ? 'Awaiting initialization...' : 'e.g., Shoes, Denim'}
                disabled={progress < 100 || isSubmitBusy}
                className={styles.input}
                required
                autoComplete="off"
                style={{
                  paddingRight: '64px',
                  // Green tint when a dropdown item is selected
                  borderColor: selectedFromDropdown ? '#059669' : undefined,
                  background: selectedFromDropdown ? '#f0fdf4' : undefined,
                }}
              />
              {allCategories.length > 0 && (
                <span style={{
                  position: 'absolute', right: '36px',
                  fontSize: '11px', color: '#94a3b8', fontWeight: '500',
                  pointerEvents: 'none', whiteSpace: 'nowrap',
                }}>
                  {allCategories.length}
                </span>
              )}
              <button
                type="button"
                tabIndex={-1}
                onClick={() => {
                  if (progress < 100 || isSubmitBusy) return;
                  setDropdownOpen(o => !o);
                  inputRef.current?.focus();
                }}
                disabled={progress < 100 || isSubmitBusy || allCategories.length === 0}
                style={{
                  position: 'absolute', right: '10px',
                  background: 'none', border: 'none', cursor: 'pointer',
                  padding: '0', display: 'flex', alignItems: 'center',
                  color: '#94a3b8', transition: 'color 0.15s',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none"
                  style={{ transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }}>
                  <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            {/* Selected category pill shown below input */}
            {selectedFromDropdown && selectedItem && (
              <div style={{
                marginTop: '6px', display: 'flex', alignItems: 'center', gap: '6px',
                fontSize: '12px', color: '#059669',
              }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                Selected from index
                {selectedItem.group && (
                  <span style={{
                    background: '#d1fae5', color: '#065f46', fontSize: '10px',
                    fontWeight: '700', padding: '1px 6px', borderRadius: '4px',
                    textTransform: 'uppercase',
                  }}>
                    {selectedItem.group}
                  </span>
                )}
                {selectedItem.raw_url && (
                  <a
                    href={selectedItem.raw_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={selectedItem.raw_url}
                    style={{ color: '#059669', fontSize: '11px', textDecoration: 'underline', marginLeft: '2px' }}
                  >
                    view source ↗
                  </a>
                )}
              </div>
            )}

            {/* Dropdown panel */}
            {dropdownOpen && (
              <div style={{
                position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0,
                zIndex: 100, background: '#ffffff',
                border: '1px solid #cbd5e1', borderRadius: '10px',
                boxShadow: '0 8px 24px rgba(0,0,0,0.10)',
                maxHeight: '260px', overflowY: 'auto',
              }}>
                {filteredCategories.length === 0 ? (
                  <div style={{ padding: '12px 14px', color: '#94a3b8', fontSize: '13px', textAlign: 'center' }}>
                    No categories match "{category}"
                  </div>
                ) : (
                  Object.entries(groupedFiltered).map(([group, items]) => (
                    <div key={group}>
                      {/* Group header */}
                      <div style={{
                        padding: '6px 12px 4px',
                        fontSize: '10px', fontWeight: '700', letterSpacing: '0.08em',
                        textTransform: 'uppercase', color: '#94a3b8',
                        borderBottom: '1px solid #f1f5f9',
                        background: '#fafafa', position: 'sticky', top: 0,
                      }}>
                        {group}
                      </div>
                      {items.map((item) => {
                        flatIndex++;
                        const currentFlatIndex = flatIndex;
                        const isHighlighted = activeIndex === currentFlatIndex;
                        const isSelected = selectedItem?.text === item.text;
                        return (
                          <div
                            key={item.text}
                            onMouseDown={() => handleDropdownSelect(item)}
                            onMouseEnter={() => setActiveIndex(currentFlatIndex)}
                            style={{
                              padding: '9px 12px',
                              cursor: 'pointer',
                              fontSize: '14px',
                              color: isSelected ? '#059669' : isHighlighted ? '#1e293b' : '#475569',
                              background: isSelected ? '#f0fdf4' : isHighlighted ? '#f1f5f9' : 'transparent',
                              display: 'flex', alignItems: 'center', gap: '8px',
                              transition: 'background 0.1s',
                              borderLeft: isSelected ? '3px solid #059669' : '3px solid transparent',
                            }}
                          >
                            {/* Checkmark if selected, folder icon otherwise */}
                            {isSelected ? (
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                                <polyline points="20 6 9 17 4 12"/>
                              </svg>
                            ) : (
                              <span style={{ fontSize: '12px', flexShrink: 0 }}>📁</span>
                            )}
                            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {item.text}
                            </span>
                            {/* Match badge */}
                            {category.trim() && !isSelected && item.text.toLowerCase().includes(category.trim().toLowerCase()) && (
                              <span style={{
                                fontSize: '10px', color: '#3b82f6', fontWeight: '600',
                                background: '#eff6ff', padding: '1px 5px', borderRadius: '4px', flexShrink: 0,
                              }}>
                                match
                              </span>
                            )}
                            {/* Eye button — <a> is valid here (not inside <button>) */}
                            {item.raw_url && (
                              <a
                                href={item.raw_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => e.stopPropagation()}
                                title={item.raw_url}
                                aria-label={`Open source URL for ${item.text}`}
                                style={{ ...eyeBtnStyle, textDecoration: 'none' }}
                                onMouseOver={(e) => { e.currentTarget.style.background = '#e2e8f0'; e.currentTarget.style.color = '#475569'; }}
                                onMouseOut={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8'; }}
                              >
                                <EyeIcon />
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Image uploads */}
        <div className={styles.fieldGroup}>
          <label className={styles.label}>Product Reference Images</label>
          <div className={styles.uploadGrid}>
            <div className={styles.uploadPanel}>
              <div className={styles.uploadHeader}>
                <span className={styles.uploadTitle}>Front Image</span>
                <span className={styles.uploadHintRequired}>Required</span>
              </div>
              <input
                type="file" accept="image/*"
                onChange={(e) => setFrontImage(e.target.files?.[0] || null)}
                disabled={progress < 100 || isSubmitBusy}
                className={styles.fileInput}
              />
              <div className={styles.previewFrame}>
                {frontImage
                  ? <img src={URL.createObjectURL(frontImage)} alt="Front product preview" className={styles.previewImage} />
                  : <div className={styles.emptyPreview}>No front image selected</div>}
              </div>
              {frontImage && <p className={styles.fileName}>{frontImage.name}</p>}
            </div>
            <div className={styles.uploadPanel}>
              <div className={styles.uploadHeader}>
                <span className={styles.uploadTitle}>Back Image</span>
                <span className={styles.uploadHint}>Optional</span>
              </div>
              <input
                type="file" accept="image/*"
                onChange={(e) => setBackImage(e.target.files?.[0] || null)}
                disabled={progress < 100 || isSubmitBusy}
                className={styles.fileInput}
              />
              <div className={styles.previewFrame}>
                {backImage
                  ? <img src={URL.createObjectURL(backImage)} alt="Back product preview" className={styles.previewImage} />
                  : <div className={styles.emptyPreview}>No back image selected</div>}
              </div>
              {backImage && <p className={styles.fileName}>{backImage.name}</p>}
            </div>
          </div>
        </div>

        {/* Submit button — label and style change based on mode */}
        <button
          type="submit"
          disabled={
            progress < 100 ||
            generatingImage ||
            !selectedItem ||
            !frontImage
          }
          className={styles.button}
          style={{ background: '#7c3aed' }}
        >
          {generatingImage ? 'Generating Images...' : '✦ Generate Images'}
        </button>
      </form>

      
    </div>
  );
}