"""
Comprehensive audio anomaly detection service.
Extracts raw audio from video and detects anomalous sound events.
"""
import librosa
import numpy as np
from typing import List, Dict, Tuple, Optional
import os
import subprocess
import tempfile


def extract_raw_audio_from_video(video_path: str, output_dir: Optional[str] = None) -> str:
    """
    Extract raw audio from video file and save it for analysis.
    Returns path to the extracted audio file.
    """
    # Check if file is a video
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    file_ext = os.path.splitext(video_path)[1].lower()
    
    if file_ext not in video_extensions:
        # Not a video file, return as-is
        return video_path
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        audio_filename = os.path.splitext(os.path.basename(video_path))[0] + "_audio.wav"
        audio_path = os.path.join(output_dir, audio_filename)
    else:
        # Use temporary file
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        audio_path = temp_audio.name
        temp_audio.close()
        print(f"[AUDIO EXTRACTION] Using temporary file: {audio_path}")
    
    try:
        # Use ffmpeg to extract audio with high quality settings
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-map', '0:a',  # Select first audio stream
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # WAV format
            '-ar', '44100',  # Higher sample rate for better analysis
            '-ac', '2',  # Stereo (preserve original channels)
            '-y',  # Overwrite output file
            audio_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=600  # 10 minute timeout
        )
        
        # Verify the extracted audio file exists
        if not os.path.exists(audio_path):
            raise Exception("Extracted audio file was not created")
        
        file_size = os.path.getsize(audio_path)
        if file_size < 1000:  # Less than 1KB is suspicious
            raise Exception(f"Extracted audio file is too small: {file_size} bytes")
        
        print(f"[AUDIO EXTRACTION] ✓ Extracted audio to {audio_path} ({file_size / 1024 / 1024:.2f} MB)")
        return audio_path
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        raise Exception(f"Failed to extract audio from video: {error_msg}")
    except FileNotFoundError:
        raise Exception("ffmpeg is required to extract audio from video files but was not found")


def analyze_audio_anomalies(audio_path: str) -> List[Dict]:
    """
    Comprehensive audio anomaly detection.
    Detects various types of anomalous sounds and categorizes them.
    
    Returns list of anomaly events with:
    - start_time: Start timestamp in seconds
    - end_time: End timestamp in seconds
    - category: Type of anomaly (LoudSound, SuddenChange, Silence, Distortion, etc.)
    - confidence: Confidence score (0.0 to 1.0)
    - description: Human-readable description
    - intensity: Intensity/severity of the anomaly
    """
    anomalies = []
    
    try:
        print(f"[AUDIO ANALYSIS] Loading audio from {audio_path}...")
        # Load audio with original sample rate for better analysis
        y, sr = librosa.load(audio_path, sr=None)
        duration = len(y) / sr
        
        if duration == 0:
            print("[AUDIO ANALYSIS] ⚠ Empty audio file")
            return anomalies
        
        print(f"[AUDIO ANALYSIS] Audio loaded: {duration:.2f}s, {sr}Hz, {len(y)} samples")
        
        # Convert to mono if stereo
        if len(y.shape) > 1:
            y = librosa.to_mono(y)
        
        # 1. Extract RMS energy over time
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        
        # Calculate statistics
        rms_mean = np.mean(rms)
        rms_std = np.std(rms)
        rms_max = np.max(rms)
        rms_min = np.min(rms)
        
        print(f"[AUDIO ANALYSIS] RMS stats: mean={rms_mean:.4f}, std={rms_std:.4f}, max={rms_max:.4f}, min={rms_min:.4f}")
        
        # 2. Extract spectral features
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
        
        # 3. Detect LOUD SOUNDS (gunshots, explosions, yelling)
        loud_anomalies = detect_loud_sounds(rms, rms_times, rms_mean, rms_std, rms_max, duration)
        anomalies.extend(loud_anomalies)
        print(f"[AUDIO ANALYSIS] ✓ Detected {len(loud_anomalies)} loud sound anomalies")
        
        # 4. Detect SUDDEN CHANGES (abrupt volume/energy changes)
        sudden_changes = detect_sudden_changes(rms, rms_times, rms_mean, rms_std, duration)
        anomalies.extend(sudden_changes)
        print(f"[AUDIO ANALYSIS] ✓ Detected {len(sudden_changes)} sudden change anomalies")
        
        # 5. Detect SILENCE (unusual quiet periods)
        silence_anomalies = detect_silence_anomalies(rms, rms_times, rms_mean, duration)
        anomalies.extend(silence_anomalies)
        print(f"[AUDIO ANALYSIS] ✓ Detected {len(silence_anomalies)} silence anomalies")
        
        # 6. Detect DISTORTION/CLIPPING (audio quality issues)
        distortion_anomalies = detect_distortion(y, rms_times, sr, duration)
        anomalies.extend(distortion_anomalies)
        print(f"[AUDIO ANALYSIS] ✓ Detected {len(distortion_anomalies)} distortion anomalies")
        
        # 7. Detect FREQUENCY ANOMALIES (unusual frequency content)
        frequency_anomalies = detect_frequency_anomalies(
            spectral_centroids, spectral_rolloff, zero_crossing_rate, rms_times, duration
        )
        anomalies.extend(frequency_anomalies)
        print(f"[AUDIO ANALYSIS] ✓ Detected {len(frequency_anomalies)} frequency anomalies")
        
        # Sort by start time
        anomalies.sort(key=lambda x: x['start_time'])
        
        # Filter to only include anomalies with confidence >= 0.8
        high_confidence_anomalies = [a for a in anomalies if a.get('confidence', 0.0) >= 0.8]
        
        print(f"[AUDIO ANALYSIS] ✓ Total anomalies detected: {len(anomalies)} (high confidence >= 0.8: {len(high_confidence_anomalies)})")
        
        return high_confidence_anomalies
        
    except Exception as e:
        print(f"[AUDIO ANALYSIS] ✗ Error analyzing audio: {e}")
        import traceback
        traceback.print_exc()
        return []


