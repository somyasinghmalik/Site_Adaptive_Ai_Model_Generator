import React from "react";
import styles from "./Step2CategorySearch.module.css";
import { OPTION_LIBRARY } from "./options";

function OptionSelector({
  label,
  category,
  value,
  onModeChange,
  customValue,
  onCustomChange
}) {
  return (
    <div className={styles.optionRow}>
      <div className={styles.optionLabel}>
        {label}
      </div>

      <div className={styles.optionContent}>
        <select
          value={value}
          onChange={(e) => onModeChange(e.target.value)}
        >
          <option value="AI_SELECTED">
            AI Selected
          </option>

          <option value="CUSTOM">
            ✏️ Custom
          </option>

          {OPTION_LIBRARY[category]?.map(option => (
            <option
              key={option}
              value={option}
            >
              {option}
            </option>
          ))}
        </select>

        {value === "CUSTOM" && (
          <input
            type="text"
            placeholder={`Describe ${label.toLowerCase()}...`}
            value={customValue}
            onChange={(e) => onCustomChange(e.target.value)}
          />
        )}
      </div>
    </div>
  );
}

export default function OptionsPanel({
  options,
  setOptions,
  imageCount,
  setImageCount,
  customPoses,
  setCustomPoses
}) {
  return (
    <div className={styles.optionsPanel}>

      {Object.keys(OPTION_LIBRARY).map((category) => (
        <OptionSelector
          key={category}
          label={category.toUpperCase()}
          category={category}
          value={options[category]?.mode}
          customValue={options[category]?.custom}
          onModeChange={(mode) =>
            setOptions(prev => ({
              ...prev,
              [category]: {
                ...prev[category],
                mode
              }
            }))
          }
          onCustomChange={(custom) =>
            setOptions(prev => ({
              ...prev,
              [category]: {
                ...prev[category],
                custom
              }
            }))
          }
        />
      ))}



      {/* ----currently not displayed---- */}
      <div style={{ display: "none" }}> 
        <div className={styles.optionRow}>
          <div className={styles.optionLabel}>
            IMAGES
          </div>

          <select
            value={imageCount}
            onChange={(e) => setImageCount(Number(e.target.value))}
          >
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
            <option value={6}>6</option>
            <option value={9}>9</option>
            <option value={12}>12</option>
          </select>
        </div>

        <div className={styles.optionRow}>
          <div className={styles.optionLabel}>
            POSES
          </div>

          <select
            value={options.poses.mode}
            onChange={(e) =>
              setOptions(prev => ({
                ...prev,
                poses: {
                  mode: e.target.value
                }
              }))
            }
          >
            <option value="AI_SELECTED">
              AI Selected
            </option>

            <option value="CUSTOM">
              ✏️ Custom
            </option>
          </select>
        </div>

        {options.poses.mode === "CUSTOM" && (
          <div className={styles.poseContainer}>
            {customPoses.map((pose, index) => (
              <input
                key={index}
                type="text"
                placeholder={`Pose ${index + 1}`}
                value={pose}
                onChange={(e) => {
                  const next = [...customPoses];
                  next[index] = e.target.value;
                  setCustomPoses(next);
                }}
              />
            ))}
          </div>
        )}
      </div>
      {/* ----currently not displayed---- */}


    </div>
  );
}