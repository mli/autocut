import argparse
import logging
import os

from . import utils


def main():
    parser = argparse.ArgumentParser(
        description="Edit videos based on transcribed subtitles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    logging.basicConfig(
        format="[autocut:%(filename)s:L%(lineno)d] %(levelname)-6s %(message)s"
    )
    logging.getLogger().setLevel(logging.INFO)

    parser.add_argument("inputs", type=str, nargs="+", help="Inputs filenames/folders")
    parser.add_argument(
        "-t",
        "--transcribe",
        help="Transcribe videos/audio into subtitles",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-c",
        "--cut",
        help="Cut a video based on subtitles",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-d",
        "--daemon",
        help="Monitor a folder to transcribe and cut",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-s",
        help="Convert .srt to a compact format for easier editing",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-m",
        "--to-md",
        help="Convert .srt to .md for easier editing",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="zh",
        choices=["zh", "en"],
        help="The output language of transcription",
    )
    parser.add_argument(
        "--prompt", type=str, default="", help="initial prompt feed into whisper"
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="small",
        choices=["tiny", "base", "small", "medium", "large", "large-v2"],
        help="The whisper model used to transcribe.",
    )
    parser.add_argument(
        "--bitrate",
        type=str,
        default="10m",
        help="The bitrate to export the cutted video, such as 10m, 1m, or 500k",
    )
    parser.add_argument(
        "--vad", help="If or not use VAD", choices=["1", "0", "auto"], default="auto"
    )
    parser.add_argument(
        "--force",
        help="Force write even if files exist",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--encoding", type=str, default="utf-8", help="Document encoding format"
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cpu", "cuda"],
        help="Force to CPU or GPU for transcribing. In default automatically use GPU if available.",
    )

    args = parser.parse_args()

    if args.transcribe:
        from .transcribe import Transcribe

        Transcribe(args).run()
    elif args.to_md:
        from .utils import trans_srt_to_md

        if len(args.inputs) == 2:
            [input_1, input_2] = args.inputs
            base, ext = os.path.splitext(input_1)
            if ext != ".srt":
                input_1, input_2 = input_2, input_1
            trans_srt_to_md(args.encoding, args.force, input_1, input_2)
        elif len(args.inputs) == 1:
            trans_srt_to_md(args.encoding, args.force, args.inputs[0])
        else:
            logging.warn(
                "Wrong number of files, please pass in a .srt file or an additional video file"
            )
    elif args.cut:
        from .cut import Cutter

        Cutter(args).run()
    elif args.daemon:
        from .daemon import Daemon

        Daemon(args).run()
    elif args.s:
        utils.compact_rst(args.inputs[0], args.encoding)
    else:
        logging.warn("No action, use -c, -t or -d")


if __name__ == "__main__":
    main()