def detect_loud_sounds(rms: np.ndarray, rms_times: np.ndarray, rms_mean: float, 
                       rms_std: float, rms_max: float, duration: float) -> List[Dict]:
    """
    Detect loud sound anomalies (gunshots, explosions, yelling).
    Less stringent: marks sounds that are 4.5+ std above mean.
    Only high-confidence events (>=0.90) are tagged as LoudSound.
    """
    anomalies = []
    
    if len(rms) == 0 or rms_max <= 0:
        return anomalies
    
    # Less strict threshold: 4.5 std above mean, or top 1% of energy values
    threshold_statistical = rms_mean + 4.5 * rms_std
    
    # Use percentile-based threshold as primary method (top 1%)
    percentile_99 = np.percentile(rms, 99) if len(rms) > 0 else rms_max * 0.99
    percentile_95 = np.percentile(rms, 95) if len(rms) > 0 else rms_max * 0.95
    
    # Use the stricter of the two methods, but ensure it's at least 95th percentile
    threshold = max(threshold_statistical, percentile_95)
    
    # Additional requirement: must be at least 2.0x the mean energy (relaxed from 2.8)
    threshold = max(threshold, rms_mean * 2.0)
    
    # Minimum duration for loud sound (0.1 to 2.0 seconds)
    min_duration = 0.1
    max_duration = 2.0
    
    # Calculate rolling average for context comparison
    window_size = max(10, int(2.0 / (rms_times[1] - rms_times[0])) if len(rms_times) > 1 else 10)
    rolling_avg = np.convolve(rms, np.ones(window_size) / window_size, mode='same')
    
    in_loud_period = False
    loud_start = None
    
    print(f"[LOUD SOUND] Relaxed thresholds (4.5std): statistical={threshold_statistical:.4f}, percentile_99={percentile_99:.4f}, final={threshold:.4f}, mean={rms_mean:.4f}")
    
    for i, (time, energy) in enumerate(zip(rms_times, rms)):
        # Must exceed threshold AND be significantly louder than local context
        local_avg = rolling_avg[i] if i < len(rolling_avg) else rms_mean
        context_multiplier = 1.8  # Relaxed from 2.3 - must be at least 1.8x louder than local context
        
        if energy > threshold and energy > local_avg * context_multiplier:
            if not in_loud_period:
                loud_start = time
                in_loud_period = True
        else:
            if in_loud_period and loud_start is not None:
                loud_duration = time - loud_start
                if min_duration <= loud_duration <= max_duration:
                    # Calculate peak energy during this period
                    time_diff = (rms_times[1] - rms_times[0]) if len(rms_times) > 1 else 1.0
                    start_idx = max(0, i - int(loud_duration / time_diff))
                    peak_energy = np.max(rms[start_idx:i])
                    
                    # Calculate how much louder than mean and context
                    intensity_ratio = peak_energy / rms_max
                    mean_ratio = peak_energy / (rms_mean + 0.001)
                    context_ratio = peak_energy / (local_avg + 0.001)
                    
                    # Relaxed criteria: top 10% of max (0.90), 2.5x mean, 2.0x context
                    if intensity_ratio > 0.90 and mean_ratio > 2.5 and context_ratio > 2.0:
                        category = "LoudSound"
                        description = f"Loud sound detected. Duration: {loud_duration:.2f}s, {mean_ratio:.1f}x mean"
                        confidence = min(0.95, 0.75 + min(intensity_ratio - 0.90, 0.1) * 10)
                        
                        # Only include if confidence >= 0.90
                        if confidence >= 0.90:
                            anomalies.append({
                                "start_time": max(0.0, loud_start - 0.2),
                                "end_time": min(duration, time + 0.2),
                                "category": category,
                                "confidence": confidence,
                                "description": description,
                                "intensity": float(intensity_ratio)
                            })
                in_loud_period = False
                loud_start = None
    
    # Handle loud sound at end of file
    if in_loud_period and loud_start is not None:
        loud_duration = duration - loud_start
        if min_duration <= loud_duration <= max_duration:
            time_diff = (rms_times[1] - rms_times[0]) if len(rms_times) > 1 else 1.0
            peak_energy = np.max(rms[-int(loud_duration / time_diff):])
            intensity_ratio = peak_energy / rms_max
            mean_ratio = peak_energy / (rms_mean + 0.001)
            
            if intensity_ratio > 0.90 and mean_ratio > 2.5:
                confidence = min(0.95, 0.75 + min(intensity_ratio - 0.90, 0.1) * 10)
                # Only include if confidence >= 0.90
                if confidence >= 0.90:
                    anomalies.append({
                        "start_time": max(0.0, loud_start - 0.2),
                        "end_time": duration,
                        "category": "LoudSound",
                        "confidence": confidence,
                        "description": f"Loud sound at end. Duration: {loud_duration:.2f}s, {mean_ratio:.1f}x mean",
                        "intensity": float(intensity_ratio)
                    })
    
    print(f"[LOUD SOUND] Detected {len(anomalies)} loud sound events")
    return anomalies


