// src/App.jsx
import React, { useState } from 'react';
import Step1UrlInput from './components/Step1UrlInput';
import Step2CategorySearch from './components/Step2CategorySearch';
import Step3DisplayPrompt from './components/Step3DisplayPrompt';

export default function App() {
  const [step, setStep] = useState(1);
  const [targetUrl, setTargetUrl] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [generatedImages, setGeneratedImages] = useState([]);

  const handleUrlSubmitted = (url) => {
    setTargetUrl(url);
    setStep(2);
  };

  const handleBackToUrlInput = () => {
    setStep(1);
    setSearchQuery('');
    setGeneratedPrompt('');
    setGeneratedImages([]);
  };

  const handleSearchCompleted = (
    query,
    promptResult,
    images = []
  ) => {
    setSearchQuery(query);
    setGeneratedPrompt(promptResult);
    setGeneratedImages(images);
    setStep(3);
  };

  // Navigates back to category searching while locking in the current brand data
  const handleGoBackToSearch = () => {
    setSearchQuery('');
    setGeneratedPrompt('');
    setGeneratedImages([]);
    setStep(2); // Retains targetUrl, updates layout view back to Step 2
  };

  return (
    <div className="app-container">
      <div className="app-card-wrapper">
        {step === 1 && (
          <Step1UrlInput onConfigured={handleUrlSubmitted} />
        )}
        
        {step === 2 && (
          <Step2CategorySearch
            targetUrl={targetUrl}
            onSearchComplete={handleSearchCompleted}
            onBack={handleBackToUrlInput}
          />
        )}
        
        {step === 3 && (
          <Step3DisplayPrompt 
            searchQuery={searchQuery} 
            resultPrompt={generatedPrompt} 
            generatedImages={generatedImages}
            onBackToSearch={handleGoBackToSearch} // Passed down to handle the screen shift
          />
        )}
      </div>
    </div>
  );
}