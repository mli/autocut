import logging
import os
import unittest

from parameterized import parameterized, param

from autocut.utils import MD
from config import (
    TEST_MEDIA_FILE,
    TestArgs,
    TEST_MEDIA_FILE_SIMPLE,
    TEST_MEDIA_FILE_LANG,
    TEST_MEDIA_PATH,
)
from autocut.transcribe import Transcribe


class TestTranscribe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.info("检查测试文件是否正常存在")
        scan_file = os.listdir(TEST_MEDIA_PATH)
        logging.info(
            "应存在文件列表："
            + str(TEST_MEDIA_FILE)
            + str(TEST_MEDIA_FILE_LANG)
            + str(TEST_MEDIA_FILE_SIMPLE)
            + "  扫描到文件列表："
            + str(scan_file)
        )
        for file in TEST_MEDIA_FILE:
            assert file in scan_file
        for file in TEST_MEDIA_FILE_LANG:
            assert file in scan_file
        for file in TEST_MEDIA_FILE_SIMPLE:
            assert file in scan_file

    @classmethod
    def tearDownClass(cls):
        for file in os.listdir(TEST_MEDIA_PATH):
            if file.endswith("md") or file.endswith("srt"):
                os.remove(TEST_MEDIA_PATH + file)

    def tearDown(self):
        for file in TEST_MEDIA_FILE_SIMPLE:
            if os.path.exists(TEST_MEDIA_PATH + file.split(".")[0] + ".md"):
                os.remove(TEST_MEDIA_PATH + file.split(".")[0] + ".md")
            if os.path.exists(TEST_MEDIA_PATH + file.split(".")[0] + ".srt"):
                os.remove(TEST_MEDIA_PATH + file.split(".")[0] + ".srt")

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE])
    def test_default_transcribe(self, file_name):
        logging.info("检查默认参数生成字幕")
        args = TestArgs()
        args.inputs = [TEST_MEDIA_PATH + file_name]
        transcribe = Transcribe(args)
        transcribe.run()
        self.assertTrue(
            os.path.exists(TEST_MEDIA_PATH + file_name.split(".")[0] + ".md")
        )

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE])
    def test_jump_done_transcribe(self, file_name):
        logging.info("检查默认参数跳过生成字幕")
        args = TestArgs()
        args.inputs = [TEST_MEDIA_PATH + file_name]
        transcribe = Transcribe(args)
        transcribe.run()
        self.assertTrue(
            os.path.exists(TEST_MEDIA_PATH + file_name.split(".")[0] + ".md")
        )

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE_LANG])
    def test_en_transcribe(self, file_name):
        logging.info("检查--lang='en'参数生成字幕")
        args = TestArgs()
        args.lang = "en"
        args.inputs = [TEST_MEDIA_PATH + file_name]
        transcribe = Transcribe(args)
        transcribe.run()
        self.assertTrue(
            os.path.exists(TEST_MEDIA_PATH + file_name.split(".")[0] + ".md")
        )

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE_LANG])
    def test_force_transcribe(self, file_name):
        logging.info("检查--force参数生成字幕")
        args = TestArgs()
        args.force = True
        args.inputs = [TEST_MEDIA_PATH + file_name]
        md0_lens = len(
            "".join(
                MD(
                    TEST_MEDIA_PATH + file_name.split(".")[0] + ".md", args.encoding
                ).lines
            )
        )
        transcribe = Transcribe(args)
        transcribe.run()
        md1_lens = len(
            "".join(
                MD(
                    TEST_MEDIA_PATH + file_name.split(".")[0] + ".md", args.encoding
                ).lines
            )
        )
        self.assertLessEqual(md1_lens, md0_lens)

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE_SIMPLE])
    def test_encoding_transcribe(self, file_name):
        logging.info("检查--encoding参数生成字幕")
        args = TestArgs()
        args.encoding = "gbk"
        args.inputs = [TEST_MEDIA_PATH + file_name]
        transcribe = Transcribe(args)
        transcribe.run()
        with open(
            os.path.join(TEST_MEDIA_PATH + file_name.split(".")[0] + ".md"),
            encoding="gbk",
        ):
            self.assertTrue(True)

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE_SIMPLE])
    def test_vad_transcribe(self, file_name):
        logging.info("检查--vad参数生成字幕")
        args = TestArgs()
        args.force = True
        args.vad = True
        args.inputs = [TEST_MEDIA_PATH + file_name]
        transcribe = Transcribe(args)
        transcribe.run()
        self.assertTrue(
            os.path.exists(TEST_MEDIA_PATH + file_name.split(".")[0] + ".md")
        )
