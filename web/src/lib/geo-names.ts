// Canonical 34 post-2025 provinces (Nghị quyết 202/2025/QH15), 63->34 mapping, GSO regions & aliases.
// Pure functions (node --test compatible) using relative .ts import of `fold`.
import { fold } from "./analyst/explain.ts"

export const PROVINCES_34 = [
  "An Giang",
  "Bắc Ninh",
  "Cà Mau",
  "Cần Thơ",
  "Cao Bằng",
  "Đà Nẵng",
  "Đắk Lắk",
  "Điện Biên",
  "Đồng Nai",
  "Đồng Tháp",
  "Gia Lai",
  "Hà Nội",
  "Hà Tĩnh",
  "Hải Phòng",
  "Hồ Chí Minh",
  "Huế",
  "Hưng Yên",
  "Khánh Hòa",
  "Lai Châu",
  "Lạng Sơn",
  "Lào Cai",
  "Lâm Đồng",
  "Nghệ An",
  "Ninh Bình",
  "Phú Thọ",
  "Quảng Ngãi",
  "Quảng Ninh",
  "Quảng Trị",
  "Sơn La",
  "Tây Ninh",
  "Thái Nguyên",
  "Thanh Hóa",
  "Tuyên Quang",
  "Vĩnh Long",
] as const

export const OLD_63_TO_34: Record<string, string> = {
  "Hà Giang": "Tuyên Quang",
  "Tuyên Quang": "Tuyên Quang",
  "Yên Bái": "Lào Cai",
  "Lào Cai": "Lào Cai",
  "Bắc Kạn": "Thái Nguyên",
  "Thái Nguyên": "Thái Nguyên",
  "Vĩnh Phúc": "Phú Thọ",
  "Hòa Bình": "Phú Thọ",
  "Phú Thọ": "Phú Thọ",
  "Bắc Giang": "Bắc Ninh",
  "Bắc Ninh": "Bắc Ninh",
  "Thái Bình": "Hưng Yên",
  "Hưng Yên": "Hưng Yên",
  "Hải Phòng": "Hải Phòng",
  "Hải Dương": "Hải Phòng",
  "Hà Nam": "Ninh Bình",
  "Nam Định": "Ninh Bình",
  "Ninh Bình": "Ninh Bình",
  "Quảng Bình": "Quảng Trị",
  "Quảng Trị": "Quảng Trị",
  "Đà Nẵng": "Đà Nẵng",
  "Quảng Nam": "Đà Nẵng",
  "Kon Tum": "Quảng Ngãi",
  "Quảng Ngãi": "Quảng Ngãi",
  "Bình Định": "Gia Lai",
  "Gia Lai": "Gia Lai",
  "Ninh Thuận": "Khánh Hòa",
  "Khánh Hòa": "Khánh Hòa",
  "Đắk Nông": "Lâm Đồng",
  "Bình Thuận": "Lâm Đồng",
  "Lâm Đồng": "Lâm Đồng",
  "Phú Yên": "Đắk Lắk",
  "Đắk Lắk": "Đắk Lắk",
  "Hồ Chí Minh": "Hồ Chí Minh",
  "Bà Rịa - Vũng Tàu": "Hồ Chí Minh",
  "Bình Dương": "Hồ Chí Minh",
  "Bình Phước": "Đồng Nai",
  "Đồng Nai": "Đồng Nai",
  "Long An": "Tây Ninh",
  "Tây Ninh": "Tây Ninh",
  "Cần Thơ": "Cần Thơ",
  "Sóc Trăng": "Cần Thơ",
  "Hậu Giang": "Cần Thơ",
  "Bến Tre": "Vĩnh Long",
  "Trà Vinh": "Vĩnh Long",
  "Vĩnh Long": "Vĩnh Long",
  "Tiền Giang": "Đồng Tháp",
  "Đồng Tháp": "Đồng Tháp",
  "Bạc Liêu": "Cà Mau",
  "Cà Mau": "Cà Mau",
  "Kiên Giang": "An Giang",
  "An Giang": "An Giang",
  "Cao Bằng": "Cao Bằng",
  "Điện Biên": "Điện Biên",
  "Hà Tĩnh": "Hà Tĩnh",
  "Lai Châu": "Lai Châu",
  "Lạng Sơn": "Lạng Sơn",
  "Nghệ An": "Nghệ An",
  "Quảng Ninh": "Quảng Ninh",
  "Thanh Hóa": "Thanh Hóa",
  "Sơn La": "Sơn La",
  "Hà Nội": "Hà Nội",
  "Thừa Thiên Huế": "Huế",
}

