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
import subprocess
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
    # PySide6 — собираем только нужные модули вместо --collect-all PySide6
    # (collect-all тянет 50+ неиспользуемых модулей: Qt3D, QtBluetooth, QtNfc и т.д.)
    '--collect-all', 'PySide6.QtCore',
    '--collect-all', 'PySide6.QtGui',
    '--collect-all', 'PySide6.QtWidgets',
    '--collect-all', 'PySide6.QtMultimedia',
    '--collect-all', 'PySide6.QtCharts',
    '--collect-all', 'PySide6.QtSvg',
    '--collect-all', 'PySide6.QtOpenGL',
    '--collect-all', 'PySide6.QtOpenGLWidgets',
    '--collect-all', 'PySide6.QtNetwork',
    '--collect-all', 'PySide6.QtTest',
    '--collect-all', 'PySide6.QtConcurrent',
    '--collect-all', 'PySide6.QtPrintSupport',
    '--collect-all', 'soundfile',
    # NumPy — только основное, без тестов
    '--collect-submodules', 'numpy',
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
    '--exclude-module', 'OpenGL',  # Optional for pyqtgraph
    '--exclude-module', 'pyqtgraph.opengl',  # Requires OpenGL
    # Exclude unused PySide6 modules (pulled by shiboken/Qt dependencies)
    '--exclude-module', 'PySide6.Qt3DAnimation',
    '--exclude-module', 'PySide6.Qt3DCore',
    '--exclude-module', 'PySide6.Qt3DExtras',
    '--exclude-module', 'PySide6.Qt3DInput',
    '--exclude-module', 'PySide6.Qt3DLogic',
    '--exclude-module', 'PySide6.Qt3DRender',
    '--exclude-module', 'PySide6.QtBluetooth',
    '--exclude-module', 'PySide6.QtDBus',
    '--exclude-module', 'PySide6.QtDataVisualization',
    '--exclude-module', 'PySide6.QtDesigner',
    '--exclude-module', 'PySide6.QtGraphs',
    '--exclude-module', 'PySide6.QtGraphsWidgets',
    '--exclude-module', 'PySide6.QtHelp',
    '--exclude-module', 'PySide6.QtHttpServer',
    '--exclude-module', 'PySide6.QtLocation',
    '--exclude-module', 'PySide6.QtNfc',
    '--exclude-module', 'PySide6.QtPdf',
    '--exclude-module', 'PySide6.QtPdfWidgets',
    '--exclude-module', 'PySide6.QtPositioning',
    '--exclude-module', 'PySide6.QtQuick',
    '--exclude-module', 'PySide6.QtQuickControls2',
    '--exclude-module', 'PySide6.QtQuick3D',
    '--exclude-module', 'PySide6.QtQuickWidgets',
    '--exclude-module', 'PySide6.QtQuickTest',
    '--exclude-module', 'PySide6.QtRemoteObjects',
    '--exclude-module', 'PySide6.QtScxml',
    '--exclude-module', 'PySide6.QtSensors',
    '--exclude-module', 'PySide6.QtSerialBus',
    '--exclude-module', 'PySide6.QtSerialPort',
    '--exclude-module', 'PySide6.QtSpatialAudio',
    '--exclude-module', 'PySide6.QtSql',
    '--exclude-module', 'PySide6.QtStateMachine',
    '--exclude-module', 'PySide6.QtSvgWidgets',
    '--exclude-module', 'PySide6.QtTextToSpeech',
    '--exclude-module', 'PySide6.QtUiTools',
    '--exclude-module', 'PySide6.QtWebChannel',
    '--exclude-module', 'PySide6.QtWebEngineCore',
    '--exclude-module', 'PySide6.QtWebEngineQuick',
    '--exclude-module', 'PySide6.QtWebEngineWidgets',
    '--exclude-module', 'PySide6.QtWebSockets',
    '--exclude-module', 'PySide6.QtWebView',
    '--exclude-module', 'PySide6.QtXml',
    '--exclude-module', 'PySide6.QtAxContainer',
    '--exclude-module', 'PySide6.QtAsyncio',
    '--exclude-module', 'PySide6.QtCanvasPainter',
    '--exclude-module', 'PySide6.QtMultimediaWidgets',
    '--exclude-module', 'PySide6.QtNetworkAuth',
    '--exclude-module', 'PySide6.QtLabsAnimation',
    '--exclude-module', 'PySide6.QtLabsFolderListModel',
    '--exclude-module', 'PySide6.QtLabsQmlModels',
    '--exclude-module', 'PySide6.QtLabsSettings',
    # Exclude numpy test/distutils submodules (not needed at runtime)
    '--exclude-module', 'numpy.f2py',
    '--exclude-module', 'numpy.distutils',
    '--exclude-module', 'numpy.testing',
    '--exclude-module', 'numpy.tests',
    '--exclude-module', 'numpy.fft.tests',
    '--exclude-module', 'numpy.lib.tests',
    '--exclude-module', 'numpy.linalg.tests',
    '--exclude-module', 'numpy.ma.tests',
    '--exclude-module', 'numpy.matrixlib.tests',
    '--exclude-module', 'numpy.polynomial.tests',
    '--exclude-module', 'numpy.random.tests',
    '--exclude-module', 'numpy.typing.tests',
    '--exclude-module', 'numpy.typing.mypy_plugin',
    '--exclude-module', 'numpy.conftest',
    '--exclude-module', 'numpy.testing.print_coercion_tables',
    # Exclude unnecessary setuptools/distutils
    '--exclude-module', 'setuptools',
    '--exclude-module', 'pkg_resources',
    '--exclude-module', 'distutils',
    '--exclude-module', 'pycparser',
    # Runtime hook for FFmpeg
    '--runtime-hook', 'hooks/runtime_ffmpeg.py',
    # Entry point
    'src/app.py',
]

