#!/usr/bin/env node
/**
 * TR清理（<vault>\Scripts\truerecall清理.js）离线测试台
 *
 * 覆盖两块：
 *   A. 纯函数 —— readiness / gatherBusy / typeName / countByType / typeSummary /
 *      field / str / num / fmtDailyRow / statsDiagnosis / dayStartHour / findRebuild / pickStore。
 *   B. 端到端（假 store）—— 清理阶段（软删 note）与统计阶段（重建 daily_stats）的编排：
 *      MODE 四态、就绪闸 / 避让闸、unknown 的保守分流、undo 清单与统计快照写不进时不动数据、
 *      两个还原 flag 各自独立、无 app 早退。
 *
 * 依赖真实插件内存的只有"删除后落盘"这一步，其余用假 store 全量覆盖。
 *
 * 用法：
 *   node test_tr_cleanup.js
 *   指向别处的副本：TR_CLEANUP_SCRIPT=D:\path\to\truerecall清理.js node test_tr_cleanup.js
 */

const fs = require("fs");
const os = require("os");
const path = require("path");

const SCRIPT =
  process.env.TR_CLEANUP_SCRIPT ||
  "<vault>\\Scripts\\truerecall清理.js";

let pass = 0;
let fail = 0;
const fails = [];

function ok(name, cond, extra) {
  if (cond) { pass++; }
  else { fail++; fails.push(name + (extra ? "  → " + extra : "")); }
}
function eq(actual, expected, label) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a === e) { pass++; }
  else { fail++; fails.push(`${label}\n    expected: ${e}\n    actual:   ${a}`); }
}
const throws = (fn) => {
  try { fn(); return false; } catch (_) { return true; }
};

/* ---------- 假环境 ---------- */

function makeDaily(over) {
  return Object.assign({
    date: "2026-09-14", reviews_completed: 41, new_cards_studied: 38,
    total_time_ms: 4762675, again_count: 7, hard_count: 1, good_count: 33,
    easy_count: 0, new_cards: 38, learning_cards: 3, review_cards: 0
  }, over || {});
}

function makeOrphanRows(n, type) {
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({ id: "note-" + i, typeId: type || "io", sourceUid: "uid-" + i,
               via: "quickadd", createdAt: 1757800000000 + i });
  }
  return out;
}

