---
name: email-butler
description: Gmail 邮件管家 — 收件箱分类摘要、阅读、代写/回复/转发、标签管理、高级搜索、邮件转任务、批量清理。全部通过 gws CLI 操作。
version: 1.0.0
metadata:
---

# 邮件管家 (Email Butler)

Tony 的 Gmail + Calendar 日常管家。Gmail 操作主要通过 `gws` CLI；Calendar/knowledge sync 走 `/home/tonyxu/brain/scripts/collectors` 与 gbrain import。

**覆盖：** 邮件 triage / 分类 / action queue / 低风险归档 / 邮件简报 / Gmail+Calendar digest sync 到 gbrain。

**不覆盖：** 通用日报简报（用 `daily-briefing` / `gws-email-calendar-briefing`）、Drive/Sheets/Docs 深度操作（用 `google-workspace`）。

## 环境

```bash
GWS=/home/linuxbrew/.linuxbrew/bin/gws
```

始终用绝对路径。首次使用前先验证 auth：

```bash
$GWS gmail +triage --max 1 --format json
```

## 写邮件前必须做的事

**每次代写/回复/转发邮件前，先加载 `tony-email-voice` skill** 并严格遵循 Tony 的写作风格。

## 功能一览

### 1. 收件箱分类 & 智能摘要

快速了解收件箱状态：

```bash
# 未读重要邮件（排除噪音）
$GWS gmail +triage --max 30 \
  --query "is:unread -category:promotions -category:social -category:forums" \
  --format json

# 特定发件人
$GWS gmail +triage --max 20 \
  --query "is:unread from:specific@example.com" \
  --format json
```

**摘要规则：**
- 同一发件人/主题的多封邮件合并为一条
- 高优先级信号：银行/支付/安全/旅行/税务/infra告警
- 低优先级直接跳过：零售促销、newsletter、社交摘要
- 输出格式：按优先级排序的 bullet list，**bold 只给真正重要的**

### 2. 阅读邮件

```bash
# 读取完整邮件内容
$GWS gmail +read --id MESSAGE_ID --format json

# 只看 headers
$GWS gmail +read --id MESSAGE_ID --headers --format json
```

`+triage` 返回的 `id` 可直接作为 `+read --id` 的值。

### 3. 代写 & 发送邮件

**⚠️ 发送前必须向 Tony 确认内容，绝不自动发送。**

```bash
# 新邮件
$GWS gmail +send \
  --to "recipient@example.com" \
  --subject "Subject" \
  --body "Email body"

# 带 CC
$GWS gmail +send \
  --to "recipient@example.com" \
  --cc "cc@example.com" \
  --subject "Subject" \
  --body "Email body"
```

### 4. 回复邮件

```bash
# 回复
$GWS gmail +reply --message-id MESSAGE_ID --body "Reply text" --format json

# 回复全部
$GWS gmail +reply-all --message-id MESSAGE_ID --body "Reply text" --format json
```

`gws gmail +reply` 不接受 `--id` 或 positional ID；必须用 `--message-id`。这里的 `MESSAGE_ID` 可以是 Gmail API message id（例如 `19ddb...`），不是 RFC `Message-ID` header。

### 5. 转发邮件

```bash
$GWS gmail +forward MESSAGE_ID --to "forward@example.com"
```

### 6. 标签管理 & 归档

#### 自动化职责边界

Tony 的邮件管家不应只做 briefing。生产自动化至少应覆盖两层：

1. **Label-only maintenance**（可自动执行）：创建/维护保守标签并批量加标签，例如 `Family`、`Receipts`、`Travel`、`Security`、`Finance`、`Recruiting`、`Action Needed`。
2. **Briefing / drafting**（用户可见）：摘要重要邮件、识别需要回复的邮件，并按 `tony-email-voice` 起草回复。

安全边界：定时自动化可以加标签；不要自动发送/回复/转发；不要自动删除；不要自动标记已读。自动归档只在规则非常明确且 Tony 已授权该类别时使用。

