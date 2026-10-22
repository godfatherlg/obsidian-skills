# True Recall 统计面板：数据源 / 为什么删卡后数字还在 / 怎么清

> 起因：2026-09-14 广哥截图 Statistics 面板问「这些记录怎么删，因为对应的卡应该都没了，但是这些数据还在」。
> 事后做源码核对 + 库内实测 + 库内实况比对，结论如下。
> 配套脚本：**已并入** `<vault>\Scripts\truerecall清理.js`（QuickAdd 宏 **`TR清理`**，`MODE="auto"` 时清完孤儿顺手按判据重建；详见 §七）。
> 本文写于 2026-09-14，当时统计重建还是一个独立脚本/宏（同日 `.3` 版并入 `TR清理`，本文已同步口径）。

## 一、面板数字读的是哪张表（源码级）

`Statistics` 顶部那六个格子（Studied today / Minutes / Correct / Current streak / Due tomorrow / Total cards）
在**没有启用筛选**时读的是**预聚合表 `daily_stats`**。源码 `getFilteredDailyStats()` 原文：

```js
getFilteredDailyStats() {
    let e = Xt(qn(this.dayStartHour)), r = `all:${e}:${this.filterCacheKey}`, n = this.dailyStatsCache.get(r);
    if (n) return n;
    ...
    if (!this.isFilterActive) i = this.sessionPersistence.getAllDailyStatsSummary();   // ← 读 daily_stats 表
    else if (!this.sqliteStore) i = {};
    else {                                                                             // ← 从 review_log 现算
        let s = this.sqliteStore.stats.getDailyStatsFromReviewLog("1970-01-01", e, {
            presetNames: this.filter.presetNames ? [...this.filter.presetNames] : void 0,
            excludeSourceUids: [...this.filter.archivedSourceUids]
        });
        i = {}; for (let o of s) i[o.date] = o;
    }
    return this.dailyStatsCache.set(r, i), i;
}
```

分叉开关是 `get isFilterActive(){ return this.filter.archivedSourceUids.size > 0 || this.filter.presetNames !== null }`
—— **只有用了 preset 或 archived 筛选，才改走"从 review_log 现算"**；平时（无筛选）走的是 `daily_stats` 预聚合表。

各格的来源（`getTodaySummary()` 与顶部组件 `V1({today, streak, dueTomorrow, totalCards})`）：

| 格子 | 来源 |
| --- | --- |
| Studied today | `daily_stats.reviews_completed`（今日那天） |
| Minutes | `Math.round(daily_stats.total_time_ms / 60000)` |
| Correct | `(good_count + easy_count) / (again + hard + good + easy)` |
| Current streak | `getStreakInfo()` —— 基于**已过滤的逐日统计**的日期序列 |
| Due tomorrow | 从活卡现算（`getDueCards` 一类） |
| Total cards | `getAllFSRSCards()` 过滤 archived 后的长度 ⇒ **这个和卡片表同步**，删卡就会掉 |

`daily_stats` 表结构（建库 DDL 原文摘录）：

```sql
CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY NOT NULL,
    reviews_completed INTEGER DEFAULT 0,
    new_cards_studied INTEGER DEFAULT 0,
    total_time_ms INTEGER DEFAULT 0,
    again_count INTEGER DEFAULT 0,
    hard_count INTEGER DEFAULT 0,
    good_count INTEGER DEFAULT 0,
    easy_count INTEGER DEFAULT 0,
    new_cards INTEGER DEFAULT 0,
    learning_cards INTEGER DEFAULT 0,
    review_cards INTEGER DEFAULT 0
);
```

## 二、为什么卡删了、复习记录也软删了，数字还在

**因为删卡不碰 `daily_stats`。** 删卡走的 `bulkSoftDelete` 源码原文：

```js
bulkSoftDelete(e) {
    let r = Date.now(), n = Nn(e.length);
    return this.db.transaction(() => {
        this.db.run(`UPDATE review_log SET deleted_at = ?, updated_at = ? WHERE card_id IN (${n}) AND deleted_at IS NULL`, [r, r, ...e]);
        this.db.run(`UPDATE cards SET deleted_at = ?, updated_at = ? WHERE id IN (${n})`, [r, r, ...e]);
    }), e.length
}
```

