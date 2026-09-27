"""Create the silent one-minute demo video used for Homework 1 submission."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1280
HEIGHT = 720
FPS = 30

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRAME_DIR = PROJECT_ROOT / "_video_frames"
OUTPUT_DIR = PROJECT_ROOT / "demo"
OUTPUT_FILE = OUTPUT_DIR / "2412190733干宸骅-演示.mp4"

FONT_REGULAR = Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")
FONT_MONO = Path("C:/Windows/Fonts/CascadiaMono.ttf")

BACKGROUND = "#07111f"
PANEL = "#101c2c"
PANEL_LIGHT = "#16263a"
TEXT = "#eef6ff"
MUTED = "#9db0c7"
CYAN = "#32d6c6"
BLUE = "#5ea1ff"
GREEN = "#56d78b"
YELLOW = "#ffd166"
RED = "#ff6b78"


def font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_MONO if mono else FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(path), size=size)


def base_canvas(scene_number: int, label: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        amount = y / HEIGHT
        color = (
            int(7 + 7 * amount),
            int(17 + 13 * amount),
            int(31 + 24 * amount),
        )
        draw.line((0, y, WIDTH, y), fill=color)
    draw.rectangle((0, 0, WIDTH, 7), fill=CYAN)
    draw.text((58, 35), "SOFTWARE ENGINEERING · HOMEWORK 1", font=font(20, bold=True), fill=CYAN)
    draw.text((58, 664), "干宸骅 · 2412190733 · 计科2403", font=font(18), fill=MUTED)
    draw.text((1090, 35), f"{scene_number:02d}/07", font=font(18, mono=True), fill=MUTED)
    draw.text((1050, 664), label, font=font(18), fill=MUTED)
    return image, draw


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    draw.rounded_rectangle(box, radius=24, fill=PANEL, outline="#27415e", width=2)


def terminal_panel(
    draw: ImageDraw.ImageDraw,
    title: str,
    lines: list[tuple[str, str]],
    *,
    top: int = 120,
    bottom: int = 620,
) -> None:
    rounded_panel(draw, (70, top, 1210, bottom))
    draw.rounded_rectangle((70, top, 1210, top + 54), radius=24, fill=PANEL_LIGHT)
    draw.rectangle((70, top + 28, 1210, top + 54), fill=PANEL_LIGHT)
    for index, color in enumerate((RED, YELLOW, GREEN)):
        x = 102 + index * 28
        draw.ellipse((x, top + 19, x + 14, top + 33), fill=color)
    draw.text((190, top + 13), title, font=font(19, mono=True), fill=MUTED)
    y = top + 82
    for text, color in lines:
        draw.text((105, y), text, font=font(23, mono=False), fill=color)
        y += 43


def save_scene(number: int, duration: float, label: str, painter) -> tuple[Path, float]:
    image, draw = base_canvas(number, label)
    painter(draw)
    path = FRAME_DIR / f"scene_{number:02d}.png"
    image.save(path, quality=96)
    return path, duration


def build_scenes() -> list[tuple[Path, float]]:
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scenes: list[tuple[Path, float]] = []

    def title_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((72, 155), "代码审查 Agent", font=font(64, bold=True), fill=TEXT)
        draw.text((76, 252), "基于 DeepSeek 的多轮工具调用", font=font(34), fill=CYAN)
        draw.rounded_rectangle((76, 340, 590, 430), radius=18, fill=PANEL, outline="#2a4868")
        draw.text((108, 365), "输入  →  工具  →  分析  →  报告", font=font(27), fill=TEXT)
        draw.text((76, 490), "静音演示 · 时长少于 1 分钟", font=font(24), fill=MUTED)

    scenes.append(save_scene(1, 5.0, "项目介绍", title_scene))

    def architecture_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((70, 112), "Agent 如何工作", font=font(42, bold=True), fill=TEXT)
        items = [
            ("01", "用户提出代码审查要求", BLUE),
            ("02", "DeepSeek 判断需要调用的工具", CYAN),
            ("03", "读取文件并返回真实代码", YELLOW),
            ("04", "生成带行号与建议的审查报告", GREEN),
        ]
        y = 205
        for number, text, color in items:
            draw.rounded_rectangle((78, y, 1200, y + 72), radius=18, fill=PANEL, outline="#28435f")
            draw.rounded_rectangle((96, y + 13, 164, y + 59), radius=12, fill=color)
            draw.text((113, y + 20), number, font=font(20, bold=True), fill=BACKGROUND)
            draw.text((194, y + 17), text, font=font(28), fill=TEXT)
            y += 92

    scenes.append(save_scene(2, 8.0, "Agent 架构", architecture_scene))

    def command_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((70, 84), "真实 DeepSeek 请求", font=font(40, bold=True), fill=TEXT)
        terminal_panel(
            draw,
            "PowerShell · code-review-agent",
            [
                ("PS> py -3 -m code_review_agent --workspace .", TEXT),
                ("    --request \"先读取 buggy_calculator.py，", TEXT),
                ("    只报告最重要的三个问题\" --verbose", TEXT),
                ("", TEXT),
                ("正在连接 deepseek-flash ...", CYAN),
            ],
            top=150,
        )

    scenes.append(save_scene(3, 7.0, "运行命令", command_scene))

    def tool_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((70, 84), "Agent 自主调用工具", font=font(40, bold=True), fill=TEXT)
        terminal_panel(
            draw,
            "Tool execution",
            [
                ("[1/1] read_file", CYAN),
                ("path: examples/buggy_calculator.py", TEXT),
                ("result: 13 lines · read successfully", GREEN),
                ("", TEXT),
                ("DeepSeek 正在基于真实文件生成结论 ...", YELLOW),
            ],
            top=150,
        )

    scenes.append(save_scene(4, 6.0, "工具调用", tool_scene))

    def report_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((70, 80), "审查结果", font=font(40, bold=True), fill=TEXT)
        findings = [
            ("高", "第 6 行", "eval 可执行任意代码", "改用受限表达式解析", RED),
            ("高", "第 2 行", "除数为零时程序异常", "显式检查并报告错误", RED),
            ("中", "第 12 行", "裸 except 掩盖真实错误", "只捕获预期异常", YELLOW),
        ]
        headers = [(92, "等级"), (210, "位置"), (380, "问题"), (820, "建议")]
        draw.rounded_rectangle((70, 150, 1210, 210), radius=16, fill="#1d3550")
        for x, text in headers:
            draw.text((x, 164), text, font=font(23, bold=True), fill=CYAN)
        y = 225
        for severity, location, problem, suggestion, color in findings:
            draw.rounded_rectangle((70, y, 1210, y + 96), radius=16, fill=PANEL, outline="#28435f")
            draw.rounded_rectangle((92, y + 25, 152, y + 70), radius=12, fill=color)
            draw.text((110, y + 31), severity, font=font(21, bold=True), fill=BACKGROUND)
            draw.text((210, y + 31), location, font=font(23), fill=MUTED)
            draw.text((380, y + 31), problem, font=font(23), fill=TEXT)
            draw.text((820, y + 31), suggestion, font=font(22), fill=GREEN)
            y += 112
        draw.text((72, 590), "工具调用：read_file", font=font(23), fill=CYAN)

    scenes.append(save_scene(5, 17.0, "审查报告", report_scene))

    def quality_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((70, 92), "工程质量与安全边界", font=font(40, bold=True), fill=TEXT)
        features = [
            ("3", "只读代码工具"),
            ("8", "最大 Agent 决策轮数"),
            ("11", "自动化测试全部通过"),
            ("0", "API Key 进入 Git 的次数"),
        ]
        x_positions = [70, 360, 650, 940]
        for x, (value, caption) in zip(x_positions, features):
            draw.rounded_rectangle((x, 210, x + 250, 455), radius=22, fill=PANEL, outline="#28435f", width=2)
            draw.text((x + 32, 240), value, font=font(68, bold=True), fill=CYAN)
            draw.multiline_text((x + 30, 342), caption, font=font(23), fill=TEXT, spacing=8)
        draw.text((72, 520), "路径隔离 · 文件大小限制 · 接口重试 · 会话记忆", font=font(28), fill=GREEN)

    scenes.append(save_scene(6, 9.0, "验证结果", quality_scene))

    def closing_scene(draw: ImageDraw.ImageDraw) -> None:
        draw.text((72, 170), "演示完成", font=font(62, bold=True), fill=TEXT)
        draw.text((76, 272), "Code Review Agent · DeepSeek", font=font(34), fill=CYAN)
        draw.rounded_rectangle((76, 370, 955, 442), radius=16, fill=PANEL, outline="#28435f")
        draw.text((105, 390), "github.com/Citlali37/code-review-agent", font=font(27, mono=True), fill=BLUE)
        draw.text((76, 500), "源代码、设计文档、测试与 PSP 记录均已提交", font=font(26), fill=MUTED)

    scenes.append(save_scene(7, 5.0, "完成", closing_scene))
    return scenes


def encode_video(scenes: list[tuple[Path, float]]) -> None:
    concat_file = FRAME_DIR / "concat.txt"
    lines: list[str] = []
    for scene_path, duration in scenes:
        lines.append(f"file '{scene_path.name}'")
        lines.append(f"duration {duration:.2f}")
    lines.append(f"file '{scenes[-1][0].name}'")
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    total_duration = sum(duration for _, duration in scenes)

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_file.name,
        "-vf",
        f"fps={FPS},format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-movflags",
        "+faststart",
        "-an",
        "-t",
        f"{total_duration:.2f}",
        str(OUTPUT_FILE),
    ]
    subprocess.run(command, cwd=FRAME_DIR, check=True)


def main() -> None:
    missing_fonts = [path for path in (FONT_REGULAR, FONT_BOLD, FONT_MONO) if not path.exists()]
    if missing_fonts:
        raise FileNotFoundError(f"Missing fonts: {missing_fonts}")
    scenes = build_scenes()
    encode_video(scenes)
    print(f"Created {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
