@echo off
:: Download Twemoji SVGs for use as flap_printer 'emoji' flaps.
:: Each line is independent -- copy, comment out, or add lines as needed.
:: Output: assets/emoji/<name>.svg
:: Browse emoji at: https://twemoji-cheatsheet.vercel.app/
::                  https://emojipedia.org  (select Twemoji style)
::
:: If emoji characters in this file get garbled, use --codepoints instead:
::   python pvv_tools\download_emoji.py --codepoints 2764-fe0f --name heart
:: Codepoints are shown on each emoji's emojipedia.org page.

pushd "%~dp0\.."
call .venv\Scripts\activate.bat
chcp 65001 > nul

REM python pvv_tools\download_emoji.py "❤️"  --name heart
REM python pvv_tools\download_emoji.py "👋🏽"
REM python pvv_tools\download_emoji.py "🐔" --name chicken
REM python pvv_tools\download_emoji.py "😂" --name joy
REM python pvv_tools\download_emoji.py "😭" --name sob
REM python pvv_tools\download_emoji.py "🙏" --name pray
REM python pvv_tools\download_emoji.py "🤣" --name rofl
REM python pvv_tools\download_emoji.py "👍" --name thumbs_up
REM python pvv_tools\download_emoji.py "😘" --name kiss
REM python pvv_tools\download_emoji.py "😊" --name smile
REM python pvv_tools\download_emoji.py "😍" --name heart_eyes
REM python pvv_tools\download_emoji.py "🥰" --name smiling_face_with_hearts
REM python pvv_tools\download_emoji.py "😉" --name wink
python pvv_tools\download_emoji.py "💀" --name skull

popd