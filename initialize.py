"""
このファイルは、最初の画面読み込み時にのみ実行される初期化処理が記述されたファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from uuid import uuid4
import sys
import unicodedata
from dotenv import load_dotenv
import streamlit as st
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
import utils
import constants as ct


############################################################
# 設定関連
############################################################
load_dotenv()


############################################################
# 関数定義
############################################################

def initialize():
    """
    画面読み込み時に実行する初期化処理
    """
    # 初期化データの用意
    initialize_session_state()
    # ログ出力用にセッションIDを生成
    initialize_session_id()
    # ログ出力の設定
    initialize_logger()
    # RAGのRetrieverを作成
    initialize_retriever()


def initialize_logger():
    """
    ログ出力の設定
    """
    os.makedirs(ct.LOG_DIR_PATH, exist_ok=True)
    
    logger = logging.getLogger(ct.LOGGER_NAME)

    if logger.hasHandlers():
        return

    log_handler = TimedRotatingFileHandler(
        os.path.join(ct.LOG_DIR_PATH, ct.LOG_FILE),
        when="D",
        encoding="utf8"
    )
    formatter = logging.Formatter(
        f"[%(levelname)s] %(asctime)s line %(lineno)s, in %(funcName)s, session_id={st.session_state.session_id}: %(message)s"
    )
    log_handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)


def initialize_session_id():
    """
    セッションIDの作成
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid4().hex


def initialize_session_state():
    """
    初期化データの用意
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []


def initialize_retriever():
    """
    Retrieverを作成
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    if "retriever" in st.session_state:
        return
    
    try:
        # CSVファイルの読み込み
        loader = CSVLoader(ct.RAG_SOURCE_PATH, encoding="utf-8")
        docs = loader.load()
        
        # デバッグ：CSVLoaderの出力形式を確認
        logger.info(f"CSVから読み込まれたドキュメント数: {len(docs)}")
        if docs:
            logger.info(f"最初のドキュメントのpage_content（最初の200文字）: {docs[0].page_content[:200]}")
            logger.info(f"最初のドキュメントのmetadata: {docs[0].metadata}")
        
        # ドキュメントが空の場合のチェック
        if not docs:
            raise ValueError("CSVファイルからドキュメントを読み込めませんでした")

        # OSがWindowsの場合、Unicode正規化と、cp932（Windows用の文字コード）で表現できない文字を除去
        for doc in docs:
            doc.page_content = adjust_string(doc.page_content)
            for key in doc.metadata:
                doc.metadata[key] = adjust_string(doc.metadata[key])

        docs_all = []
        for doc in docs:
            docs_all.append(doc.page_content)

        # OpenAI APIキーの確認
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません。Streamlit CloudのSecretsで設定してください。")

        # OpenAI Embeddingsの初期化
        embeddings = OpenAIEmbeddings()
        
        # ChromaDBとベクトル検索の初期化を試行
        retriever = None
        try:
            # Chromaデータベースの初期化（Streamlit Cloud対応）
            db = None
            try:
                # まず、より基本的な設定でChromaDBを初期化
                import chromadb
                from chromadb.config import Settings
                
                # メモリ内でのみ動作するクライアントを作成
                chroma_client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=None,
                    anonymized_telemetry=False
                ))
                
                # コレクション名を一意にするためにセッションIDを使用
                collection_name = f"products_{st.session_state.session_id[:8]}"
                
                db = Chroma.from_documents(
                    docs, 
                    embedding=embeddings,
                    client=chroma_client,
                    collection_name=collection_name
                )
                
            except Exception as chroma_error:
                logger.warning(f"ChromaDB初期化エラー: {chroma_error}")
                logger.info("代替方法でChromaDBを初期化します")
                
                # フォールバック：最小限の設定でChromaDBを初期化
                try:
                    db = Chroma.from_documents(
                        docs, 
                        embedding=embeddings
                    )
                except Exception as fallback_error:
                    logger.error(f"フォールバックChromaDB初期化も失敗: {fallback_error}")
                    db = None
            
            # dbが正常に作成された場合のみretrieverを作成
            if db is not None:
                retriever = db.as_retriever(search_kwargs={"k": ct.TOP_K})
                logger.info("ChromaDBベクトル検索の初期化が完了しました")
            else:
                logger.warning("ChromaDBの初期化に失敗しました")
            
        except Exception as vector_error:
            logger.error(f"ベクトル検索の初期化に失敗: {vector_error}")
            logger.info("BM25検索のみで続行します")
            retriever = None

        # BM25 Retrieverの初期化
        bm25_retriever = BM25Retriever.from_texts(
            docs_all,
            preprocess_func=utils.preprocess_func,
            k=ct.TOP_K
        )
        
        # Ensemble Retrieverの作成
        if retriever:
            # ChromaDBが正常に動作している場合
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, retriever],
                weights=ct.RETRIEVER_WEIGHTS
            )
            logger.info("EnsembleRetriever（BM25 + ChromaDB）の初期化が完了しました")
        else:
            # ChromaDBが利用できない場合はBM25のみを使用
            ensemble_retriever = bm25_retriever
            logger.warning("ChromaDBが利用できないため、BM25Retrieverのみを使用します")

        st.session_state.retriever = ensemble_retriever
        
        # 成功ログ
        if retriever:
            logger.info("Retrieverの初期化が完了しました（BM25 + ベクトル検索）")
        else:
            logger.info("Retrieverの初期化が完了しました（BM25のみ）")
        
    except Exception as e:
        # エラーの詳細をログに記録
        error_msg = f"Retrieverの初期化中にエラーが発生しました: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Streamlit Cloudでのデバッグ用に詳細なエラー情報を表示
        st.error(f"初期化エラーの詳細: {str(e)}")
        st.error("以下の項目を確認してください:")
        st.error("1. OPENAI_API_KEYがStreamlit CloudのSecretsに設定されているか")
        st.error("2. data/products.csvファイルが存在するか")
        st.error("3. 必要なパッケージがすべてインストールされているか")
        
        # 環境情報の表示
        st.write("**環境情報:**")
        st.write(f"- Python version: {sys.version}")
        st.write(f"- Current working directory: {os.getcwd()}")
        st.write(f"- Files in data directory: {os.listdir('data') if os.path.exists('data') else 'data directory not found'}")
        
        # エラーを再発生させて上位で処理
        raise


def adjust_string(s):
    """
    Windows環境でRAGが正常動作するよう調整
    
    Args:
        s: 調整を行う文字列
    
    Returns:
        調整を行った文字列
    """
    # 調整対象は文字列のみ
    if type(s) is not str:
        return s

    # OSがWindowsの場合、Unicode正規化と、cp932（Windows用の文字コード）で表現できない文字を除去
    if sys.platform.startswith("win"):
        s = unicodedata.normalize('NFC', s)
        s = s.encode("cp932", "ignore").decode("cp932")
        return s
    
    # OSがWindows以外の場合はそのまま返す
    return s