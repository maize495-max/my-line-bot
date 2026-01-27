import os
import json
import gspread
from flask import Flask, request, abort
from google.oauth2.service_account import Credentials

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    StickerMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
)

app = Flask(__name__)

# =========================
# LINE設定
# =========================
conf = Configuration(
    access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
)
handler = WebhookHandler(
    os.environ.get("LINE_CHANNEL_SECRET")
)

# =========================
# Google Sheets
# =========================
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    json_str = os.environ.get("GOOGLE_SHEETS_JSON")
    if not json_str:
        raise ValueError("GOOGLE_SHEETS_JSON 未設定")

    credentials = Credentials.from_service_account_info(
        json.loads(json_str), scopes=scopes
    )
    gc = gspread.authorize(credentials)
    return gc.open("line_bot_memory").sheet1


# =========================
# Webhook
# =========================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


# =========================
# テキスト受信
# =========================
@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event):
    raw_text = event.message.text
    norm = (
        raw_text.replace(" ", "")
        .replace("　", "")
        .replace("：", ":")
        .replace("，", ",")
        .replace("、", ",")
    )

    sheet = get_sheet()
    replies = []

    # 固定返信
    if norm == "お疲れ様":
        replies.append(StickerMessage(packageId=446, stickerId=1989))
        replies.append(TextMessage(text="今日もお疲れ様！"))

    # 学習トリガー
    elif norm.startswith("教える:"):
        keyword = norm.replace("教える:", "")
        if keyword:
            # 学習待ち状態を保存
            sheet.append_row([f"__WAIT__{event.source.user_id}", keyword])
            replies.append(
                TextMessage(text="OK！次に覚えさせたいスタンプを送ってね 👍")
            )
        else:
            replies.append(
                TextMessage(text="教える:キーワード の形で送ってね")
            )

    # 検索
    else:
        records = sheet.get_all_records()
        found = None
        for r in records:
            k = str(r["keyword"]).replace(" ", "").replace("　", "")
            if k == norm:
                found = r["response"]
                break

        if found:
            if found.startswith("STK:"):
                _, pkg, stk = found.split(":")[0], *found.replace("STK:", "").split(",")
                replies.append(
                    StickerMessage(
                        packageId=int(pkg.strip()),
                        stickerId=int(stk.strip()),
                    )
                )
            else:
                replies.append(TextMessage(text=found))
        else:
            replies.append(TextMessage(text="まだ知らないな〜 教えて？"))

    send_reply(event.reply_token, replies)


# =========================
# スタンプ受信（学習用）
# =========================
@handler.add(MessageEvent, message=StickerMessageContent)
def handle_sticker(event):
    sheet = get_sheet()
    records = sheet.get_all_records()

    wait_key = f"__WAIT__{event.source.user_id}"
    keyword = None
    row_index = None

    for i, r in enumerate(records, start=2):
        if r["keyword"] == wait_key:
            keyword = r["response"]
            row_index = i
            break

    if not keyword:
        return

    package_id = event.message.package_id
    sticker_id = event.message.sticker_id

    # 学習内容を書き換え
    sheet.update(f"A{row_index}", keyword)
    sheet.update(f"B{row_index}", f"STK:{package_id},{sticker_id}")

    send_reply(
        event.reply_token,
        [
            TextMessage(
                text=f"「{keyword}」にスタンプを覚えたよ！"
            )
        ],
    )


# =========================
# 返信共通処理
# =========================
def send_reply(token, messages):
    with ApiClient(conf) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=token,
                messages=messages[:5],
            )
        )


# =========================
# 起動
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)