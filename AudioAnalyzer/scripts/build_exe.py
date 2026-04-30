"""
Сборка Windows .exe с помощью PyInstaller.

Назначение:
- Создание одного исполняемого файла AudioTransformer.exe
- Автоматическое определение и внедрение FFmpeg/FFprobe
- Исключение устаревших и ненужных модулей

Использование:
    python scripts/build_exe.py
"""
import os
import shutil
from PyInstaller.__main__ import run

# Ensure we execute from repo root
root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
os.chdir(root)

# Clean previous build artifacts to guarantee fresh exe
for d in ('build', 'dist'):
    try:
        shutil.rmtree(os.path.join(root, d))
    except Exception:
        pass

args = [
    '--noconfirm',
    '--clean',
    '--onefile',
    '--windowed',
    '--name', 'AudioTransformer',
    '--paths', 'src',
    # PySide6 and soundfile need full collection
    '--collect-all', 'PySide6',
    '--collect-all', 'soundfile',
    # NumPy submodules
    '--collect-submodules', 'numpy',
    # PyWavelets for Daubechies DWT (pywt.wavedec/waverec)
    '--collect-submodules', 'pywt',
    # Our processing module
    '--collect-submodules', 'processing',
    # Explicitly include our UI modules (ui_new is the active one)
    '--hidden-import', 'ui_new',
    '--hidden-import', 'ui_new.main_window',
    '--hidden-import', 'ui_new.worker',
    '--hidden-import', 'ui_new.log_handler',
    '--hidden-import', 'ui_new.presets',
    '--hidden-import', 'ui_new.constants',
    '--hidden-import', 'ui_new.components',
    '--hidden-import', 'ui_new.components.dashboard',
    '--hidden-import', 'ui_new.components.onboarding',
    '--hidden-import', 'ui_new.components.toast',
    '--hidden-import', 'ui_new.components.wizards',
    '--hidden-import', 'ui_new.components.shortcuts',
    '--hidden-import', 'ui_new.mixins',
    '--hidden-import', 'ui_new.mixins.worker_mixin',
    '--hidden-import', 'ui_new.mixins.comparison_mixin',
    '--hidden-import', 'ui_new.mixins.settings_mixin',
    '--hidden-import', 'ui_new.mixins.player_mixin',
    '--hidden-import', 'ui_new.mixins.spectrum_mixin',
    '--hidden-import', 'ui_new.mixins.files_mixin',
    '--hidden-import', 'ui_new.widgets',
    '--hidden-import', 'ui_new.widgets.results_table',
    '--hidden-import', 'ui_new.widgets.spectrum_widget',
    '--hidden-import', 'ui_new.widgets.spectrogram_3d',
    '--hidden-import', 'ui_new.services',
    '--hidden-import', 'ui_new.services.audio_service',
    '--hidden-import', 'ui_new.services.file_service',
    '--hidden-import', 'ui_new.services.config',
    '--hidden-import', 'ui_new.export_xlsx',
    '--hidden-import', 'ui_new.reports',
    '--hidden-import', 'ui_new.ml_integration',
    '--hidden-import', 'ui_new.audio_editor',
    # Processing module imports
    '--hidden-import', 'processing',
    '--hidden-import', 'processing.audio_ops',
    '--hidden-import', 'processing.codecs',
    '--hidden-import', 'processing.metrics',
    '--hidden-import', 'processing.utils',
    '--hidden-import', 'processing.api',
    '--hidden-import', 'processing.parallel_ola',
    # Processing transforms
    '--hidden-import', 'processing.transforms',
    '--hidden-import', 'processing.transforms.base',
    '--hidden-import', 'processing.transforms.fft',
    '--hidden-import', 'processing.transforms.dct',
    '--hidden-import', 'processing.transforms.dwt',
    '--hidden-import', 'processing.transforms.fwht',
    '--hidden-import', 'processing.transforms.huffman',
    '--hidden-import', 'processing.transforms.rosenbrock',
    '--hidden-import', 'processing.transforms.extended',
    # Utils
    '--hidden-import', 'utils',
    '--hidden-import', 'utils.logging_setup',
    # Exclude unrelated third-party packages
    '--exclude-module', 'ui',  # Unrelated package named "ui"
    '--exclude-module', 'tkinter',
    '--exclude-module', 'matplotlib',
    '--exclude-module', 'PIL',
    '--exclude-module', 'scipy',
    '--exclude-module', 'pytest',  # Not needed at runtime
    '--exclude-module', 'numpy.f2py.tests',  # Requires pytest
    '--exclude-module', 'OpenGL',  # Optional for pyqtgraph
    '--exclude-module', 'pyqtgraph.opengl',  # Requires OpenGL
    # NOTE: do NOT exclude 'distutils' — setuptools vendors it and
    # PyInstaller's hook-distutils.py creates an alias to the vendored copy.
    # Excluding it causes: ValueError: Target module "distutils" already imported as ExcludedModule
    # Runtime hook for FFmpeg
    '--runtime-hook', 'hooks/runtime_ffmpeg.py',
    # Entry point
    'src/app.py',
]

# Bundle ffmpeg and ffprobe to eliminate external deps
# Prefer vendored third_party/ffmpeg/bin, fallback to system PATH
ffmpeg = None
ffprobe = None

# Check for vendored FFmpeg
vend_ffmpeg = os.path.join(root, 'third_party', 'ffmpeg', 'bin', 'ffmpeg.exe')
vend_ffprobe = os.path.join(root, 'third_party', 'ffmpeg', 'bin', 'ffprobe.exe')
if os.path.isfile(vend_ffmpeg):
    ffmpeg = vend_ffmpeg
if os.path.isfile(vend_ffprobe):
    ffprobe = vend_ffprobe

# Fallback to system PATH
if not ffmpeg:
    for name in ('ffmpeg.exe', 'ffmpeg'):
        for p in os.environ.get('PATH', '').split(os.pathsep):
            cand = os.path.join(p, name)
            if os.path.isfile(cand):
                ffmpeg = cand
                break
        if ffmpeg:
            break

if not ffprobe:
    # Prefer sibling to found ffmpeg
    if ffmpeg and ffmpeg.lower().endswith('ffmpeg.exe'):
        cand = ffmpeg[:-10] + 'ffprobe.exe'
        if os.path.isfile(cand):
            ffprobe = cand
    if not ffprobe:
        for name in ('ffprobe.exe', 'ffprobe'):
            for p in os.environ.get('PATH', '').split(os.pathsep):
                cand = os.path.join(p, name)
                if os.path.isfile(cand):
                    ffprobe = cand
                    break
            if ffprobe:
                break

# Add FFmpeg binaries to the build
if ffmpeg:
    args = ['--add-binary', f'{ffmpeg};.'] + args
    print(f"Using FFmpeg: {ffmpeg}")
if ffprobe:
    args = ['--add-binary', f'{ffprobe};.'] + args
    print(f"Using FFprobe: {ffprobe}")

print("Building AudioTransformer.exe...")
print(f"Root: {root}")
run(args)
print("Build complete. Output: dist/AudioTransformer.exe")
