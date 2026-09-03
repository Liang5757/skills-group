# 中央汇金公开信息跟踪器

这是一个“证据优先”的公开披露跟踪器。它不会把季度持仓快照伪装成实时成交，也不会把“退出前十大股东”解释成清仓。

## 已实现

- 中央汇金官网资讯中心抓取、原始 HTML 归档和明确操作识别。
- 巨潮资讯公告标题查询、原始元数据归档和数据源水位记录。
- 港交所权益披露（DI）按申报人检索、官方列表页归档，并以 `DEEMED_INTEREST_CHANGE` 单独建账。
- 东方财富全市场十大股东/十大流通股东扫描，严格匹配：
  - 中央汇金投资有限责任公司；
  - 中央汇金资产管理有限责任公司；
  - 名称明确包含汇金资管的单一资产管理计划；
  - 中国证券金融股份有限公司，始终标记为关联受控主体而非汇金直接交易。
- SQLite 持仓快照、事件账本、幂等键和数据源健康状态。
- 东方财富分页原始 JSON 归档；完整性同时校验页数和原始行数。
- 持仓事件语义：快照增加/减少、进入/退出前十、仅比例变化。
- 可选飞书 Webhook 推送；失败通知进入持久化发件箱并在后续轮询重试。
- `watch` 常驻轮询官网和巨潮；重复抓取不会重复生成事件。

## 信息边界

- `CONFIRMED_*` 只用于官方来源明确写出的操作。
- `SNAPSHOT_*` 只表示两个期末快照之间有变化，不能定位交易日。
- `ENTERED_TOP10` 不等于首次买入。
- `LEFT_TOP10` 不等于减持或清仓。
- 东方财富属于聚合源，事件置信度固定为 `AGGREGATED_SNAPSHOT`，需要回查官方报告。
- 中国证券金融股份有限公司始终作为 `RELATED_CONTROLLED` 单独入账，默认不进入中央汇金直接操作告警。
- 比例变化小于四位小数展示精度的一半时视为计算噪声，不生成事件。
- 报告期法定披露窗口结束前，不把分页完整等同于市场披露完整，因此不会生成退出前十事件或建立完整基线。
- 巨潮 `searchkey` 只搜索公告标题，不能替代季度全市场持仓扫描。
- 港交所 DI 披露可能是受控法团权益、淡仓或其他法定申报原因，不能仅凭股份变化列推断中央汇金直接买卖。
- 中国证监会 2026 年新版公募基金定期报告准则自 5 月 1 日实施，已不再固定要求披露上市基金前十名持有人；因此 ETF 份额持有人链路只能覆盖历史或自愿披露，不能承诺连续完整。
- 尚未公开、低于披露阈值或未进入前十名的操作无法可靠获得。

## 本地运行

以下命令均从 `.agents/skills/huijin-tracker/` 目录执行。

```bash
export PYTHONPATH="$PWD/src"
python -m huijin_tracker init
python -m huijin_tracker collect-huijin --years 2025,2026
python -m huijin_tracker collect-cninfo --since 2026-09-01 --until 2026-09-02
python -m huijin_tracker collect-hkex --since 2026-08-20 --until 2026-09-02
python -m huijin_tracker sync-holdings --period 2026-03-31 --scope top10_float
python -m huijin_tracker watch --interval-seconds 1800
python -m huijin_tracker events
python -m huijin_tracker status
```

飞书通知是可选的：

```bash
export HUJIN_FEISHU_WEBHOOK='https://open.feishu.cn/open-apis/bot/v2/hook/...'
export HUJIN_FEISHU_SECRET='可选的签名密钥'
```

不要把 Webhook 或签名密钥写入源码、配置样例或日志。

## 建议调度

- 官网和公告元数据：披露时段每 15–30 分钟，其他时段每小时。
- 持仓聚合扫描：每个报告季按报告期运行一次；数据未披露完时不要把扫描标记为完整。
- `watch` 仅轮询轻量的官网与公告源，不会每 30 分钟扫描五万多条季度持仓。
- 每次扫描先跑较早报告期建立基线，再跑新报告期生成差异事件。
- `sync-holdings` 始终保存证金公司数据以保持跨期口径稳定，但默认不展示或通知；需要审阅时加 `--include-related`。
- `--max-pages` 仅用于冒烟测试，所得扫描永远不视为完整；`--force-complete` 只应用于已人工核验覆盖率的开放报告期。
- 生产环境应保留 `data/archive/`，并备份 SQLite 数据库。

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

测试覆盖主体归因、计划账户隔离、官网解析、已完成操作与未来计划区分、分页及行数完整性、原始证据回调、报告窗口、基线、快照增减、比例噪声、进入/退出前十、当前期缺席证据、不完整扫描保护、幂等性、通知重试和源站失败计数。