function makeFake(opts) {
  const o = opts || {};
  const orphans = o.orphans !== undefined ? o.orphans : 8;
  const calls = {
    run: [], query: [], saveNow: 0, markDirty: 0, rebuild: [], append: [],
    write: [], remove: [], noteDelete: []
  };
  const state = {
    dailyStats: o.dailyStats !== undefined ? o.dailyStats : [makeDaily()],
    drc: o.drc !== undefined ? o.drc : [{ date: "2026-09-14", card_id: "c1" }],
    liveCards: o.liveCards !== undefined ? o.liveCards : 0,
    delCards: o.delCards !== undefined ? o.delCards : 413,
    liveNotes: o.liveNotes !== undefined ? o.liveNotes : orphans,
    orphans,
    orphanRows: o.orphanRows !== undefined ? o.orphanRows : makeOrphanRows(orphans),
    rlTotal: o.rlTotal !== undefined ? o.rlTotal : 53,
    rlLive: o.rlLive !== undefined ? o.rlLive : 0,
    rebuildThrows: !!o.rebuildThrows,
    noteDeletedAt: o.noteDeletedAt || {}
  };

  const norm = (sql) => String(sql).replace(/\s+/g, " ").trim();

  const db = {
    query(sql) {
      calls.query.push(sql);
      const s = norm(sql);
      if (s.startsWith("SELECT * FROM daily_stats")) return state.dailyStats.map((r) => Object.assign({}, r));
      if (s.startsWith("SELECT * FROM daily_reviewed_cards")) return state.drc.map((r) => Object.assign({}, r));
      if (s.startsWith("SELECT n.id AS id")) return state.orphanRows.map((r) => Object.assign({}, r));
      return [];
    },
    get(sql, params) {
      const s = norm(sql);
      if (s.startsWith("SELECT deleted_at FROM notes WHERE id = ?")) {
        const id = params && params[0];
        const v = state.noteDeletedAt[id];
        return v === undefined ? { deleted_at: 1757800000000 } : { deleted_at: v };
      }
      if (s.startsWith("SELECT COUNT(*) AS n FROM cards WHERE deleted_at IS NULL")) return { n: state.liveCards };
      if (s.startsWith("SELECT COUNT(*) AS n FROM cards WHERE deleted_at IS NOT NULL")) return { n: state.delCards };
      if (s.startsWith("SELECT COUNT(*) AS n FROM notes n ")) return { n: state.orphans };
      if (s.startsWith("SELECT COUNT(*) AS n FROM notes WHERE deleted_at IS NULL")) return { n: state.liveNotes };
      if (s.startsWith("SELECT COUNT(*) AS n FROM review_log WHERE deleted_at IS NULL")) return { n: state.rlLive };
      if (s.startsWith("SELECT COUNT(*) AS n FROM review_log")) return { n: state.rlTotal };
      if (s.startsWith("SELECT COUNT(*) AS n FROM daily_reviewed_cards")) return { n: state.drc.length };
      if (s.startsWith("SELECT COUNT(*) AS n FROM daily_stats")) return { n: state.dailyStats.length };
      return null;
    },
    run(sql, params) { calls.run.push([norm(sql), params]); return 1; }
  };

  const rebuildFn = function (h) {
    calls.rebuild.push(h);
    if (state.rebuildThrows) throw new Error("boom");
    // 模拟插件行为：清空两张表后按 live review_log 重算（这里 live=0 → 结果空）
    state.dailyStats = [];
    state.drc = [];
  };

  const statsHolder = { rebuildDailyStatsFromReviewLog: o.rebuildOn === "store" ? undefined : rebuildFn };
  if (o.rebuildOn === "store") delete statsHolder.rebuildDailyStatsFromReviewLog;

  const notesRepo = { delete: (id) => { calls.noteDelete.push(id); return true; } };

  const store = {
    db, notes: notesRepo, stats: statsHolder,
    noteTypes: { getById: () => ({ name: "Image occlusion" }) },
    saveNow: async () => { calls.saveNow++; return o.saveNowReturns !== undefined ? o.saveNowReturns : true; },
    markDirty: () => { calls.markDirty++; }
  };
  if (o.readyState === "ready") store.isReady = () => true;
  else if (o.readyState === "not-ready") store.isReady = () => false;
  else if (o.readyState === "throw") store.isReady = () => { throw new Error("nope"); };
  else if (o.readyState === "isLoaded") {
    store.isLoaded = o.isLoaded !== false;
    db.isReady = () => o.dbReady !== false;
  }
  if (o.halted) store.persistenceHalted = true;

  const plugin = { settings: { dayStartHour: o.dayStartHour !== undefined ? o.dayStartHour : 4 } };
  if (o.storeKey === "store") plugin.store = store; else plugin.cardStore = store;
  if (o.busyBackup) plugin.coreApp = { backgroundBackupManager: { getStatus: () => ({ isBackupInProgress: true }) } };
  if (o.busyCloud) plugin.cloudSyncManager = { coordinator: { isSyncing: { value: true } } };
  if (o.busyCloudStatic) plugin.cloudSyncManager = { coordinator: { isSyncing: true } };
  if (o.busyDevice) plugin.syncCoordinator = { isSyncing: { value: true } };
  if (o.backupThrows) plugin.coreApp = { backgroundBackupManager: { getStatus: () => { throw new Error("x"); } } };

  const flags = o.flags || {};
  const adapter = {
    write: async (p, body) => { calls.write.push([p, body]); return true; },
    append: async (p, line) => { calls.append.push([p, line]); if (o.appendThrows) throw new Error("no append"); return true; },
    read: async (p) => (o.undoText || {})[p] || "",
    exists: async (p) => !!flags[p],
    remove: async (p) => { calls.remove.push(p); return true; }
  };

  const app = o.noApp ? null : { vault: { adapter }, plugins: { plugins: { "true-recall": plugin } } };
  return { app, store, plugin, calls, state, flags };
}

function makeParams(app, noticeSink) {
  class Notice { constructor(msg) { noticeSink.push(msg); } }
  return { app, obsidian: { Notice } };
}

/* ---------- 变体加载（改 MODE / 等待时长 / 临时路径用） ---------- */

// 每次运行用独立子目录，避免读到上一轮遗留的日志/清单文件（曾因此误判过一次）
const TMP_DIR = path.join(os.tmpdir(), "tr_cleanup_test_" + Date.now() + "_" + Math.random().toString(36).slice(2))
  .replace(/\\/g, "/");
fs.mkdirSync(TMP_DIR, { recursive: true });

function loadVariant(replacements) {
  let src = fs.readFileSync(SCRIPT, "utf8");
  for (const [a, b] of replacements) src = src.split(a).join(b);
  const f = path.join(os.tmpdir(), "tr_cleanup_variant_" + Math.random().toString(36).slice(2) + ".js");
  fs.writeFileSync(f, src, "utf8");
  return f;
}

