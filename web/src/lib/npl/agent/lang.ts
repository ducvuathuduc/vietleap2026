// Per-message language detection for the NPL assistant (brief T7 item 2):
// Vietnamese diacritics win immediately; without them a few unaccented
// Vietnamese words that never collide with English decide; anything else is
// English. The result is a hint for the model, which also mirrors the user.
const VI_DIACRITICS = /[ăâđêôơưáàảãạấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i

const VI_WORDS =
  /\b(ngan hang|ngân hàng|no xau|nợ xấu|no xấu|khong|không|bao nhieu|bao nhiêu|la gi|là gì|cho toi|cho tôi|toi muon|tôi muốn|so sanh|so sánh|du bao|dự báo|quý|quy [1-4]|ty |triệu|tỷ)\b/i

export type Lang = "vi" | "en"

export function detectLang(text: string): Lang {
  if (VI_DIACRITICS.test(text)) return "vi"
  if (VI_WORDS.test(text)) return "vi"
  return "en"
}
