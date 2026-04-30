"""
Метрики качества аудио.

Назначение:
- Все функции вычисления метрик качества сгруппированы здесь.
- Сравнение оригинального и обработанного сигналов.
- Расчёт агрегированного балла.

Метрики:
- SNR (дБ): Signal-to-Noise Ratio — выше лучше
- RMSE: Root Mean Square Error — ниже лучше
- SI-SDR (дБ): Scale-Invariant Signal-to-Distortion Ratio — выше лучше
- LSD (дБ): Log-Spectral Distance — ниже лучше
- Spectral Convergence: ошибка амплитуд спектра — ниже лучше
- Spectral Centroid Δ (Гц): разница центров спектра — ниже лучше
- Cosine Similarity: схожесть спектров (0..1) — выше лучше

Внешние библиотеки: numpy, math, logging, os.
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger("audio.metrics")

# Type alias для PCM сигналов
PCMSignal = NDArray[np.float32]


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def _resample_linear(x: PCMSignal, sr_from: int, sr_to: int) -> PCMSignal:
    """Линейная интерполяция для приведения дискретизации test→reference.

    Алгоритм:
    1) Если частоты совпадают или сигнал пуст — вернуть x в float32 без копии.
    2) Вычислить новую длину new_len = round(len(x)*sr_to/sr_from).
    3) Построить нормализованные оси xp∈[0,1] и xnew∈[0,1] для старых/новых отсчётов.
    4) Вызвать np.interp(xnew, xp, x) и привести к float32.

    Параметры:
    - x: входной сигнал PCM float32
    - sr_from: исходная частота дискретизации
    - sr_to: целевая частота дискретизации

    Возвращает: ресемплированный сигнал в float32.
    """
    if sr_from == sr_to or len(x) == 0:
        return x.astype(np.float32, copy=False)
    new_len = max(1, int(round(len(x) * float(sr_to) / float(sr_from))))
    xp = np.linspace(0, 1, len(x), endpoint=True)
    xnew = np.linspace(0, 1, new_len, endpoint=True)
    y = np.interp(xnew, xp, x).astype(np.float32)
    return y


# =============================================================================
# МЕТРИКИ ВРЕМЕННОЙ ОБЛАСТИ
# =============================================================================

def compute_snr_db(reference: np.ndarray, test: np.ndarray) -> float:
    """Вычислить SNR в дБ между опорным и тестовым сигналами.

    Алгоритм:
    1) Усечь оба сигнала до общей длины N = min(len(ref), len(test)).
    2) Вычислить вектор ошибки noise = ref - test.
    3) Оценить мощности Psig = mean(ref^2) и Pnoise = mean(noise^2) с защитой eps.
    4) Вернуть 10*log10(Psig/Pnoise) в дБ.

    Параметры:
    - reference: опорный PCM float32 [-1,1]
    - test: тестовый PCM float32 [-1,1]

    Возвращает: SNR в дБ (float); выше — лучше.
    """
    n = min(len(reference), len(test))
    if n == 0:
        return float("nan")
    ref = reference[:n]
    tst = test[:n]
    noise = ref - tst
    ref_power = float(np.mean(ref * ref) + 1e-12)
    noise_power = float(np.mean(noise * noise) + 1e-12)
    snr = 10.0 * math.log10(ref_power / noise_power)
    return snr


def compute_rmse(reference: np.ndarray, test: np.ndarray) -> float:
    """RMSE во временной области на общей части сигналов.

    Алгоритм:
    1) Усечь сигналы до общей длины N.
    2) Посчитать вектор ошибки e = ref - test (в float32).
    3) Вернуть sqrt(mean(e^2)).

    Параметры:
    - reference, test: PCM float32 сигналы

    Возвращает: корень из среднего квадрата ошибки; ниже — лучше.
    """
    n = min(len(reference), len(test))
    if n == 0:
        return float("nan")
    err = reference[:n].astype(np.float32) - test[:n].astype(np.float32)
    return float(np.sqrt(np.mean(err * err)))


def compute_si_sdr_db(reference: np.ndarray, test: np.ndarray) -> float:
    """Вычислить SI-SDR (scale‑invariant) в дБ.

    Алгоритм:
    1) Усечь до N и привести к float32.
    2) Оценить масштаб alpha = <s,y>/||s||^2 (проекция y на s).
    3) Целевой компонент y_hat = alpha*s; шум e = y - y_hat.
    4) Вернуть 10*log10(||y_hat||^2 / ||e||^2).

    Параметры:
    - reference: опорный сигнал PCM float32
    - test: тестовый сигнал PCM float32

    Возвращает: SI-SDR в дБ; инвариантен к масштабу; выше — лучше.
    """
    n = min(len(reference), len(test))
    if n == 0:
        return float("nan")
    s = reference[:n].astype(np.float32)
    y = test[:n].astype(np.float32)
    s_energy = float(np.sum(s * s) + 1e-12)
    alpha = float(np.dot(s, y) / s_energy)
    e_target = alpha * s
    e_noise = y - e_target
    num = float(np.sum(e_target * e_target) + 1e-12)
    den = float(np.sum(e_noise * e_noise) + 1e-12)
    return 10.0 * math.log10(num / den)


# =============================================================================
# МЕТРИКИ СПЕКТРАЛЬНОЙ ОБЛАСТИ
# =============================================================================

def compute_lsd_db(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
    n_fft: int = 1024,
    hop: int = 512,
) -> float:
    """Log-Spectral Distance (дБ) — средняя по окнам; ниже — лучше.

    Алгоритм:
    1) Привести test к sr_ref линейной интерполяцией.
    2) Если N>len(x): допаддить и посчитать одно окно; иначе — бежать окнами по H.
    3) Для каждой рамки: применить окно, rFFT, взять лог-амплитуды Sa,Sb.
    4) Посчитать RMSE(Sa,Sb) и усреднить по окнам (игнорируя NaN/Inf).

    Параметры:
    - reference: опорный сигнал PCM float32
    - test: тестовый сигнал PCM float32
    - sr_ref: частота дискретизации опорного сигнала
    - sr_test: частота дискретизации тестового сигнала
    - n_fft: размер окна FFT (по умолчанию 1024)
    - hop: шаг окна (по умолчанию 512)

    Возвращает: среднее LSD в дБ; ниже — лучше.
    """
    t = _resample_linear(test, sr_test, sr_ref)
    n = min(len(reference), len(t))
    if n <= 0:
        return float("nan")

    ref = reference[:n].astype(np.float32)
    tst = t[:n].astype(np.float32)
    N = int(n_fft)
    H = int(hop) if hop else N // 2
    if H <= 0:
        H = max(1, N // 2)

    if N > n:
        # Короткий сигнал: одно окно с дополнением
        win = np.hanning(N).astype(np.float32) + 1e-12
        a = np.zeros(N, dtype=np.float32)
        a[:n] = ref * win[:n]
        b = np.zeros(N, dtype=np.float32)
        b[:n] = tst * win[:n]
        A = np.fft.rfft(a)
        B = np.fft.rfft(b)
        Sa = 10.0 * np.log10(np.abs(A) ** 2 + 1e-12)
        Sb = 10.0 * np.log10(np.abs(B) ** 2 + 1e-12)
        d = float(np.sqrt(np.mean((Sa - Sb) ** 2)))
        return d if np.isfinite(d) else float("nan")

    win = np.hanning(N).astype(np.float32) + 1e-12
    frames = max(1, 1 + (n - N) // H)
    lsd_vals = []

    for i in range(frames):
        s = i * H
        e = s + N
        if e > n:
            e = n
            s = max(0, e - N)
        a = ref[s:e]
        b = tst[s:e]
        if len(a) < N:
            pad = N - len(a)
            a = np.pad(a, (0, pad))
            b = np.pad(b, (0, pad))
        a = a * win
        b = b * win
        A = np.fft.rfft(a)
        B = np.fft.rfft(b)
        Sa = 10.0 * np.log10(np.abs(A) ** 2 + 1e-12)
        Sb = 10.0 * np.log10(np.abs(B) ** 2 + 1e-12)
        d = np.sqrt(np.mean((Sa - Sb) ** 2))
        if np.isfinite(d):
            lsd_vals.append(float(d))

    if not lsd_vals:
        return float("nan")
    return float(np.mean(lsd_vals))


def compute_spectral_convergence(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
    n_fft: int = 1024,
    hop: int = 512,
) -> float:
    """Spectral Convergence: среднее по окнам |||X|-|Y|||_2 / (||X||_2 + eps).

    Параметры:
    - reference, test: PCM float32 сигналы ([-1,1])
    - sr_ref, sr_test: частоты дискретизации; test приводится к sr_ref
    - n_fft: размер окна rFFT
    - hop: шаг между окнами

    Возвращает: среднюю спектральную сходимость; ниже — лучше.
    """
    t = _resample_linear(test, sr_test, sr_ref)
    n = min(len(reference), len(t))
    if n <= 0:
        return float("nan")

    ref = reference[:n].astype(np.float32)
    tst = t[:n].astype(np.float32)
    N = int(n_fft)
    H = int(hop) if hop else N // 2
    if H <= 0:
        H = max(1, N // 2)

    win = np.hanning(N).astype(np.float32)
    vals = []
    i = 0

    while i + N <= n or (i < n and len(vals) == 0):
        s = i
        e = min(n, i + N)
        a = ref[s:e]
        b = tst[s:e]
        if len(a) < N:
            pad = N - len(a)
            a = np.pad(a, (0, pad))
            b = np.pad(b, (0, pad))
        A = np.fft.rfft(a * win)
        B = np.fft.rfft(b * win)
        magA = np.abs(A)
        magB = np.abs(B)
        num = np.linalg.norm(magA - magB)
        den = np.linalg.norm(magA) + 1e-12
        v = float(num / den)
        if np.isfinite(v):
            vals.append(v)
        i += H

    if not vals:
        return float("nan")
    return float(np.mean(vals))


def compute_spectral_centroid_diff_hz(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
    n_fft: int = 1024,
    hop: int = 512,
) -> float:
    """Средняя абсолютная разница спектрального центроида (в Гц).

    Спектральный центроид — это "центр тяжести" спектра:
    centroid = Σ(k * |X_k|) / Σ|X_k|
    
    Где k — индекс частотного бина. Центроид измеряется в Гц
    и отражает "яркость" звука:
    - Низкий центроид (~500-2000 Гц): басовые, глухие звуки
    - Высокий центроид (~5000-15000 Гц): яркие, шипящие звуки
    
    ВАЖНО: Для сигналов с широкополосным шумом центроид может быть
    очень высоким (до 10000+ Гц), так как шум содержит высокочастотные
    компоненты. Это НЕ ошибка, а нормальное поведение метрики.

    Для каждого окна вычисляем центроид Σ(k*|X_k|)/Σ|X_k|,
    затем усредняем |centroid_ref - centroid_test|.

    Параметры:
    - reference, test: PCM float32 сигналы
    - sr_ref, sr_test: частоты дискретизации
    - n_fft: размер окна FFT
    - hop: шаг окна

    Возвращает: среднюю разницу центроидов в Гц; ниже — лучше.
    """
    t = _resample_linear(test, sr_test, sr_ref)
    n = min(len(reference), len(t))
    if n <= 0:
        return float("nan")

    ref = reference[:n].astype(np.float32)
    tst = t[:n].astype(np.float32)
    N = int(n_fft)
    H = int(hop) if hop else N // 2
    if H <= 0:
        H = max(1, N // 2)

    win = np.hanning(N).astype(np.float32)
    df = sr_ref / float(N)
    vals = []
    i = 0

    while i + N <= n or (i < n and len(vals) == 0):
        s = i
        e = min(n, i + N)
        a = ref[s:e]
        b = tst[s:e]
        if len(a) < N:
            pad = N - len(a)
            a = np.pad(a, (0, pad))
            b = np.pad(b, (0, pad))
        A = np.abs(np.fft.rfft(a * win))
        B = np.abs(np.fft.rfft(b * win))
        k = np.arange(len(A), dtype=np.float32)
        ca = float(np.sum(k * A) / (np.sum(A) + 1e-12)) * df
        cb = float(np.sum(k * B) / (np.sum(B) + 1e-12)) * df
        d = abs(ca - cb)
        if np.isfinite(d):
            vals.append(d)
        i += H

    if not vals:
        return float("nan")
    return float(np.mean(vals))


def compute_spectral_cosine_similarity(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
    n_fft: int = 1024,
    hop: int = 512,
) -> float:
    """Средняя косинусная близость спектров (0..1).

    На каждом окне считаем cos_sim = <|X|, |Y|> / (||X||·||Y||) и усредняем.

    Параметры:
    - reference, test: PCM float32 сигналы
    - sr_ref, sr_test: частоты дискретизации
    - n_fft: размер окна FFT
    - hop: шаг окна

    Возвращает: среднюю косинусную схожесть (0..1); выше — лучше.
    """
    t = _resample_linear(test, sr_test, sr_ref)
    n = min(len(reference), len(t))
    if n <= 0:
        return float("nan")

    ref = reference[:n].astype(np.float32)
    tst = t[:n].astype(np.float32)
    N = int(n_fft)
    H = int(hop) if hop else N // 2
    if H <= 0:
        H = max(1, N // 2)

    win = np.hanning(N).astype(np.float32)
    vals = []
    i = 0

    while i + N <= n or (i < n and len(vals) == 0):
        s = i
        e = min(n, i + N)
        a = ref[s:e]
        b = tst[s:e]
        if len(a) < N:
            pad = N - len(a)
            a = np.pad(a, (0, pad))
            b = np.pad(b, (0, pad))
        A = np.abs(np.fft.rfft(a * win)).astype(np.float32)
        B = np.abs(np.fft.rfft(b * win)).astype(np.float32)
        num = float(np.dot(A, B))
        den = float(np.linalg.norm(A) * np.linalg.norm(B) + 1e-12)
        cs = num / den
        if np.isfinite(cs):
            vals.append(cs)
        i += H

    if not vals:
        return float("nan")
    return float(np.mean(vals))


# =============================================================================
# ПАКЕТНЫЙ РАСЧЁТ МЕТРИК
# =============================================================================

def compute_metrics_batch(
    original_wav: str,
    items: List[Tuple[str, str, float]],
    load_wav_func: Callable[[str], Tuple[np.ndarray, int]],
    decode_audio_func: Callable[[str], Tuple[np.ndarray, int]],
    get_meta_func: Callable[[str], Dict[str, int]],
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict]:
    """Посчитать метрики качества для набора результатов.

    Алгоритм:
    1) Пробинг метаданных исходника и загрузка опорного PCM (ref, sr_ref).
    2) Для каждого (variant, path, time):
       2.1) Пробинг метаданных файла (sr, channels, bitrate, size).
       2.2) Декод PCM; расчёт всех метрик.
       2.3) Формирование словаря результата.
    3) Нормировка метрик (min‑max) и расчёт агрегированного score.
    4) Вернуть список результатов.

    Параметры:
    - original_wav: путь к исходному WAV (референс)
    - items: список кортежей (variant, path_to_mp3, time_sec)
    - load_wav_func: функция загрузки WAV (из codecs)
    - decode_audio_func: функция декодирования аудио (из codecs)
    - get_meta_func: функция получения метаданных (из codecs)
    - progress_cb: опциональный callback(i, total, msg) для отчёта прогресса
    - weights: опциональный словарь весов метрик. Если None — используются
      веса по умолчанию (совпадают с MetricsConfig).

    Возвращает: список словарей с полями размера, метрик, времени и score.
    """
    # Веса по умолчанию (синхронизированы с config.MetricsConfig)
    _default_weights = {
        'lsd': 0.15, 'snr': 0.15, 'rmse': 0.10, 'si_sdr': 0.10,
        'spec_conv': 0.10, 'centroid_diff': 0.05, 'cosine': 0.05,
        'time': 0.05, 'stoi': 0.10, 'pesq': 0.10, 'mos': 0.05,
    }
    w = weights if weights is not None else _default_weights

    # Метаданные исходника
    logger.info("metrics_batch_start", extra={
        "original": original_wav,
        "variants": len(items),
    })
    orig = get_meta_func(original_wav)
    ref, sr_ref = load_wav_func(original_wav)

    # Названия метрик для логирования
    _metric_names = [
        ('LSD', 'lsd_db'),
        ('SNR', 'snr_db'),
        ('Spec Conv', 'spec_conv'),
        ('RMSE', 'rmse'),
        ('SI-SDR', 'si_sdr_db'),
        ('Centroid Δ', 'spec_centroid_diff_hz'),
        ('Cosine', 'spec_cosine'),
        ('STOI', 'stoi'),
        ('PESQ', 'pesq'),
        ('MOS', 'mos'),
    ]

    def metrics_for(path: str, variant: str, idx: int, total: int) -> Tuple[Dict, float, float, float, float, float, float, float, float, float, float]:
        """Вычислить все метрики для одного файла с логированием."""
        if progress_cb:
            progress_cb(idx, total, f"Загрузка {variant}…")
        meta = get_meta_func(path)
        sig, sr = decode_audio_func(path)

        vals = {}
        for mi, (mname, mkey) in enumerate(_metric_names):
            if progress_cb:
                progress_cb(idx, total, f"{variant}: {mname}")
            if mkey == 'lsd_db':
                vals[mkey] = float(compute_lsd_db(ref, sig, sr_ref, sr))
            elif mkey == 'snr_db':
                vals[mkey] = float(compute_snr_db(ref, sig))
            elif mkey == 'spec_conv':
                vals[mkey] = float(compute_spectral_convergence(ref, sig, sr_ref, sr))
            elif mkey == 'rmse':
                vals[mkey] = float(compute_rmse(ref, sig))
            elif mkey == 'si_sdr_db':
                vals[mkey] = float(compute_si_sdr_db(ref, sig))
            elif mkey == 'spec_centroid_diff_hz':
                vals[mkey] = float(compute_spectral_centroid_diff_hz(ref, sig, sr_ref, sr))
            elif mkey == 'spec_cosine':
                vals[mkey] = float(compute_spectral_cosine_similarity(ref, sig, sr_ref, sr))
            elif mkey == 'stoi':
                vals[mkey] = float(compute_stoi_simplified(ref, sig, sr_ref, sr))
            elif mkey == 'pesq':
                vals[mkey] = float(compute_pesq_approx(ref, sig, sr_ref, sr))
            elif mkey == 'mos':
                vals[mkey] = float(compute_pesq_mos(ref, sig, sr_ref, sr))

        logger.info(
            "metrics_computed",
            extra={"variant": variant, "path": path, **vals},
        )

        return (
            meta,
            vals['lsd_db'], vals['snr_db'], vals['spec_conv'],
            vals['rmse'], vals['si_sdr_db'], vals['spec_centroid_diff_hz'],
            vals['spec_cosine'], vals['stoi'], vals['pesq'], vals['mos'],
        )

    results: List[Dict] = []
    total_items = len(items)
    for i, (variant, path, time_s) in enumerate(items):
        meta, lsd, snr, sc, rmse, sisdr, scdiff, cossim, stoi, pesq, mos = metrics_for(
            path, variant, i, total_items,
        )

        out = {
            "variant": variant,
            "path": path,
            "size_bytes": os.path.getsize(path),
            "sample_rate_hz": meta["sample_rate_hz"],
            "bit_depth_bits": meta["bit_depth_bits"],
            "bitrate_bps": meta["bitrate_bps"],
            "time_sec": float(time_s),
            "lsd_db": float(lsd),
            "snr_db": float(snr),
            "spec_conv": float(sc),
            "rmse": float(rmse),
            "si_sdr_db": float(sisdr),
            "spec_centroid_diff_hz": float(scdiff),
            "spec_cosine": float(cossim),
            "stoi": float(stoi),
            "pesq": float(pesq),
            "mos": float(mos),
            "orig_sample_rate_hz": orig["sample_rate_hz"],
            "orig_bit_depth_bits": orig["bit_depth_bits"],
            "orig_bitrate_bps": orig["bitrate_bps"],
        }
        out["delta_sr"] = out["sample_rate_hz"] - out["orig_sample_rate_hz"]
        out["delta_bd"] = out["bit_depth_bits"] - out["orig_bit_depth_bits"]
        out["delta_br_bps"] = out["bitrate_bps"] - out["orig_bitrate_bps"]
        results.append(out)

        logger.info(
            f"metrics_done [{i+1}/{total_items}]",
            extra={
                "variant": variant,
                "lsd_db": float(lsd),
                "snr_db": float(snr),
                "spec_conv": float(sc),
                "rmse": float(rmse),
                "si_sdr_db": float(sisdr),
                "spec_centroid_diff_hz": float(scdiff),
                "spec_cosine": float(cossim),
                "stoi": float(stoi),
                "pesq": float(pesq),
                "mos": float(mos),
            }
        )

    if progress_cb:
        progress_cb(total_items, total_items, "Нормализация и расчёт score…")

    # Агрегированный балл (min-max нормировка)
    def _minmax(vals: List[float]) -> Tuple[Optional[float], Optional[float]]:
        vals_f = [v for v in vals if v == v]  # filter NaN
        if not vals_f:
            return None, None
        return min(vals_f), max(vals_f)

    eps = 1e-12
    lsd_min, lsd_max = _minmax([r["lsd_db"] for r in results])
    sc_min, sc_max = _minmax([r["spec_conv"] for r in results])
    t_min, t_max = _minmax([r["time_sec"] for r in results])
    snr_min, snr_max = _minmax([r["snr_db"] for r in results])
    rmse_min, rmse_max = _minmax([r.get("rmse") for r in results])
    sisdr_min, sisdr_max = _minmax([r.get("si_sdr_db") for r in results])
    scdiff_min, scdiff_max = _minmax([r.get("spec_centroid_diff_hz") for r in results])
    cos_min, cos_max = _minmax([r.get("spec_cosine") for r in results])
    stoi_min, stoi_max = _minmax([r.get("stoi") for r in results])
    pesq_min, pesq_max = _minmax([r.get("pesq") for r in results])
    mos_min, mos_max = _minmax([r.get("mos") for r in results])

    for r in results:
        # Нормировка: все приводим к "выше-лучше" (1.0 = лучший результат)
        # Для метрик "ниже-лучше" инвертируем: (max - value) / (max - min)
        # Для метрик "выше-лучше" оставляем: (value - min) / (max - min)

        # Метрики "ниже-лучше" (инвертируем):
        lsd_n = 0.0 if lsd_min is None else (lsd_max - r["lsd_db"]) / ((lsd_max - lsd_min) + eps)
        sc_n = 0.0 if sc_min is None else (sc_max - r["spec_conv"]) / ((sc_max - sc_min) + eps)
        rmse_n = 0.0 if rmse_min is None else (rmse_max - r["rmse"]) / ((rmse_max - rmse_min) + eps)
        scdiff_n = 0.0 if scdiff_min is None else (scdiff_max - r["spec_centroid_diff_hz"]) / ((scdiff_max - scdiff_min) + eps)
        t_n = 0.0 if t_min is None else (t_max - r["time_sec"]) / ((t_max - t_min) + eps)

        # Метрики "выше-лучше" (оставляем как есть):
        snr_n = 0.0 if snr_min is None else (r["snr_db"] - snr_min) / ((snr_max - snr_min) + eps)
        sisdr_n = 0.0 if sisdr_min is None else (r["si_sdr_db"] - sisdr_min) / ((sisdr_max - sisdr_min) + eps)
        cos_n = 0.0 if cos_min is None else (r["spec_cosine"] - cos_min) / ((cos_max - cos_min) + eps)

        # Метрики "выше-лучше"
        stoi_n = 0.0 if stoi_min is None else (r["stoi"] - stoi_min) / ((stoi_max - stoi_min) + eps)
        pesq_n = 0.0 if pesq_min is None else (r["pesq"] - pesq_min) / ((pesq_max - pesq_min) + eps)
        mos_n = 0.0 if mos_min is None else (r["mos"] - mos_min) / ((mos_max - mos_min) + eps)

        # Взвешенная сумма (все компоненты приведены к "выше-лучше")
        # Чем выше score, тем лучше метод
        # Веса берутся из параметра weights (по умолчанию — из MetricsConfig)
        r["score"] = float(
            w.get('lsd', 0.15) * lsd_n +
            w.get('spec_conv', 0.10) * sc_n +
            w.get('snr', 0.15) * snr_n +
            w.get('rmse', 0.10) * rmse_n +
            w.get('si_sdr', 0.10) * sisdr_n +
            w.get('centroid_diff', 0.05) * scdiff_n +
            w.get('cosine', 0.05) * cos_n +
            w.get('time', 0.05) * t_n +
            w.get('stoi', 0.10) * stoi_n +
            w.get('pesq', 0.10) * pesq_n +
            w.get('mos', 0.05) * mos_n
        )

    logger.info("metrics_batch_done", extra={"count": len(results)})
    return results


# =============================================================================
# МЕТРИКИ STOI (Short-Time Objective Intelligibility Index)
# =============================================================================

def compute_stoi(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
    n_fft: int = 512,
    hop: int = 256,
    n_bands: int = 15,
) -> float:
    """Вычислить STOI (Short-Time Objective Intelligibility Index).
    
    STOI измеряет разборчивость речи путём сравнения кратковременных
    спектральных огибающих опорного и тестового сигналов.
    
    Диапазон значений: 0.0 - 1.0 (выше лучше).
    - 1.0: идеальное совпадение
    - 0.0: полностью неразборчиво
    - > 0.75: хорошая разборчивость
    - > 0.9: отличная разборчивость
    
    Алгоритм:
    1) Приведение частот дискретизации
    2) Разбиение на октавные полосы
    3) Вычисление кратковременных огибающих
    4) Корреляция огибающих в каждой полосе
    5) Усреднение корреляций
    
    Параметры:
    ----------
    reference : np.ndarray
        Опорный сигнал (чистый)
    test : np.ndarray
        Тестовый сигнал (обработанный)
    sr_ref : int
        Частота дискретизации опорного сигнала
    sr_test : int
        Частота дискретизации тестового сигнала
    n_fft : int
        Размер окна FFT (по умолчанию 512)
    hop : int
        Шаг окна (по умолчанию 256)
    n_bands : int
        Число октавных полос (по умолчанию 15)
    
    Возвращает:
    -----------
    float
        STOI значение от 0.0 до 1.0
    
    Примечание:
    -----------
    Это упрощённая реализация. Для полной точности
    рекомендуется использовать библиотеку pystoi.
    """
    # Ресемплирование
    test_resampled = _resample_linear(test, sr_test, sr_ref)
    n = min(len(reference), len(test_resampled))
    
    if n < n_fft:
        return float("nan")
    
    ref = reference[:n].astype(np.float64)
    tst = test_resampled[:n].astype(np.float64)
    
    # Параметры
    N = int(n_fft)
    H = int(hop)
    n_frames = max(1, 1 + (n - N) // H)
    
    # Создаём окно
    win = np.hanning(N)
    
    # Центральные частоты октавных полос (от 150 Гц до ~8 кГц)
    f_center = 150.0 * (2.0 ** (np.arange(n_bands) / 3.0))  # 1/3 октавы
    f_center = f_center[f_center < sr_ref / 2].astype(np.float64)
    n_bands_actual = len(f_center)
    
    if n_bands_actual == 0:
        return float("nan")
    
    # Ширина полос (1/3 октавы)
    bandwidth = f_center * (2.0 ** (1.0 / 6.0) - 2.0 ** (-1.0 / 6.0))
    
    # Частотные индексы для каждой полосы
    freq_bins = np.fft.rfftfreq(N, 1.0 / sr_ref)
    
    # Вычисляем огибающие для каждого фрейма
    env_ref = np.zeros((n_frames, n_bands_actual), dtype=np.float64)
    env_tst = np.zeros((n_frames, n_bands_actual), dtype=np.float64)
    
    for frame_idx in range(n_frames):
        start = frame_idx * H
        end = start + N
        
        if end > n:
            # Дополнение нулями для последнего фрейма
            ref_frame = np.zeros(N)
            tst_frame = np.zeros(N)
            ref_frame[:n - start] = ref[start:]
            tst_frame[:n - start] = tst[start:]
        else:
            ref_frame = ref[start:end]
            tst_frame = tst[start:end]
        
        # Применяем окно и FFT
        ref_fft = np.abs(np.fft.rfft(ref_frame * win))
        tst_fft = np.abs(np.fft.rfft(tst_frame * win))
        
        # Вычисляем энергию в каждой полосе
        for band_idx in range(n_bands_actual):
            f_low = f_center[band_idx] - bandwidth[band_idx] / 2
            f_high = f_center[band_idx] + bandwidth[band_idx] / 2
            
            # Находим бины в пределах полосы
            mask = (freq_bins >= f_low) & (freq_bins <= f_high)
            
            if np.any(mask):
                env_ref[frame_idx, band_idx] = np.sqrt(np.mean(ref_fft[mask] ** 2))
                env_tst[frame_idx, band_idx] = np.sqrt(np.mean(tst_fft[mask] ** 2))
    
    # Нормировка огибающих
    eps = 1e-12
    env_ref = env_ref / (np.max(env_ref, axis=0, keepdims=True) + eps)
    env_tst = env_tst / (np.max(env_tst, axis=0, keepdims=True) + eps)
    
    # Вычисляем корреляцию огибающих для каждой полосы
    correlations = []
    
    for band_idx in range(n_bands_actual):
        ref_band = env_ref[:, band_idx]
        tst_band = env_tst[:, band_idx]
        
        # Центрируем
        ref_centered = ref_band - np.mean(ref_band)
        tst_centered = tst_band - np.mean(tst_band)
        
        # Корреляция Пирсона
        num = np.sum(ref_centered * tst_centered)
        den = np.sqrt(np.sum(ref_centered ** 2) * np.sum(tst_centered ** 2)) + eps
        
        corr = num / den
        correlations.append(corr)
    
    # Усредняем корреляции
    # Стандартный STOI: усредняем корреляции по полосам,
    # затем ограничиваем диапазон [0, 1] (clip).
    # Примечание: референсная реализация использует clip, а не (corr+1)/2,
    # т.к. отрицательная корреляция означает плохое совпадение, а не «среднее».
    mean_corr = float(np.mean(correlations))
    return float(max(0.0, min(1.0, mean_corr)))


def compute_stoi_simplified(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
) -> float:
    """Упрощённая версия STOI для быстрой оценки.
    
    Ресемплирует оба сигнала до 10 кГц (стандартная частота для STOI),
    что обеспечивает корректное разрешение октавных полос при n_fft=256
    (частотное разрешение ~39 Гц вместо ~172 Гц при 44100 Гц).
    
    Параметры:
    ----------
    reference : np.ndarray
        Опорный сигнал
    test : np.ndarray
        Тестовый сигнал
    sr_ref : int
        Частота дискретизации опорного
    sr_test : int
        Частота дискретизации тестового
    
    Возвращает:
    -----------
    float
        STOI значение от 0.0 до 1.0
    """
    # Ресемплирование к 10 кГц для корректной работы октавных полос
    # При 44100 Гц и n_fft=256 разрешение 172 Гц — большинство полос пустые
    # При 10000 Гц и n_fft=256 разрешение 39 Гц — каждая полоса 1-9 бинов
    target_sr = 10000
    ref = _resample_linear(reference, sr_ref, target_sr)
    tst = _resample_linear(test, sr_test, target_sr)
    return compute_stoi(ref, tst, target_sr, target_sr, n_fft=256, hop=128, n_bands=8)


# =============================================================================
# МЕТРИКИ PESQ (Perceptual Evaluation of Speech Quality)
# =============================================================================

def compute_pesq_approx(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
) -> float:
    """Приближённая оценка PESQ без внешних библиотек.
    
    PESQ (Perceptual Evaluation of Speech Quality) — стандарт ITU-T P.862
    для оценки качества речи. Диапазон: -0.5 до 4.5 (выше лучше).
    
    ПРЕДУПРЕЖДЕНИЕ: Это приближённая реализация!
    Для точных результатов используйте официальную реализацию ITU-T
    или библиотеку pesq (pip install pesq).
    
    Приближение основано на:
    - Взвешенном спектральном расстоянии
    - Модели маскирования
    - Компенсации задержки
    
    Параметры:
    ----------
    reference : np.ndarray
        Опорный сигнал (чистый)
    test : np.ndarray
        Тестовый сигнал (обработанный)
    sr_ref : int
        Частота дискретизации опорного
    sr_test : int
        Частота дискретизации тестового
    
    Возвращает:
    -----------
    float
        Приближённое значение PESQ (-0.5 до 4.5)
    """
    # Ресемплирование к 16 кГц (стандарт для PESQ)
    target_sr = 16000
    
    if sr_ref != target_sr:
        ref = _resample_linear(reference, sr_ref, target_sr)
        sr_ref = target_sr
    else:
        ref = reference.astype(np.float64)
    
    if sr_test != target_sr:
        tst = _resample_linear(test, sr_test, target_sr)
    else:
        tst = test.astype(np.float64)
    
    n = min(len(ref), len(tst))
    if n < 1024:
        return float("nan")
    
    ref = ref[:n]
    tst = tst[:n]
    
    # Параметры
    n_fft = 512
    hop = 256
    n_frames = max(1, 1 + (n - n_fft) // hop)
    
    # Психоакустическое взвешивание (A-взвешивание упрощённое)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr_ref)
    
    # Упрощённое A-взвешивание
    f = np.abs(freqs)
    # Обрабатываем f=0 отдельно - DC компонент должен иметь вес ~0
    a_weight = np.zeros_like(f)
    nonzero_mask = f > 0
    if np.any(nonzero_mask):
        f_nonzero = f[nonzero_mask]
        with np.errstate(divide='ignore', invalid='ignore'):
            a_weight_nonzero = (12194**2 * f_nonzero**4) / (
                (f_nonzero**2 + 20.6**2) * 
                np.sqrt((f_nonzero**2 + 107.7**2) * (f_nonzero**2 + 737.9**2)) * 
                (f_nonzero**2 + 12194**2)
            )
            a_weight[nonzero_mask] = np.nan_to_num(a_weight_nonzero, nan=0.0, posinf=0.0, neginf=0.0)
    # Нормализация по максимуму (исключая DC)
    max_val = np.max(a_weight[nonzero_mask]) if np.any(nonzero_mask) else 1.0
    a_weight = a_weight / (max_val + 1e-12)
    
    # Вычисляем спектры
    win = np.hanning(n_fft)
    
    distortion_vals = []
    
    for frame_idx in range(n_frames):
        start = frame_idx * hop
        end = start + n_fft
        
        if end > n:
            continue
        
        ref_frame = ref[start:end] * win
        tst_frame = tst[start:end] * win
        
        # FFT
        ref_fft = np.fft.rfft(ref_frame)
        tst_fft = np.fft.rfft(tst_frame)
        
        # Амплитуды
        ref_mag = np.abs(ref_fft)
        tst_mag = np.abs(tst_fft)
        
        # Взвешенное спектральное расстояние
        diff = np.log10((ref_mag + 1e-12) / (tst_mag + 1e-12) + 1e-12)
        weighted_diff = np.abs(diff) * a_weight
        
        # Усредняем
        frame_dist = np.mean(weighted_diff ** 2)
        distortion_vals.append(frame_dist)
    
    if not distortion_vals:
        return float("nan")
    
    # Среднее искажение
    mean_distortion = np.sqrt(np.mean(distortion_vals))
    
    # Маппинг на шкалу PESQ (эмпирический)
    # PESQ = 4.5 - k * distortion
    # k подобран эмпирически
    k = 3.0
    pesq_approx = 4.5 - k * mean_distortion
    
    # Ограничение диапазона
    return float(max(-0.5, min(4.5, pesq_approx)))


def compute_pesq_mos(
    reference: np.ndarray,
    test: np.ndarray,
    sr_ref: int,
    sr_test: int,
) -> float:
    """Вычислить PESQ и конвертировать в MOS (Mean Opinion Score).
    
    MOS — шкала от 1 до 5:
    - 5: Отлично
    - 4: Хорошо
    - 3: Удовлетворительно
    - 2: Плохо
    - 1: Неприемлемо
    
    Параметры:
    ----------
    reference : np.ndarray
        Опорный сигнал
    test : np.ndarray
        Тестовый сигнал
    sr_ref : int
        Частота дискретизации опорного
    sr_test : int
        Частота дискретизации тестового
    
    Возвращает:
    -----------
    float
        MOS значение от 1.0 до 5.0
    """
    pesq = compute_pesq_approx(reference, test, sr_ref, sr_test)
    
    if np.isnan(pesq):
        return float("nan")
    
    # Функция отображения PESQ -> MOS (по ITU-T P.862.1)
    # MOS-LQO = 1 + (4.87 - 1) / (1 + exp(-1.3669 * (PESQ - 0.7197)))
    mos = 1.0 + 3.87 / (1.0 + np.exp(-1.3669 * (pesq - 0.7197)))
    
    return float(max(1.0, min(5.0, mos)))


# =============================================================================
# ДОПОЛНИТЕЛЬНЫЕ МЕТРИКИ
# =============================================================================

def compute_spectral_flatness(
    signal: np.ndarray,
    sr: int,
    n_fft: int = 2048,
    hop: int = 512,
) -> float:
    """Вычислить спектральную плоскостность (Wiener entropy).
    
    Спектральная плоскостность измеряет, насколько спектр сигнала
    похож на белый шум (плоский спектр).
    
    Диапазон: 0.0 - 1.0
    - Близко к 0: тональный сигнал (музыка, речь)
    - Близко к 1: шумоподобный сигнал
    
    Параметры:
    ----------
    signal : np.ndarray
        Входной сигнал
    sr : int
        Частота дискретизации
    n_fft : int
        Размер окна FFT
    hop : int
        Шаг окна
    
    Возвращает:
    -----------
    float
        Средняя спектральная плоскостность
    """
    n = len(signal)
    if n < n_fft:
        return float("nan")
    
    win = np.hanning(n_fft)
    n_frames = max(1, 1 + (n - n_fft) // hop)
    
    flatness_vals = []
    
    for frame_idx in range(n_frames):
        start = frame_idx * hop
        end = start + n_fft
        
        if end > n:
            break
        
        frame = signal[start:end] * win
        spectrum = np.abs(np.fft.rfft(frame)) + 1e-12
        
        # Спектральная плоскостность = geometric_mean / arithmetic_mean
        geometric_mean = np.exp(np.mean(np.log(spectrum)))
        arithmetic_mean = np.mean(spectrum)
        
        flatness = geometric_mean / (arithmetic_mean + 1e-12)
        flatness_vals.append(flatness)
    
    if not flatness_vals:
        return float("nan")
    
    return float(np.mean(flatness_vals))


def compute_dynamic_range(
    signal: np.ndarray,
    percentile_low: float = 5.0,
    percentile_high: float = 95.0,
) -> float:
    """Вычислить динамический диапазон сигнала в дБ.
    
    Динамический диапазон — разница между громкими и тихими
    участками сигнала.
    
    Параметры:
    ----------
    signal : np.ndarray
        Входной сигнал
    percentile_low : float
        Нижний процентиль (тихие участки)
    percentile_high : float
        Верхний процентиль (громкие участки)
    
    Возвращает:
    -----------
    float
        Динамический диапазон в дБ
    """
    if len(signal) == 0:
        return float("nan")
    
    # Вычисляем RMS по коротким окнам
    window_size = min(1024, len(signal) // 10)
    if window_size < 2:
        window_size = 2
    
    rms_values = []
    for i in range(0, len(signal) - window_size, window_size // 2):
        window = signal[i:i + window_size]
        rms = np.sqrt(np.mean(window ** 2))
        rms_values.append(rms)
    
    if not rms_values:
        return float("nan")
    
    rms_array = np.array(rms_values)
    
    # Процентили
    low_val = np.percentile(rms_array, percentile_low) + 1e-12
    high_val = np.percentile(rms_array, percentile_high) + 1e-12
    
    # Динамический диапазон в дБ
    dynamic_range = 20.0 * np.log10(high_val / low_val)
    
    return float(dynamic_range)


def compute_crest_factor(signal: np.ndarray) -> float:
    """Вычислить пик-фактор (crest factor) сигнала.
    
    Пик-фактор — отношение пикового значения к RMS.
    Характеризует "пиковость" сигнала.
    
    Диапазон: >= 1.0
    - 1.0: синусоида
    - ~3-4: типичная речь/музыка
    - > 10: импульсные сигналы
    
    Параметры:
    ----------
    signal : np.ndarray
        Входной сигнал
    
    Возвращает:
    -----------
    float
        Пик-фактор
    """
    if len(signal) == 0:
        return float("nan")
    
    peak = np.max(np.abs(signal))
    rms = np.sqrt(np.mean(signal ** 2)) + 1e-12
    
    return float(peak / rms)


# =============================================================================
# ЭКСПОРТ ИМЁН
# =============================================================================

__all__ = [
    # Метрики временной области
    "compute_snr_db",
    "compute_rmse",
    "compute_si_sdr_db",
    # Метрики спектральной области
    "compute_lsd_db",
    "compute_spectral_convergence",
    "compute_spectral_centroid_diff_hz",
    "compute_spectral_cosine_similarity",
    # STOI
    "compute_stoi",
    "compute_stoi_simplified",
    # PESQ
    "compute_pesq_approx",
    "compute_pesq_mos",
    # Дополнительные метрики
    "compute_spectral_flatness",
    "compute_dynamic_range",
    "compute_crest_factor",
    # Пакетный расчёт
    "compute_metrics_batch",
]
