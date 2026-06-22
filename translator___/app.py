import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from deep_translator import GoogleTranslator
from deep_translator.exceptions import LanguageNotSupportedException, RequestError

app = Flask(__name__)
CORS(app)

# Display Name -> Google Translate language code
# (free Google Translate web endpoint via deep-translator, no API key needed)
LANGUAGES = {
    "Auto-detect": "auto",
    "Afrikaans": "af", "Albanian": "sq", "Amharic": "am", "Arabic": "ar",
    "Armenian": "hy", "Azerbaijani": "az", "Basque": "eu", "Belarusian": "be",
    "Bengali": "bn", "Bosnian": "bs", "Bulgarian": "bg", "Catalan": "ca",
    "Cebuano": "ceb", "Chichewa": "ny", "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW", "Corsican": "co", "Croatian": "hr",
    "Czech": "cs", "Danish": "da", "Dutch": "nl", "English": "en",
    "Esperanto": "eo", "Estonian": "et", "Filipino": "tl", "Finnish": "fi",
    "French": "fr", "Frisian": "fy", "Galician": "gl", "Georgian": "ka",
    "German": "de", "Greek": "el", "Gujarati": "gu", "Haitian Creole": "ht",
    "Hausa": "ha", "Hawaiian": "haw", "Hebrew": "iw", "Hindi": "hi",
    "Hmong": "hmn", "Hungarian": "hu", "Icelandic": "is", "Igbo": "ig",
    "Indonesian": "id", "Irish": "ga", "Italian": "it", "Japanese": "ja",
    "Javanese": "jw", "Kannada": "kn", "Kazakh": "kk", "Khmer": "km",
    "Korean": "ko", "Kurdish (Kurmanji)": "ku", "Kyrgyz": "ky", "Lao": "lo",
    "Latin": "la", "Latvian": "lv", "Lithuanian": "lt", "Luxembourgish": "lb",
    "Macedonian": "mk", "Malagasy": "mg", "Malay": "ms", "Malayalam": "ml",
    "Maltese": "mt", "Maori": "mi", "Marathi": "mr", "Mongolian": "mn",
    "Myanmar (Burmese)": "my", "Nepali": "ne", "Norwegian": "no",
    "Odia (Oriya)": "or", "Pashto": "ps", "Persian": "fa", "Polish": "pl",
    "Portuguese": "pt", "Punjabi": "pa", "Romanian": "ro", "Russian": "ru",
    "Samoan": "sm", "Scots Gaelic": "gd", "Serbian": "sr", "Sesotho": "st",
    "Shona": "sn", "Sindhi": "sd", "Sinhala": "si", "Slovak": "sk",
    "Slovenian": "sl", "Somali": "so", "Spanish": "es", "Sundanese": "su",
    "Swahili": "sw", "Swedish": "sv", "Tajik": "tg", "Tamil": "ta",
    "Tatar": "tt", "Telugu": "te", "Thai": "th", "Turkish": "tr",
    "Turkmen": "tk", "Ukrainian": "uk", "Urdu": "ur", "Uyghur": "ug",
    "Uzbek": "uz", "Vietnamese": "vi", "Welsh": "cy", "Xhosa": "xh",
    "Yiddish": "yi", "Yoruba": "yo", "Zulu": "zu",
}


@app.route("/")
def index():
    return render_template("index.html", languages=list(LANGUAGES.keys()))


@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    src_lang = data.get("source_language", "Auto-detect")
    tgt_lang = data.get("target_language", "Spanish")

    if not text:
        return jsonify({"error": "No text provided"}), 400
    if not tgt_lang or tgt_lang == "Auto-detect":
        return jsonify({"error": "Please select a target language"}), 400
    if len(text) > 5000:
        return jsonify({"error": "Text exceeds 5000 character limit"}), 400

    src_code = LANGUAGES.get(src_lang, "auto")
    tgt_code = LANGUAGES.get(tgt_lang)

    if not tgt_code or tgt_code == "auto":
        return jsonify({"error": "Invalid target language"}), 400

    try:
        translated = GoogleTranslator(source=src_code, target=tgt_code).translate(text)
        if not translated:
            return jsonify({"error": "Translation returned empty result. Try again."}), 500
        return jsonify({
            "translation": translated,
            "source_language": src_lang,
            "target_language": tgt_lang,
        })

    except LanguageNotSupportedException:
        return jsonify({"error": "One of the selected languages isn't supported."}), 400
    except RequestError:
        return jsonify({"error": "Could not reach the translation service. Check your internet connection."}), 502
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/languages")
def languages():
    return jsonify({"languages": list(LANGUAGES.keys())})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
