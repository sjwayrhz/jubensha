"""剧本 PDF 解析管线：文字版直接提取，扫描版走 OCR。

method 返回值： "text"（文字提取） | "ocr"（OCR 识别）。
"""
import io
import logging
from typing import Protocol

log = logging.getLogger("jubensha.parse")


def extract_text(pdf_path: str) -> str:
    """用 PyMuPDF 提取 PDF 全文（按页拼接）。"""
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError("未安装 PyMuPDF，请 pip install PyMuPDF") from e
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise RuntimeError(f"PDF 打开失败：{e}") from e
    parts: list[str] = []
    with doc:
        for page in doc:
            parts.append(page.get_text("text"))
    return "\n".join(parts).strip()


class OCRBackend(Protocol):
    """OCR 后端接口：输入单页图片字节，返回识别文本。"""

    def ocr_image(self, image_bytes: bytes) -> str: ...


class PaddleOCRBackend:
    """默认 OCR 实现：PaddleOCR 中文识别。

    首次运行会自动下载模型（需要能访问外网 / 代理）。
    兼容 PaddleOCR 2.x（ocr()）与 3.x（predict()）两种 API。
    """

    def __init__(self, lang: str = "ch") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise RuntimeError(
                "未安装 paddleocr，请 pip install paddleocr paddlepaddle"
            ) from e
        log.info("初始化 PaddleOCR（首次运行会下载模型，请耐心等待）…")
        # use_textline_orientation 取代了旧版 use_angle_cls（3.x）；2.x 用 use_angle_cls
        try:
            self._engine = PaddleOCR(use_textline_orientation=True, lang=lang)
        except TypeError:
            self._engine = PaddleOCR(use_angle_cls=True, lang=lang)
        self._use_predict = hasattr(self._engine, "predict")

    def ocr_image(self, image_bytes: bytes) -> str:
        import numpy as np
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        arr = np.array(img)
        if self._use_predict:
            # PaddleOCR 3.x
            out = self._engine.predict(arr)
            texts: list[str] = []
            for item in out or []:
                data = item.json if hasattr(item, "json") else item
                if isinstance(data, dict):
                    texts.extend(data.get("rec_texts", []))
            return "\n".join(t for t in texts if t).strip()
        # PaddleOCR 2.x
        out = self._engine.ocr(arr, cls=True)
        texts = []
        for line in out[0] if out and out[0] else []:
            # line: [bbox, (text, confidence)]
            try:
                texts.append(line[1][0])
            except (IndexError, TypeError):
                continue
        return "\n".join(t for t in texts if t).strip()


def ocr_pdf(pdf_path: str, backend: OCRBackend | None = None) -> str:
    """把 PDF 每页渲染成图片，逐页 OCR 后拼接。"""
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError("未安装 PyMuPDF，请 pip install PyMuPDF") from e
    backend = backend or PaddleOCRBackend()
    parts: list[str] = []
    doc = fitz.open(pdf_path)
    with doc:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            text = backend.ocr_image(img_bytes)
            log.info("OCR 第 %d 页完成，%d 字", i + 1, len(text))
            parts.append(text)
    return "\n".join(parts).strip()


def parse_pdf(
    pdf_path: str,
    text_threshold: int = 200,
    ocr_backend: OCRBackend | None = None,
) -> tuple[str, str]:
    """解析 PDF，返回 (全文, method)。

    先尝试文字提取；有效字符数 < text_threshold 则判定为扫描版，走 OCR。
    OCR 失败/未安装时抛清晰错误，不静默跳过。
    """
    text = extract_text(pdf_path)
    if len(text) >= text_threshold:
        log.info("文字版 PDF，直接提取 %d 字", len(text))
        return text, "text"
    log.info("文字提取仅 %d 字（阈值 %d），判定为扫描版，走 OCR", len(text), text_threshold)
    try:
        ocr_text = ocr_pdf(pdf_path, backend=ocr_backend)
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"OCR 识别失败：{e}") from e
    if not ocr_text:
        raise RuntimeError("OCR 未识别出任何文字，请检查 PDF 是否为有效扫描件")
    return ocr_text, "ocr"
