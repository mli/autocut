import logging
import os

# 定义一个日志收集器
logger = logging.getLogger()
# 设置收集器的级别，不设定的话，默认收集warning及以上级别的日志
logger.setLevel("DEBUG")
# 设置日志格式
fmt = logging.Formatter("%(filename)s-%(lineno)d-%(asctime)s-%(levelname)s-%(message)s")
# 设置日志处理器-输出到文件,并且设置编码格式
if not os.path.exists("./log"):
    os.makedirs("./log")
file_handler = logging.FileHandler("./log/log.txt", encoding="utf-8")
# 设置日志处理器级别
file_handler.setLevel("DEBUG")
# 处理器按指定格式输出日志
file_handler.setFormatter(fmt)
# 输出到控制台
ch = logging.StreamHandler()
# 设置日志处理器级别
ch.setLevel("DEBUG")
# 处理器按指定格式输出日志
ch.setFormatter(fmt)
# 收集器和处理器对接，指定输出渠道
# 日志输出到文件
logger.addHandler(file_handler)
# 日志输出到控制台
logger.addHandler(ch)

TEST_VIDEO_PATH = "./test/video/"
TEST_CONTENT_PATH = "./test/content/"
TEST_VIDEO_FILE = ["test001.mp4", "test002.mov", "test003.mkv", "test004.flv"]
TEST_VIDEO_FILE_LANG = ["test001_en.mp4"]
TEST_VIDEO_FILE_SIMPLE = ["test001.mp4"]


class TestArgs:
    def __init__(
        self,
        encoding="utf-8",
        sampling_rate=16000,
        bitrate="10m",
        lang="zh",
        prompt="",
        whisper_model="small",
        device=None,
        vad=False,
        force=False,
    ):
        self.inputs = []
        self.bitrate = bitrate
        self.encoding = encoding
        self.sampling_rate = sampling_rate
        self.lang = lang
        self.prompt = prompt
        self.whisper_model = whisper_model
        self.device = device
        self.vad = vad
        self.force = force
