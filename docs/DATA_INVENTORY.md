# FairRyde 数据清单：原始数据与处理后的数据

截至 2026-10-14，`main` 的提交 `305cb29`（A2 合并之后）。所有数字都由脚本直接从仓库文件算出；在这个提交上运行 `python3 kb/build_kb.py --no-xlsx --no-fuzz`，结果为 `ERROR 0 | WARN 0 | INFO 5`。

分类标准：

- **原始数据**：从外部拿到、FairRyde 没有改写措辞的材料（主办方、Ryde、政府和其他平台的公开页面、新闻报道、曹老师的协议）。做过格式转换（PDF 转文字、HTML 转纯文本、破折号统一成连字符），但内容不变。
- **处理后的数据**：FairRyde 根据原始数据写出、算出或判定的东西（知识库、引擎、报告、验证结果、修复记录）。
- **缺口**：被引用或需要、但不在仓库里的数据（第 3 节）。

## 0. 总览

| 类别 | 位置 | 文件 | 体积 | 状态 |
|---|---|---|---|---|
| 原始：主办方手册和样例案件 | `kb/sources/organizer/` | 2 | 67 KB | 自 7 Oct 冻结以来未变 |
| 原始：曹老师的 ChordX 协议 | `kb/sources/chordx_knowledge_base.md` | 1 | 18 KB | 未变 |
| 原始：Ryde 政策语料 | `kb/sources/ryde_policy_corpus.json` | 1 | 303 KB | 未变 |
| 原始（二手整理）：调研笔记 | `kb/sources/research/` | 3 | 226 KB | 未变 |
| 原始：真实投诉摘录 | `validation/V1_taxonomy/10_*.jsonl` | 3 | 58 KB | 7 Oct 收集 |
| 处理后：知识库 YAML | `kb/*.yaml` | 12 | 349 KB | v0.1 加 A1、A1b、A2 的修改 |
| 处理后：构建脚本、引擎、测试 | `kb/build_kb.py`, `kb/tools/` | 14 | 405 KB | 同上 |
| 处理后：生成的报告和 Excel | `kb/out/` | 4 | 406 KB | 报告是最新的；两个 Excel 还停在 v0.1 |
| 处理后：第 1 轮验证 | `validation/`（V1 至 V5、packs、prompts、tools） | 280 | 1.6 MB | 7 Oct 完成，结论 NO-GO |
| 处理后：v0.2 每步检查 | `validation/build_checks/` | 21 | 937 KB | A1、A1b、A2 已完成 |

"未变"的依据：`validation/00_freeze.json` 里这些文件的 SHA-256 与现在的文件一致。

## 1. 原始数据

### 1.1 主办方（机密，仓库公开前必须删除）

| 文件 | 内容 | 规模 | 来源与日期 |
|---|---|---|---|
| `kb/sources/organizer/handbook.txt` | 黑客松手册全文的文字版；Ryde 赛道在第 5 节（挑战说明、四类争议、交付要求） | 59 KB | 主办方，2026-09-22（registry ID `ORG-HANDBOOK`） |
| `kb/sources/organizer/disp002.md` | 唯一的官方样例案件 DISP-002（No-show 扣费争议，期望裁决 UPHELD）。Markdown 里嵌一个 JSON，8 个部分：`dispute_ticket`, `rider_profile`, `driver_profile`, `trip_data`, `gps_telemetry`, `chat_logs`, `app_events`, `cancellation_policy`，共 59 个叶子字段 | 8 KB | 主办方，2026-09（`ORG-DISP002`）；人名和车牌是主办方虚构的 |

### 1.2 曹老师（内部，不可公开）

| 文件 | 内容 | 规模 |
|---|---|---|
| `kb/sources/chordx_knowledge_base.md` | ChordX 知识库协议 ONT.1 至 ONT.12 草稿（2026-09-25 修改）：三层框架 Taxonomy / Ontology / Rules、数据清单模板、ONT.11 脱敏实践。中文 | 18 KB |

### 1.3 Ryde 公开政策（`kb/sources/ryde_policy_corpus.json`，303 KB）

2026-10-05 通过 Ryde 帮助中心的公开 Zendesk API 抓取。

