import logging
import os
import unittest

from parameterized import parameterized, param

from autocut.cut import Cutter
from config import TestArgs, TEST_VIDEO_PATH, TEST_VIDEO_FILE_SIMPLE, TEST_CONTENT_PATH


class TestCut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.info("检查测试文件是否正常存在")
        scan_file = os.listdir(TEST_VIDEO_PATH)
        logging.info("应存在文件列表：" + str(TEST_VIDEO_FILE_SIMPLE) +
                     "  扫描到文件列表：" + str(scan_file))
        for file in TEST_VIDEO_FILE_SIMPLE:
            assert file in scan_file

    def tearDown(self):
        for file in TEST_VIDEO_FILE_SIMPLE:
            if os.path.exists(TEST_VIDEO_PATH+file.split('.')[0]+'_cut.mp4'):
                os.remove(TEST_VIDEO_PATH+file.split('.')[0]+'_cut.mp4')

    @parameterized.expand([param(file) for file in TEST_VIDEO_FILE_SIMPLE])
    def test_srt_cut(self, file_name):
        args = TestArgs()
        args.inputs = [TEST_VIDEO_PATH+file_name, TEST_CONTENT_PATH+file_name.split('.')[0]+'_srt.srt']
        cut = Cutter(args)
        cut.run()
        self.assertTrue(os.path.exists(TEST_VIDEO_PATH+file_name.split('.')[0]+'_cut.mp4'))

    @parameterized.expand([param(file) for file in TEST_VIDEO_FILE_SIMPLE])
    def test_md_cut(self, file_name):
        args = TestArgs()
        args.inputs = [TEST_VIDEO_PATH+file_name, TEST_CONTENT_PATH+file_name.split('.')[0]+'.srt',
                       TEST_CONTENT_PATH+file_name.split('.')[0]+'_md.md']
        cut = Cutter(args)
        cut.run()
        self.assertTrue(os.path.exists(TEST_VIDEO_PATH+file_name.split('.')[0]+'_cut.mp4'))