当前邮件管家生产脚本：

```bash
# Full ops wrapper：每小时做 Gmail label maintenance + Action Queue + Gmail/Calendar collectors + gbrain imports；19 点顺带低风险归档
bash -lic '/home/tonyxu/copilot-home-assistant/scripts/email_butler_ops.py'

# Maintenance-only legacy wrapper：保留为手动 fallback，不再单独 cron
bash -lic '/home/tonyxu/copilot-home-assistant/scripts/email_butler_label_maintenance.py'
```

Full ops wrapper 内部调用：
```bash
# 1) Model-filtered label maintenance：扫描最近 7 天邮件；每封邮件一次性由 model 判断所有生产标签
#    Family / Receipts / Travel / Security / Finance / Recruiting / Ops/Infrastructure / ADU / Home / Read Later / Action Needed
#    默认每次最多 review 60 封未缓存邮件；缓存已判定结果，避免 hourly 重扫。
bash -lic '/home/tonyxu/copilot-home-assistant/scripts/email_butler_label_maintenance.py'

# 2) Action queue：只读扫描新增待处理邮件；有新增才通知 Tony；对需要回复的邮件附 suggested_reply draft（只建议，不发送）
bash -lic '/home/tonyxu/copilot-home-assistant/scripts/email_butler_action_queue.py'

# 3) 低风险归档：只移除 INBOX，不删除、不标已读；仅 consolidated wrapper 在 19 点运行
bash -lic '/home/tonyxu/copilot-home-assistant/scripts/email_butler_low_risk_archive.py'
```

生产 cron 形态：
- `email-butler-ops`: `15 8-21 * * *`, `deliver=origin`。
  - 每小时运行 label maintenance + read-only Action Queue + Gmail/Calendar collectors + gbrain digest imports (`--no-embed`)。
  - 19 点那次额外运行 low-risk archive。
  - `new_action_count=0` 且 sync 健康时 `[SILENT]`；有新增 Action Queue 最多 5 条短提醒；sync/import 失败才告警。
- Email briefing 继续保留：10:30 / 15:30 / 20:00 PT。
  - 每次邮件简报都要读取 `/home/tonyxu/.local/state/copilot-home-assistant/email_butler_ops_latest.json`（如果存在），在末尾加入 `🛠 **Maintenance**`，用 1-3 条说明最近 Email Butler 还做了哪些 maintenance：标签维护、Action Queue、Gmail/Calendar collectors + gbrain import、低风险归档。
  - Maintenance section 只写安全计数/状态；不要暴露 message IDs、raw JSON、tokens、DB URLs、stack traces 或完整邮件正文。
- 不要重新拆成 `daytime-gmail-calendar-digest-sync` / `email-butler-maintenance` / `email-butler-label-maintenance` / `email-butler-action-queue` / `email-butler-low-risk-archive` 多个 cron；这些旧碎片已被 `email-butler-ops` consolidation 替代。

经验坑：
- `execute_code` 环境可能拿不到 gws keyring credential；生产脚本/手动验证用 `bash -lic '...'` 跑，更接近 cron/terminal 的可用 auth 环境。
- `email-butler-ops.py` is now the owner for daytime Gmail+Calendar digest sync into gbrain. Do not maintain a separate `daytime-gmail-calendar-digest-sync` cron unless Tony explicitly asks to split it again.
- Gmail `resultSizeEstimate` 对复杂 label/category/OR 查询可能明显不可靠（本次同一个 inbox 估算反复给 201）；做批量归档或噪音审计时必须分页取实际 `messages` IDs，或用本地导出聚合验证，不要只信 estimate。
- Wrapper 输出可能混有 bash no-job-control 提示；解析 JSON 时不要简单取第一个 `{` 后整段 `json.loads`，要用 `json.JSONDecoder().raw_decode` 找第一个可解析 JSON object。
- Action queue 要过滤纯验证码邮件（`authentication code` / `verification code`），否则会制造假待办。
  - Determine reportable Action Queue items from `new_action_items` only. If `new_action_items` is empty, respond `[SILENT]` even if `new_action_count` or diagnostic candidate counters are nonzero. Never invent placeholder bullets like “未返回”; missing item details means no reportable item.
  - `new_action_count` now equals emitted item count; `candidate_count` / `filtered_count` are diagnostic only and may show candidates suppressed because Tony already replied or the newest thread message is an ack.
