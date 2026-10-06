import json, os, re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

KB = json.load(open(os.path.join(os.path.dirname(__file__), "kb.json"), encoding="utf-8"))
STOP = set("من في على هل ما ماذا كيف متى متي عن الى الي هو هي اذا كان ان لو ام او ثم هذا هذه التي الذي كم اين لماذا".split())
DIG = "٠١٢٣٤٥٦٧٨٩"

def norm(s):
    s = re.sub(r"[\u064B-\u065F\u0640]", "", s)
    s = re.sub(r"[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return "".join(str(DIG.index(c)) if c in DIG else c for c in s)

IDX = [(e, norm(e[1]), norm(e[2])) for e in KB]

def search(q, k=3):
    n = norm(q)
    nums = [int(x) for x in re.findall(r"\d+", n)]
    words = [re.sub(r"^(وال|بال|لل|ال)", "", w) for w in re.split(r"[^\u0621-\u064Aa-z0-9]+", n)
             if len(w) > 1 and not w.isdigit() and w not in STOP]
    words = [w for w in words if len(w) > 1]
    out = []
    for e, t, x in IDX:
        s = sum(3 for w in words if w in t) + sum(1 for w in words if w in x)
        a, *b = map(int, e[0].split("-"))
        b = b[0] if b else a
        s += sum(12 for n_ in nums if a <= n_ <= b)
        if s:
            out.append((s, e))
    return [e for _, e in sorted(out, key=lambda z: -z[0])[:k]]

def ai_answer(q, hits):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic
    ctx = "\n".join(f"[المواد {e[0]}] {e[1]}: {e[2]}" for e in hits)
    msg = anthropic.Anthropic(api_key=key).messages.create(
        model="claude-sonnet-5-5", max_tokens=700,
        messages=[{"role": "user", "content":
            "أجب بالعربية بإيجاز اعتماداً على نصوص مدونة الأحكام الشرعية في مسائل الأحوال الشخصية "
            "(المذهب الجعفري، العراق 2025) التالية فقط، واذكر أرقام المواد. إن لم تكفِ النصوص فقل ذلك.\n\n"
            f"السؤال: {q}\n\nالنصوص:\n{ctx}"}])
    return msg.content[0].text

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً ⚖️\nاسألني عن مدونة الأحكام الشرعية في الأحوال الشخصية (الجعفرية): "
        "زواج، طلاق، حضانة، وصية، ميراث… أو اكتب رقم المادة.\n"
        "للتثقيف العام وليس استشارة قانونية.")

async def answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.message.text
    hits = search(q)
    if not hits:
        await update.message.reply_text("لم أجد مواداً مطابقة. جرّب صياغة أخرى أو اذكر الموضوع.")
        return
    try:
        txt = ai_answer(q, hits)
    except Exception:
        txt = None
    if txt:
        txt += "\n\nالمواد: " + "، ".join(e[0] for e in hits)
    else:
        txt = "\n\n".join(f"📌 المواد ({e[0]}) – {e[1]}\n{e[2]}" for e in hits)
    for i in range(0, len(txt), 4000):
        await update.message.reply_text(txt[i:i + 4000])

app = ApplicationBuilder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
app.run_polling()