def detect_sudden_changes(rms: np.ndarray, rms_times: np.ndarray, 
                         rms_mean: float, rms_std: float, duration: float) -> List[Dict]:
    """
    Detect EXTREME sudden energy changes (abrupt volume changes).
    Very strict: only marks changes that are dramatically different from normal.
    """
    anomalies = []
    
    if len(rms) < 2:
        return anomalies
    
    # Calculate energy changes
    energy_changes = np.diff(rms)
    
    # MUCH STRICTER threshold: 4.0 std, or top 2% of changes
    change_threshold_statistical = rms_std * 4.0
    change_threshold_percentile = np.percentile(np.abs(energy_changes), 98) if len(energy_changes) > 0 else rms_std * 4.0
    change_threshold = max(change_threshold_statistical, change_threshold_percentile)
    
    # Also require change to be at least 2x the mean energy
    change_threshold = max(change_threshold, rms_mean * 2.0)
    
    print(f"[SUDDEN CHANGE] Strict threshold: {change_threshold:.4f} (std={rms_std:.4f}, mean={rms_mean:.4f})")
    
    for i, change in enumerate(energy_changes):
        abs_change = abs(change)
        if abs_change > change_threshold:
            time = rms_times[i]
            change_ratio = abs_change / (rms_mean + 0.001)  # Avoid division by zero
            
            # Require EXTREME change: at least 3x the mean energy in a single step
            if change_ratio > 3.0:
                category = "SuddenChange"
                direction = "increase" if change > 0 else "decrease"
                # Higher confidence for larger changes
                confidence = min(0.9, 0.7 + min((change_ratio - 3.0) / 2.0, 0.2))
                
                # Only include if confidence >= 0.8
                if confidence >= 0.8:
                    anomalies.append({
                        "start_time": max(0.0, time - 0.3),
                        "end_time": min(duration, time + 0.3),
                        "category": category,
                        "confidence": confidence,
                        "description": f"EXTREME sudden energy {direction} ({change_ratio:.1f}x mean, {abs_change:.4f})",
                        "intensity": float(change_ratio)
                    })
    
    print(f"[SUDDEN CHANGE] Detected {len(anomalies)} extreme sudden changes")
    return anomalies


