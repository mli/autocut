import srt


class TranscribeMiddleware:
    def __init__(self, args, subs: list[srt.Subtitle]):
        self.args = args
        self.subs = subs
        self.SINGLE_SUB_MAX_LEN = 16

    def run(self):
        if self.args.lang == "zh":
            if self.args.sub_optimize_cn:
                self._sub_split_CN()

            if len(self.args.modal_words_cn.strip()) > 0:
                self._sub_filter_modal_CN()

    def _sub_split_CN(self):
        import datetime

        new_subs = []

        for sub in self.subs:
            duration = (sub.end - sub.start).total_seconds()

            # for my opinion, the sub don't need any mood punctuation mark
            sub_content_temp = sub.content.strip() \
                .replace(",", "，").replace("。", "，").replace("！", "，").replace("？", "，")
            sub_split_list = sub_content_temp.split("，")
            sub_len = len(sub_content_temp) - sub_content_temp.count("，")

            # Sliding Window to control single sentence length
            interval_start = sub.start.total_seconds()
            interval_end = sub.start.total_seconds()
            interval_len = 0
            start_index = 0
            for index, sub_split in enumerate(sub_split_list):
                interval_end = interval_end + (len(sub_split) / sub_len) * duration
                interval_len = interval_len + len(sub_split) + 1

                if interval_len < self.SINGLE_SUB_MAX_LEN + 1:
                    continue

                new_subs.append(srt.Subtitle(index=0,
                                             start=datetime.timedelta(seconds=interval_start),
                                             end=datetime.timedelta(seconds=interval_end),
                                             content=sub_split if index == start_index
                                             else "，".join(sub_split_list[start_index:index + 1])))

                interval_start = interval_end
                start_index = index + 1
                interval_len = 0

            if interval_len != 0:
                new_subs.append(srt.Subtitle(index=0,
                                             start=datetime.timedelta(seconds=interval_start),
                                             end=datetime.timedelta(seconds=interval_end),
                                             content=sub.content.strip() if start_index == 0
                                             else "，".join(sub_split_list[start_index:])))

        self.subs.clear()
        self.subs.extend(new_subs)

    def _sub_filter_modal_CN(self):
        key_list = [key.strip() for key in self.args.modal_words_cn.split(",")]
        for sub in self.subs:
            for char in sub.content.strip():
                if char in key_list:
                    sub.content = sub.content.replace(char, "")