// 基准副本：日志与 undo 一律改写到系统临时目录，别碰真实的 .workbuddy\tmp
const base = require(loadVariant([
  ["C:\\\\Users\\\\<user>\\\\.workbuddy\\\\tmp\\\\truerecall-cleanup.log", TMP_DIR + "/tr-cleanup-test.log"],
  ["C:\\\\Users\\\\<user>\\\\.workbuddy\\\\tmp\\\\truerecall-cleanup-undo.jsonl", TMP_DIR + "/tr-cleanup-test-undo.jsonl"],
  ["C:\\\\Users\\\\<user>\\\\.workbuddy\\\\tmp\\\\truerecall-stats-undo.jsonl", TMP_DIR + "/tr-stats-test-undo.jsonl"]
]));

const T = base._test || {};

const logOf = (env) => env.calls.write.map((w) => w[1]).join("\n");

/* ---------- A. 导出面与纯函数 ---------- */

eq(typeof base, "function", "模块本身应是 QuickAdd 可调用的函数");
for (const k of ["errText", "refValue", "num", "field", "str", "fmtDailyRow", "statsDiagnosis",
                 "dayStartHour", "findRebuild", "readiness", "gatherBusy", "typeName",
                 "countByType", "typeSummary", "pickStore"]) {
  eq(typeof T[k], "function", "_test." + k + " 已导出");
}

/* A1. refValue */
eq(T.refValue(true), true, "refValue(true)");
eq(T.refValue(false), false, "refValue(false)");
eq(T.refValue({ value: true }), true, "refValue({value:true})");
eq(T.refValue({ value: false }), false, "refValue({value:false})");
eq(T.refValue(null), null, "refValue(null)");
eq(T.refValue(undefined), undefined, "refValue(undefined)");
eq(T.refValue({ value: 0 }), 0, "refValue({value:0})");

/* A2. readiness */
eq(T.readiness({ isReady: () => true }), { state: "ready", detail: "store.isReady()" },
  "isReady()=true → ready");
eq(T.readiness({ isReady: () => false }), { state: "not-ready", detail: "store.isReady()" },
  "isReady()=false → not-ready");
eq(T.readiness({ isReady: () => { throw new Error("boom"); } }).state, "unknown",
  "isReady() 抛错 → unknown");
eq(T.readiness({ isLoaded: true, db: { isReady: () => true } }),
  { state: "ready", detail: "store.isLoaded + store.db.isReady()" },
  "isLoaded=true + db.isReady()=true → ready");
eq(T.readiness({ isLoaded: false, db: { isReady: () => true } }).state, "not-ready",
  "isLoaded=false → not-ready");
eq(T.readiness({ isLoaded: true, db: { isReady: () => false } }).state, "not-ready",
  "db.isReady()=false → not-ready");
eq(T.readiness({ isLoaded: true }).state, "ready",
  "无 db.isReady 时按 isLoaded=true 放行（dbReady 默认真）");
eq(T.readiness({ isLoaded: true, db: { isReady: () => { throw new Error("x"); } } }).state,
  "not-ready", "db.isReady() 抛错 → not-ready");
eq(T.readiness({}).state, "unknown", "都没有 → unknown");
eq(T.readiness(null).detail, "store 不可用", "store 为 null → unknown");
eq(T.readiness({ isReady: () => true, isLoaded: false }).state, "ready",
  "isReady 优先于 isLoaded");

/* A3. gatherBusy */
eq(T.gatherBusy(null), [], "空 plugin → 不忙");
eq(T.gatherBusy({}), [], "无任何管理器 → 不忙");
eq(T.gatherBusy({ coreApp: { backgroundBackupManager: { getStatus: () => ({ isBackupInProgress: true }) } } }),
  ["后台备份进行中"], "coreApp 备份进行中");
eq(T.gatherBusy({ coreApp: { backgroundBackupManager: { getStatus: () => ({ isBackupInProgress: false }) } } }),
  [], "备份未进行 → 不忙");
eq(T.gatherBusy({ coreApp: { backgroundBackupManager: { getStatus: () => { throw new Error("x"); } } } }),
  [], "getStatus 抛错 → 不忙（不误报）");
eq(T.gatherBusy({ backgroundBackupManager: { getStatus: () => ({ isBackupInProgress: true }) } }),
  ["后台备份进行中"], "无 coreApp 时退回 plugin.backgroundBackupManager");
eq(T.gatherBusy({ coreApp: { backgroundBackupManager: null } }), [],
  "backgroundBackupManager 为 null（备份未开）→ 不忙");
eq(T.gatherBusy({ coreApp: { backgroundBackupManager: {} } }), [], "无 getStatus 方法 → 不忙");
eq(T.gatherBusy({ cloudSyncManager: { coordinator: { isSyncing: { value: true } } } }),
  ["云同步进行中"], "云同步 ref=true");