- Action queue 和邮件简报对 reply-worthy 邮件要给 `suggested_reply` / 草稿：招聘/猎头邮件也必须显示建议 draft，不能只写“默认忽略/无需处理”。招聘默认生成 Tony 风格的简短婉拒 draft；其他明显需要回复的人工邮件可用 `tony-email-voice` 风格生成 1–3 句 draft。绝不自动发送/回复，只输出建议。
- Action queue 必须过滤已处理线程：如果 thread 最新消息来自 Tony 自己，或对方最新回复只是 ack（如 “Thanks for the heads up Tony!”）且没有新问题/请求，不要再提示回复草稿。也不要把 Tony 自己的 SENT 回复当成新的待处理邮件。
- 自动归档只碰低风险类别：`category:promotions/social/forums older_than:7d`、`label:Recruiting older_than:7d`、`label:Read Later older_than:14d`、明确成功/恢复类的 `Ops/Infrastructure older_than:3d`、以及旧购物物流通知。不要自动归档 `Action Needed`、`Security`、`Family`、`ADU`、`Home`。
- Label maintenance production policy: scan recent mail broadly and let the model classify **all production labels per message**. Do not use one-off sender/domain/subject rules as the primary recall mechanism, and do not direct-keyword-label `Family`, `Receipts`, `Travel`, `Security`, `Finance`, `Recruiting`, `Ops/Infrastructure`, `ADU`, `Home`, `Read Later`, or `Action Needed`.
- `email_butler_label_maintenance.py` uses `newer_than:7d -in:spam -in:trash`, then classifies uncached messages against all labels in one model pass per batch. Default safeguards: `SCAN_MAX=500`, `MAX_REVIEW_PER_RUN=60`, `BATCH_SIZE=40`, `classified_recent` cache for ~8 days. If it times out, lower `--max-review`/batch size; do not revert to per-label keyword recall.
- When debugging label-maintenance timeout, first run `python3 -m py_compile /home/tonyxu/copilot-home-assistant/scripts/email_butler_label_maintenance.py`, verify every rule still has `model=True`, then run `bash -lic '/home/tonyxu/copilot-home-assistant/scripts/email_butler_label_maintenance.py'`. If manually triggering the cron job with `cronjob(action='run')`, check/reset `next_run_at` afterward because manual runs can skew it; reapply `15 8-21 * * *` if needed.
- If Tony asks to resend an email briefing and `cronjob(action='run')` says success but nothing arrives, inspect the newest output under `~/.local/state/copilot-home-assistant/output/<job_id>/` and `~/.local/state/copilot-home-assistant/logs/errors.log` before rerunning repeatedly. Known failure mode: the cron run can generate a valid briefing but fail while saving/delivering with `[Errno 28] No space left on device`; if so, verify `df -h`, read the saved briefing response from the output file, and send the final briefing manually with `send_message` rather than relying on another cron trigger.
- If Tony says new emails are not being labeled, do not stop at a successful ops run. Audit recent unlabeled mail directly with a query like `newer_than:1d -in:spam -in:trash`, fetch metadata samples, and check whether they were skipped by `classified_recent`, hit `MAX_REVIEW_PER_RUN` backlog, or were model-classified as zero labels. Fix the scan/caching/model prompt, not one-off sender/domain rules.
- After changing candidate queries, run label maintenance manually and verify by mapping Gmail label IDs back to names via `gws gmail users labels list`, then checking recent labeled samples. Expected examples after the fix: ChargePoint response required → `Action Needed`; GitHub Actions run failed → `Ops/Infrastructure`; Pat Leave approval → `Family` + `Action Needed`; Stanford event → `Read Later`; BoA/Fidelity transactions → `Finance`. Some normal GitHub comments and Redfin listing updates should remain unlabeled unless Tony explicitly wants a new label category.
- When calendar/briefing has upcoming money reminders (tuition, mortgage, bank transfer, credit card payment), Email Butler should treat recent confirmation emails as state updates: `payment confirmation`, `Direct Debit Withdrawal`, `Deposit Received`, `wire transfer advice`, `scheduled`, `completed`. Surface them as “已付/已转/已扣款” and suppress stale “needs verification/payment” wording in later briefings.
- For the 2026-05-01 reminders, known confirmation pattern: SVIS/Blackbaud payment confirmation; Fidelity direct debit withdrawal by BB TUITION for $37,973; Fidelity deposit received for account ending 2603; Bank of America wire transfer advice notices for $5,000-style transfers. Use these as precedent for future finance reminders.
- PenFed mortgage correction from Tony (2026-04-29): current payment due is **$9,747.99 on 2026-06-01** and **Autopay is Off**. Do not treat the 2026-05-01 PenFed calendar reminder as paid/autopaid unless a direct PenFed payment confirmation appears or Tony says he paid it. For future briefings, surface this as a manual upcoming payment unless completed evidence exists.