| 部分 | 内容 | 数量 |
|---|---|---|
| `articles` | 帮助中心文章：标题、URL、受众、所属栏目、创建和编辑日期、正文 `body_text`、自动抽取的 `key_statements` | 125 篇（乘客 65，司机 60；其中 2 篇是 10-05 为核对 taxonomy 术语补抓的） |
| `terms_of_use` | Ryde 使用条款（最后修改 2022-04-06） | 49 条；第 18、20 条只抓到摘录 |
| `section_listings` | 帮助中心栏目结构 | 46 个栏目 |
| `failures` | 没抓到的内容 | 7 项（2 篇文章、ToU 第 18 和 20 条、子条款编号、7.1 和 7.2 的邮箱、栏目总表） |

要知道的局限：抓取经过 WebFetch，正文是模型把 HTML 转写成的纯文本，不是逐字节副本。抽查了 6 篇的原始 HTML，措辞逐字一致；另有 37 条早先独立记录的原文片段在语料里全部找到。`key_statements` 是脚本自动抽的句子（每句都是正文的精确子串），严格说已经是轻度处理。

### 1.4 调研笔记（二手整理，5 Oct）

这三份是团队整理的笔记，不是一手文件；但它们是仓库里唯一保存外部网页原话的地方，KB 的引文就是对照它们核验的。

| 文件 | 内容 | 规模 |
|---|---|---|
| `kb/sources/research/02_industry_dispute_benchmark.md` | 其他平台（Grab、Gojek、Zig、TADA、Uber、Lyft、Bolt、DiDi）的取消、No-show、等候、车费、清洁、安全规则，每条带链接和日期 | 86 KB |
| `kb/sources/research/07_singapore_regulation_and_responsible_ai.md` | 新加坡法规与负责任 AI 背景（Platform Workers Act、LTA、PDPA、IMDA 框架等），标注 Binding / Guidance / Reference only | 85 KB |
| `kb/sources/research/09_fact_check.md` | 对笔记 01 至 08 中关键结论的事实核查，记录 Grab、Bolt、DiDi、LTA、IMDA 页面的逐字原文；`sources.yaml` 里 6 个外部来源的引文都对照这份核验 | 55 KB |

### 1.5 手工录入的外部数值（原文件不在仓库，数值在 `kb/reference_data.yaml`）

| 表 | 来源 | 可信度 |
|---|---|---|
| `ERP_RATE_TABLE` | LTA ERP 费率表，2026-03-23 起生效（只录了用到的闸口） | A |
| `VENUES` | OneMap 查询的地点坐标，3 个地点 | A |
| `PLATFORM_FEE_TIERS`, `TRANSACTION_FEE_LOCAL`, `TRANSACTION_FEE_FOREIGN`, `ERP_RIDER_SHARE` | Ryde 帮助中心文章（语料里有原文） | A |
| `CANCELLATION_FEE_DECOMPOSITION` | Ryde 文章脚注推算 S$6.61 = S$5.00 加平台费加交易费 | B |
| `TAXI_TARIFF` | ComfortDelGro 出租车计价（出自调研笔记 08，笔记不在仓库） | C |

### 1.6 真实投诉摘录（验证 V1.1，7 Oct 收集）

| 文件 | 内容 | 数量 |
|---|---|---|
| `validation/V1_taxonomy/10_cases.jsonl` | 新闻和论坛上的真实乘客或司机投诉摘录，带来源 URL、媒体、日期；人名、车牌、电话已替换成 `[NAME]` 等占位符 | 20 条（Ryde 7、Gojek 6、Grab 5、TADA 1、其他 1） |
| `validation/V1_taxonomy/10_collection_log.jsonl` | 收集时检索过的每个 URL 及是否入选、原因 | 134 个 URL |
| `validation/V1_taxonomy/10_cases_for_classifier.jsonl` | 同一批 20 条，去掉来源信息后给分类器用 | 20 条 |

这是项目里仅有的真实争议文本。真实的 Ryde 工单和历史裁决拿不到（见第 3 节）。

## 2. 处理后的数据

### 2.1 知识库（`kb/*.yaml`）