eq(T.gatherBusy({ cloudSyncManager: { coordinator: { isSyncing: { value: false } } } }),
  [], "云同步 ref=false");
eq(T.gatherBusy({ cloudSyncManager: { coordinator: { isSyncing: true } } }),
  ["云同步进行中"], "云同步普通布尔也认");
eq(T.gatherBusy({ syncCoordinator: { isSyncing: { value: true } } }),
  ["设备同步进行中"], "设备同步 ref=true");
eq(T.gatherBusy({ cloudSyncManager: { coordinator: { isSyncing: { value: true } } }, syncCoordinator: { isSyncing: { value: true } } }),
  ["云同步进行中", "设备同步进行中"], "两个同步器同时忙");
eq(T.gatherBusy({
  coreApp: { backgroundBackupManager: { getStatus: () => ({ isBackupInProgress: true }) } },
  cloudSyncManager: { coordinator: { isSyncing: { value: true } } }
}), ["后台备份进行中", "云同步进行中"], "备份 + 云同步同时忙");
eq(T.gatherBusy({ cloudSyncManager: {} }), [], "cloudSyncManager 无 coordinator → 不忙");
eq(T.gatherBusy({ syncing: true }), [], "无关字段不影响");

/* A4. typeName */
eq(T.typeName({ noteTypes: { getById: () => ({ name: "Image occlusion" }) } }, "abc"),
  "Image occlusion", "取到 name");
eq(T.typeName({ noteTypes: { getById: () => ({ slug: "io" }) } }, "abc"), "io", "退到 slug");
eq(T.typeName({ noteTypes: { getById: () => null } }, "abc"), "abc", "查不到 → 退回 id");
eq(T.typeName({ noteTypes: { getById: () => { throw new Error("x"); } } }, "abc"),
  "abc", "getById 抛错 → 退回 id");
eq(T.typeName({}, "abc"), "abc", "无 noteTypes → 退回 id");
eq(T.typeName({}, ""), "(未知类型)", "无 id → 占位名");
eq(T.typeName({}, null), "(未知类型)", "id=null → 占位名");

/* A5. countByType / typeSummary */
const store1 = { noteTypes: { getById: (id) => ({ name: id === "io" ? "Image occlusion" : "Basic" }) } };
eq(T.countByType(store1, [{ type: "io" }, { type: "io" }, { type: "basic" }]),
  { "Image occlusion": 2, Basic: 1 }, "按类型计数");
eq(T.typeSummary(T.countByType(store1, [{ type: "io" }, { type: "io" }, { type: "basic" }])),
  "Image occlusion ×2、Basic ×1", "一行摘要");
eq(T.countByType(store1, []), {}, "空清单 → 空统计");
eq(T.typeSummary({}), "无", "空统计 → 无");

/* A6. field / str */
eq(T.field({ id: "x", ID: "y" }, ["id", "ID"]), "x", "别名命中首个");
eq(T.field({ ID: "y" }, ["id", "ID"]), "y", "别名命中次个");
eq(T.field({ id: null, ID: "y" }, ["id", "ID"]), "y", "null 跳过改用别名");
eq(T.field(null, ["id"]), null, "行对象为空");
eq(T.str({ id: 7 }, ["id"]), "7", "str 转字符串");
eq(T.field({ createdAt: 0 }, ["createdAt"]), 0, "0 是有效值（不当空）");

/* A7. num */
eq(T.num({ db: { get: () => ({ n: 5 }) } }, "x"), 5, "num 读 n");
eq(T.num({ db: { get: () => ({ cnt: 3 }) } }, "x"), 3, "num 读 cnt");
eq(T.num({ db: { get: () => ({ foo: 9 }) } }, "x"), 9, "num 读首个数字字段");
eq(T.num({ db: { get: () => null } }, "x"), 0, "num 无行 → 0");

/* A8. fmtDailyRow */
eq(T.fmtDailyRow(makeDaily()),
  "2026-09-14  复习41次 新卡38 用时79.4分 对33 易0 硬1 重7", "标准下划线列名");
eq(T.fmtDailyRow({ date: "2026-09-13", reviewsCompleted: 12, newCardsStudied: 11, totalTimeMs: 341986,
                   again: 2, hard: 0, good: 10, easy: 0 }),
  "2026-09-13  复习12次 新卡11 用时5.7分 对10 易0 硬0 重2", "驼峰别名");
eq(T.fmtDailyRow({ date: "d", reviews_completed: 1, new_cards_studied: 1, total_time_ms: 0 }).includes("用时0分"),
  true, "无用时 → 0 分");

/* A9. statsDiagnosis（合并后的核心新增判据） */
eq(T.statsDiagnosis({ days: 1, reviewsSum: 41, rlLive: 0 }).need, true,
  "统计 41 次 vs 未软删 0 条 → 需要重建");