def detect_silence_anomalies(rms: np.ndarray, rms_times: np.ndarray, 
                             rms_mean: float, duration: float) -> List[Dict]:
    """
    Detect EXTREME silence periods (unusual quiet periods).
    Very strict: only marks periods that are dramatically quieter than normal.
    """
    anomalies = []
    
    # MUCH STRICTER silence threshold: 5% of mean or absolute 0.005
    # This ensures only EXTREMELY quiet periods are detected
    silence_threshold = max(0.005, rms_mean * 0.05)
    
    # Require longer silence periods: at least 5 seconds
    min_silence_duration = 5.0
    
    # Also check that silence is significantly quieter than surrounding context
    window_size = max(10, int(3.0 / (rms_times[1] - rms_times[0])) if len(rms_times) > 1 else 10)
    rolling_avg = np.convolve(rms, np.ones(window_size) / window_size, mode='same')
    
    print(f"[SILENCE] Strict threshold: {silence_threshold:.4f} (mean={rms_mean:.4f}), min_duration={min_silence_duration}s")
    
    in_silence = False
    silence_start = None
    
    for i, (time, energy) in enumerate(zip(rms_times, rms)):
        local_avg = rolling_avg[i] if i < len(rolling_avg) else rms_mean
        
        # Must be below threshold AND at least 5x quieter than local context
        if energy < silence_threshold and energy < local_avg * 0.2:
            if not in_silence:
                silence_start = time
                in_silence = True
        else:
            if in_silence and silence_start is not None:
                silence_duration = time - silence_start
                if silence_duration >= min_silence_duration:
                    # Calculate average energy during silence
                    time_diff = (rms_times[1] - rms_times[0]) if len(rms_times) > 1 else 1.0
                    start_idx = max(0, i - int(silence_duration / time_diff))
                    avg_silence_energy = np.mean(rms[start_idx:i]) if start_idx < i else energy
                    
                    # Must be at least 10x quieter than mean
                    quiet_ratio = rms_mean / (avg_silence_energy + 0.001)
                    if quiet_ratio > 10.0:
                        confidence = min(0.9, 0.7 + min((quiet_ratio - 10.0) / 20.0, 0.2))
                        # Only include if confidence >= 0.8
                        if confidence >= 0.8:
                            anomalies.append({
                                "start_time": max(0.0, silence_start - 0.5),
                                "end_time": min(duration, time + 0.5),
                                "category": "Silence",
                                "confidence": confidence,
                                "description": f"EXTREME silence period ({silence_duration:.1f}s, {quiet_ratio:.1f}x quieter than mean)",
                                "intensity": float(quiet_ratio / 20.0)  # Normalize to 0-1
                            })
                in_silence = False
                silence_start = None
    
    # Handle silence at end
    if in_silence and silence_start is not None:
        silence_duration = duration - silence_start
        if silence_duration >= min_silence_duration:
            time_diff = (rms_times[1] - rms_times[0]) if len(rms_times) > 1 else 1.0
            avg_silence_energy = np.mean(rms[-int(silence_duration / time_diff):]) if len(rms) > 0 else rms[-1]
            quiet_ratio = rms_mean / (avg_silence_energy + 0.001)
            
            if quiet_ratio > 10.0:
                confidence = min(0.9, 0.7 + min((quiet_ratio - 10.0) / 20.0, 0.2))
                # Only include if confidence >= 0.8
                if confidence >= 0.8:
                    anomalies.append({
                        "start_time": max(0.0, silence_start - 0.5),
                        "end_time": duration,
                        "category": "Silence",
                        "confidence": confidence,
                        "description": f"EXTREME silence at end ({silence_duration:.1f}s, {quiet_ratio:.1f}x quieter)",
                        "intensity": float(quiet_ratio / 20.0)
                    })
    
    print(f"[SILENCE] Detected {len(anomalies)} extreme silence periods")
    return anomalies