# ======================================================================
# Bundle ffmpeg and ffprobe to eliminate external deps
# ======================================================================
# Priorities:
#   1. Vendored: third_party/ffmpeg/bin/{ffmpeg,ffprobe}.exe
#   2. System PATH (including WinGet Gyan.FFmpeg)
#   3. Fail with clear instructions
# ======================================================================
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

# Also check WinGet Gyan.FFmpeg location (not always in PATH)
if not ffmpeg:
    try:
        winget_base = os.path.join(
            os.environ.get('LOCALAPPDATA', ''),
            'Microsoft', 'WinGet', 'Packages'
        )
        if os.path.isdir(winget_base):
            for entry in os.listdir(winget_base):
                if entry.lower().startswith('gyan.ffmpeg'):
                    # Try common subdir names
                    for ver_dir in os.listdir(os.path.join(winget_base, entry)):
                        if ver_dir.startswith('ffmpeg'):
                            cand = os.path.join(winget_base, entry, ver_dir, 'bin', 'ffmpeg.exe')
                            if os.path.isfile(cand):
                                ffmpeg = cand
                                break
                    if ffmpeg:
                        break
    except Exception:
        pass

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

# ======================================================================
# CRITICAL: abort if FFmpeg was not found
# ======================================================================
if not ffmpeg:
    print("")
    print("=" * 70)
    print("  ERROR: FFmpeg not found!")
    print("=" * 70)
    print("  The built exe will NOT be able to process audio files.")
    print("")
    print("  To fix this, choose ONE option:")
    print("")
    print("  Option A — Install FFmpeg system-wide:")
    print("    1. Download: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip")
    print("    2. Extract to a folder (e.g. C:\ffmpeg)")
    print("    3. Add C:\ffmpeg\bin to system PATH")
    print("    4. Reopen terminal and re-run build")
    print("")
    print("  Option B — Vendored (no PATH needed):")
    print("    1. Download ffmpeg.exe and ffprobe.exe from the link above")
    print(f"    2. Place them in: {os.path.join(root, 'third_party', 'ffmpeg', 'bin')}")
    print("    3. Re-run build")
    print("")
    print("  Option C — Quick install via winget:")
    print("    winget install Gyan.FFmpeg")
    print("    (then reopen terminal and re-run build)")
    print("=" * 70)
    print("")
    import sys
    sys.exit(1)

print("Building AudioTransformer.exe...")
print(f"Root: {root}")
run(args)
print("Build complete. Output: dist/AudioTransformer.exe")
