"use client"

import { CountUp } from "@/components/ratewatch/count-up"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatNumber, type Lang } from "@/lib/npl/view"

export function KeyNumbers({
  cards,
  lang,
}: {
  cards: { title: string; value: number; digits: number; suffix: string; help: string }[]
  lang: Lang
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader>
            <CardTitle>{card.title}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            <p className="text-2xl font-semibold tabular-nums">
              <CountUp value={card.value} text={(value) => `${formatNumber(value, lang, card.digits)}${card.suffix}`} />
            </p>
            <p className="text-sm text-muted-foreground">{card.help}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