def detect_distortion(y: np.ndarray, rms_times: np.ndarray, sr: int, duration: float) -> List[Dict]:
    """
    Detect EXTREME audio distortion/clipping.
    Very strict: only marks severe clipping that indicates audio quality issues.
    """
    anomalies = []
    
    # MUCH STRICTER clipping threshold: 99% of max value (near-maximum clipping)
    clip_threshold = 0.99
    max_amplitude = np.max(np.abs(y))
    
    if max_amplitude == 0:
        return anomalies
    
    # Find samples that are extremely close to maximum (severe clipping)
    clipping_samples = np.where(np.abs(y) > max_amplitude * clip_threshold)[0]
    
    if len(clipping_samples) > 0:
        # Group consecutive clipping samples
        clipping_times = librosa.samples_to_time(clipping_samples, sr=sr)
        
        # Find clusters of clipping - require more samples for a cluster
        clusters = []
        current_cluster = [clipping_times[0]]
        
        for time in clipping_times[1:]:
            if time - current_cluster[-1] < 0.05:  # Within 50ms (tighter grouping)
                current_cluster.append(time)
            else:
                # Require at least 50 samples (more strict)
                if len(current_cluster) > 50:
                    clusters.append((current_cluster[0], current_cluster[-1]))
                current_cluster = [time]
        
        if len(current_cluster) > 50:
            clusters.append((current_cluster[0], current_cluster[-1]))
        
        print(f"[DISTORTION] Found {len(clusters)} clipping clusters from {len(clipping_samples)} samples")
        
        for start_time, end_time in clusters:
            duration_clip = end_time - start_time
            # Require at least 100ms of clipping (more strict)
            if duration_clip > 0.1:
                # Calculate percentage of samples that are clipping
                start_sample = librosa.time_to_samples(start_time, sr=sr)
                end_sample = librosa.time_to_samples(end_time, sr=sr)
                clip_percentage = len(clipping_samples[(clipping_samples >= start_sample) & (clipping_samples <= end_sample)]) / max(1, end_sample - start_sample)
                
                # Only mark if >50% of samples in this period are clipping
                if clip_percentage > 0.5:
                    confidence = min(0.95, 0.8 + min(duration_clip * 1.0, 0.15))
                    # Only include if confidence >= 0.8
                    if confidence >= 0.8:
                        anomalies.append({
                            "start_time": max(0.0, start_time - 0.1),
                            "end_time": min(duration, end_time + 0.1),
                            "category": "Distortion",
                            "confidence": confidence,
                            "description": f"SEVERE audio clipping/distortion ({duration_clip:.2f}s, {clip_percentage:.1%} clipped)",
                            "intensity": float(clip_percentage)
                        })
    
    print(f"[DISTORTION] Detected {len(anomalies)} severe distortion events")
    return anomalies