export const PROVINCE_34_REGION: Record<string, string> = {
  "An Giang": "Đồng bằng sông Cửu Long",
  "Bắc Ninh": "Đồng bằng sông Hồng",
  "Cà Mau": "Đồng bằng sông Cửu Long",
  "Cần Thơ": "Đồng bằng sông Cửu Long",
  "Cao Bằng": "Trung du và miền núi phía Bắc",
  "Đà Nẵng": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Đắk Lắk": "Tây Nguyên",
  "Điện Biên": "Trung du và miền núi phía Bắc",
  "Đồng Nai": "Đông Nam Bộ",
  "Đồng Tháp": "Đồng bằng sông Cửu Long",
  "Gia Lai": "Tây Nguyên",
  "Hà Nội": "Đồng bằng sông Hồng",
  "Hà Tĩnh": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Hải Phòng": "Đồng bằng sông Hồng",
  "Hồ Chí Minh": "Đông Nam Bộ",
  "Huế": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Hưng Yên": "Đồng bằng sông Hồng",
  "Khánh Hòa": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Lai Châu": "Trung du và miền núi phía Bắc",
  "Lạng Sơn": "Trung du và miền núi phía Bắc",
  "Lào Cai": "Trung du và miền núi phía Bắc",
  "Lâm Đồng": "Tây Nguyên",
  "Nghệ An": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Ninh Bình": "Đồng bằng sông Hồng",
  "Phú Thọ": "Trung du và miền núi phía Bắc",
  "Quảng Ngãi": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Quảng Ninh": "Đồng bằng sông Hồng",
  "Quảng Trị": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Sơn La": "Trung du và miền núi phía Bắc",
  "Tây Ninh": "Đông Nam Bộ",
  "Thái Nguyên": "Trung du và miền núi phía Bắc",
  "Thanh Hóa": "Bắc Trung Bộ và Duyên hải miền Trung",
  "Tuyên Quang": "Trung du và miền núi phía Bắc",
  "Vĩnh Long": "Đồng bằng sông Cửu Long",
}

const FOLDED_INDEX = new Map<string, string>()
for (const p of PROVINCES_34) FOLDED_INDEX.set(fold(p), p)
for (const [oldName, newName] of Object.entries(OLD_63_TO_34)) {
  FOLDED_INDEX.set(fold(oldName), newName)
}

const EXTRA_ALIASES: Record<string, string> = {
  "tp ho chi minh": "Hồ Chí Minh",
  "tp hcm": "Hồ Chí Minh",
  "tphcm": "Hồ Chí Minh",
  "hcm": "Hồ Chí Minh",
  "hcmc": "Hồ Chí Minh",
  "ho chi minh city": "Hồ Chí Minh",
  "sai gon": "Hồ Chí Minh",
  "saigon": "Hồ Chí Minh",
  "sg": "Hồ Chí Minh",
  "hanoi": "Hà Nội",
  "hn": "Hà Nội",
  "ha noi capital": "Hà Nội",
  "brvt": "Hồ Chí Minh",
  "vung tau": "Hồ Chí Minh",
  "tt hue": "Huế",
  "thua thien hue": "Huế",
  "thua thien": "Huế",
  "daklak": "Đắk Lắk",
  "dac lac": "Đắk Lắk",
  "daknong": "Lâm Đồng",
  "danang": "Đà Nẵng",
  "haiphong": "Hải Phòng",
  "bac can": "Thái Nguyên",
}
for (const [k, v] of Object.entries(EXTRA_ALIASES)) FOLDED_INDEX.set(k, v)

export function canonicalProvince34(raw: unknown): {
  province: string | null
  region: string | null
  convertedFrom63: boolean
} {
  if (typeof raw !== "string" && typeof raw !== "number") {
    return { province: null, region: null, convertedFrom63: false }
  }
  const text = String(raw).trim()
  if (!text) return { province: null, region: null, convertedFrom63: false }

  const parts = text.includes(",") ? [text, text.split(",").pop() ?? text] : [text]
  for (const part of parts) {
    const f = fold(part)
      .replace(/^(?:tinh|thanh pho|tp|t p|city of|province of|thu do)\s+/, "")
      .replace(/\s+(?:province|city|capital)$/, "")
      .trim()
    if (!f) continue
    let hit = FOLDED_INDEX.get(f)
    if (!hit) {
      const compact = f.replace(/\s+/g, "")
      for (const [k, v] of FOLDED_INDEX.entries()) {
        if (k.replace(/\s+/g, "") === compact) {
          hit = v
          break
        }
      }
    }
    if (hit) {
      return {
        province: hit,
        region: PROVINCE_34_REGION[hit] ?? null,
        convertedFrom63: fold(hit) !== f && fold(part) !== fold(hit) && Boolean(OLD_63_TO_34[text] || Object.keys(OLD_63_TO_34).some((o) => fold(o) === f && fold(OLD_63_TO_34[o]) !== f)),
      }
    }
  }
  return { province: null, region: null, convertedFrom63: false }
}

/** True when a numeric metric represents a ratio/percentage and should disallow `sum` aggregation. */
export function isRatioMetric(name: string): boolean {
  return /(pct|%|ty_le|rate|ratio|_per_|^per_|_m2$|roe|roa)/i.test(name)
}