只软删 `cards` + 这些卡的 `review_log`，**一个字都没写 `daily_stats`**。
`daily_stats` 的写入点只有两处，都由"复习动作"触发：`updateDailyStats()`
（`INSERT ... ON CONFLICT(date) DO UPDATE SET reviews_completed = reviews_completed + excluded.reviews_completed ...`，**累加**）
与 `decrementDailyStats()`（`MAX(0, x - ?)`，撤销复习）。

⇒ 数据层真相：**`daily_stats` 是纯派生表，权威源只有 `review_log`**。
卡删光后 `review_log` 里那些行虽然还在（软删），但 `daily_stats` 里的聚合值没人去减。

## 三、没有官方"清空统计"入口

2026-09-14 逐处核过：

1. **命令面板没有**：`addCommand({id:...})` 全表 37 个 id（`add-flashcard` / `open-stats` / `create-backup` / `import-anki` …），没有任何统计/重置类命令；`open-stats` 只是打开面板。
2. **源码没有重置函数**：搜 `resetStatistics|clearStatistics|clearReviewHistory|resetReview|deleteAllReviews` → **0 命中**。
3. **Local API 也不行**：71 条路由里没有统计端点；而且 **`POST /query` 只放行 SELECT** ——
   ```js
   let s = i.sql.trim();
   if (!s.toUpperCase().startsWith("SELECT")) { fe(e, 403, "Only SELECT queries are allowed"); return; }
   if (s.replace(/;\s*$/, "").includes(";")) { fe(e, 403, "Multiple statements are not allowed"); return; }
   ```
   所以别指望"从外部一句 SQL 清掉"。

## 四、正解 = 调插件自己的重建方法

插件已经内置了重建逻辑，只是没有 UI 入口：

```js
plugin.cardStore.stats.rebuildDailyStatsFromReviewLog(plugin.settings.dayStartHour)
```

源码原文（`dailyProgress` 段）：

```js
rebuildDailyStatsFromReviewLog(e = 4) {
    let r = this.db.query(`SELECT card_id, reviewed_at, rating, state, time_spent_ms
                           FROM review_log
                           WHERE deleted_at IS NULL
                             AND reviewed_at IS NOT NULL
                             AND (review_kind IS NULL OR review_kind != 'preview')`);
    ... // 按 dayStartHour 分桶累加
    this.db.transaction(() => {
        this.db.run("DELETE FROM daily_stats");
        this.db.run("DELETE FROM daily_reviewed_cards");
        for (let [s, o] of n) { this.db.run("INSERT INTO daily_stats (...) VALUES (...)", ...); ... }
    })
}
```

即：**先清空两张派生表，再从"未软删的 `review_log`"重算**。
它本来就是插件自己的修复路径 —— 设备/云同步拉到数据后会调它
（`mergeFromRemote` 里 `if (e.cardsApplied > 0 || e.reviewLogsApplied > 0) this.localStore.stats.rebuildDailyStatsFromReviewLog(...)`；
pull 路径同理），而且失败只记一行 `Failed to rebuild stats: ...`。

⇒ 卡与复习记录都已软删时（`review_log` 未软删数 = 0），重建结果就是**两张空表 = 统计归零**。

## 五、「换个筛选数字就变 0」是假象，不能当解决办法

启用任意 preset / archived 筛选 → `isFilterActive` 为真 → 走 `getDailyStatsFromReviewLog()`，
那是**从 `review_log` 现算**，本来就看不到已软删的记录 ⇒ 数字当场变 0。
（该方法的 SQL 里 `WHERE r.deleted_at IS NULL AND c.deleted_at IS NULL` 是写死的 —— 2026-09-14 源码核对，
所以 `TR清理` 之后这条路径**同样**是 0，两条路都对得上。
反过来说，**「切个筛选数字就变 0」不是重建生效的证据**：它只是换了个视角看同一个 0。）
但那只是换个视角看 0：`daily_stats` 里的旧值还在，**取消筛选就回来了**；
而且以后每次复习是 `ON CONFLICT DO UPDATE ... = 旧值 + 新值`，旧值会**一直累加**在上面。
⇒ 必须重建，不能靠筛选。

