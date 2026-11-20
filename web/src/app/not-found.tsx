import Link from "next/link"

export default function NotFound() {
  return (
    <main className="mx-auto flex max-w-lg flex-col gap-3 px-6 py-16">
      <h1 className="text-xl font-semibold">Không tìm thấy</h1>
      <p className="text-sm text-muted-foreground">Mã ngân hàng hoặc đường dẫn này không có trong bản số liệu.</p>
      <Link href="/" className="text-sm underline underline-offset-4">Về trang tổng quan</Link>
    </main>
  )
}
