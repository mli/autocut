import logging
import os
import unittest

from parameterized import parameterized, param

from autocut.cut import Cutter
from config import TestArgs, TEST_MEDIA_PATH, TEST_MEDIA_FILE_SIMPLE, TEST_CONTENT_PATH


class TestCut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.info("检查测试文件是否正常存在")
        scan_file = os.listdir(TEST_MEDIA_PATH)
        logging.info(
            "应存在文件列表："
            + str(TEST_MEDIA_FILE_SIMPLE)
            + "  扫描到文件列表："
            + str(scan_file)
        )
        for file in TEST_MEDIA_FILE_SIMPLE:
            assert file in scan_file

    def tearDown(self):
        for file in TEST_MEDIA_FILE_SIMPLE:
            namepart = os.path.join(
                TEST_MEDIA_PATH, os.path.splitext(file)[0] + "_cut."
            )
            if os.path.exists(namepart + "mp4"):
                os.remove(namepart + "mp4")
            if os.path.exists(namepart + "mp3"):
                os.remove(namepart + "mp3")

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE_SIMPLE])
    def test_srt_cut(self, file_name):
        args = TestArgs()
        args.inputs = [
            os.path.join(TEST_MEDIA_PATH, file_name),
            os.path.join(TEST_CONTENT_PATH, "test_srt.srt"),
        ]
        cut = Cutter(args)
        cut.run()
        namepart = os.path.join(
            TEST_MEDIA_PATH, os.path.splitext(file_name)[0] + "_cut."
        )
        self.assertTrue(
            os.path.exists(namepart + "mp4") or os.path.exists(namepart + "mp3")
        )

    @parameterized.expand([param(file) for file in TEST_MEDIA_FILE_SIMPLE])
    def test_md_cut(self, file_name):
        args = TestArgs()
        args.inputs = [
            TEST_MEDIA_PATH + file_name,
            os.path.join(TEST_CONTENT_PATH, "test.srt"),
            os.path.join(TEST_CONTENT_PATH, "test_md.md"),
        ]
        cut = Cutter(args)
        cut.run()
        namepart = os.path.join(
            TEST_MEDIA_PATH, os.path.splitext(file_name)[0] + "_cut."
        )
        self.assertTrue(
            os.path.exists(namepart + "mp4") or os.path.exists(namepart + "mp3")
        )
