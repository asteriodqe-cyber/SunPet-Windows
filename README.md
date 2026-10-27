# 太对了 · SunPet Windows 版

mac 桌宠 [SunPet](https://github.com/Ganzhe2028/SunPet)（孙宇晨「太对了」）的 Windows 移植。点头像说一句，拖着换位置，右键调设置。不联网，不要权限，不占任务栏。

仅 Windows 10/11 64 位。安装包见 [Releases](../../releases)。

![face](Assets/face.png)

## 装

1. 从 [Releases](../../releases/latest) 下载最新的 `SunPet-1.1.0-Setup.exe`
2. 双击安装（免管理员权限，默认装进 `%LOCALAPPDATA%\Programs\SunPet`）
3. 装好自动启动；之后从开始菜单「太对了 SunPet」打开

第一次打开若有 SmartScreen 提示，点「更多信息 → 仍要运行」——只是因为没买代码签名证书，不是有毒。

## 怎么玩

| 动作 | 会发生什么 |
| --- | --- |
| 点一下头像 | 随机说一句。28 句播完一轮之前不重复 |
| 拖着头像 | 换个位置，退出后还记得 |
| 右键头像 / 右键托盘图标 | 全部设置 |
| 单击托盘图标 | 直接说一句 |

设置项：随机/固定播一句、挑句子、勾选排除某句（不参与轮播）、音量、头像大中小、移回屏幕右下角、退出。托盘右键可正常卸载。

## 和 Mac 版的差异

原版是 Swift/AppKit、仅 macOS 14+ Apple Silicon，无法直接在 Windows 编译，本仓库是它的**功能移植**（PySide6/Qt）：

- ✅ 移植：随机轮播、固定句、挑句、排除句、音量、大小、位置记忆、透明置顶悬浮窗、说话时摇头+字幕气泡、托盘、单实例
- ❌ 未移植：摇笔记本触发（依赖苹果机身加速度计）、三桌宠互相捧哏（依赖 macOS DistributedNotificationCenter）

## 自己编译

需要 Python 3.10+ 和 [Inno Setup 7](https://jrsoftware.org/isdl.php)（只做 exe 不打出安装包的话可以没有）：

```bat
build.bat
```

或手动：

```bash
pip install PySide6 PyInstaller
python -m PyInstaller --noconfirm --clean --windowed --name SunPet --icon app.ico --add-data "Assets;Assets" SunPet.py
"C:\Program Files\Inno Setup 7\ISCC.exe" installer.iss
```

产物：`dist\SunPet\`（绿色版文件夹）或 `installer_output\SunPet-1.1.0-Setup.exe`（安装包）。

自检：`dist\SunPet\SunPet.exe --self-test`，校验 28 段音频齐全且时长正常，输出 `PASS`。

## 素材来源与声明

- 本移植基于原仓库 [Ganzhe2028/SunPet](https://github.com/Ganzhe2028/SunPet)（代码 MIT），素材与原仓库相同：B 站[《对话孙宇晨：年轻人如何抓住 AI 时代的机会？》](https://www.bilibili.com/video/BV1fcHD6cEw3/)中 28 个时间点的原声截取
- **音频和头像的版权属于原权利人，不在 MIT 许可范围内**，仅作学习交流和玩梗，请勿商用
- 原权利人如觉得不合适，请开 issue，会移除

## License

代码 MIT，见 [LICENSE](LICENSE)。素材版权归原权利人所有。
