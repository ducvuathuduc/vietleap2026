DONE V-TECH
Acceptance checks (all run this session, 19:32-19:52 Asia/Saigon):
- Installed-docs reads: ai 7.0.173 docs greps/sed (tool calling, stopWhen, Output.object, @ai-sdk/otel, ToolLoopAgent) — exit 0, claims cited to file+line.
- Live fetches via web tools, all HTTP-successful: langfuse.com (integration/pricing/self-hosting/masking/url/regions/faq), ai-sdk.dev (bedrock provider), docs.aws.amazon.com (ECS overview/create-full/work, EventBridge Scheduler, models-region-compatibility), aws.amazon.com (bedrock/pricing, fargate/pricing, ECS blog), docs.claude.com (pricing), home.treasury.gov (yield curve), cmegroup.com (FedWatch), fred.stlouisfed.org (DGS10), imf.org (DataMapper API probe).
- Negative claims recorded with URL + response: Bedrock Claude ap-southeast-1 price (served text truncated before Claude rows), Nova availability cells not extractable, IMF API {"error":"Blob not found"}, DataMapper SPA placeholders.
Files written: TECH.md (findings, every claim cited+marked), REPORT.md — both in this task folder; zero repo edits, zero installs, no processes touched.
Not done: npm installs, repo changes (forbidden by brief); Langfuse JS/TS masking hook name and ALB hourly price not fetched (listed in TECH.md gaps).
Risks for Kiro: (1) Bedrock Claude pricing for ap-southeast-1 unverified — budget with Anthropic list $2/$10 per 1M (Sonnet 5.5) as upper bound; (2) @langfuse/vercel-ai-sdk needs Node >= 22 — check deploy image; (3) Kimi 3's $3/$15 CRIS row is NOT Claude pricing — do not misquote.