```bash
# 列出所有标签
$GWS gmail users labels list --params '{"userId": "me"}' --format json

# 创建标签（如果不存在）
$GWS gmail users labels create \
  --params '{"userId":"me"}' \
  --json '{"name":"Family","labelListVisibility":"labelShow","messageListVisibility":"show"}' \
  --format json

# 给单封邮件加标签
$GWS gmail users messages modify \
  --params '{"userId": "me", "id": "MESSAGE_ID"}' \
  --json '{"addLabelIds": ["LABEL_ID"]}'

# 批量给邮件加标签（优先用这个，避免 execute_code 50 tool-call 限制）
$GWS gmail users messages batchModify \
  --params '{"userId":"me"}' \
  --json '{"ids":["MESSAGE_ID_1","MESSAGE_ID_2"],"addLabelIds":["LABEL_ID"]}' \
  --format json

# 移除标签（如标记已读）
$GWS gmail users messages modify \
  --params '{"userId": "me", "id": "MESSAGE_ID"}' \
  --json '{"removeLabelIds": ["UNREAD"]}'

# 归档（移除 INBOX 标签）
$GWS gmail users messages modify \
  --params '{"userId": "me", "id": "MESSAGE_ID"}' \
  --json '{"removeLabelIds": ["INBOX"]}'
```

### 家庭邮件分类流程

当 Tony 要求“分类家庭邮件”时：

1. 先列出标签，确认是否已有 `Family`；没有就创建。
2. 用 Gmail `users messages list` 搜索候选邮件，只取 message IDs，避免大量 `+triage` 输出污染上下文。
3. 推荐初始查询窗口 `newer_than:90d`，关键词覆盖孩子/学校/家庭活动：
   ```text
   (Aaron OR Alvin OR Han OR "Tony and Han" OR "Menlo Children" OR MCC OR preschool OR Bloomz OR SVIS OR school OR "Picture Day" OR "30-Day Notice" OR "Menlo Swim" OR "Soccer Shots" OR SportsEngine OR Mavericks OR Lydia)
   ```
4. 对候选 ID 去重后用 `users messages batchModify` 分批添加 `Family` 标签（每批 ≤100）。不要逐封 `modify`，会撞 execute_code 50 tool-call 限制。
5. 抽样验证：
   ```bash
   $GWS gmail +triage --max 10 --query 'label:Family newer_than:90d (Aaron OR Alvin OR "Menlo Children" OR Bloomz OR "Menlo Swim" OR "Soccer Shots" OR SVIS OR Lydia)' --format json
   ```
