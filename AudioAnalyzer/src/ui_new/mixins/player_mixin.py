"""
Миксин для аудиоплеера.

Содержит:
- Построение вкладки Плеер
- Управление воспроизведением
- Обработку сигналов плеера
- Публикацию событий через Event Bus

Использование:
    class MainWindow(PlayerMixin, QMainWindow):
        ...
"""
from __future__ import annotations

import datetime
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Event Bus integration
from ..events import (
    EventBus,
    EventType,
    PlayerEvent,
    emit_player_state_changed,
)

logger = logging.getLogger("ui_new.mixins.player")


class PlayerMixin:
    """Миксин для аудиоплеера.

    Предоставляет:
    - Построение вкладки Плеер
- Управление воспроизведением
    - Обработку сигналов плеера

    Требуемые атрибуты в классе-носителе:
    - self._log_emitter (UiLogEmitter)
    """

    # =========================================================================
    # ПОСТРОЕНИЕ ВКЛАДКИ ПЛЕЕР
    # =========================================================================

    def _build_player_tab(self) -> Tuple[QWidget, Dict[str, Any]]:
        """Построить вкладку Плеер.

        Возвращает:
        -----------
        Tuple[QWidget, Dict[str, Any]]
            (виджет вкладки, словарь виджетов)
        """
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)

        widgets = {}

        # Заголовок
        player_header = QLabel("🎵 Плеер аудиофайлов")
        player_header.setStyleSheet(
            "font-weight: bold; font-size: 14px; margin: 5px;"
        )
        layout.addWidget(player_header)

        # -------------------------------------------------------------------------
        # Панель выбора файла
        # -------------------------------------------------------------------------
        file_panel = QHBoxLayout()

        file_panel.addWidget(QLabel("Файл:"))
        widgets['player_file_edit'] = QLineEdit()
        widgets['player_file_edit'].setReadOnly(True)
        widgets['player_file_edit'].setPlaceholderText(
            "Выберите файл для воспроизведения..."
        )
        file_panel.addWidget(widgets['player_file_edit'], 1)

        widgets['btn_browse_player'] = QPushButton("Обзор...")
        widgets['btn_browse_player'].setToolTip("Выбрать аудиофайл (WAV, MP3)")
        file_panel.addWidget(widgets['btn_browse_player'])

        layout.addLayout(file_panel)

        # -------------------------------------------------------------------------
        # Информация о файле
        # -------------------------------------------------------------------------
        widgets['player_info_label'] = QLabel("Файл не выбран")
        widgets['player_info_label'].setStyleSheet("color: gray; margin: 5px;")
        layout.addWidget(widgets['player_info_label'])

        # -------------------------------------------------------------------------
        # Плеер контролы
        # -------------------------------------------------------------------------
        controls_panel = QHBoxLayout()

        widgets['btn_play'] = QPushButton("▶️ Воспроизвести")
        widgets['btn_play'].setToolTip("Начать воспроизведение")
        widgets['btn_play'].setEnabled(False)
        controls_panel.addWidget(widgets['btn_play'])

        widgets['btn_pause'] = QPushButton("⏸️ Пауза")
        widgets['btn_pause'].setToolTip("Приостановить воспроизведение")
        widgets['btn_pause'].setEnabled(False)
        controls_panel.addWidget(widgets['btn_pause'])

        widgets['btn_stop'] = QPushButton("⏹️ Стоп")
        widgets['btn_stop'].setToolTip("Остановить воспроизведение")
        widgets['btn_stop'].setEnabled(False)
        controls_panel.addWidget(widgets['btn_stop'])

        # Громкость
        controls_panel.addWidget(QLabel("🔊"))
        widgets['volume_slider'] = QSlider(Qt.Orientation.Horizontal)
        widgets['volume_slider'].setRange(0, 100)
        widgets['volume_slider'].setValue(80)
        widgets['volume_slider'].setMaximumWidth(150)
        widgets['volume_slider'].setToolTip("Громкость (0-100%)")
        controls_panel.addWidget(widgets['volume_slider'])

        widgets['volume_label'] = QLabel("80%")
        widgets['volume_label'].setMinimumWidth(40)
        controls_panel.addWidget(widgets['volume_label'])

        controls_panel.addStretch(1)
        layout.addLayout(controls_panel)

        # -------------------------------------------------------------------------
        # Прогресс воспроизведения
        # -------------------------------------------------------------------------
        progress_panel = QHBoxLayout()
        widgets['position_label'] = QLabel("00:00")
        widgets['position_label'].setMinimumWidth(50)
        progress_panel.addWidget(widgets['position_label'])

        widgets['position_slider'] = QSlider(Qt.Orientation.Horizontal)
        widgets['position_slider'].setRange(0, 1000)
        widgets['position_slider'].setValue(0)
        widgets['position_slider'].setToolTip("Позиция воспроизведения")
        progress_panel.addWidget(widgets['position_slider'], 1)

        widgets['duration_label'] = QLabel("00:00")
        widgets['duration_label'].setMinimumWidth(50)
        progress_panel.addWidget(widgets['duration_label'])

        layout.addLayout(progress_panel)

        # -------------------------------------------------------------------------
        # Инициализация медиаплеера
        # -------------------------------------------------------------------------
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.8)

        self._current_player_file: Optional[str] = None

        return page, widgets

    # =========================================================================
    # ОБРАБОТЧИКИ ПЛЕЕРА
    # =========================================================================

    def on_browse_player_file(self) -> None:
        """Диалог выбора аудиофайла для воспроизведения."""
        from ..main_window import PROJECT_ROOT

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аудиофайл",
            str(PROJECT_ROOT),
            "Аудиофайлы (*.wav *.mp3);;WAV файлы (*.wav);;MP3 файлы (*.mp3)",
        )
        if file_path:
            self._load_player_file(file_path)

    def _load_player_file(self, file_path: str) -> None:
        """Загрузить файл в плеер."""
        self._current_player_file = file_path
        self.player_file_edit.setText(file_path)

        # Информация о файле
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
            self.player_info_label.setText(
                f"📁 {os.path.basename(file_path)} | "
                f"{size_mb:.2f} МБ | "
                f"Изменён: {mtime.strftime('%Y-%m-%d %H:%M')}"
            )
            self.player_info_label.setStyleSheet("color: #333; margin: 5px;")
        except Exception as e:
            self.player_info_label.setText(f"Ошибка: {e}")
            self.player_info_label.setStyleSheet("color: red; margin: 5px;")

        # Загружаем в плеер
        self._media_player.setSource(QUrl.fromLocalFile(file_path))
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

    def on_player_play(self) -> None:
        """Начать воспроизведение."""
        self._media_player.play()

    def on_player_pause(self) -> None:
        """Приостановить воспроизведение."""
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._media_player.play()
        else:
            self._media_player.pause()

    def on_player_stop(self) -> None:
        """Остановить воспроизведение."""
        self._media_player.stop()
        self.position_slider.setValue(0)
        self.position_label.setText("00:00")

    def on_volume_changed(self, value: int) -> None:
        """Изменить громкость."""
        self._audio_output.setVolume(value / 100.0)
        self.volume_label.setText(f"{value}%")

    def on_player_position_changed(self, position: int) -> None:
        """Обновить позицию воспроизведения."""
        duration = self._media_player.duration()
        if duration > 0:
            self.position_slider.setValue(int(position / duration * 1000))

        # Форматирование времени
        seconds = position // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        self.position_label.setText(f"{minutes:02d}:{seconds:02d}")

    def on_player_duration_changed(self, duration: int) -> None:
        """Обновить длительность трека."""
        seconds = duration // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        self.duration_label.setText(f"{minutes:02d}:{seconds:02d}")

    def on_player_state_changed(self, state) -> None:
        """Изменение состояния плеера.
        
        Публикует событие PLAYER_STATE_CHANGED через Event Bus.
        """
        state_name = "stopped"
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("▶️ Играет...")
            self.btn_play.setEnabled(False)
            self.btn_pause.setEnabled(True)
            state_name = "playing"
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.btn_play.setText("▶️ Воспроизвести")
            self.btn_play.setEnabled(True)
            self.btn_pause.setText("▶️ Продолжить")
            state_name = "paused"
        else:  # StoppedState
            self.btn_play.setText("▶️ Воспроизвести")
            self.btn_play.setEnabled(True)
            self.btn_pause.setText("⏸️ Пауза")
            self.btn_pause.setEnabled(True)
            state_name = "stopped"
        
        # Публикуем событие через Event Bus
        emit_player_state_changed(
            state=state_name,
            file_path=self._current_player_file or "",
            position_ms=self._media_player.position(),
            duration_ms=self._media_player.duration(),
            source="PlayerMixin.on_player_state_changed"
        )
        logger.debug("Player state changed: %s", state_name)

    def on_player_error(self) -> None:
        """Обработка ошибки плеера."""
        error = self._media_player.errorString()
        if error:
            self.player_info_label.setText(f"❌ Ошибка: {error}")
            self.player_info_label.setStyleSheet("color: red; margin: 5px;")

    def on_position_slider_moved(self, value: int) -> None:
        """Перемотка по слайдеру."""
        duration = self._media_player.duration()
        if duration > 0:
            position = int(value / 1000 * duration)
            self._media_player.setPosition(position)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

__all__ = [
    "PlayerMixin",
]
