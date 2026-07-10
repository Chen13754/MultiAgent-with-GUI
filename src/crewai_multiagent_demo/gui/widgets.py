from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


PLATA_ORANGE = QColor("#ff5a14")
PLATA_LINK = QColor("#2414e8")
PLATA_PURPLE = QColor("#7b2cff")
PLATA_RED = QColor("#ff2d55")
PLATA_SUCCESS = QColor("#15c76f")
PLATA_WARNING = QColor("#ff3b30")
TEXT_DARK = QColor("#090a0d")
TEXT_MUTED = QColor("#7b7f89")
PANEL_LINE = QColor(9, 10, 13, 18)


class GlassPanel(QFrame):
    """Shared rounded panel used by the Plata-inspired desktop UI."""

    def __init__(self, object_name: str = "GlassPanel") -> None:
        super().__init__()
        self.setObjectName(object_name)
        self.setFrameShape(QFrame.Shape.StyledPanel)


class PlataPanel(GlassPanel):
    def __init__(self, object_name: str = "PlataPanel") -> None:
        super().__init__(object_name)


class MetricCard(GlassPanel):
    def __init__(self, title: str, value: str = "-") -> None:
        super().__init__("MetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("MetricTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_status(self, status: str) -> None:
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class PulseButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self._phase = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setInterval(32)
        self._timer.timeout.connect(self._tick)

    def set_pulsing(self, active: bool) -> None:
        self._active = active
        if active and not self._timer.isActive():
            self._timer.start()
        elif not active:
            self._timer.stop()
            self._phase = 0.0
            self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.018) % 1.0
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt override.
        super().paintEvent(event)
        if not self._active or not self.isEnabled():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width() * 0.42
        x = -width + (self.width() + width * 2) * self._phase
        gradient = QLinearGradient(x, 0, x + width, 0)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 96))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(x, 1, width, self.height() - 2), 18, 18)