eq(T.statsDiagnosis({ days: 1, reviewsSum: 41, rlLive: 0 }).reason.includes("已过期"), true,
  "需要重建时理由写「已过期」");
eq(T.statsDiagnosis({ days: 2, reviewsSum: 53, rlLive: 53 }).need, false,
  "统计 53 次 vs 未软删 53 条 → 一致，无需重建");
eq(T.statsDiagnosis({ days: 2, reviewsSum: 53, rlLive: 53 }).reason.includes("一致"), true,
  "一致时理由写「一致」");
eq(T.statsDiagnosis({ days: 0, reviewsSum: 0, rlLive: 0 }).need, false, "两表皆空 → 一致");
eq(T.statsDiagnosis({}).need, false, "缺字段 → 视为 0/0 一致（不误触发）");
eq(T.statsDiagnosis(null).need, false, "入参 null 不炸");
eq(T.statsDiagnosis({ days: 1, reviewsSum: 0, rlLive: 7 }).need, true,
  "统计表空但实习记录有 7 条 → 需要重建");

/* A10. dayStartHour */
eq(T.dayStartHour({ settings: { dayStartHour: 6 } }), 6, "正常取值");
eq(T.dayStartHour({ settings: { dayStartHour: 0 } }), 0, "0 合法");
eq(T.dayStartHour({ settings: { dayStartHour: 23 } }), 23, "23 合法");
eq(T.dayStartHour({ settings: { dayStartHour: 99 } }), 4, "越界 → 4");
eq(T.dayStartHour({}), 4, "缺失 → 4");
eq(T.dayStartHour({ settings: { dayStartHour: "5" } }), 4, "字符串 → 4");

/* A11. findRebuild */
eq((T.findRebuild(makeFake({}).store) || {}).where, "store.stats", "命中 store.stats");
eq((function () { const s = makeFake({ rebuildOn: "store" }).store; s.rebuildDailyStatsFromReviewLog = () => {}; return (T.findRebuild(s) || {}).where; })(),
  "store", "命中 store 自身");
eq((function () { const s = makeFake({ rebuildOn: "store" }).store; s.dailyProgress = { rebuildDailyStatsFromReviewLog: () => {} }; return (T.findRebuild(s) || {}).where; })(),
  "store.dailyProgress", "命中 dailyProgress");
eq(T.findRebuild(makeFake({ rebuildOn: "store" }).store), null, "都没有 → null");

/* A12. pickStore（判据 = saveNow + notes.delete + db.query） */
eq((T.pickStore(makeFake({}).plugin) || {}).key, "cardStore", "命中 cardStore");
eq((T.pickStore(makeFake({ storeKey: "store" }).plugin) || {}).key, "store", "命中 store");
eq((T.pickStore({ weird: makeFake({}).store }) || {}).key, "weird(反射)", "反射兜底");
eq(T.pickStore({}), null, "未命中 → null");
eq(T.pickStore({ cardStore: { db: { query() {} }, saveNow() {} } }), null, "缺 notes.delete 不算（判据已收紧）");
eq(T.pickStore({ cardStore: { db: { query() {} }, saveNow() {}, notes: { delete() {} } } }).key,
  "cardStore", "三件齐备即命中");

/* ---------- B. 端到端 ---------- */

