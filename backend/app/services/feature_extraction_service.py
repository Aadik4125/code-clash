from __future__ import annotations

import io
from typing import Any

import librosa
import numpy as np
from scipy import stats


def _agg_stats(arr: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(arr)) if arr.size else 0.0,
        "std": float(np.std(arr)) if arr.size else 0.0,
        "var": float(np.var(arr)) if arr.size else 0.0,
        "median": float(np.median(arr)) if arr.size else 0.0,
        "skew": float(stats.skew(arr)) if arr.size else 0.0,
        "kurtosis": float(stats.kurtosis(arr)) if arr.size else 0.0,
    }


def extract_features(audio_bytes: bytes, transcript: str) -> dict[str, dict[str, Any]]:
    """Extract a broad set (~20+) of acoustic, temporal, and linguistic features.

    Returns nested dicts: `acoustic`, `temporal`, `linguistic`.
    """
    y, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000, mono=True)

    duration_sec = float(librosa.get_duration(y=y, sr=sr))

    # Short-time features
    rms = librosa.feature.rms(y=y)[0]
    zcr = librosa.feature.zero_crossing_rate(y=y)[0]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

    # Global / summary stats
    acoustic = {
        "duration_sec": duration_sec,
        "rms": _agg_stats(rms),
        "zcr": _agg_stats(zcr),
        "spectral_centroid": _agg_stats(cent),
        "spectral_bandwidth": _agg_stats(bandwidth),
        "spectral_rolloff": _agg_stats(rolloff),
        "spectral_flatness": _agg_stats(flatness),
        "spectral_contrast": {
            "mean": float(np.mean(contrast)) if contrast.size else 0.0,
            "std": float(np.std(contrast)) if contrast.size else 0.0,
        },
        "chroma": {
            "mean": [float(np.mean(chroma[i])) for i in range(chroma.shape[0])],
            "std": [float(np.std(chroma[i])) for i in range(chroma.shape[0])],
        },
        "mfcc": {
            "mean": [float(np.mean(mfcc[i])) for i in range(mfcc.shape[0])],
            "std": [float(np.std(mfcc[i])) for i in range(mfcc.shape[0])],
            "var": [float(np.var(mfcc[i])) for i in range(mfcc.shape[0])],
        },
        "spectral_contrast_bands": contrast.shape[0] if contrast.size else 0,
    }

    # Pitch / harmonic features
    try:
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        harmonic_energy = np.sum(np.abs(y_harmonic))
        total_energy = np.sum(np.abs(y))
        harmonic_ratio = float(harmonic_energy / total_energy) if total_energy > 0 else 0.0
    except Exception:
        harmonic_ratio = 0.0

    # Tempo / rhythm
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)

    temporal = {
        "speech_rate_estimate": float(max(1.0, len(transcript.split())) / max(1.0, duration_sec)),
        "tempo_bpm": float(tempo),
        "onset_count": int(len(onset_frames)),
        "onset_rate": float(len(onset_frames) / max(1.0, duration_sec)),
        "harmonic_ratio": harmonic_ratio,
    }

    # Linguistic features
    words = [w for w in transcript.split() if w.strip()]
    unique_words = len(set(w.lower() for w in words))
    avg_word_length = float(np.mean([len(w) for w in words])) if words else 0.0
    linguistic = {
        "word_count": len(words),
        "unique_word_count": unique_words,
        "lexical_diversity": float(unique_words / len(words)) if words else 0.0,
        "avg_word_length": avg_word_length,
    }

    # Derived aggregate features commonly used in analysis
    derived = {
        "mfcc_variability_mean": float(np.mean(np.var(mfcc, axis=1))),
        "rms_mean": float(np.mean(rms)) if rms.size else 0.0,
        "rms_var": float(np.var(rms)) if rms.size else 0.0,
        "zcr_mean": float(np.mean(zcr)) if zcr.size else 0.0,
        "zcr_var": float(np.var(zcr)) if zcr.size else 0.0,
        "spectral_centroid_mean": float(np.mean(cent)) if cent.size else 0.0,
        "spectral_bandwidth_mean": float(np.mean(bandwidth)) if bandwidth.size else 0.0,
        "spectral_rolloff_mean": float(np.mean(rolloff)) if rolloff.size else 0.0,
        "spectral_flatness_mean": float(np.mean(flatness)) if flatness.size else 0.0,
        "tempo": float(tempo),
    }

    # Combine into returned structure
    return {
        "acoustic": {**acoustic, **derived, "harmonic_ratio": harmonic_ratio},
        "temporal": temporal,
        "linguistic": linguistic,
    }