## 六、缓存：不用重载 Obsidian，但**必须让面板重新取一次数**

先说对的一半 —— 大部分统计小组件（周视图 / 热力图 / Load Balance / Note Performance 之类）确实是
**每次取数现场 `new`**，形状一致：

```js
let n = new ci(r.plugin.fsrsService, r.plugin.flashcardManager, r.plugin.sessionPersistence, r.plugin.settings.dayStartHour);
```

这类实例自带一个全新的 `dailyStatsCache` Map，**即用即弃**，不存在跨请求残留。

**但主 `Statistics` 视图不是这样（2026-09-14 实机踩到）**。它的取数函数 `$oe(t,e,r)` 里：

```js
let c = Ce(() => { let A = new ci(n.fsrsService, n.flashcardManager, n.sessionPersistence, n.settings.dayStartHour);
                   return A.setSqliteStore(n.cardStore), A; }, [n]);
// …
le(() => {                       // ← 真正的取数在这里，还带 300ms 节流
    c.setCardSnapshot(u), c.setFilter(f ?? ny);
    let h = window.setTimeout(() => { if (!A) { let g = c.getTodaySummary(), y = c.getStreakInfo(), … a.value = { today: g, … }; } }, m);
});
```

两点要点：

1. `c = Ce(…, [n])` 的依赖只有 plugin ⇒ **统计实例与视图同寿命**，它自己的 `dailyStatsCache`
   （最多 20 条，key = `` `all:${todayKey}:${filterCacheKey}` ``）会一直留着。
2. 结果存进组件状态 `a.value`，取数发生在那个 effect 里；effect 只在
   **卡片集合 / 筛选 / 时间范围 / 面板可见性**变化时重跑 —— **`daily_stats` 表被外部改写不在依赖里**，
   插件也没有任何"统计表变了"的事件。

⇒ **外部脚本重建完，已经开着的面板会继续显示旧对象**。类内的 `clearDailyStatsCaches()` 只在同一实例的
`setFilter` / `setCardSnapshot` 里被调用，且两处都有 `!==` 守卫 —— 值没变就不清，指望不上。

**实证**（2026-09-14）：`TR清理` 22:29:08 重建成功（日志 `复核 daily_stats=0 天`，只读查库也确认为 0 行），
22:30:33 面板仍显示 Studied today 41 / Minutes 79 / Correct 80% / streak 2d；
**点一下 `Archived` 筛选，数字立刻变 0** —— 因为筛选变了，effect 重跑、重新查库。

**实操结论**：

- 判据看**日志那一行**（`复核 daily_stats=? 天`）或只读查库，**别信面板**；
- 重建后**关掉统计面板重开**，或点一下筛选 / 切一下时间范围即可见新值；
- 不需要重启 Obsidian，也不需要脚本去清缓存（缓存挂在视图实例上，脚本够不着）。

## 七、本机实现：统计重建已并入 QuickAdd 宏 `TR清理`（现 `2026-09-14.4`）

- 脚本：`<vault>\Scripts\truerecall清理.js`（**`2026-09-14.4`**；统计这半同日 `.3` 从独立脚本 `truerecall统计重建.js` 并进来，旧脚本与宏 `TR统计重建` 一起退役；`.4` 只在重建成功的 Notice 里加了一句"面板不会自动刷新"的提示，逻辑未变）。
- 宏：QuickAdd Macro **`TR清理`**（`command:true`、**`runOnStartup:false`**，手动跑一次就把两件事做完）。
- 顶部常量 `MODE` 四态：`"auto"`（默认 = 清孤儿 + 按需重建统计）| `"stats"`（只重建）| `"cleanup"`（只清孤儿，不碰统计）| `"report"`（只报告，不改任何数据）。
- 一趟的顺序：① 盘点报告（活卡 / 软删卡 / 活 note / 孤儿 / `review_log` 总数与未软删数 /
  `daily_stats` 逐日明细 / `daily_reviewed_cards` 行数）；② 两道闸（清理、重建、还原**共用同一套**，只过一次）；
  ③ 清孤儿（删前写 `.true-recall/tr-cleanup-undo.jsonl`，写不进去就一条都不删）；
  ④ 重建统计（**仅当判据要求**）—— 先把 `daily_stats` 与 `daily_reviewed_cards` 全量快照写入
  `.true-recall/tr-stats-undo.jsonl`（**快照写不进去就不重建**），再调
  `store.stats.rebuildDailyStatsFromReviewLog(plugin.settings.dayStartHour)`，然后 `markDirty()` + `saveNow()`，
  最后复核两张表行数；⑤ 一条汇总 Notice。