(async function main() {

  // B0. auto：有孤儿 + 统计过期 → 删 note 且重建
  {
    const env = makeFake({ readyState: "ready" });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 8, "auto：软删 8 条孤儿 note");
    eq(env.calls.rebuild.length, 1, "auto：重建统计一次");
    eq(env.calls.rebuild[0], 4, "auto：重建参数 = dayStartHour");
    ok("auto：saveNow 被调", env.calls.saveNow >= 1);
    ok("auto：markDirty 被调", env.calls.markDirty >= 1);
    ok("auto：写了 note 撤销清单", env.calls.append.some((a) => a[1].includes("soft-delete notes")));
    ok("auto：写了统计快照", env.calls.append.some((a) => a[1].includes("rebuild daily_stats")));
    ok("auto：快照含原始 41 次", env.calls.append.some((a) => a[1].includes("\"reviews_completed\":41")));
    const log = logOf(env);
    ok("auto：日志含计数", log.includes("活卡=0"));
    ok("auto：日志含统计判据", log.includes("统计判据 需要重建"));
    ok("auto：日志含复核", log.includes("复核 daily_stats=0 天"));
    ok("auto：日志含完成", log.includes("=== 完成 ==="));
    ok("auto：Notice 汇总两件事", notices.some((n) => n.includes("已清理孤儿 note 8 条")
        && n.includes("统计已重建：1 天 → 0 天")));
  }

  // B1. auto：无孤儿 + 统计过期 → 只重建（不再早退，这是合并后的关键行为）
  {
    const env = makeFake({ readyState: "ready", orphans: 0, orphanRows: [] });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "无孤儿：不删任何 note");
    eq(env.calls.rebuild.length, 1, "无孤儿：仍然重建统计");
    ok("无孤儿：日志标出跳过清理", logOf(env).includes("跳过清理"));
    ok("无孤儿：Notice 只报统计", notices.some((n) => n.includes("统计已重建") && !n.includes("已清理孤儿")));
  }

  // B2. auto：有孤儿 + 统计一致 → 只清理
  {
    const env = makeFake({ readyState: "ready", rlLive: 41 });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 8, "统计一致：照常删孤儿");
    eq(env.calls.rebuild.length, 0, "统计一致：不重建");
    ok("统计一致：日志标出跳过重建", logOf(env).includes("跳过统计重建"));
    ok("统计一致：Notice 只报清理", notices.some((n) => n.includes("已清理孤儿") && !n.includes("统计已重建")));
  }

  // B3. auto：两件事都没有 → 早退（不过闸、不落盘）
  {
    const env = makeFake({ readyState: "ready", orphans: 0, orphanRows: [], rlLive: 41 });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "无事可做：不删");
    eq(env.calls.rebuild.length, 0, "无事可做：不重建");
    eq(env.calls.saveNow, 0, "无事可做：不落盘");
    ok("无事可做：Notice 说无需处理", notices.some((n) => n.includes("无需处理")));
  }

  // B4. MODE="report" → 只报告
  {
    const variant = loadVariant([['const MODE = "auto"', 'const MODE = "report"']]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready" });
    const notices = [];
    await mod(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "report：不删");
    eq(env.calls.rebuild.length, 0, "report：不重建");
    eq(env.calls.saveNow, 0, "report：不落盘");
    eq(env.calls.append.length, 0, "report：不写清单");
    ok("report：日志声明只报告", logOf(env).includes("MODE=report"));
    fs.unlinkSync(variant);
  }

  // B5. MODE="cleanup" → 不碰统计
  {
    const variant = loadVariant([['const MODE = "auto"', 'const MODE = "cleanup"']]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready" });
    await mod(makeParams(env.app, []));
    eq(env.calls.noteDelete.length, 8, "cleanup：删孤儿");
    eq(env.calls.rebuild.length, 0, "cleanup：不重建");
    ok("cleanup：日志声明跳过统计", logOf(env).includes("MODE 不含统计"));
    fs.unlinkSync(variant);
  }

  // B6. MODE="stats" → 不清孤儿
  {
    const variant = loadVariant([['const MODE = "auto"', 'const MODE = "stats"']]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready" });
    await mod(makeParams(env.app, []));
    eq(env.calls.noteDelete.length, 0, "stats：不删孤儿");
    eq(env.calls.rebuild.length, 1, "stats：重建统计");
    ok("stats：日志声明跳过清理", logOf(env).includes("MODE 不含清理"));
    fs.unlinkSync(variant);
  }

  // B7. 就绪闸 not-ready → 中止
  {
    const env = makeFake({ readyState: "not-ready" });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "not-ready：不删");
    eq(env.calls.rebuild.length, 0, "not-ready：不重建");
    eq(env.calls.saveNow, 0, "not-ready：不落盘");
    ok("not-ready：日志含 ABORT", logOf(env).includes("ABORT"));
    ok("not-ready：Notice 提示中止", notices.some((n) => n.includes("未就绪")));
  }

  // B8. 持久化挂起 → 中止
  {
    const env = makeFake({ readyState: "ready", halted: true });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "挂起：不删");
    eq(env.calls.rebuild.length, 0, "挂起：不重建");
    ok("挂起：日志含 persistenceHalted = true", logOf(env).includes("persistenceHalted = true"));
    ok("挂起：Notice 提示", notices.some((n) => n.includes("持久化已挂起")));
  }

  // B9. 避让闸：一直忙 → 中止（把等待压到 1ms）
  {
    const variant = loadVariant([["const BUSY_WAIT_MS = 1500", "const BUSY_WAIT_MS = 1"]]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready", busyBackup: true, busyCloud: true });
    await mod(makeParams(env.app, []));
    eq(env.calls.noteDelete.length, 0, "避让闸：不删");
    eq(env.calls.rebuild.length, 0, "避让闸：不重建");
    const log = logOf(env);
    ok("避让闸：日志报两项忙", log.includes("后台备份进行中、云同步进行中"));
    ok("避让闸：日志含 ABORT", log.includes("ABORT 清理"));
    fs.unlinkSync(variant);
  }

  // B10. 就绪判据 unknown：清理保守跳过、统计照做（合并后的分流）
  {
    const env = makeFake({});   // 无 isReady / isLoaded → unknown；liveCards=0 有孤儿
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "unknown+活卡0：不删 note（保守）");
    eq(env.calls.rebuild.length, 1, "unknown：统计仍重建（只动派生表）");
    const log = logOf(env);
    ok("unknown：日志声明保守跳过", log.includes("保守起见只报告不删"));
    ok("unknown：Notice 提示人工确认", notices.some((n) => n.includes("请人工确认")));
  }

  // B11. 就绪判据 unknown 但活卡 > 0 → 放行清理
  {
    const env = makeFake({ liveCards: 12 });
    await base(makeParams(env.app, []));
    eq(env.calls.noteDelete.length, 8, "unknown+活卡>0：照常清理");
    ok("unknown+活卡>0：日志有 WARN 放行", logOf(env).includes("退回保守判据放行"));
  }

  // B12. note 撤销清单写不进（append 抛错 + fs 回落失败）→ 不删、但统计照做
  {
    // 把回落路径换成"一个目录"：appendFileSync 到目录必抛 EISDIR
    const variant = loadVariant([
      ["C:\\\\Users\\\\<user>\\\\.workbuddy\\\\tmp\\\\truerecall-cleanup-undo.jsonl", TMP_DIR + "/"]
    ]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready", appendThrows: true });
    await mod(makeParams(env.app, []));
    eq(env.calls.noteDelete.length, 0, "清单写不进：一条都不删");
    eq(env.calls.rebuild.length, 1, "清单写不进：统计不受影响，照常重建");
    ok("清单写不进：日志标出 SKIP", logOf(env).includes("没有还原路就不动"));
    fs.unlinkSync(variant);
  }

  // B13. 统计快照写不进 → 跳过重建、但清理照做
  {
    const variant = loadVariant([
      ["C:\\\\Users\\\\<user>\\\\.workbuddy\\\\tmp\\\\truerecall-stats-undo.jsonl", TMP_DIR + "/"]
    ]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready", appendThrows: true });
    await mod(makeParams(env.app, []));
    eq(env.calls.rebuild.length, 0, "快照写不进：不重建");
    eq(env.calls.noteDelete.length, 8, "快照写不进：清理不受影响");
    ok("快照写不进：日志标出跳过", logOf(env).includes("没有还原凭据就不重建"));
    fs.unlinkSync(variant);
  }

  // B14. 找不到重建方法 → 不落盘第二次、清理仍然完成
  {
    const env = makeFake({ readyState: "ready", rebuildOn: "store" });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.rebuild.length, 0, "无重建方法：未调重建");
    ok("无重建方法：日志含 FAIL", logOf(env).includes("找不到 rebuildDailyStatsFromReviewLog"));
    ok("无重建方法：Notice 报未重建", notices.some((n) => n.includes("统计未重建")));
  }

  // B15. 重建抛错 → 报错但仍完成了清理
  {
    const env = makeFake({ readyState: "ready", rebuildThrows: true });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.rebuild.length, 1, "重建抛错：确实调过一次");
    eq(env.calls.noteDelete.length, 8, "重建抛错：清理已完成");
    ok("重建抛错：Notice 报错", notices.some((n) => n.includes("统计重建失败")));
  }

  // B16. 落盘失败 → 提示再跑一次
  {
    const env = makeFake({ readyState: "ready", saveNowReturns: false });
    const notices = [];
    await base(makeParams(env.app, notices));
    ok("落盘失败：提示重跑", notices.some((n) => n.includes("落盘失败")));
    ok("落盘失败：日志有提示", logOf(env).includes("落盘失败"));
  }

  // B17. note 还原模式：只回 note、删 flag、不碰统计
  {
    const batch = { at: "2026-09-14 22:30:00", action: "soft-delete notes",
                    count: 2, items: [{ id: "note-1" }, { id: "note-2" }] };
    const flags = { ".true-recall/undo-restore.flag": true };
    const env = makeFake({ readyState: "ready", flags,
      undoText: { ".true-recall/tr-cleanup-undo.jsonl": JSON.stringify(batch) + "\n" } });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.run.filter((c) => c[0].startsWith("UPDATE notes SET deleted_at = NULL")).length, 2,
      "还原 note：两条 UPDATE");
    eq(env.calls.remove, [".true-recall/undo-restore.flag"], "还原 note：删掉自己的 flag");
    eq(env.calls.noteDelete.length, 0, "还原模式：不走清理");
    eq(env.calls.rebuild.length, 0, "还原模式：不走重建");
    ok("还原 note：Notice 报条数", notices.some((n) => n.includes("已还原孤儿 note 2 条")));
  }

  // B18. 统计还原模式：回填两张表 + 删自己的 flag
  {
    const batch = { at: "2026-09-14 22:40:00", action: "rebuild daily_stats",
                    dailyStats: [makeDaily()],
                    dailyReviewedCards: [{ date: "2026-09-14", card_id: "c1" }] };
    const flags = { ".true-recall/stats-restore.flag": true };
    const env = makeFake({ readyState: "ready", flags,
      undoText: { ".true-recall/tr-stats-undo.jsonl": JSON.stringify(batch) + "\n" } });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.run.filter((c) => c[0].startsWith("INSERT OR REPLACE INTO daily_stats")).length, 1,
      "还原统计：1 行 daily_stats");
    eq(env.calls.run.filter((c) => c[0].startsWith("INSERT OR REPLACE INTO daily_reviewed_cards")).length, 1,
      "还原统计：1 行 daily_reviewed_cards");
    eq(env.calls.remove, [".true-recall/stats-restore.flag"], "还原统计：删掉自己的 flag");
    ok("还原统计：Notice 报天数", notices.some((n) => n.includes("已还原 1 天统计")));
  }

  // B19. 两个 flag 同时存在 → 各做各的（闸只过一次）
  {
    const b1 = { at: "t1", action: "soft-delete notes", items: [{ id: "note-1" }] };
    const b2 = { at: "t2", action: "rebuild daily_stats", dailyStats: [makeDaily()], dailyReviewedCards: [] };
    const flags = { ".true-recall/undo-restore.flag": true, ".true-recall/stats-restore.flag": true };
    const env = makeFake({ readyState: "ready", flags,
      undoText: { ".true-recall/tr-cleanup-undo.jsonl": JSON.stringify(b1) + "\n",
                  ".true-recall/tr-stats-undo.jsonl": JSON.stringify(b2) + "\n" } });
    await base(makeParams(env.app, []));
    eq(env.calls.run.filter((c) => c[0].startsWith("UPDATE notes")).length, 1, "双 flag：还原了 note");
    eq(env.calls.run.filter((c) => c[0].startsWith("INSERT OR REPLACE INTO daily_stats")).length, 1,
      "双 flag：也还原了统计");
    eq(env.calls.remove.length, 2, "双 flag：两个 flag 都删掉");
    eq(env.calls.saveNow, 2, "双 flag：两段各落盘一次");
  }

  // B20. 还原 flag 在但没有快照 → 终止、不删 flag
  {
    const flags = { ".true-recall/stats-restore.flag": true };
    const env = makeFake({ readyState: "ready", flags, undoText: {} });
    const notices = [];
    await base(makeParams(env.app, notices));
    eq(env.calls.remove.length, 0, "空快照：不删 flag");
    ok("空快照：Notice 提示没有可还原", notices.some((n) => n.includes("没有可还原的统计快照")));
  }

  // B21. 无 app → 早退
  {
    const notices = [];
    await base(makeParams(null, notices));
    ok("无 app：弹 Notice 中止", notices.some((n) => n.includes("拿不到")));
  }

  // B22. 插件未启用 → 中止（把 40 次重试压到 0）
  {
    const variant = loadVariant([["for (let i = 1; i <= 40 && !plugin; i++)", "for (let i = 1; i <= 0 && !plugin; i++)"]]);
    const mod = require(variant);
    const notices = [];
    await mod(makeParams({ vault: { adapter: { write: async () => {} } }, plugins: { plugins: {} } }, notices));
    ok("插件未启用：Notice 中止", notices.some((n) => n.includes("未启用")));
    fs.unlinkSync(variant);
  }

  // B23. MODE="cleanup" 且无孤儿 → 无事可做（不给统计留后门）
  {
    const variant = loadVariant([['const MODE = "auto"', 'const MODE = "cleanup"']]);
    const mod = require(variant);
    const env = makeFake({ readyState: "ready", orphans: 0, orphanRows: [], rlLive: 0 });
    const notices = [];
    await mod(makeParams(env.app, notices));
    eq(env.calls.noteDelete.length, 0, "cleanup 无孤儿：不删");
    eq(env.calls.rebuild.length, 0, "cleanup 无孤儿：不重建");
    ok("cleanup 无孤儿：Notice 无需处理", notices.some((n) => n.includes("无需处理")));
    fs.unlinkSync(variant);
  }

  /* ---------- 汇总 ---------- */
  const total = pass + fail;
  console.log(`\nTR清理（含统计重建）离线测试台：${pass}/${total} PASS`);
  if (fail) {
    console.log(`\n失败 ${fail} 项：`);
    for (const f of fails) console.log("  ✗ " + f);
    process.exit(1);
  }
})();