现状是 v0.1（5 Oct 建成，7 Oct 冻结验证）加上 A1、A1b、A2 三步修改，也就是做到一半的 v0.2；文件里的版本号还是 `0.1.0`，要到 A5 才改成 0.2.0。冻结时的 v0.1 原样保存在 `validation/packs/kb/`（五个核心 YAML 与 v0.1 逐字节相同），可以直接对比。

| 文件 | 内容 | 现在的数量 | 相对 v0.1 的变化 |
|---|---|---|---|
| `taxonomy.yaml` | 第 1 层分类：受控词表 | 22 个词表；争议类型 `TX-CASE` 33 个叶子（6 个大类） | 措辞小改 |
| `ontology.yaml` | 第 2 层本体：实体、属性、角色、关系、事件、状态机，以及 DISP-002 字段映射 | 20 个实体、22 个关系、11 个角色、35 个事件、4 个状态机、17 种 finding；DISP-002 映射 59/59 | 小改 |
| `rules.yaml` | 第 3 层规则：每条规则有来源条款原文、可信度 A 至 D、模式 HARD / READ；一张决策表 `DT-CW-NOSHOW` | 88 条规则；可信度 A 27、B 11、C 5、D 45；HARD 74、HARD+READ 6、READ 8；引用 158 处（124 处逐字核验、27 处无引文的设计假设、7 处转述）；决策表 96 种组合，无缺口无重叠 | v0.1 是 87 条（A1 新增 FC-R00）；C 6 变 5、D 43 变 45（A2 把 FC-R08 降为 D）；引用由 139 增至 158 |
| `reference_data.yaml` | 参数和参考表 | 2 个参数档（`organizer_case`, `ryde_2026`）、31 个共享参数、8 张表 | A2 新增 `ERP_RIDER_SHARE` 表（v0.1 是 7 张） |
| `playbooks.yaml` | 每类争议的处理流程 | 11 个（受理分类、No-show、乘客取消、等候费、绕路、ERP、改目的地、未接载、清洁费、转人工、转客服） | A1 至 A2 改了 No-show、等候费、绕路、ERP 四个流程的文字 |
| `scope.yaml` | 决策目标、11 个能力问题、v0.1 范围：裁决 5 类，需审批 3 类，转人工 8 类，转客服 6 类 | | 小改 |
| `open_items.yaml` | 待决事项 | Jasper 的决定 D1 至 D38；给主办方的问题 16 个；给曹老师的问题 6 个 | A1、A1b、A2 新增 D27 至 D38 |
| `sources.yaml` | 来源登记 | 15 份文件，加上 125 篇 Ryde 文章自动登记 | 未变 |
| `inventory.yaml` | ONT.3 数据收集清单 | 20 项：已有 8、部分已有 3（ToU 缺两条、ERP 只有一张表、地点只有 3 个）、缺 4、拿不到或不公开 3、待产出 2 | 未变 |
| `privacy.yaml` | ONT.11 脱敏规则：替换 8 类，保留 5 类 | | 未变 |
| `protocol_gap.yaml` | ChordX 协议各节与本 KB 的对照 | 19 行 | 未变 |
| `annotation_schema.yaml` | 人工标注表的设计 | 5 组字段、验证计划 | 小改 |

### 2.2 构建脚本、引擎和测试（`kb/build_kb.py`, `kb/tools/`）

| 文件 | 作用 | 备注 |
|---|---|---|
| `build_kb.py`, `kbload.py`, `checks.py`, `stats.py`, `report_md.py`, `make_xlsx.py` | 读 YAML、做一致性检查和引文核验、出报告和 Excel | |
| `engine_noshow.py` | No-show 争议的参考引擎（按 DT-CW-NOSHOW 判定） | A1、A1b、A2 改过；乘客消息的读取逻辑已冻结（D34） |
| `engine_toll.py` | ERP 计算（服务类型例外、优先顺序） | A2 新增 |
| `engine_gates.py` | 闸门 G3（AUTH-04）的可执行形式：看历史和不看历史的结果不一致时，保留不看历史的裁决，层级 APPROVE | A2 新增 |
| `selftest.py` | 引擎自测：99 个变体、39 个 ERP 案例、规则卡检查 | v0.1 是 61 个变体 |
| `cw_f06_reading_corpus.json` | A1 审查员为攻击 CW-F06 消息读取而写的 428 条乘客消息及标签；与精确用例合起来是 565 条读取测试，全部通过 | A1b 新增 |
| `fuzz_presence.py`, `explain.py`, `privacy_scan.py` | 模糊测试、裁决说明文字、隐私扫描 | |

