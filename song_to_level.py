import argparse
import random
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json
import os
import subprocess
import tempfile
import shutil
import soundfile as sf

import numpy as np
import librosa


# Output tuple format: (time_in_seconds, box_index, color)
LevelEvent = Tuple[float, int, str]


@dataclass
class Config:
    path: str
    bpm: Optional[float]
    offset: float
    quantize: str          # "off", "1/4", "1/8", "1/16"
    min_gap: float         # seconds, prevent spam
    max_events: int
    difficulty: float      # 0..1, higher => more notes
    seed: int
    pattern: str           # "spectral", "alternating", "random"
    color_mode: str        # "alternate", "energy", "random"
    stem: str              # "mix", "instrumental", "vocals", "percussive", "harmonic"
    demucs_model: str      # e.g. "htdemucs"
    no_demucs: bool        # if True, never use demucs even if stem asks for it
    timing: str            # "onsets" or "downbeats"  (NEW)


def quantize_times(times: np.ndarray, bpm: float, grid: str) -> np.ndarray:
    beat = 60.0 / bpm
    if grid == "1/4":
        step = beat
    elif grid == "1/8":
        step = beat / 2.0
    elif grid == "1/16":
        step = beat / 4.0
    else:
        return times
    return np.round(times / step) * step


def compress_min_gap(times: np.ndarray, min_gap: float) -> np.ndarray:
    if len(times) == 0:
        return times
    kept = [float(times[0])]
    for t in times[1:]:
        if float(t) - kept[-1] >= min_gap:
            kept.append(float(t))
    return np.array(kept, dtype=float)


def pick_times_by_difficulty(times: np.ndarray, strength: np.ndarray, difficulty: float, max_events: int) -> np.ndarray:
    if len(times) == 0:
        return times
    target = int(max(1, min(max_events, round(len(times) * (0.25 + 0.75 * difficulty)))))
    idx = np.argsort(strength)[::-1][:target]
    return np.sort(times[idx])


def map_boxes_spectral(y: np.ndarray, sr: int, times: np.ndarray) -> List[int]:
    if len(times) == 0:
        return []
    hop_length = 512
    cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
    frames = librosa.time_to_frames(times, sr=sr, hop_length=hop_length)
    frames = np.clip(frames, 0, len(cent) - 1)
    cent_vals = cent[frames]
    q1, q2, q3 = np.quantile(cent_vals, [0.25, 0.5, 0.75])

    boxes: List[int] = []
    for c in cent_vals:
        if c <= q1:
            boxes.append(2)  # S (bass)
        elif c <= q2:
            boxes.append(3)  # A
        elif c <= q3:
            boxes.append(1)  # D
        else:
            boxes.append(0)  # W (bright)
    return boxes


def map_boxes_alternating(n: int, seed: int) -> List[int]:
    rng = random.Random(seed)
    order = [0, 1, 2, 3]
    rng.shuffle(order)
    return [order[i % 4] for i in range(n)]


def map_boxes_random(n: int, seed: int) -> List[int]:
    rng = random.Random(seed)
    return [rng.randrange(4) for _ in range(n)]


def pick_colors(times: np.ndarray, y: np.ndarray, sr: int, mode: str, seed: int) -> List[str]:
    rng = random.Random(seed)
    if len(times) == 0:
        return []
    if mode == "alternate":
        return ["red" if i % 2 == 0 else "blue" for i in range(len(times))]
    if mode == "random":
        return ["red" if rng.random() < 0.5 else "blue" for _ in range(len(times))]

    # mode == "energy"
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    frames = librosa.time_to_frames(times, sr=sr, hop_length=hop_length)
    frames = np.clip(frames, 0, len(rms) - 1)
    e = rms[frames]
    thresh = float(np.median(e))
    return ["red" if float(val) >= thresh else "blue" for val in e]


def detect_onsets(y: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, backtrack=False, units="frames")
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    onset_frames = np.clip(onset_frames, 0, len(onset_env) - 1)
    onset_strength = onset_env[onset_frames]
    return onset_times.astype(float), onset_strength.astype(float)


