// Prefer the language of the main clause when a question names a term in the other language.
const VI_DIACRITICS = /[ăâđêôơưáàảãạấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]/i
const EN_LEAD = /^(?:please\s+)?(?:what|which|why|when|where|who|how|does|did|is|are|could|can|should|show|explain|compare|tell|give|define)\b/i

const VI_WORDS =
  /\b(ngan hang|ngân hàng|no xau|nợ xấu|no xấu|khong|không|bao nhieu|bao nhiêu|la gi|là gì|cho toi|cho tôi|toi muon|tôi muốn|so sanh|so sánh|du bao|dự báo|quý|quy [1-4]|ty |triệu|tỷ)\b/i

export type Lang = "vi" | "en"

export function detectLang(text: string): Lang {
  const question = text.normalize("NFC").trim()
  if (EN_LEAD.test(question)) return "en"
  if (VI_DIACRITICS.test(question)) return "vi"
  if (VI_WORDS.test(question)) return "vi"
  return "en"
}