### 2.3 生成的报告和 Excel（`kb/out/`）

| 文件 | 内容 | 是否最新 |
|---|---|---|
| `check_report.md` | 构建报告：全部计数、问题列表、引擎自测表、DISP-002 裁决 | 最新（A2） |
| `disp002_trace.md` | DISP-002 逐步推理轨迹：在两个参数档下都是 UPHOLD，审批层级 APPROVE | 最新（A2） |
| `FairRyde_KB_v0.1.xlsx` | 知识库中文工作簿，19 个工作表（说明、协议对照、范围、数据清单、Taxonomy、实体、关系、事件、DISP-002 映射、Rules、决策表、参考数据、操作指引、审批权限、来源、三层视图、引擎自测、标注方案、待决问题） | **过期**：还是 v0.1，缺 A1 至 A2 的修改（例如没有 FC-R00） |
| `FairRyde_Annotation_v0.1.xlsx` | 人工标注表（说明、标注表、覆盖检查、下拉列表） | **过期**：同上 |

两个 Excel 会在 A5 的完整构建时重新生成；需要更早拿到，可以运行不带 `--no-xlsx` 的 `python3 kb/build_kb.py`。

### 2.4 第 1 轮独立验证（`validation/`，7 Oct，对象是冻结的 v0.1）

| 位置 | 内容 | 关键数字 |
|---|---|---|
| `00_freeze.json`, `01_plan.yaml`, `01_plan.sha256` | 冻结哈希；预先登记的计划、阈值和判定规则 | 35 个文件 |
| `packs/` | 发给验证代理的输入包，全部是原始数据或 KB 的副本或摘录，没有新信息：`packs/kb` 是 v0.1 的五个 YAML；`packs/policy` 是手册、DISP-002、125 篇 Ryde 文章各一个 txt、索引和使用条款；`packs/sources` 是按来源 ID 的摘录（有几个就是 `09_fact_check.md` 全文）；`packs/ontology` 14 项；`packs/rules` 22 条规则各两遍；`packs/taxonomy` 1 个 | 212 个文件 |
| `V1_taxonomy/` | 20 条真实投诉（见 1.6），KB 分类结果、盲评标签、裁定 | M1 分类准确率 18/20 = 0.90，好 |
| `V2_ontology/` | 抽 14 个本体项目核对原文 | M2 11/14 = 0.79，差 |
| `V3_rules/` | 分层抽 20 条规则加关键路径规则，两位审查员盲审，再裁决分歧 | M3 13/20 = 0.65，差 |
| `V4_e2e/` | 只依据 Ryde 政策写的 15 个合成案件 E01 至 E15（No-show 4、乘客取消 2、等候费 2、绕路 2、ERP 1、清洁费 1、安全 1、失物 1、评分申诉 1），预期结果、仅按政策的标签、参考答案、引擎和 KB 应用者的判定、比对、裁决；`46_human_check.jsonl` 是 Jasper 11 Oct 对 4 个不一致案件的确认 | M5 留出集判定准确率 11/15 = 0.73，可接受 |
| `V5_scorecard/` | 引文核验、评分卡、完整性检查、时间线、修复清单 FX1 至 FX9（FX1 至 FX7 为第一优先级）、评分卡网页 | M4 冲突或无依据率 7/34 = 0.21，差；结论 NO-GO |
| `prompts/` | 每个验证代理的提示词 | 12 个 |
| `run_log.jsonl` | 每一步的开始和结束记录，7 Oct 至今 | 77 条（本步之前） |

### 2.5 v0.2 每步检查（`validation/build_checks/`）

每步保存：引擎重跑结果、新 KB 应用者对受影响案件的判定、四位审查员加怀疑者的两轮审查、逐条处理记录。