6. 汇报数量和样本，并说明如果关键词偏宽，可能混入少量边缘项（如家庭 assistant digest），但核心孩子/学校/家庭活动邮件已归类。

### Recruiting 邮件分类审计流程

当 Tony 要求“列出/检验 recruiting 邮件”时：

1. 不要只信当前 `Recruiting` label；先导出完整当前集合再审计。
   - 用 `gws gmail users messages list --params '{"userId":"me","q":"label:Recruiting","maxResults":100}' --format json` 分页取 IDs。
   - 对每封用 metadata get 取 `From` / `Subject` / `Date` / `labels` / `snippet`，避免读取完整正文。
2. 生成一个本地 CSV/Markdown 审计表，字段至少包括：date、from、subject、domain、labels、snippet、classification。
   - 默认路径可用 `/tmp/recruiting_audit/recruiting_emails.csv` 和 `/tmp/recruiting_audit/recruiting_audit.md`。
3. 分类判断要分层：
   - `likely_recruiting`: recruiter domains、known recruiter contacts、明确 role/opportunity/interview/staff engineer/client engineering manager 等。
   - `job_board_low_value`: Glassdoor/Indeed/job alerts 类。
   - `likely_false_positive`: newsletter、digest、webinar、sale/promo、restaurant/event/open house、USPS digest、school/family updates。
   - `needs_review`: 需要 Tony 判断的边界项。
4. If发现误标，先改成模型过滤或收紧候选规则，再批量移除误标 label。
   - Recruiting 不能只靠简单关键词。生产脚本应先用 broad candidate query 找候选，再用 an LLM 判断是否真的是给 Tony 的 job/career opportunity outreach。
   - **重要坑：不要使用裸 `join us` 直接加 label。** 它会误伤“join us at event/open house/world of coffee/Galaxy Unpacked/GrafanaCON”等活动营销邮件。`join us` 只能作为候选信号，最终必须交给 model 判断。
   - 模型判断标准：保留 recruiter / hiring manager / specific role / interview/follow-up / compensation or role pitch；拒绝 marketing/promotions/newsletters/events/open houses/restaurants/USPS digests/school-family updates/generic articles。
   - Production Recruiting should be discovered by the all-mail 7-day scan plus model classification, not by one-off sender/domain/subject patches. Historical audits/backfills may use a wider explicit window, but recurring maintenance should stay recent and bounded.
5. 批量清理只移除 `Recruiting` label，不删除、不归档、不标已读。
6. 重新跑 `/home/tonyxu/copilot-home-assistant/scripts/email_butler_label_maintenance.py` 后再次导出审计表，汇报：总数、明显正确数、误标数、边界项、主要 sender domains。

### 7. 高级搜索

```bash
# Gmail 搜索语法完整参考见 google-workspace skill 的 references/gmail-search-syntax.md

# 常用搜索模式
$GWS gmail +triage --max 20 --query "has:attachment filename:pdf newer_than:7d" --format json
$GWS gmail +triage --max 20 --query "from:boss@company.com newer_than:1d" --format json
$GWS gmail +triage --max 20 --query "subject:invoice newer_than:30d" --format json
$GWS gmail +triage --max 20 --query "is:starred" --format json
$GWS gmail +triage --max 20 --query "larger:5M newer_than:30d" --format json
```

### 8. 邮件转任务

```bash
$GWS workflow +email-to-task MESSAGE_ID
```

### 9. 批量清理

对噪音类别做批量归档/删除：

```bash
# 查看 promotions 类别
$GWS gmail +triage --max 50 \
  --query "category:promotions newer_than:7d" --format json

# 批量归档 promotions（用 execute_code 循环）
# 先列出 IDs，再逐个 modify 移除 INBOX 标签

# 查看 social 类别
$GWS gmail +triage --max 50 \
  --query "category:social newer_than:7d" --format json
```

**⚠️ 批量删除前必须确认。归档可以直接做，删除不行。**

#### Tony 授权时的批量归档模式

