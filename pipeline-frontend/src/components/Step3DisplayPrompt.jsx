import React from 'react';
import styles from './Step3DisplayPrompt.module.css';

export default function Step3DisplayPrompt({ searchQuery, resultPrompt, generatedImages, onBackToSearch }) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <span className={styles.badge}>Analysis Output Ready</span>
        <h2 className={styles.title}>Extracted Archetype Blueprint</h2>
        <p className={styles.queryDisplay}>Active Filter: <span>"{searchQuery}"</span></p>
      </div>

      <div className={styles.promptSection}>
        <label className={styles.label}>Target Gemini Structured Tag Output</label>
        <div className={styles.terminal} style={{ whiteSpace: 'pre-wrap' }}>
          {resultPrompt ? resultPrompt : "// No structural description models matched your search query rules safely."}
        </div>
      </div>

      <div className={styles.canvasPlaceholder}>
        <p className={styles.placeholderTitle}>
          Generated Images
        </p>

        {generatedImages && generatedImages.length > 0 ? (
          <div className={styles.imageGrid}>
            {generatedImages.map((img, index) => (
              <div
                key={index}
                className={styles.imageCard}
              >
                <img
                  src={img}
                  alt={`Generated ${index + 1}`}
                  className={styles.generatedImage}
                />

                <button
                  className={styles.downloadButton}
                  onClick={async () => {
                    try {
                      const response = await fetch(img);

                      const blob = await response.blob();

                      const blobUrl = window.URL.createObjectURL(blob);

                      const link = document.createElement("a");
                      link.href = blobUrl;
                      link.download = `generated-image-${index + 1}.jpg`;

                      document.body.appendChild(link);
                      link.click();
                      link.remove();

                      window.URL.revokeObjectURL(blobUrl);
                    } catch (err) {
                      console.error(err);
                      alert("Failed to download image");
                    }
                  }}
                >
                  Download Image {index + 1}
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className={styles.placeholderBody}>
            No generated images available.
          </p>
        )}
      </div>

      {/* Explicitly fires the step-back function */}
      <button onClick={onBackToSearch} className={styles.resetButton}>
        Back to Category Search
      </button>
    </div>
  );
}