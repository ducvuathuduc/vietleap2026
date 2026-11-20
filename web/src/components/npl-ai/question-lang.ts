import type { Lang } from "@/lib/npl/view"

type Prompts = Record<Lang, readonly [string, string, string]>

const overview: Prompts = {
  vi: [
    "Mức nợ xấu trung vị mới nhất là bao nhiêu?",
    "Tỷ lệ bao phủ nợ xấu trung vị mới nhất là bao nhiêu?",
    "Nợ xấu thường thay đổi thế nào qua các quý?",
  ],
  en: [
    "What is the latest median NPL?",
    "What is the latest median NPL coverage ratio?",
    "How does NPL usually change by quarter?",
  ],
}

const pagePrompts: Record<string, Prompts | undefined> = {
  "/ngan-hang": {
    vi: ["So sánh biến động nợ xấu mới nhất của ACB và VCB.", "Nợ xấu của TCB thay đổi thế nào qua các quý?", "Dự báo nợ xấu quý tới của MBB là bao nhiêu?"],
    en: ["Compare the latest NPL changes at ACB and VCB.", "How has TCB’s NPL changed over time?", "What is the NPL forecast for MBB next quarter?"],
  },
  "/giai-ma": {
    vi: ["Giải mã mức giảm nợ xấu của VCB quý mới nhất.", "ACB có cờ nào trong quý mới nhất?", "Nợ xấu của TCB thay đổi bao nhiêu sau khi điều chỉnh mùa vụ?"],
    en: ["Run the four decoder checks for VCB’s latest quarter.", "Which decoder flags are active for ACB in the latest quarter?", "What is TCB’s latest seasonally adjusted NPL change?"],
  },
  "/thi-truong": {
    vi: ["Giá cổ phiếu có liên hệ với biến động nợ xấu không?", "Phân tích thị trường sử dụng giai đoạn nào?", "Mối liên hệ với giá khác thế nào khi điều chỉnh mùa vụ?"],
    en: ["Are stock returns associated with changes in NPL?", "What period does the market analysis cover?", "How does seasonal adjustment affect the relationship with returns?"],
  },
  "/phuong-phap": {
    vi: ["Hiệu ứng mùa vụ được ước tính thế nào?", "Khoảng tin cậy của hiệu ứng quý nói lên điều gì?", "Phép kiểm định dự báo nợ xấu được thực hiện thế nào?"],
    en: ["How are seasonal quarter effects estimated?", "What do the confidence intervals for quarter effects show?", "How is the NPL forecast backtested?"],
  },
  "/du-lieu": {
    vi: ["Dữ liệu nợ xấu bao phủ giai đoạn nào?", "Nguồn của tỷ lệ nợ xấu là gì?", "Dữ liệu tổng quan bao gồm bao nhiêu ngân hàng?"],
    en: ["What period does the NPL data cover?", "Where does the NPL ratio come from?", "How many banks are covered in the overview?"],
  },
}

export function promptsFor(pathname: string): Prompts {
  const path = pathname.replace(/\/$/, "")
  const bank = /^\/ngan-hang\/([^/]+)/.exec(path)
  if (bank?.[1]) {
    const code = bankCode(bank[1])
    return {
      vi: [
        `Nợ xấu và tỷ lệ bao phủ của ${code} thay đổi thế nào qua các quý?`,
        `Giải mã biến động nợ xấu của ${code} trong quý mới nhất.`,
        `Dự báo nợ xấu quý tới của ${code} là bao nhiêu?`,
      ],
      en: [
        `How have ${code}’s NPL and coverage ratios changed over time?`,
        `Run the decoder for ${code} in the latest quarter.`,
        `What is the next-quarter NPL forecast for ${code}?`,
      ],
    }
  }
  return pagePrompts[path] ?? overview
}

export function visibleText(value: string): string {
  return value
    .replace(/(\*\*|__)([^\n]+?)\1/g, "$2")
    .replace(/[ \t]*\bM[456]\b(?:[ \t]*[–—-][ \t]*\bM[456]\b)?/gi, "")
    .replace(/[ \t]*\bget_ratios\b/gi, "")
    .replace(/[ \t]*\bconsolidated\b/gi, "")
    .replace(/[ \t]*\btool-[a-z0-9_-]+\b/gi, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/^[ \t]+/, "")
}

function bankCode(raw: string): string {
  try {
    return decodeURIComponent(raw).toUpperCase()
  } catch {
    return raw.toUpperCase()
  }
}