当 Tony 明确说“archive 所有 X/Y 邮件”时，可以直接批量归档匹配项：只移除 `INBOX`，不删除、不标已读。推荐用 raw Gmail API 分页取全量 ID，再 `batchModify`，不要用 `+triage` 抽样或逐封 `modify`。

```bash
# 先 sanity check
$GWS gmail users messages list \
  --params '{"userId":"me","q":"in:inbox (synology OR redfin)","maxResults":1}' \
  --format json

# 分页收集所有 ids 后，按 ≤500/批 remove INBOX
$GWS gmail users messages batchModify \
  --params '{"userId":"me"}' \
  --json '{"ids":["MESSAGE_ID_1","MESSAGE_ID_2"],"removeLabelIds":["INBOX"]}' \
  --format json
```

验证要跑原 combined query 和拆开的单项 query，例如：
- `in:inbox (synology OR redfin)`
- `in:inbox synology`
- `in:inbox redfin`

经验值：Tony 已授权过归档 `Synology`/`DigitalOne` 与 `Redfin` inbox 噪音；这类机器通知/房产 listing update 可视为低风险归档候选。汇报时只给数量和安全边界：“只移除 INBOX，没有删除/标已读”。

### 10. 监控新邮件

```bash
# 实时监控（后台运行）
$GWS gmail +watch --format json
```

## 操作优先级判断

| 信号 | 优先级 | 处理 |
|------|--------|------|
| 银行/支付/安全告警 | 🔴 高 | 立即通知 Tony |
| 税务/法律/政府 | 🔴 高 | 立即通知 + 摘要 |
| 旅行变更/取消 | 🟡 中高 | 摘要 + 建议行动 |
| Infra 告警 (TeslaMate/Synology) | 🟡 中高 | 合并同类 + 摘要 |
| 个人重要 (Fidelity/保险) | 🟡 中 | 摘要 |
| 零售/促销 | ⚪ 低 | 跳过或批量归档 |
| Newsletter/社交摘要 | ⚪ 低 | 跳过或批量归档 |
| 招聘/猎头邮件 | ⚪ 低 | 摘要 + 建议拒绝 draft（不自动发送） |

## 常用操作流程

### "帮我看看邮箱"

1. `+triage --max 30` 排除噪音
2. 按优先级分组摘要
3. 高优先级用 `+read` 获取详情
4. 提供行动建议（需要回复的草拟回复）

### "帮我回这封邮件"

1. `+read MESSAGE_ID` 获取原文
2. 加载 `tony-email-voice` skill
3. 草拟回复，展示给 Tony
4. 确认后 `+reply MESSAGE_ID --body "..."`

### "清理一下收件箱"

1. 分类扫描：promotions / social / forums / updates
2. 展示各类别数量和样本
3. 确认后批量归档
4. 报告清理结果

Noisy sender/category heuristics live in `references/noisy-mail-sources.md`; load it before proposing or executing broad inbox archive rules.

### "我有什么 monthly subscription / recurring bills"

使用 Gmail receipts/subscription emails 做快速订阅审计；详细流程见 `references/subscription-audit-from-gmail.md`。默认先扫 `/home/tonyxu/brain/sources/gmail/messages/*.json`，按 merchant/service 聚合，再对高信号邮件用 `gws gmail +read --id ... --format json` 读全文抽取价格/renewal date。输出要分清：active monthly、recurring household bills、usage-based cloud/API invoices、annual memberships/domain renewals、canceled/on-hold/uncertain。不要把 ChatGPT “will not renew”、Blue Bottle “on hold”、Descript cancel/refund 当 active subscription；也不要把 Cloudflare/AWS/OpenRouter 这类 usage/invoice 直接算成固定月费，除非邮件明说 cadence/amount。

### "根据已导出的 email 历史优化邮箱管理"

优先用本地导出，不要直接从 Gmail 全量重抓。当前 canonical export 路径：

