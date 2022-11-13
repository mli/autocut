import srt


class TranscribeMiddleware:
    def __init__(self, args, subs: list[srt.Subtitle]):
        self.args = args
        self.subs = subs
        self.SINGLE_SUB_CN_MAX_LEN = self.args.sub_cn_inline_limit
        self.MODAL_WORDS_CN = self.args.sub_cn_modal_words.strip()

    def run(self):
        if self.args.lang == "zh":
            if self.args.sub_cn_inline_limit > 0:
                self._sub_split_CN()

            if len(self.args.sub_cn_modal_words.strip()) > 0:
                self._sub_filter_modal_CN()

    def _sub_split_CN(self):
        import datetime
        import jionlp as jio

        new_subs = []

        for sub in self.subs:
            duration = (sub.end - sub.start).total_seconds()

            # sometimes zh-res will occur English comma
            sub_content_temp = sub.content.strip().replace(",", "，")
            # use jionlp[https://github.com/dongrixinyu/JioNLP] to split Chinese sentence
            sub_split_list = jio.split_sentence(sub_content_temp, criterion='fine')
            sub_len = len(sub_content_temp)

            # Sliding Window to control single sentence length, in the case of uniform speech speed
            interval_start = sub.start.total_seconds()
            interval_end = sub.start.total_seconds()
            interval_len = 0
            start_index = 0

            def _add_sub(target_index):
                new_subs.append(srt.Subtitle(index=0,
                                             start=datetime.timedelta(seconds=interval_start),
                                             end=datetime.timedelta(seconds=interval_end),
                                             content="".join(sub_split_list[start_index:target_index])))

            for index, sub_split_item in enumerate(sub_split_list):
                sub_split = sub_split_item.strip()

                if index > 0 and interval_len + len(sub_split) > self.SINGLE_SUB_CN_MAX_LEN + self.SINGLE_SUB_CN_MAX_LEN // 2:
                    _add_sub(index)
                    interval_start = interval_end
                    start_index = index
                    interval_len = 0

                interval_len = interval_len + len(sub_split)
                interval_end = interval_end + (len(sub_split) / sub_len) * duration

                if interval_len < self.SINGLE_SUB_CN_MAX_LEN + 1:
                    continue

                _add_sub(index + 1)
                interval_start = interval_end
                start_index = index + 1
                interval_len = 0

            if interval_len != 0:
                new_subs.append(srt.Subtitle(index=0,
                                             start=datetime.timedelta(seconds=interval_start),
                                             end=datetime.timedelta(seconds=interval_end),
                                             content="".join(sub_split_list[start_index:])))

        self.subs.clear()
        self.subs.extend(new_subs)

    def _sub_filter_modal_CN(self):
        import jionlp as jio
        import re

        key_list = [key.strip() for key in self.MODAL_WORDS_CN.split(",")]
        for sub in self.subs:
            # list of separate short sentence
            sub_split_list = jio.split_sentence(sub.content.strip().replace(",", "，"), criterion='fine')

            trigger = False
            new_sub_split_list = []
            for sub_split_item in sub_split_list:
                sub_split = sub_split_item.strip()
                # via jionlp, the last character is always text or punctuation
                last_word_index = -1 if re.match(r"^[\u4E00-\u9FA5A-Za-z0-9_]+$", sub_split[-1]) else -2

                if sub_split[last_word_index] in key_list:
                    trigger = True
                    temp = sub_split[:last_word_index]
                    if last_word_index == -2:
                        temp += sub_split[-1]
                    new_sub_split_list.append(temp)
                    continue

                new_sub_split_list.append(sub_split)

            if trigger:
                sub.content = "".join(new_sub_split_list)
