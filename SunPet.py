# -*- coding: utf-8 -*-
"""
SunPet「太对了」Windows 版
macOS 原版（Swift/AppKit）的移植：https://github.com/Ganzhe2028/SunPet

点头像说一句「太对了」，拖着换位置，右键调设置。
不联网，不要权限，不占任务栏。
mac 版独有的「机身摇晃」和跨桌宠「捧哏联动」依赖 Apple 硬件/通知中心，
Windows 版不含这两项，其余玩法一致。
"""
import json
import os
import random
import sys

from PySide6.QtCore import Qt, QTimer, QPoint, QSettings, QUrl, QElapsedTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap, QTransform, QCursor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QMenu,
    QSystemTrayIcon,
    QWidget,
    QWidgetAction,
)

APP_NAME = "太对了 · SunPet"
SERVER_NAME = "SunPet_SingleInstance_Ganzhe2028_v1"


def resource_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "Assets", name)


class PetWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Ganzhe2028", "SunPet")

        with open(resource_path("clips.json"), encoding="utf-8") as f:
            self.clips = json.load(f)
        if not self.clips:
            raise RuntimeError("clips.json 为空")

        self.face_pix = QPixmap(resource_path("face.png"))
        if self.face_pix.isNull():
            raise RuntimeError("face.png 缺失")

        # ---- 状态 ----
        self.volume = float(self.settings.value("volume", 0.65))
        self.size = int(self.settings.value("size", 180))
        self.random_mode = self.settings.value("randomMode", "true") == "true"
        self.pinned_id = self._to_int(self.settings.value("pinnedID"))
        self.excluded = set(
            self._to_int_list(self.settings.value("excludedIDs", []))
        )
        self.bag = []
        self.last_id = None
        self.dragged = False
        self._drag_offset = QPoint()
        self.phase = 0.0
        self._base_pix = None  # 当前尺寸缩放好的头像

        # ---- 窗口 ----
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setToolTip("点击随机播放一句 · 拖动移动 · 右键设置")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.resize(self.size, self.size + 48)

        self.face_label = QLabel(self)
        self.caption_label = QLabel(self)
        self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.caption_label.setStyleSheet(
            "background: rgba(0,0,0,184); border-radius: 10px;"
            " color: white; font-size: 12px; padding: 2px 6px;"
        )
        self.caption_label.hide()

        # ---- 音频 ----
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)
        self.player.playbackStateChanged.connect(self._playback_state_changed)
        self.player.mediaStatusChanged.connect(self._media_status_changed)

        # ---- 动画 ----
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self._wobble_tick)

        self.caption_timer = QTimer(self)
        self.caption_timer.setSingleShot(True)
        self.caption_timer.timeout.connect(self.caption_label.hide)

        # ---- 托盘 ----
        self.tray = QSystemTrayIcon(QIcon(self.face_pix), self)
        self.tray.setToolTip(APP_NAME)
        self._tray_menu = QMenu()
        self._tray_menu.aboutToShow.connect(self._rebuild_tray_menu)
        self.tray.setContextMenu(self._tray_menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

        # ---- 位置 ----
        self._restore_position()
        self.show()

        QTimer.singleShot(400, lambda: self.show_caption("点我一下 · 右键设置", 5))

    # ---------- 工具 ----------
    @staticmethod
    def _to_int(v):
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int_list(v):
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            out = []
            for x in v:
                try:
                    out.append(int(x))
                except (TypeError, ValueError):
                    pass
            return out
        return [int(v)]

    def _rescale_face(self):
        self._base_pix = self.face_pix.scaled(
            self.size - 24,
            self.size - 52,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.face_label.setPixmap(self._base_pix)
        self.face_label.move(12, 40)
        self.face_label.resize(self.size - 24, self.size - 52)
        self.caption_label.setGeometry(4, 4, self.size - 8, 34)

    def resizeEvent(self, event):
        self._rescale_face()
        super().resizeEvent(event)

    # ---------- 字幕 ----------
    def show_caption(self, text: str, seconds: float = 3.0):
        self.caption_timer.stop()
        self.caption_label.setText(text)
        self.caption_label.adjustSize()
        w = min(self.caption_label.width() + 12, self.size - 8)
        self.caption_label.resize(w, 34)
        self.caption_label.move((self.size - w) // 2, 4)
        self.caption_label.show()
        self.caption_timer.start(int(seconds * 1000))

    # ---------- 动画 ----------
    def _playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.animate(False)

    def _media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.InvalidMedia:
            self.animate(False)
            self.show_caption("播放失败：音频无法解码", 5)

    def animate(self, enabled: bool):
        self.phase = 0.0
        if enabled:
            if not self.anim_timer.isActive():
                self.anim_timer.start()
        else:
            self.anim_timer.stop()
            if self._base_pix:
                self.face_label.setPixmap(self._base_pix)

    def _wobble_tick(self):
        import math

        self.phase += 0.38
        angle = math.sin(self.phase) * 3.15  # 弧度 0.055 ≈ 3.15°
        bounce = abs(math.sin(self.phase)) * 3
        cx = self._base_pix.width() / 2
        cy = self._base_pix.height() / 2
        t = (
            QTransform()
            .translate(cx, cy - bounce)
            .rotate(angle)
            .translate(-cx, -cy)
        )
        self.face_label.setPixmap(self._base_pix.transformed(
            t, Qt.TransformationMode.SmoothTransformation
        ))

    # ---------- 播放 ----------
    def clip_by_id(self, cid):
        for c in self.clips:
            if c["id"] == cid:
                return c
        return None

    def pin_valid(self):
        return self.pinned_id is not None and self.clip_by_id(self.pinned_id)

    def play_next(self):
        if not self.random_mode and self.pin_valid():
            self.play(self.clip_by_id(self.pinned_id))
            return
        self.play_random()

    def play_random(self):
        pool = [i for i, c in enumerate(self.clips) if c["id"] not in self.excluded]
        if not pool:
            return
        self.bag = [i for i in self.bag if i in pool]
        if not self.bag:
            self.bag = pool[:]
            random.shuffle(self.bag)
            if len(self.bag) > 1 and self.clips[self.bag[-1]]["id"] == self.last_id:
                self.bag[0], self.bag[-1] = self.bag[-1], self.bag[0]
        self.play(self.clips[self.bag.pop()])

    def play(self, clip):
        self.player.stop()
        path = resource_path(os.path.join("Clips", clip["file"]))
        if not os.path.exists(path):
            self.animate(False)
            self.show_caption("播放失败：找不到音频文件", 5)
            return
        self.player.setSource(QUrl.fromLocalFile(path))
        self.audio_out.setVolume(self.volume)
        self.player.play()
        self.last_id = clip["id"]
        self.animate(True)
        self.show_caption(clip["label"], clip["duration"] + 0.5)

    # ---------- 交互 ----------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragged = False
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - (
                self.frameGeometry().topLeft() + self._drag_offset
            )
            if self.dragged or delta.manhattanLength() > 4:
                self.dragged = True
                self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragged:
                self._save_position()
            else:
                self.play_next()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self._popup_menu(event.globalPos())

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.play_next()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.play_next()

    # ---------- 菜单 ----------
    def _mode_title(self):
        if self.random_mode or not self.pin_valid():
            return "固定播一句"
        c = self.clip_by_id(self.pinned_id)
        return "固定播一句（%02d %s）" % (c["id"], c["label"])

    def _build_menu(self, menu: QMenu):
        menu.clear()

        title = menu.addAction("孙宇晨 · 太对了（%d句）" % len(self.clips))
        title.setEnabled(False)

        mode_menu = menu.addMenu("播放方式")
        mode_group = QActionGroup(mode_menu)
        act_rand = mode_menu.addAction("随机一句（一轮不重复）")
        act_rand.setCheckable(True)
        act_rand.setChecked(self.random_mode)
        act_fix = mode_menu.addAction(self._mode_title())
        act_fix.setCheckable(True)
        act_fix.setChecked(not self.random_mode)
        for a in (act_rand, act_fix):
            mode_group.addAction(a)
        act_rand.triggered.connect(lambda: self.set_mode(True))
        act_fix.triggered.connect(lambda: self.set_mode(False))

        choose_menu = menu.addMenu("挑一句")
        choose_group = QActionGroup(choose_menu)
        choose_group.setExclusive(False)
        if not self.random_mode:
            hint = choose_menu.addAction("点任意一句＝固定播这句")
            hint.setEnabled(False)
            choose_menu.addSeparator()
        for c in self.clips:
            a = choose_menu.addAction("%02d  %s" % (c["id"], c["label"]))
            a.setCheckable(True)
            a.setChecked(not self.random_mode and self.pinned_id == c["id"])
            choose_group.addAction(a)
            a.triggered.connect(lambda checked=False, clip=c: self.choose_clip(clip))

        filter_menu = menu.addMenu("轮播内容")
        hint = filter_menu.addAction("取消勾选＝不参与随机播")
        hint.setEnabled(False)
        filter_menu.addSeparator()
        for c in self.clips:
            wa = QWidgetAction(filter_menu)
            box = QCheckBox("%02d  %s" % (c["id"], c["label"]))
            box.setChecked(c["id"] not in self.excluded)
            box.toggled.connect(lambda checked, cid=c["id"]: self.toggle_excluded(cid, checked))
            wa.setDefaultWidget(box)
            filter_menu.addAction(wa)
        filter_menu.addSeparator()
        act_all = filter_menu.addAction("全部恢复")
        act_all.triggered.connect(self.enable_all_clips)

        menu.addAction("随机播一次", self.play_random)
        menu.addAction("停止播放", self.stop_playing)
        menu.addSeparator()

        vol_menu = menu.addMenu("音量")
        vol_group = QActionGroup(vol_menu)
        for n in (0, 25, 50, 65, 80, 100):
            label = "静音" if n == 0 else "%d%%" % n
            a = vol_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(abs(self.volume - n / 100) < 0.01)
            vol_group.addAction(a)
            a.triggered.connect(lambda checked=False, v=n / 100: self.set_volume(v))

        size_menu = menu.addMenu("头像大小")
        size_group = QActionGroup(size_menu)
        for name, n in (("小", 130), ("中", 180), ("大", 240)):
            a = size_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked(self.size == n)
            size_group.addAction(a)
            a.triggered.connect(lambda checked=False, s=n: self.set_size(s))

        menu.addAction("移回屏幕右下角", self.reset_position)
        menu.addSeparator()
        menu.addAction("退出桌宠", QApplication.instance().quit)

    def _popup_menu(self, pos):
        m = QMenu()
        self._build_menu(m)
        m.exec(pos)

    def _rebuild_tray_menu(self):
        self._build_menu(self._tray_menu)

    # ---------- 设置动作 ----------
    def choose_clip(self, clip):
        if not self.random_mode:
            self.pinned_id = clip["id"]
            self.settings.setValue("pinnedID", clip["id"])
        self.play(clip)

    def set_mode(self, random_mode: bool):
        self.random_mode = random_mode
        if not random_mode and not self.pin_valid():
            self.pinned_id = (self.clip_by_id(self.last_id) or self.clips[0])["id"]
        self.settings.setValue("randomMode", "true" if random_mode else "false")
        if self.pinned_id is not None:
            self.settings.setValue("pinnedID", self.pinned_id)
        if random_mode:
            self.show_caption("播放方式：随机一句", 4)
        else:
            c = self.clip_by_id(self.pinned_id)
            self.show_caption("已固定：%02d %s" % (c["id"], c["label"]), 4)

    def toggle_excluded(self, cid: int, checked: bool):
        if checked:
            self.excluded.discard(cid)
        else:
            if len(self.excluded) >= len(self.clips) - 1:
                self.show_caption("至少留一句在轮播里", 3)
                # 把勾状态改回去：找到对应 checkbox 不易，直接重建菜单即可
                self._rebuild_open_menus()
                return
            self.excluded.add(cid)
        self.settings.setValue("excludedIDs", sorted(self.excluded))
        self.bag = []

    def _rebuild_open_menus(self):
        # 菜单正在弹出时不能清空重建；用提示代替即可，下次打开会反映状态
        pass

    def enable_all_clips(self):
        self.excluded.clear()
        self.settings.setValue("excludedIDs", [])
        self.bag = []
        self.show_caption("轮播已恢复全部", 2)

    def stop_playing(self):
        self.player.stop()
        self.caption_timer.stop()
        self.caption_label.hide()
        self.animate(False)

    def set_volume(self, v: float):
        self.volume = v
        self.audio_out.setVolume(v)
        self.settings.setValue("volume", v)

    def set_size(self, s: int):
        self.size = max(120, min(260, s))
        self.resize(self.size, self.size + 48)
        self.settings.setValue("size", self.size)
        self._save_position()

    def reset_position(self):
        rect = QApplication.primaryScreen().availableGeometry()
        self.move(rect.right() - self.size - 32, rect.bottom() - self.height() - 24)
        self._save_position()

    def _save_position(self):
        self.settings.setValue("pos", self.pos())

    def _restore_position(self):
        pos = self.settings.value("pos")
        if pos is not None:
            p = QPoint(pos)
            rect = QApplication.primaryScreen().availableGeometry()
            if rect.contains(p):
                self.move(p)
                return
        self.reset_position()

    def closeEvent(self, event):
        self._save_position()
        super().closeEvent(event)


def run_self_test(app) -> int:
    """--self-test：校验资源完整性，打印 PASS/FAIL。"""
    ok = True
    checks = []
    with open(resource_path("clips.json"), encoding="utf-8") as f:
        clips = json.load(f)
    checks.append("clips=%d" % len(clips))
    for c in clips:
        p = resource_path(os.path.join("Clips", c["file"]))
        d = c.get("duration", 0)
        if not os.path.exists(p):
            ok = False
            checks.append("FAIL clip %d missing %s" % (c["id"], c["file"]))
        elif not (0.25 < d < 7):
            ok = False
            checks.append("FAIL clip %d bad duration %.3f" % (c["id"], d))
    checks.append("PASS" if ok else "FAIL")
    print("\n".join(checks))
    return 0 if ok else 1


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SunPet")
    app.setOrganizationName("Ganzhe2028")
    app.setQuitOnLastWindowClosed(False)

    if "--self-test" in sys.argv:
        sys.exit(run_self_test(app))

    # 单实例：已有一个在跑就直接退出
    sock = QLocalSocket()
    sock.connectToServer(SERVER_NAME)
    if sock.waitForConnected(200):
        sys.exit(0)
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)

    win = PetWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