```text
/home/tonyxu/brain/sources/gmail/messages/*.json
/home/tonyxu/brain/state/gmail_backfill_state.json
/home/tonyxu/.local/state/copilot-home-assistant/email_butler_ops_latest.json
/home/tonyxu/.local/state/copilot-home-assistant/email_butler_label_maintenance.json
/home/tonyxu/.local/state/copilot-home-assistant/email_butler_low_risk_archive.json
```

分析步骤：
1. 读取 `messages/*.json`，按 sender/domain/label/year/month/category 聚合；重点看 `INBOX`、`UNREAD`、`CATEGORY_UPDATES/PROMOTIONS/SOCIAL/FORUMS`、`IMPORTANT`。
2. 做语义簇，而不是只按 Gmail category：
   - `Ops/Infrastructure`: Synology, DigitalOne, Cloudflare, n8n, Bitwarden, uptime。
   - `Shopping/Logistics`: Amazon, USPS, UPS, FedEx, order/shipped/delivered/receipt。
   - `Finance/Tax`: Fidelity, Chase, BoA, PayPal, Venmo, Mint, TurboTax, IRS, insurance。
   - `ADU`: Menlo Park permit, BLD2025-01110, J&P Design, ADU/geotech/plan-review threads。
   - `Home`: property tax, home insurance, mortgage, PG&E/Recology/utilities, non-ADU home maintenance.
   - `Family/School`: Han Chen, kids, school, preschool, Bloomz, Menlo Swim, Soccer Shots。
   - `Travel`: Airbnb, United/Delta/Southwest, Expedia, hotel, reservation, itinerary, Uber/Lyft。
   - `Read Later`: newsletter, digest, WSJ/NYT/Insider/Substack/media。
    - `Recruiting`: model-filtered recruiter/hiring outreach and explicit role/opportunity threads. All production labels are model-filtered; candidate keywords/domains are only retrieval hints. Avoid broad direct-label terms like bare `join us`; they pull in events, promotions, newsletters, and restaurants. Known examples may exist, but production recall should rely on broad semantic recruiting signals rather than hard-coded one-off sender domains.
   - `Security/Identity`: security, verification, login, password, 2FA, new device。
3. Current production labels include: `Family`, `Receipts`, `Travel`, `Security`, `Finance`, `Recruiting`, `Ops/Infrastructure`, `ADU`, `Home`, `Read Later`, `Action Needed`.
4. 输出要给判断，不要只给统计：说明邮箱实际是什么结构、最大噪音源、哪些类别适合自动归档、哪些类别必须保守。
5. 推荐动作按安全等级分层：
   - Safe: label-only、低风险归档只移除 `INBOX`。
   - Conservative: receipts/newsletters/ops success 默认归档；error/security/tax deadline 进 `Action Needed`。
   - Manual-confirm: delete、mark-read、大规模 historical cleanup、任何 send/reply/forward。
6. 对 Tony 的典型结论：Inbox 应只保留需要人处理的邮件；历史邮箱主要是机器通知、交易流水、家庭/房产项目档案。优化重点是 Inbox hygiene，不是更勤快读邮件。
7. 若需要用实时 Gmail count 验证，`gws users messages list` 的 `resultSizeEstimate` 对复杂 query 可能不可靠；只作为 sanity check，核心分析以本地导出聚合为准。

## 安全规则

1. **绝不自动发送邮件** — 必须 Tony 确认
2. **绝不自动删除** — 归档可以，删除必须确认
3. **敏感邮件（银行/安全）内容不外传**
4. **招聘邮件低优先级，但在邮件简报 / Action Queue 中出现时必须附建议拒绝 draft；不自动发送**

## Pitfalls

- `gws` 可能不在 PATH 上，始终用 `/home/linuxbrew/.linuxbrew/bin/gws`
- `+triage` 返回的 ID 用于 `+read`/`+reply` 等后续操作
- 批量操作注意 rate limit，每次 API 调用间加适当延迟
- Gmail 搜索语法中 `-category:promotions` 用减号排除
- 如果 gws auth 失败，参考 `fix-gws-linuxbrew-path` skill
