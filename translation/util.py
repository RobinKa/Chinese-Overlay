import re
from functools import lru_cache


def get_pinyin(text):
    """Returns the pinyin for the given chinese text."""
    import pinyin
    return pinyin.get(text)


def get_all_phrase_translations(text):
    """Returns the dictionary translation for all possible
    phrase combinations in the given chinese text."""
    import pinyin.cedict
    return pinyin.cedict.all_phrase_translations(text)


def get_translate_fn(src_lang="zh-CN", dst_lang="en"):
    """Returns a function that google-translates text from a
    source to a target language. This implementation also caches
    its results."""
    from googletrans import Translator as GoogleTranslator
    translator = GoogleTranslator()

    @lru_cache(maxsize=None)
    def google_translate(text):
        return translator.translate(text, src=src_lang, dest=dst_lang).text

    return google_translate


def contains_chinese(text):
    """Returns whether the given text contains any chinese characters."""
    return re.search(u'[\u4e00-\u9fff]', text)