def detect_downbeats_4_4(y: np.ndarray, sr: int, bpm_hint: Optional[float]) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Returns downbeat times (beat 1 of each bar) for 4/4 by:
      1) beat tracking -> beat frames
      2) taking every 4th beat as a "downbeat"
    Also returns a strength value per downbeat (from onset envelope at those beat frames)
    and the detected tempo from librosa.
    """
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # Beat tracking (tempo detection can be imperfect, but works decently for 4/4 pop/rock)
    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        start_bpm=(bpm_hint if bpm_hint is not None else 120.0),
        tightness=100
    )

    if beat_frames is None or len(beat_frames) == 0:
        return np.array([], dtype=float), np.array([], dtype=float), float(tempo)

    # Take every 4th beat as downbeat (assuming beat_frames[0] is near beat 1)
    downbeat_frames = beat_frames[::4]
    downbeat_times = librosa.frames_to_time(downbeat_frames, sr=sr).astype(float)

    downbeat_frames = np.clip(downbeat_frames, 0, len(onset_env) - 1)
    strength = onset_env[downbeat_frames].astype(float)

    return downbeat_times, strength, float(tempo)


def _ffmpeg_to_wav_if_needed(input_path: str) -> Tuple[str, Optional[str]]:
    """
    Returns (wav_path, tmpdir_or_None).
    If input is already wav, returns it unchanged.
    Uses imageio-ffmpeg bundled ffmpeg so you don't need system FFmpeg.
    """
    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".wav":
        return input_path, None

    try:
        import imageio_ffmpeg as ffm
    except ImportError as e:
        raise RuntimeError(
            "Need imageio-ffmpeg to decode mp3 without system ffmpeg: python -m pip install imageio-ffmpeg"
        ) from e

    tmpdir = tempfile.mkdtemp(prefix="song_to_level_wav_")
    wav_path = os.path.join(tmpdir, "decoded.wav")
    ffmpeg = ffm.get_ffmpeg_exe()

    cmd = [ffmpeg, "-y", "-i", input_path, "-ac", "2", "-ar", "44100", wav_path]
    subprocess.check_call(cmd)
    return wav_path, tmpdir


def _load_audio_any(path: str, sr: Optional[int], mono: bool):
    """
    Robust loading:
    - If librosa fails on mp3 due to missing system codecs, decode to wav using imageio-ffmpeg.
    """
    try:
        return librosa.load(path, sr=sr, mono=mono)
    except Exception:
        wav_path, tmpdir = _ffmpeg_to_wav_if_needed(path)
        try:
            y, sr_out = librosa.load(wav_path, sr=sr, mono=mono)
            return y, sr_out
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)


def _demucs_separate_numpy(path: str, model_name: str, want: str) -> Tuple[np.ndarray, int, str]:
    """
    Separate using Demucs Python API (no torchaudio.load, no torchcodec, no system ffmpeg required).
    want: "instrumental" or "vocals"
    Returns mono waveform y, sr, label.
    """
    import torch
    from demucs.pretrained import get_model
    from demucs.apply import apply_model

    model = get_model(model_name)
    model.eval()

    target_sr = int(model.samplerate)
    channels = int(model.audio_channels)

    y, sr = _load_audio_any(path, sr=target_sr, mono=False)

    if y.ndim == 1:
        y = np.stack([y, y], axis=0)
    if y.shape[0] != channels:
        if channels == 2 and y.shape[0] == 1:
            y = np.vstack([y, y])
        else:
            y = np.mean(y, axis=0, keepdims=True)

    wav = torch.tensor(y, dtype=torch.float32).unsqueeze(0)  # (1, C, T)

    with torch.no_grad():
        sources = apply_model(model, wav, shifts=1, split=True, overlap=0.25, progress=True)
        sources = sources[0]  # (nsrc, C, T)

    names = list(model.sources)  # e.g. ['drums', 'bass', 'other', 'vocals']
    name_to_idx = {n: i for i, n in enumerate(names)}

    if want == "vocals":
        if "vocals" not in name_to_idx:
            raise RuntimeError(f"Demucs model sources did not include vocals. sources={names}")
        out = sources[name_to_idx["vocals"]]
    else:
        idxs = [i for i, n in enumerate(names) if n != "vocals"] if "vocals" in name_to_idx else list(range(len(names)))
        out = torch.zeros_like(sources[0])
        for i in idxs:
            out = out + sources[i]

    out_np = out.cpu().numpy()  # (C, T)
    mono = np.mean(out_np, axis=0).astype(np.float32)
    return mono, target_sr, f"demucs_api:{model_name}:{want}"


def select_audio(cfg: Config) -> Tuple[np.ndarray, int, str]:
    # Original mix
    if cfg.stem == "mix":
        y, sr = _load_audio_any(cfg.path, sr=None, mono=True)
        return y, sr, "mix"

    # HPSS (no demucs)
    if cfg.stem in ("percussive", "harmonic"):
        y, sr = _load_audio_any(cfg.path, sr=None, mono=True)
        y_h, y_p = librosa.effects.hpss(y)
        if cfg.stem == "percussive":
            return y_p, sr, "percussive(hpss)"
        return y_h, sr, "harmonic(hpss)"

    # Demucs stems (optional)
    if cfg.stem in ("instrumental", "vocals"):
        if cfg.no_demucs:
            y, sr = _load_audio_any(cfg.path, sr=None, mono=True)
            return y, sr, f"mix(fallback:no-demucs requested for {cfg.stem})"

        want = "instrumental" if cfg.stem == "instrumental" else "vocals"
        return _demucs_separate_numpy(cfg.path, cfg.demucs_model, want)

    raise RuntimeError(f"Unknown --stem value: {cfg.stem}")


def main():
    ap = argparse.ArgumentParser(description="Convert a song into a rhythm-game level list (JSON).")
    ap.add_argument("path", help="Audio file path")
    ap.add_argument("--bpm", type=float, default=None, help="If set, quantization uses this BPM")
    ap.add_argument("--offset", type=float, default=0.0, help="Seconds to add to every event time")
    ap.add_argument("--quantize", choices=["off", "1/4", "1/8", "1/16"], default="1/8",
                    help="Quantize to beat grid (requires --bpm)")
    ap.add_argument("--min-gap", type=float, default=0.12, help="Minimum seconds between events")
    ap.add_argument("--max-events", type=int, default=10000, help="Maximum number of events to output")
    ap.add_argument("--difficulty", type=float, default=0.6, help="0..1 (higher => more notes)")
    ap.add_argument("--seed", type=int, default=1234, help="Random seed for patterns")
    ap.add_argument("--pattern", choices=["spectral", "alternating", "random"], default="spectral",
                    help="How to choose box lanes")
    ap.add_argument("--color-mode", choices=["alternate", "energy", "random"], default="alternate",
                    help="How to choose red/blue")
    ap.add_argument("--out", default=None, help="Output JSON path (e.g., level.json)")

    ap.add_argument("--stem", choices=["mix", "instrumental", "vocals", "percussive", "harmonic"], default="mix",
                    help="Audio source for charting")
    ap.add_argument("--demucs-model", default="htdemucs",
                    help="Demucs model name (used when --stem instrumental/vocals)")
    ap.add_argument("--save-stem", default=None, help="If set, save the selected stem to this WAV path")
    ap.add_argument("--no-demucs", action="store_true",
                    help="Disable Demucs entirely (instrumental/vocals will fall back to mix)")

    # NEW: timing mode
    ap.add_argument("--timing", choices=["onsets", "downbeats"], default="onsets",
                    help="Event timing source. 'downbeats' makes notes only on 4/4 downbeats (beat 1 each bar).")

    args = ap.parse_args()

    cfg = Config(
        path=args.path,
        bpm=args.bpm,
        offset=args.offset,
        quantize=args.quantize,
        min_gap=args.min_gap,
        max_events=args.max_events,
        difficulty=max(0.0, min(1.0, args.difficulty)),
        seed=args.seed,
        pattern=args.pattern,
        color_mode=args.color_mode,
        stem=args.stem,
        demucs_model=args.demucs_model,
        no_demucs=bool(args.no_demucs),
        timing=args.timing,
    )

    # Load chosen audio source
    y, sr, used_source = select_audio(cfg)

    if args.save_stem is not None:
        sf.write(args.save_stem, y, sr)
        print(f"Saved stem audio to: {args.save_stem}")

    detected_tempo = None

    # 1) Get raw times + strength
    if cfg.timing == "downbeats":
        times, strength, tempo = detect_downbeats_4_4(y, sr, cfg.bpm)
        detected_tempo = tempo
    else:
        times, strength = detect_onsets(y, sr)

    # 2) Thin by min gap
    times = compress_min_gap(times, cfg.min_gap)

    # If we used onsets, rebuild strength after thinning (same as before).
    # If we used downbeats, the strength is already aligned to beat frames; rebuild by nearest original downbeat time.
    if len(times) > 0:
        if cfg.timing == "downbeats":
            raw_times, raw_strength, _tempo = detect_downbeats_4_4(y, sr, cfg.bpm)
            if len(raw_times) > 0:
                idx = np.argmin(np.abs(raw_times[:, None] - times[None, :]), axis=0)
                strength = raw_strength[idx]
            else:
                strength = np.array([], dtype=float)
        else:
            raw_times, raw_strength = detect_onsets(y, sr)
            idx = np.argmin(np.abs(raw_times[:, None] - times[None, :]), axis=0)
            strength = raw_strength[idx]
    else:
        strength = np.array([], dtype=float)

    # 3) Pick subset by difficulty
    times = pick_times_by_difficulty(times, strength, cfg.difficulty, cfg.max_events)

    # 4) Quantize
    if cfg.quantize != "off":
        if cfg.bpm is None:
            # If user didn't supply bpm, but we're in downbeats mode, we can still quantize using detected tempo.
            if cfg.timing == "downbeats" and detected_tempo is not None and detected_tempo > 0:
                bpm_for_quant = float(detected_tempo)
                times = quantize_times(times, bpm_for_quant, cfg.quantize)
                times = compress_min_gap(np.unique(times), cfg.min_gap)
            else:
                print("WARNING: --quantize was set but --bpm was not provided, so quantize is ignored.")
        else:
            times = quantize_times(times, cfg.bpm, cfg.quantize)
            times = compress_min_gap(np.unique(times), cfg.min_gap)

    # 5) Apply offset
    times = times + float(cfg.offset)
    times = times[times >= 0.0]

    # 6) Choose box indices
    if cfg.pattern == "spectral":
        boxes = map_boxes_spectral(y, sr, times)
    elif cfg.pattern == "alternating":
        boxes = map_boxes_alternating(len(times), cfg.seed)
    else:
        boxes = map_boxes_random(len(times), cfg.seed)

    # Enforce: no consecutive box repeats
    rng = random.Random(cfg.seed + 9999)
    for i in range(1, len(times)):
        if boxes[i] == boxes[i - 1]:
            choices = [0, 1, 2, 3]
            choices.remove(boxes[i - 1])
            boxes[i] = rng.choice(choices)

    # 7) Choose colors
    colors = pick_colors(times, y, sr, cfg.color_mode, cfg.seed)

    # 8) Build level list
    level: List[LevelEvent] = []
    for t, b, c in zip(times, boxes, colors):
        level.append((round(float(t), 3), int(b), str(c)))

    # Save JSON
    out_path = args.out
    if out_path is None:
        base, _ = os.path.splitext(cfg.path)
        out_path = base + ".level.json"

    payload = {
        "meta": {
            "source": cfg.path,
            "audio_used": used_source,
            "bpm": cfg.bpm,
            "detected_bpm": detected_tempo,
            "time_signature": "4/4",
            "quantize": cfg.quantize,
            "offset": cfg.offset,
            "min_gap": cfg.min_gap,
            "difficulty": cfg.difficulty,
            "pattern": cfg.pattern,
            "color_mode": cfg.color_mode,
            "seed": cfg.seed,
            "stem": cfg.stem,
            "no_demucs": cfg.no_demucs,
            "timing": cfg.timing,
        },
        "level": [{"t": t, "box": b, "color": c} for (t, b, c) in level],
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nSaved JSON to: {out_path}")
    print(f"# events: {len(level)}  sr: {sr}  length_s: {len(y)/sr:.2f}  audio_used: {used_source}")


if __name__ == "__main__":
    main()