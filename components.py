
"""
このファイルは、画面表示に特化した関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import logging
import streamlit as st
import constants as ct


############################################################
# 関数定義
############################################################

def display_app_title():
    """
    タイトル表示
    """
    st.markdown(f"## {ct.APP_NAME}")


def display_initial_ai_message():
    """
    AIメッセージの初期表示
    """
    with st.chat_message("assistant", avatar=ct.AI_ICON_FILE_PATH):
        st.markdown("こちらは対話型の商品レコメンド生成AIアプリです。「こんな商品が欲しい」という情報・要望を画面下部のチャット欄から送信いただければ、おすすめの商品をレコメンドいたします。")
        st.markdown("**入力例**")
        st.info("""
        - 「長時間使える、高音質なワイヤレスイヤホン」
        - 「机のライト」
        - 「USBで充電できる加湿器」
        """)


def display_conversation_log():
    """
    会話ログの一覧表示
    """
    for message in st.session_state.messages:
        if message["role"] == "user":
            with st.chat_message("user", avatar=ct.USER_ICON_FILE_PATH):
                st.markdown(message["content"])
        else:
            with st.chat_message("assistant", avatar=ct.AI_ICON_FILE_PATH):
                display_product(message["content"])


def display_product(result):
    """
    商品情報の表示

    Args:
        result: LLMからの回答
    """
    logger = logging.getLogger(ct.LOGGER_NAME)

    try:
        # resultが空またはNoneの場合のチェック
        if not result:
            st.error("商品情報を取得できませんでした。")
            return
        
        # resultの構造をログに記録（デバッグ用）
        logger.info(f"result type: {type(result)}")
        logger.info(f"result content: {result}")

        # resultがリストの場合、最初の要素を取得
        if isinstance(result, list) and len(result) > 0:
            logger.info(f"複数のドキュメントが返されました。件数: {len(result)}")
            # 最初のドキュメント（最も関連性が高い）を使用
            product_content = result[0].page_content
            logger.info(f"最初のドキュメントのpage_content: {product_content[:200]}...")
        elif hasattr(result, 'page_content'):
            product_content = result.page_content
        else:
            st.error("商品データの形式が不正です。")
            st.write("**デバッグ情報:**")
            st.write(f"データ型: {type(result)}")
            st.write(f"データ内容: {str(result)[:200]}...")
            return

        # 商品情報のパース
        product_lines = product_content.split("\n")
        product = {}
        
        # デバッグ：商品データの内容をログに記録
        logger.info(f"商品データの行数: {len(product_lines)}")
        logger.info(f"商品データの最初の5行: {product_lines[:5]}")
        
        for line in product_lines:
            if ": " in line:
                key, value = line.split(": ", 1)  # 最初の": "のみで分割
                product[key] = value
                logger.debug(f"解析成功: {key} = {value}")
            elif line.strip():  # 空行でない場合
                logger.warning(f"解析できない行: {line}")

        # デバッグ：解析された商品情報をログに記録
        logger.info(f"解析された商品フィールド: {list(product.keys())}")
        
        # 必須フィールドの確認
        required_fields = ['name', 'price', 'id']
        missing_fields = [field for field in required_fields if field not in product]
        
        if missing_fields:
            st.error(f"必須項目が不足しています: {', '.join(missing_fields)}")
            st.write("**利用可能なフィールド:**")
            st.write(list(product.keys()))
            st.write("**商品データの生の内容:**")
            st.code(product_content[:500] + "..." if len(product_content) > 500 else product_content)
            return

        st.markdown("以下の商品をご提案いたします。")

        # 「商品名」と「価格」と「在庫状況」
        stock_info = ""
        stock_message = ""
        if 'stock_status' in product:
            stock_status = product['stock_status']
            if stock_status == "あり":
                stock_info = " ✅ **在庫あり**"
            elif stock_status == "残りわずか":
                stock_info = " ⚠️ **残りわずか**"
                stock_message = "⚠️ ご好評につき、在庫数が残りわずかです。購入をご希望の場合、お早めのご注文をおすすめいたします。"
            elif stock_status == "なし":
                stock_info = " ❌ **在庫なし**"
                stock_message = "❗ 申し訳ございませんが、本商品は在庫切れとなっております。入荷まで もうしばらくお待ちください。"

        st.success(f"""
                商品名：{product['name']}（商品ID: {product['id']}）\n
                価格：{product['price']}{stock_info}
        """)

        # 在庫状況の詳細メッセージ表示
        if stock_message:
            if stock_status == "残りわずか":
                st.warning(stock_message)
            elif stock_status == "なし":
                st.error(stock_message)

        # 「商品カテゴリ」と「メーカー」と「ユーザー評価」
        category = product.get('category', '未設定')
        maker = product.get('maker', '未設定')
        score = product.get('score', '未評価')
        review_number = product.get('review_number', '0')
        
        st.code(f"""
            商品カテゴリ：{category}\n
            メーカー：{maker}\n
            評価：{score}（{review_number}件）
        """, language=None, wrap_lines=True)

        # 商品画像
        if 'file_name' in product:
            try:
                st.image(f"images/products/{product['file_name']}", width=400)
            except Exception as img_error:
                logger.warning(f"画像の表示に失敗: {img_error}")
                st.warning("商品画像を表示できませんでした。")
        else:
            st.warning("商品画像情報がありません。")

        # 商品説明
        if 'description' in product:
            st.code(product['description'], language=None, wrap_lines=True)
        else:
            st.warning("商品説明がありません。")

        # おすすめ対象ユーザー
        if 'recommended_people' in product:
            st.markdown("**こんな方におすすめ！**")
            st.info(product["recommended_people"])

        # 商品ページのリンク
        st.link_button("商品ページを開く", type="primary", use_container_width=True, url="https://google.com")

    except Exception as e:
        # 詳細なエラー情報をログに記録
        error_msg = f"商品情報の表示中にエラーが発生: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # ユーザーにエラー情報を表示
        st.error("商品情報の表示に失敗しました。")
        st.write("**エラーの詳細:**")
        st.write(f"エラータイプ: {type(e).__name__}")
        st.write(f"エラーメッセージ: {str(e)}")
        
        # デバッグ情報
        if 'result' in locals():
            st.write("**デバッグ情報:**")
            st.write(f"入力データ型: {type(result)}")
            st.write(f"入力データ: {str(result)[:500]}...")
        
        # エラーを再発生させて上位で処理
        raise