- **是否重建的判据 = `statsDiagnosis`（纯函数）**：`daily_stats` 各天 `reviews_completed` 之和
  vs `review_log WHERE deleted_at IS NULL` 条数；**相等就跳过**（不做无谓写库），不等才重建。
  两者都为空也算相等 ⇒ 干净库上跑 `TR清理` 不会平白重算。
- **还原**：两套 flag 各自独立，可同轮一起做 ——
  `.true-recall/undo-restore.flag` → 复活最近一批被清理的 note；
  `.true-recall/stats-restore.flag` → 用 undo 清单里**最近一批**快照 `INSERT OR REPLACE` 回填两张表；
  跑完各自删掉自己的 flag。（统计本可重算，一般用不到；留着是因为"可回滚"是本 skill 的一贯要求。）
- 诊断日志：`.true-recall/tr-cleanup.log`（**覆盖写**，**与清理共用一份**；原 `tr-stats.log` 随独立脚本一起退役）。
- 离线测试台：`scripts/test_tr_cleanup.js` —— **187 项**（`TR_CLEANUP_SCRIPT` 可指向任意副本）。
  覆盖：纯函数 15 个（含 `statsDiagnosis` 八条判据、`pickStore` 反射兜底、`readiness` 七条路径、
  `gatherBusy` 六种组合、`dayStartHour`、`fmtDailyRow`、`findRebuild` 四个落点）、端到端 24 组
  （MODE 四态 / 有孤儿+统计过期 / 无孤儿只重建 / 统计一致只清理 / 两件都无早退 / 就绪闸 not-ready /
  持久化挂起 / unknown 的保守分流与放行 / 避让闸超时 / 撤销清单写不进 / 快照写不进 / 找不到重建方法 /
  重建抛错 / 落盘失败 / note 还原 / 统计还原 / 双 flag 同轮 / 无 app / 插件未启用）。
- **⚠️ 就绪判据 `unknown` 时的分流（合并后刻意如此）**：清理侧**保守挡**（删 note 不可逆，宁可漏清；
  全库活卡=0 时只报告不删），统计侧**放行**（只动派生统计表、不碰卡片，且重算可由下一次运行自愈）。
  两道闸的其余部分（`persistenceHalted`、后台备份、云同步等待重试）两者完全一致。

## 八、库内实测（2026-09-14 22:xx，对照截图）

重建前快照（Local API 只读）：

- `daily_stats` **2 行**：`2026-09-13`（复习 12 次 / 新卡 11 / 341986ms）、
  `2026-09-14`（复习 **41** 次 / 新卡 38 / **4762675ms** / good 33 / hard 1 / again 7）。
- `review_log` **53 条，其中未软删 0 条**（全被删卡连带软删）。
- `daily_reviewed_cards` **0 行**；活卡 **0**、软删卡 **413**。

对照截图：Studied today **41** ✓、Minutes **79**（4762675/60000 = 79.4）✓、
Correct **80%**（33/41 = 80.5%）✓、Current streak **2d**（09-13、09-14 两天的记录）✓、
Total cards **0**（活卡确实是 0）✓ —— **六个数字全部对上 `daily_stats` 那一行，实锤它读的就是预聚合表**。

## 九、附：`daily_reviewed_cards` 是什么

"今天复习过哪些卡"的明细表，`PRIMARY KEY (date, card_id)`；
`getReviewedToday()` = `getReviewedCardIds(今天)` 读它，`recordReviewedCard` / `removeReviewedCard` 写它。
它与 `daily_stats` 同属派生数据，**删卡同样不会清它**，重建时被 `DELETE` 后一并重算。
