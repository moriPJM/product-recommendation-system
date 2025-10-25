"""
このファイルは、画面表示以外の様々な関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import logging
from typing import List
import constants as ct

# SudachiPyは条件付きインポート
try:
    from sudachipy import tokenizer, dictionary
    SUDACHI_AVAILABLE = True
except ImportError:
    SUDACHI_AVAILABLE = False


############################################################
# 関数定義
############################################################

def build_error_message(message):
    """
    エラーメッセージと管理者問い合わせテンプレートの連結

    Args:
        message: 画面上に表示するエラーメッセージ

    Returns:
        エラーメッセージと管理者問い合わせテンプレートの連結テキスト
    """
    return "\n".join([message, ct.COMMON_ERROR_MESSAGE])


def preprocess_func(text):
    """
    形態素解析による日本語の単語分割
    Args:
        text: 単語分割対象のテキスト
    
    Returns:
        単語分割を実施後のテキスト
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    if SUDACHI_AVAILABLE:
        try:
            # SudachiPyによる形態素解析を試行
            tokenizer_obj = dictionary.Dictionary(dict="full").create()
            mode = tokenizer.Tokenizer.SplitMode.A
            tokens = tokenizer_obj.tokenize(text, mode)
            words = [token.surface() for token in tokens]
            words = list(set(words))
            return words
        except Exception as e:
            # SudachiPyでエラーが発生した場合は簡単な分割にフォールバック
            logger.warning(f"SudachiPyでエラーが発生しました。シンプルな分割にフォールバック: {str(e)}")
    
    # SudachiPyが利用できない場合やエラーの場合のフォールバック処理
    import re
    # 日本語文字、英数字、ひらがな、カタカナを含む単語を抽出
    words = re.findall(r'[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', text)
    return list(set(words)) if words else [text]