def detect_frequency_anomalies(spectral_centroids: np.ndarray, spectral_rolloff: np.ndarray,
                               zero_crossing_rate: np.ndarray, rms_times: np.ndarray, 
                               duration: float) -> List[Dict]:
    """
    Detect EXTREME frequency-based anomalies (unusual frequency content).
    Very strict: only marks frequency content that is dramatically different from normal.
    Extreme anomalies (4+ std) are also tagged as LoudSound.
    """
    anomalies = []
    
    if len(spectral_centroids) == 0:
        return anomalies
    
    # Calculate statistics
    centroid_mean = np.mean(spectral_centroids)
    centroid_std = np.std(spectral_centroids)
    rolloff_mean = np.mean(spectral_rolloff)
    rolloff_std = np.std(spectral_rolloff)
    zcr_mean = np.mean(zero_crossing_rate)
    zcr_std = np.std(zero_crossing_rate)
    
    # MUCH STRICTER thresholds: 3.5 std deviations (instead of 2)
    centroid_high_threshold = centroid_mean + 3.5 * centroid_std
    centroid_low_threshold = centroid_mean - 3.5 * centroid_std
    rolloff_threshold = rolloff_mean + 3.5 * rolloff_std
    zcr_threshold = zcr_mean + 3.5 * zcr_std
    
    print(f"[FREQUENCY] Strict thresholds: centroid={centroid_low_threshold:.1f}-{centroid_high_threshold:.1f}, rolloff>{rolloff_threshold:.1f}, zcr>{zcr_threshold:.4f}")
    
    # Group nearby anomalies together (within 0.5 seconds)
    anomaly_groups = []
    current_group = None
    
    for i, (time, centroid, rolloff, zcr) in enumerate(zip(rms_times, spectral_centroids, spectral_rolloff, zero_crossing_rate)):
        is_anomaly = False
        anomaly_score = 0
        description_parts = []
        max_deviation = 0.0
        
        # Check for EXTREME high frequency anomalies (3.5 std)
        if centroid > centroid_high_threshold:
            is_anomaly = True
            anomaly_score += 1
            deviation = (centroid - centroid_mean) / (centroid_std + 0.001)
            max_deviation = max(max_deviation, deviation)
            description_parts.append(f"EXTREME high frequency ({deviation:.1f} std)")
        
        # Check for EXTREME low frequency anomalies (3.5 std)
        if centroid < centroid_low_threshold:
            is_anomaly = True
            anomaly_score += 1
            deviation = (centroid_mean - centroid) / (centroid_std + 0.001)
            max_deviation = max(max_deviation, deviation)
            description_parts.append(f"EXTREME low frequency ({deviation:.1f} std)")
        
        # Check for EXTREME spectral rolloff
        if rolloff > rolloff_threshold:
            is_anomaly = True
            anomaly_score += 1
            deviation = (rolloff - rolloff_mean) / (rolloff_std + 0.001)
            max_deviation = max(max_deviation, deviation)
            description_parts.append(f"EXTREME spectral rolloff ({deviation:.1f} std)")
        
        # Check for EXTREME zero crossing rate (indicates severe noise or distortion)
        if zcr > zcr_threshold:
            is_anomaly = True
            anomaly_score += 1
            deviation = (zcr - zcr_mean) / (zcr_std + 0.001)
            max_deviation = max(max_deviation, deviation)
            description_parts.append(f"EXTREME zero crossing rate ({deviation:.1f} std)")
        
        # Only mark if multiple indicators OR single very extreme indicator (4+ std)
        if is_anomaly and (anomaly_score >= 2 or any("EXTREME" in desc for desc in description_parts)):
            if current_group is None or time - current_group['end_time'] > 0.5:
                # Start new group
                if current_group is not None:
                    anomaly_groups.append(current_group)
                current_group = {
                    'start_time': time,
                    'end_time': time,
                    'descriptions': description_parts,
                    'score': anomaly_score,
                    'max_deviation': max_deviation
                }
            else:
                # Extend current group
                current_group['end_time'] = time
                current_group['descriptions'].extend(description_parts)
                current_group['score'] = max(current_group['score'], anomaly_score)
                current_group['max_deviation'] = max(current_group['max_deviation'], max_deviation)
    
    if current_group is not None:
        anomaly_groups.append(current_group)
    
    # Create anomalies from groups
    for group in anomaly_groups:
        duration_anomaly = group['end_time'] - group['start_time']
        if duration_anomaly > 0.1:  # At least 100ms
            unique_descriptions = list(set(group['descriptions']))[:3]  # Limit to 3 unique
            confidence = min(0.9, 0.75 + min(group['score'] * 0.05, 0.15))
            
            # Only include if confidence >= 0.8
            if confidence >= 0.8:
                # Determine if this should also be tagged as LoudSound
                # Criteria: (score >= 3 OR max_deviation >= 4.0) AND confidence >= 0.90
                is_loud = (group['score'] >= 3 or group['max_deviation'] >= 4.0) and confidence >= 0.90
                
                if is_loud:
                    # Add as both FrequencyAnomaly AND LoudSound
                    categories = ["FrequencyAnomaly", "LoudSound"]
                else:
                    categories = ["FrequencyAnomaly"]
                
                anomalies.append({
                    "start_time": max(0.0, group['start_time'] - 0.2),
                    "end_time": min(duration, group['end_time'] + 0.2),
                    "category": categories,
                    "confidence": confidence,
                    "description": f"EXTREME frequency anomaly: {', '.join(unique_descriptions)}",
                    "intensity": float(min(group['score'] / 4.0, 1.0))
                })
    
    print(f"[FREQUENCY] Detected {len(anomalies)} extreme frequency anomalies")
    return anomalies