| 步骤 | 修的是什么 | 两轮发现 | 处理结果 |
|---|---|---|---|
| A1 | FX1 乘客证据按内容判断；FX2 计价出租车不做绕路退款 | 46 条 | 修复 41，部分或减轻 2，未改 2，记入待决 1 |
| A1b | 落实 Jasper 的决定 D27、D30、D31；冻结消息读取（D34） | 72 条 | 修复 68，怀疑者驳回 2，部分 1，未修 1 |
| A2 | FX3 ERP 例外和优先顺序；FX5 闸门 G3；D32；D34 限制 1 | 88 条 | 修复 70，部分 6，记入待决 8，驳回 4 |

A2 第 1 轮启动时参数没传进去，没有跑 KB 应用者，所以 A2 目录里没有 `02_applier.jsonl`；第 2 轮正常（E10、E11、E03 三个案件的判定都与参考一致）。

## 3. 缺口：需要或被引用、但不在仓库里的数据

| 数据 | 情况 | 记录在哪 |
|---|---|---|
| 化名对照表（真名到代号） | 按 ONT.11 只放在 Jasper 电脑上（`kb/private/` 已被 git 忽略），不是缺失 | `privacy.yaml` |
| ADP AppKey | 绝不入库 | `CLAUDE.md` |
| 主办方的其他样例案件（DISP-001、绕路、脏污、安全） | 没有 | `inventory.yaml` |
| 赛道评分细则 | 没有 | `inventory.yaml` |
| DISP-002 缺的行程字段（预约类型、服务类型、计价方式、各时间点、车费明细、实际里程、推荐路线、乘客 GPS） | 没有，KB 里标为 data_gap 并推断或转人工 | `ontology.yaml`, `inventory.yaml` |
| Ryde 内部：真实工单和历史裁决、退款审批权限表、RydeX 和 RydePOOL 车费公式 | 拿不到 | `inventory.yaml` |
| 人工金标准标注（标注表） | 待产出 | `inventory.yaml`, `annotation_schema.yaml` |
| ERP 费率表：2026-09-07 起是否有新表；完整表 | 只有 2026-03-23 的部分 | `inventory.yaml` |
| LTA DataMall 交通快照 | 没有，合成案件里用标为 synthetic 的快照 | `inventory.yaml` |
| LTA 出租车司机（TDVL）违规清单 | 只找到私召车 PDVL 的 | `docs/NEXT_STEPS.md` |
| Ryde 使用条款第 18、20 条全文；2 篇帮助中心文章 | 抓取失败 | `ryde_policy_corpus.json` 的 `failures` |
| 调研笔记 01、03、04、05、06、08 | `09_fact_check.md` 核查过它们，`TAXI_TARIFF` 引用了笔记 08，但笔记本身不在仓库 | 本清单 |
| ChordX `chordx_core.md`（DRT/DEP）和 `chordx_security.md`（SEC.6 密级） | 已向曹老师索取 | `open_items.yaml` |
| 原始 PDF（手册、LTA、IMDA、PDPC） | 仓库里只有文字版或引文记录 | `sources.yaml` |

## 4. 数据怎么流动

1. 原始数据（第 1 节）到知识库：规则、本体和分类按原文写成 YAML，每条引文必须是来源的精确子串，由 `build_kb.py` 核验。
2. 知识库到生成物：`build_kb.py` 产出检查报告、DISP-002 轨迹和 Excel，并跑引擎自测和隐私扫描。
3. 冻结并验证：`freeze.py` 记下哈希，`packs/` 打包输入，V1 至 V5 由独立代理判定，得出评分卡和修复清单。
4. 按修复清单逐步改（A1、A1b、A2，接下来 A3 至 A5），每步做同样的独立检查，结果存入 `build_checks/`，剩下的问题进 `open_items.yaml`。
5. A5 冻结 v0.2 之后做第 2 轮验证（`validation/round2/`）。

## 5. 公开仓库前要删除的文件

主办方手册和样例（`kb/sources/organizer/`, `validation/packs/policy/organizer_*`, `validation/packs/sources/ORG-*`）；曹老师的协议（`kb/sources/chordx_knowledge_base.md`, `validation/packs/sources/INT-CHORDX-ONT.txt`）。
