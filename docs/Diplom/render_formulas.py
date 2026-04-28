"""Генерация PNG-изображений формул метрик качества для встраивания в DOCX."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['mathtext.fontset'] = 'cm'
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

OUTPUT_DIR = "/home/z/my-project/VKR_To_END/docs/Diplom/formula_images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def render_formula(latex_str, filename, fontsize=14, dpi=200):
    """Рендер LaTeX-формулы в PNG."""
    fig, ax = plt.subplots(figsize=(0.1, 0.1))
    ax.axis("off")
    text = ax.text(0, 0.5, f"${latex_str}$", fontsize=fontsize,
                   transform=ax.transAxes, verticalalignment="center",
                   usetex=False)
    fig.canvas.draw()
    bbox = text.get_window_extent(fig.canvas.get_renderer())
    fig.set_size_inches(bbox.width / dpi + 0.15, bbox.height / dpi + 0.15)
    path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.04, transparent=True)
    plt.close()
    return path

formulas = {
    # 1. SNR
    "f1_snr_noise": r"\mathrm{noise}[n] = x[n] - y[n]",
    "f1_snr_psig": r"P_{\mathrm{signal}} = \frac{1}{N} \sum_{n=0}^{N-1} x^2[n] + \varepsilon",
    "f1_snr_pnoise": r"P_{\mathrm{noise}} = \frac{1}{N} \sum_{n=0}^{N-1} \mathrm{noise}^2[n] + \varepsilon",
    "f1_snr": r"\mathrm{SNR} = 10 \cdot \log_{10}\!\left(\frac{P_{\mathrm{signal}}}{P_{\mathrm{noise}}}\right)\;\text{, дБ}",

    # 2. RMSE
    "f2_rmse_e": r"e[n] = x[n] - y[n]",
    "f2_rmse": r"\mathrm{RMSE} = \sqrt{\frac{1}{N} \sum_{n=0}^{N-1} e^2[n]}",

    # 3. SI-SDR
    "f3_sisdr_alpha": r"\alpha = \frac{\sum_{n=0}^{N-1} x[n] \cdot y[n]}{\sum_{n=0}^{N-1} x^2[n] + \varepsilon}",
    "f3_sisdr_yhat": r"\hat{y}[n] = \alpha \cdot x[n]",
    "f3_sisdr_enoise": r"e_{\mathrm{noise}}[n] = y[n] - \hat{y}[n]",
    "f3_sisdr": r"\mathrm{SI\text{-}SDR} = 10 \cdot \log_{10}\!\left(\frac{\sum \hat{y}^2[n] + \varepsilon}{\sum e_{\mathrm{noise}}^2[n] + \varepsilon}\right)\;\text{, дБ}",

    # 4. LSD
    "f4_lsd_fft": r"X_m[k] = \mathrm{rFFT}\!\left(x_m[n] \cdot w[n]\right)",
    "f4_lsd_log": r"S_x[k] = 10 \cdot \log_{10}\!\left(|X_m[k]|^2 + \varepsilon\right)",
    "f4_lsd_frame": r"\mathrm{LSD}_m = \sqrt{\frac{1}{K} \sum_{k=0}^{K-1} \left(S_x[k] - S_y[k]\right)^2}",
    "f4_lsd": r"\mathrm{LSD} = \frac{1}{M} \sum_{m=0}^{M-1} \mathrm{LSD}_m\;\text{, дБ}",

    # 5. Spectral Convergence
    "f5_sc_fft": r"X_m[k] = \mathrm{rFFT}\!\left(x_m[n] \cdot w[n]\right)",
    "f5_sc": r"\mathrm{SC}_m = \frac{||\,|X_m| - |Y_m|\,||_2}{||\,|X_m|\,||_2 + \varepsilon}",

    # 6. Centroid
    "f6_centroid": r"c_x = \left(\frac{\sum_{k=0}^{K-1} k \cdot |X_m[k]|}{\sum_{k=0}^{K-1} |X_m[k]| + \varepsilon}\right) \cdot \Delta f\;\text{, Гц}",
    "f6_diff": r"\Delta c_m = |c_x - c_y|",

    # 7. Cosine Similarity
    "f7_cos": r"\cos\theta_m = \frac{\sum_{k=0}^{K-1} A_m[k] \cdot B_m[k]}{||A_m|| \cdot ||B_m|| + \varepsilon}",

    # 8. STOI
    "f8_stoi_env": r"\mathrm{env}_{\mathrm{ref}}[m,\,b] = \sqrt{\frac{1}{L_b}\sum_{k \in b} |X_{\mathrm{ref}}[m,\,k]|^2}",
    "f8_stoi_corr": r"r_b = \frac{\sum_{m} (\bar{e}_r - \mu_r)(\bar{e}_t - \mu_t)}{\sqrt{\sum_{m}(\bar{e}_r - \mu_r)^2 \cdot \sum_{m}(\bar{e}_t - \mu_t)^2} + \varepsilon}",
    "f8_stoi": r"\mathrm{STOI} = \mathrm{clip}\!\left(\frac{1}{B}\sum_{b=0}^{B-1} r_b,\;0,\;1\right)",

    # 9. PESQ
    "f9_pesq_aw": r"W(f) = \frac{12194^2 \cdot f^4}{(f^2 + 20{,}6^2)\sqrt{(f^2 + 107{,}7^2)(f^2 + 737{,}9^2)}\,(f^2 + 12194^2)}",
    "f9_pesq_diff": r"\mathrm{diff}[k] = \left|\log_{10}\!\left(\frac{|X_m[k]| + \varepsilon}{|Y_m[k]| + \varepsilon} + \varepsilon\right)\right| \cdot W(f)",
    "f9_pesq": r"\mathrm{PESQ} = \max\!\left(-0{,}5,\;\min\!\left(4{,}5,\;4{,}5 - 3{,}0 \cdot D\right)\right)",

    # 10. MOS
    "f10_mos": r"\mathrm{MOS} = 1 + \frac{3{,}87}{1 + \exp\!\left(-1{,}3669 \cdot (\mathrm{PESQ} - 0{,}7197)\right)}",

    # 11. Score norm
    "f11_norm_inv": r"\mathrm{norm} = \frac{\max - V}{\max - \min + \varepsilon}\;\text{  (ниже лучше)}",
    "f11_norm_dir": r"\mathrm{norm} = \frac{V - \min}{\max - \min + \varepsilon}\;\text{  (выше лучше)}",
    "f11_score": r"\mathrm{Score} = \sum_{i=1}^{11} w_i \cdot \mathrm{norm}_i",
}

for name, latex in formulas.items():
    try:
        path = render_formula(latex, f"{name}.png")
        print(f"OK: {name} -> {path}")
    except Exception as e:
        print(f"ERR: {name} -> {e}")

print(f"\nDone. {len(formulas)} formulas rendered to {OUTPUT_DIR}")