class PlataStatusBadge(QLabel):
    def __init__(self, text: str = "", status: str = "neutral") -> None:
        super().__init__(text)
        self.setObjectName("PlataStatusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        self.setProperty("status", status)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class AgentCreditCard(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("AgentCreditCard")
        self.model = "-"
        self.status = "待运行"
        self.tasks = "0"
        self.elapsed = "-"
        self.progress = 0
        self.active_agent = "等待启动"
        self._shine = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(34)
        self._timer.timeout.connect(self._tick)
        self.setMinimumHeight(215)

    def set_metrics(
        self,
        *,
        model: str,
        status: str,
        tasks: str,
        elapsed: str,
        progress: int,
        active_agent: str | None = None,
    ) -> None:
        self.model = model
        self.status = status
        self.tasks = tasks
        self.elapsed = elapsed
        self.progress = max(0, min(100, progress))
        if active_agent:
            self.active_agent = active_agent
        if status == "运行中" and not self._timer.isActive():
            self._timer.start()
        elif status != "运行中":
            self._timer.stop()
            self._shine = 0.0
        self.update()

    def _tick(self) -> None:
        self._shine = (self._shine + 0.018) % 1.0
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt override.
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#fffafa"))
        gradient.setColorAt(0.34, QColor("#eef7ff"))
        gradient.setColorAt(0.68, QColor("#eaffdf"))
        gradient.setColorAt(1.0, QColor("#ffe6ef"))
        painter.setPen(QPen(QColor(9, 10, 13, 20), 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 24, 24)

        painter.setPen(QPen(QColor(255, 90, 20, 190), 2))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 24, 24)

        if self._timer.isActive():
            width = rect.width() * 0.36
            x = rect.left() - width + (rect.width() + width * 2) * self._shine
            shine = QLinearGradient(x, rect.top(), x + width, rect.top())
            shine.setColorAt(0.0, QColor(255, 255, 255, 0))
            shine.setColorAt(0.5, QColor(255, 255, 255, 115))
            shine.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shine)
            painter.drawRoundedRect(QRectF(x, rect.top(), width, rect.height()), 24, 24)

        painter.setPen(PLATA_ORANGE)
        brand = QFont("Segoe UI", 28, QFont.Weight.Bold)
        brand.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        painter.setFont(brand)
        painter.drawText(rect.adjusted(26, 22, -20, -20), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, "AGENT")

        painter.setPen(QColor("#090a0d"))
        painter.setFont(QFont("Microsoft YaHei UI", 12, QFont.Weight.DemiBold))
        painter.drawText(rect.adjusted(28, 84, -28, -20), Qt.AlignmentFlag.AlignLeft, f"模型 {self.model}")
        painter.setFont(QFont("Microsoft YaHei UI", 11))
        painter.setPen(TEXT_MUTED)
        painter.drawText(rect.adjusted(28, 116, -28, -20), Qt.AlignmentFlag.AlignLeft, f"当前 {self.active_agent}")

        bar = QRectF(rect.left() + 28, rect.bottom() - 42, rect.width() - 56, 8)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(9, 10, 13, 22))
        painter.drawRoundedRect(bar, 4, 4)
        painter.setBrush(PLATA_ORANGE)
        painter.drawRoundedRect(QRectF(bar.left(), bar.top(), bar.width() * self.progress / 100, bar.height()), 4, 4)

        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.DemiBold))
        painter.setPen(QColor("#090a0d"))
        painter.drawText(rect.adjusted(28, -54, -28, -20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, self.status)
        painter.drawText(rect.adjusted(28, -54, -28, -20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, f"{self.progress}%")

        painter.setPen(QColor(9, 10, 13, 95))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(rect.adjusted(28, -26, -28, -8), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, f"任务 {self.tasks}")
        painter.drawText(rect.adjusted(28, -26, -28, -8), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, f"耗时 {self.elapsed}")


class MotionEventList(QListWidget):
    EVENT_COLORS = {
        "run_started": PLATA_ORANGE,
        "task_completed": PLATA_SUCCESS,
        "run_completed": PLATA_SUCCESS,
        "run_failed": PLATA_WARNING,
    }

    def add_motion_item(self, text: str, event_type: str) -> None:
        item = QListWidgetItem(text)
        accent = self.EVENT_COLORS.get(event_type, PLATA_ORANGE)
        item.setForeground(TEXT_DARK)
        item.setBackground(QColor(accent.red(), accent.green(), accent.blue(), 22))
        item.setData(Qt.ItemDataRole.UserRole, event_type)
        self.addItem(item)
        self.scrollToBottom()


class AnimatedAgentGraph(QWidget):
    def __init__(self, *, reduced_motion: bool = False) -> None:
        super().__init__()
        self.setObjectName("AgentGraph")
        self.setMinimumHeight(320)
        self.reduced_motion = reduced_motion
        self.running = False
        self.progress = 0
        self.phase = 0.0
        self.active_index = 0
        self.status = "idle"
        self.events: list[dict[str, Any]] = []
        self.agent_names = ["分析", "策略", "评审", "总结"]
        self._timer = QTimer(self)
        self._timer.setInterval(32)
        self._timer.timeout.connect(self._tick)
        if not reduced_motion:
            self._timer.start()

    def reset(self) -> None:
        self.events.clear()
        self.progress = 0
        self.phase = 0.0
        self.active_index = 0
        self.status = "idle"
        self.running = False
        self.update()

    def set_running(self, running: bool) -> None:
        self.running = running
        self.status = "running" if running else self.status
        if running and not self.reduced_motion and not self._timer.isActive():
            self._timer.start()
        self.update()

    def set_progress(self, progress: int) -> None:
        self.progress = max(0, min(100, progress))
        completed = max(0, sum(1 for event in self.events if event.get("type") == "task_completed"))
        self.active_index = min(3, completed)
        self.update()

    def handle_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type == "run_started":
            self.status = "running"
            self.running = True
            self.active_index = 0
        elif event_type == "task_completed":
            self.active_index = min(3, self.active_index + 1)
        elif event_type == "run_completed":
            self.status = "succeeded"
            self.running = False
            self.progress = 100
        elif event_type == "run_failed":
            self.status = "failed"
            self.running = False
        self.events.append(event)
        self.events = self.events[-5:]
        self.update()

    def set_completed(self) -> None:
        self.status = "succeeded"
        self.running = False
        self.progress = 100
        self.active_index = 3
        self.update()

    def set_failed(self) -> None:
        self.status = "failed"
        self.running = False
        self.update()

    def _tick(self) -> None:
        self.phase = (self.phase + 0.012) % 1.0
        self.update()

    def _points(self) -> list[tuple[float, float]]:
        w = max(1, self.width())
        h = max(1, self.height())
        return [
            (w * 0.18, h * 0.64),
            (w * 0.38, h * 0.30),
            (w * 0.66, h * 0.38),
            (w * 0.80, h * 0.70),
        ]

    def _path(self) -> QPainterPath:
        points = self._points()
        path = QPainterPath()
        path.moveTo(*points[0])
        path.cubicTo(
            self.width() * 0.26,
            self.height() * 0.16,
            self.width() * 0.28,
            self.height() * 0.34,
            *points[1],
        )
        path.cubicTo(
            self.width() * 0.48,
            self.height() * 0.18,
            self.width() * 0.56,
            self.height() * 0.56,
            *points[2],
        )
        path.cubicTo(
            self.width() * 0.75,
            self.height() * 0.18,
            self.width() * 0.70,
            self.height() * 0.82,
            *points[3],
        )
        return path

    def paintEvent(self, event: Any) -> None:  # noqa: N802 - Qt override.
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_backdrop(painter)
        path = self._path()
        self._paint_path(painter, path)
        self._paint_pulses(painter, path)
        self._paint_nodes(painter)
        self._paint_event_cards(painter)

    def _paint_backdrop(self, painter: QPainter) -> None:
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QColor("#ffffff"))
        gradient.setColorAt(0.56, QColor("#fff8f2"))
        gradient.setColorAt(1.0, QColor("#f4f5f9"))
        painter.setPen(QPen(PANEL_LINE, 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(QPen(QColor(255, 90, 20, 24), 1))
        for index in range(4):
            y = rect.top() + 38 + index * 58
            painter.drawLine(int(rect.left() + 24), int(y), int(rect.right() - 24), int(y + 18))

    def _paint_path(self, painter: QPainter, path: QPainterPath) -> None:
        painter.setPen(QPen(QColor(255, 90, 20, 42), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)
        color = PLATA_WARNING if self.status == "failed" else PLATA_SUCCESS if self.status == "succeeded" else PLATA_ORANGE
        painter.setPen(QPen(color, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)

    def _paint_pulses(self, painter: QPainter, path: QPainterPath) -> None:
        if self.reduced_motion or not self.running:
            return
        for offset in (0.0, 0.34, 0.68):
            percent = (self.phase + offset) % 1.0
            point = path.pointAtPercent(percent)
            alpha = int(160 * (1.0 - abs(0.5 - percent) * 0.7))
            glow = QRadialGradient(point, 20)
            glow.setColorAt(0.0, QColor(255, 90, 20, alpha))
            glow.setColorAt(1.0, QColor(255, 90, 20, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(point, 20, 20)

    def _paint_nodes(self, painter: QPainter) -> None:
        for index, (x, y) in enumerate(self._points()):
            active = index == self.active_index and self.status == "running"
            done = self.status == "succeeded" or index < self.active_index
            failed = self.status == "failed" and index == self.active_index
            accent = PLATA_WARNING if failed else PLATA_SUCCESS if done else PLATA_ORANGE if active else QColor("#b9bcc4")
            radius = 24
            if active and not self.reduced_motion:
                radius += 3 + math.sin(self.phase * math.tau) * 2
            glow = QRadialGradient(x, y, radius + 18)
            glow.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), 90))
            glow.setColorAt(1.0, QColor(accent.red(), accent.green(), accent.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(QRectF(x - radius - 16, y - radius - 16, (radius + 16) * 2, (radius + 16) * 2))

            painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 170), 1.5))
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(x - 24, y - 24, 48, 48))
            painter.setBrush(accent)
            painter.setPen(Qt.PenStyle.NoPen)
            if done:
                painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
                painter.setPen(QColor("#ffffff"))
                painter.setBrush(accent)
                painter.drawEllipse(QRectF(x - 12, y - 12, 24, 24))
                painter.drawText(QRectF(x - 12, y - 13, 24, 24), Qt.AlignmentFlag.AlignCenter, "✓")
            else:
                painter.drawEllipse(QRectF(x - 7, y - 7, 14, 14))

            painter.setPen(TEXT_DARK)
            font = QFont("Microsoft YaHei UI", 9)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            label_rect = QRectF(x - 48, y + 31, 96, 24)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self.agent_names[index])

    def _paint_event_cards(self, painter: QPainter) -> None:
        if not self.events:
            painter.setPen(TEXT_MUTED)
            painter.setFont(QFont("Microsoft YaHei UI", 10))
            painter.drawText(
                QRectF(24, 18, self.width() - 48, 28),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "等待工作流事件...",
            )
            return

        painter.setFont(QFont("Microsoft YaHei UI", 8))
        base_x = self.width() * 0.58
        base_y = 22
        for offset, item in enumerate(reversed(self.events[-4:])):
            event_type = str(item.get("type", ""))
            accent = {
                "run_started": ACCENT_CYAN,
                "task_completed": ACCENT_GREEN,
                "run_completed": ACCENT_GREEN,
                "run_failed": ACCENT_CORAL,
            }.get(event_type, PLATA_ORANGE)
            x = base_x + (offset % 2) * 22
            y = base_y + offset * 45
            rect = QRectF(x, y, self.width() * 0.34, 34)
            painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 70), 1))
            painter.setBrush(QColor(255, 255, 255, 218))
            painter.drawRoundedRect(rect, 8, 8)
            painter.setPen(accent)
            painter.drawLine(int(rect.left() + 10), int(rect.top() + 9), int(rect.left() + 10), int(rect.bottom() - 9))
            painter.setPen(TEXT_DARK)
            text = str(item.get("agent") or item.get("type") or "event")
            painter.drawText(rect.adjusted(20, 0, -10, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class PlataBottomSheet(QDialog):
    def __init__(self, parent: QWidget, title: str, message: str, primary_text: str = "完成") -> None:
        super().__init__(parent)
        self.setObjectName("PlataBottomSheet")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        icon = QLabel("✓")
        icon.setObjectName("SheetSuccessIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignHCenter)

        title_label = QLabel(title)
        title_label.setObjectName("SheetTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setObjectName("SheetMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        primary = QPushButton(primary_text)
        primary.setObjectName("PrimaryButton")
        primary.clicked.connect(self.accept)
        layout.addWidget(primary)
        self.setFixedWidth(430)


def show_success_sheet(parent: QWidget, title: str, message: str, primary_text: str = "完成") -> None:
    sheet = PlataBottomSheet(parent, title, message, primary_text)
    sheet.exec()


def fade_in(widget: QWidget, duration: int = 160) -> QPropertyAnimation:
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation
