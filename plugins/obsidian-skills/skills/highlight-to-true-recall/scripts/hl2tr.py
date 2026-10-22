# -*- coding: utf-8 -*-
"""hl2tr.py — 把 Obsidian md 里的 ==高亮== 转成 True Recall 的 cloze 卡。

配套 skill: highlight-to-true-recall

用法
----
  python hl2tr.py "<md路径>"                    预览,什么都不写
  python hl2tr.py "<md路径>" --apply            写 frontmatter flashcard_uid + 经插件 Local API 建卡
  python hl2tr.py "<md路径>" --apply --sqlite   旧路线:直接写 SQLite(必须先完全退出 Obsidian)
  python hl2tr.py "<md路径>" --apply --force    仅 --sqlite 路线有效:Obsidian 运行中也强写
  python hl2tr.py "<md路径>" --no-source-text   不写 source_text(会失去"跳回原文"能力)
  python hl2tr.py "<md路径>" --keep-cloze-bold  挖空里保留用户自己写的 ** (默认会清掉,见下)
  python hl2tr.py "<md路径>" --relink           只把已建卡片的 Extra 就地改成可点行链接(见下)
  python hl2tr.py "<md路径>" --relink --apply   真正写回(需要 Obsidian 在跑 + Local API 开着)
  python hl2tr.py "<md路径>" --plain-extra      卡面 Extra 不写成链接,只留纯文字
  python hl2tr.py "<md路径>" --no-anchor        URL 不带 anchor(链接更短,但笔记改动后不再自愈)
  python hl2tr.py "<md路径>" --cloze-mark      给挖空内容与 hint 包 ==…==(⛔ 2026-10-12 起默认关闭;
                                               加这个开关才开启,旧开关 --no-cloze-mark 已作废)
  python hl2tr.py "<md路径>" --no-indent-merge 缩进行各自独立成块(退回 2026-09-17 之前的旧口径)
  python hl2tr.py "<md路径>" --token=<token>    v2.5.0 起 Local API 要鉴权,显式给 token
                                               (不给则依次试环境变量 TRUE_RECALL_TOKEN、
                                                本机凭证文件 <skill目录>/.local-api-token)

卡面最后那行"第 N 块"做成一键跳转链接
------------------------------------
内置 Cloze 卡型的答案面是 `{{cloze:Text}}<br>{{Extra}}`,所以 Extra 就显示在卡片最下方。
默认把 Extra 写成 markdown 链接:

    [《笔记名》·第 3 块](obsidian://adv-uri?vault=...&filepath=...&line=42&anchor=...)

它由 FakeLink 接管(本机未装 Advanced URI,FakeLink 已注册 obsidian://adv-uri 并拦截点击),
点一下就直接打开源笔记、光标落在该块所在行并滚动居中 —— 不用再去卡片面板搜卡、
右键 Open Source、手动切窗口。anchor 是该行前 40 字,FakeLink 开了 lineLinkSelfHeal
时会用它自动纠正行号漂移。注意只有 Extra 变、source_text 与 FSRS 调度都不动,
所以 --relink 是幂等且无损的。

挖空里的加粗为什么要清掉
------------------------
插件渲染"揭示答案"时,自己会把挖空内容包成 **...**(源码 I0())。
若内容里本来就有用户写的 **,叠加成 ****内容**** → CommonMark 实测是嵌套
<strong><strong>…</strong></strong>,冗余且脆弱(标记一旦不成对就会露出字面 **)。
所以默认清掉挖空内部的 ** 与 __,加粗交给插件那一层;只改卡面 Text,
**不动 source_text**(它必须与笔记正文逐字一致,跳转才 indexOf 得到)。

⚠️ 光清掉 ** 还不够(2026-09-17 实测):仍有 6.3% 的卡加粗会失效、星号字面显示。
根因是 CommonMark 的 flanking 规则 —— 插件那对 ** 能不能"开"取决于它后面那个字符,
能不能"闭"取决于它前面那个字符:内容首尾是标点、外侧又紧贴文字时就开不了/闭不了
(`若**$A$**经`、`是**重要。**在`)。修法:在挖空内容两端各插一个 Word Joiner(U+2060),
它属于 Cf 类,既不算空白也不算标点 —— ** 永远能开能闭,且不可见、不干扰 MathJax。
默认开启,`--no-wj` 可关。详见 cloze_fill() 的 docstring。
⚠️ WJ 护的是**插件那对 `**`**,与脚本包不包 `==` 无关 ⇒ 停 `==` 之后 WJ **照留**。

⛔ 挖空内容**不再**套 ==…==(2026-09-17 广哥定;**2026-10-12 起默认关闭**,`--cloze-mark` 才可开)。
下面整段自 2026-10-12 起只作历史留档。
当初的目的:给 CSS 一个**只命中挖空**的钩子 —— 插件那对 ** 的加粗与用户自己画的 **粗体**
在 DOM 上分不开,只靠加粗染色会把块内粗体一起染绿(现存 157 张 cloze 卡里 48 张中招)。
第一版用 `<span class="tr-cloze">` **实测无效**(卡面是 CM6 实时预览编辑器,不是
MarkdownRenderer:`**` → `.cm-strong`;行内 HTML 按单标签走 HtmlWidget → 只剩空 span),
改用 `==` 后实时预览出 `span.cm-highlight`、阅读视图出 `<mark>`,两种模式都有钩子。
mark 在内、WJ 在外,WJ 才能保证 ** 开闭(详见 CLOZE_MARK 常量注释)。
配套 CSS:<vault>/.obsidian/snippets/true-recall-挖空-高亮黄加粗.css(2026-09-17 由
`true-recall-答案面挖空-去加粗改颜色.css` 改名;名字里的「加粗」已不准确 ——
2026-09-20 起该片段把字重压回 normal、只留底色。需在
Obsidian 设置 → 外观 → CSS 片段 里勾选)。

两条写入路线
------------
  [默认] Local API —— 插件自带的 HTTP 接口(127.0.0.1:27182)。
    ⚠️ v2.5.0 起必须带本机 token:插件在"路由匹配之前"就校验,缺失或不对一律 401,
       连 /status 探活都不例外(v2.4.2 是只绑本机、无鉴权,别再照旧写)。
       token 来源优先级:--token=xxx > 环境变量 TRUE_RECALL_TOKEN >
       本机凭证文件 <skill目录>/.local-api-token(不在 vault 内、不进笔记)。
       取 token:Obsidian 设置 → True Recall → Local API → Copy token。
    优点:① 走插件自己的 createNoteBatch,不会被"笔记↔卡片"同步判为无来源而软删;
          ② 必须 Obsidian 正在运行(服务器在插件里),不用退出;
          ③ 能一并写入 source_text → 复习面板上的"跳回源笔记"才有反应。
    前提:设置 → Local API → 打开 "Enable local API"。
    ⚠️ v2.5.0 新增开关 apiEnableSqlQuery(默认关闭):关着时 /query 一律返回 403
       sql-query-disabled。本脚本已自动降级 —— 改走 GET /notes/cards?source_uid=…
       (该接口 SQL 里写死 c.deleted_at IS NULL,只返活卡),所以**不必**去开那个开关
       也能正常建卡与 --relink。
       ⚠️ 但这条路由返回的不是原始字段:`question` 是卡面展示态(`{{c1::x}}`→`[...]`)、
       `answer` 是整面(渲染 Text + "<br>" + Extra) —— 2026-09-15 实测:旧版直接拿它们
       当 cloze 的 Text/Extra 比幂等键,**永远不相等 ⇒ 每跑一次多一整批卡**。现在改用
       ①本地 Text 渲染归一化(_render_cloze)+ 从 answer 切出 Extra,_extra_from_answer)
       ②逐张 GET /cards/:id 取 sourceText(块原文,含 ==)当第二重键,命中任一即跳过。
       两处"复核活跃卡数"是纯打印,/query 关着时跳过。
  [--sqlite] 直写库 —— 2026-09-14 实测会被 softDeleteWithCascade 级联软删,仅作兜底。

知识块切分规则(默认)
--------------------
1. 空行 / 标题行(# 开头) / 代码围栏 ``` 是硬边界,不属于任何块。
2. 列表项行(^\\s*([-*+]|\\d+\\.)\\s)→ 未缩进的每行独立成块。
   缩进归属(2026-09-17 起默认):**任何行首带缩进的行,一律并入上方最近的未缩进行
   所在块,不另起一块**(多级缩进也归同一个父块);`--no-indent-merge` 关掉即退回
   「缩进子项也算独立块」的旧行为。
3. 引用行(> 开头)→ 连续引用行合并成一块。
4. 表格行(| 开头)→ 每行独立成块。
5. 其他非空行 → 连续多行合并成一块(遇上述边界断开)。
6. 跨行高亮(== 在某行开、后面的行合)→ 把跨越的块合并成一块。

一个块 = 一张卡 = 一个 True Recall note;块内所有高亮统一 {{c1::...}}(同一编号),
所以一次复习只出这一张卡,并把该块所有空一起挖掉。

source_text 取什么
------------------
默认取「该块在笔记里的原始文本(含 == 标记、含 [[链接]])」。插件跳转时执行
  doc.indexOf(source_text) → 命中则滚动居中并高亮 2 秒
所以必须与笔记正文逐字一致;取整块原文是最稳的做法(插件自己手建的卡存的正是
'==**行动研究**==' 这种含 == 的原文)。
"""
import os, re, sys, json, glob, uuid, shutil, sqlite3, time, subprocess, datetime, unicodedata
import urllib.request, urllib.error

VAULT = r"<vault>"
BACKUP_DIR = r"~\.workbuddy\tmp"
PLUGIN_DIR = r"<vault>\.obsidian\plugins\true-recall"
CLOZE_TYPE = "builtin-cloze"
UID_FIELD = "flashcard_uid"
UID_LEN = 8
API_PORT_DEFAULT = 27182
# v2.5.0 起 Local API 每个请求都要带本机 token。凭证文件放在 skill 目录里
# (不在 vault 内、不会变成笔记),内容就是一行 token。
TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".local-api-token")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------- 基础 ----------

def find_db(vault=VAULT):
    cands = glob.glob(os.path.join(vault, ".true-recall", "*", "*.db"))
    cands = [c for c in cands if not c.endswith(".bak")]
    if not cands:
        raise SystemExit("找不到 True Recall 数据库(.true-recall/*/*.db)")
    cands.sort(key=os.path.getmtime, reverse=True)
    return cands[0]


def read_settings():
    try:
        return json.load(open(os.path.join(PLUGIN_DIR, "data.json"), encoding="utf-8"))
    except Exception:
        return {}


def api_port():
    return int(read_settings().get("apiPort") or API_PORT_DEFAULT)


def api_token():
    """本机 Local API 的 token(v2.5.0 起必需,缺失一律 401)。

    优先级:--token=xxx > 环境变量 TRUE_RECALL_TOKEN(官方 CLI 约定的名字) >
    本机凭证文件 .local-api-token。都取不到就返回空串 —— 请求会 401,
    届时报错信息会指路去设置页 Copy token。
    """
    for a in sys.argv[1:]:
        if a.startswith("--token="):
            return a.split("=", 1)[1].strip()
    v = (os.environ.get("TRUE_RECALL_TOKEN") or "").strip()
    if v:
        return v
    try:
        v = open(TOKEN_FILE, encoding="utf-8").read().strip()
        if v:
            return v
    except Exception:
        pass
    return ""


def obsidian_running():
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Obsidian.exe"], capture_output=True)
        return "Obsidian.exe" in r.stdout.decode("gbk", errors="ignore")
    except Exception:
        return False


def gen_uid():
    return uuid.uuid4().hex[:UID_LEN]


# 本机有系统代理(HTTP_PROXY/HTTPS_PROXY),必须显式绕开,
# 否则 127.0.0.1 的请求会被代理拦成 502 Bad Gateway,看不出真原因。
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api_call(path, payload=None, method=None, timeout=25):
    """调用插件 Local API。成功返回 data,失败抛 RuntimeError。

    v2.5.0 起所有路由都要带 token —— 鉴权在"路由匹配之前"做,所以 /status 探活也要带。
    """
    url = "http://127.0.0.1:%d%s" % (api_port(), path)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"))
    if body:
        req.add_header("Content-Type", "application/json")
    tok = api_token()
    if tok:
        # 插件两种头都认:x-true-recall-token 或 Authorization: Bearer <token>
        req.add_header("x-true-recall-token", tok)
    try:
        with _NO_PROXY.open(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        if e.code == 401:
            raise RuntimeError(
                "Local API 需要本机 token(%s) —— v2.5.0 起插件给所有路由加了鉴权。\n"
                "→ 去 Obsidian 设置 → True Recall → Local API → 点 Copy token,然后三选一:\n"
                "    ① 命令行 --token=<token>\n"
                "    ② 设环境变量 TRUE_RECALL_TOKEN\n"
                "    ③ 写进本机凭证文件 %s(一行,只放 token)"
                % ("当前没带 token" if not tok else "带了但不对", TOKEN_FILE))
        raise RuntimeError("Local API 返回 HTTP %d(%s):%s" % (e.code, path, detail[:200]))
    except urllib.error.URLError as e:
        raise RuntimeError("连不上 Local API(%s):%s\n"
                           "→ 请在 Obsidian 设置 → True Recall → Local API 打开 Enable local API"
                           % (url, e))
    res = json.loads(raw)
    if not res.get("ok"):
        raise RuntimeError("API 返回错误:%s" % res.get("error"))
    return res.get("data")


_sql_query_ok = None


def sql_query_ok():
    """/query 能不能用 —— v2.5.0 起受设置项 apiEnableSqlQuery 控制,默认是关的。

    关着时 /query 一律 403 sql-query-disabled。探测一次就缓存,免得每处都试一遍。
    """
    global _sql_query_ok
    if _sql_query_ok is None:
        try:
            api_call("/query", {"sql": "select 1 as n"}, timeout=5)
            _sql_query_ok = True
        except Exception:
            _sql_query_ok = False
            print("  (/query 不可用,已自动改用 GET /notes/cards 查活卡 —— "
                  "想让脚本走更精确的 SQL,去插件设置 Local API 里打开 "
                  "Enable SQL query endpoint 即可,不开也不影响建卡)")
    return _sql_query_ok


def cards_by_uid(uid, with_source_text=False):
    """降级查卡:GET /notes/cards?source_uid=…(v2.5.0 的 /query 默认关时用这条)。

    SQL 里写死 c.deleted_at IS NULL ⇒ 只返活卡,与幂等判据一致。
    返回 [(card_id, fields_dict)],fields_dict 三个键:
      · Text   = question 的**渲染归一化**(见 _render_cloze);
      · Extra  = 从 answer 里切出来的**真 Extra**;
      · Answer = 原样 answer(= 渲染后的 Text + "<br>" + Extra)。
    ⚠️ 2026-09-15 实测踩坑:插件这条接口返回的 `question` 已经是**卡面展示态**
    (`{{c1::x}}` 被渲染成 `[...]`)、`answer` 是整面(含 Text 那段),把它们当成
    cloze 的 Text/Extra 直接比对会**永远不相等** ⇒ 幂等失效、每跑一次多一整批卡
    (当天实测:同一篇笔记连跑两次 --apply,库里出现 6 张、两份重复)。
    with_source_text=True 时再逐张 GET /cards/:id 取 **sourceText**(块原文,含 `==`),
    这是最可靠的幂等键 —— 与本地块的 source_text 逐字可比。
    ⚠️ limit 必须显式给:该接口默认只返 50 条,本库一篇笔记能到 50+ 张卡,上限 200。
    """
    d = api_call("/notes/cards?source_uid=%s&limit=200" % uid)
    out = []
    for c in (d.get("cards") or []):
        cid = c.get("id")
        if not cid:
            continue
        ans = c.get("answer") or ""
        rec = {"Text": _render_cloze(c.get("question") or ""),
               "Extra": _extra_from_answer(ans),
               "Answer": ans}
        if with_source_text:
            try:
                one = api_call("/cards/%s" % cid)
                # ⚠️ GET /cards/:id 返回的是**扁平对象**(sourceText 直接在顶层),
                # 没有 {ok,data} 包一层 —— 2026-09-15 实测:写成 `one.get("data") or {}`
                # 会让 SourceText 恒为空串 ⇒ source_text 幂等键失效 ⇒ 每复跑一次多一整批卡。
                rec["SourceText"] = ((one.get("data") or one).get("sourceText") or "")
            except Exception:
                rec["SourceText"] = ""
        out.append((cid, rec))
    return out


# ---------- 行链接(卡面 Extra 用) ----------

ANCHOR_LEN = 40          # 与 FakeLink 的 getLineAnchor 保持一致(取该行前 40 字)
_vault_id_cache = None


def vault_id():
    """从 %APPDATA%\\obsidian\\obsidian.json 里读出本 vault 的 id(FakeLink 生成的链接带它)。

    读不到就返回空串 —— FakeLink 的 adv-uri 处理器只认 filepath/line/anchor,
    vault 参数带不带都能跳,所以这里失败不影响功能。
    """
    global _vault_id_cache
    if _vault_id_cache is not None:
        return _vault_id_cache
    _vault_id_cache = ""
    try:
        p = os.path.join(os.environ.get("APPDATA", ""), "obsidian", "obsidian.json")
        d = json.load(open(p, encoding="utf-8"))
        for k, v in (d.get("vaults") or {}).items():
            if os.path.normcase(os.path.normpath(v.get("path", ""))) == \
               os.path.normcase(os.path.normpath(VAULT)):
                _vault_id_cache = k
                break
    except Exception:
        pass
    return _vault_id_cache


def line_uri(rel_path, line, anchor=None):
    """拼 FakeLink 能识别的行链接(格式与其右键"复制行链接(adv-uri)"一致)。"""
    from urllib.parse import quote
    parts = []
    # 口径与 JS 侧(truerecall跳原图.js 的 vaultParam())一致:vault id 优先,
    # 读不到 obsidian.json 时退用 vault 名(目录 basename)。给系统协议路由留一个可用值。
    vid = vault_id() or os.path.basename(VAULT)
    if vid:
        parts.append("vault=" + quote(vid, safe=""))
    parts.append("filepath=" + quote(rel_path, safe=""))
    parts.append("line=%d" % line)
    parts.append("column=1&openmode=true&view-mode=source")
    if anchor:
        parts.append("anchor=" + quote(anchor, safe=""))
    return "obsidian://adv-uri?" + "&".join(parts)


# ---------- frontmatter ----------

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)
UID_RE = re.compile(r"^flashcard_uid:\s*[\"']?([a-f0-9]+)[\"']?\s*$", re.M)


def read_uid(text):
    m = FM_RE.match(text)
    if not m:
        return None
    m2 = UID_RE.search(m.group(1))
    return m2.group(1) if m2 else None


def set_uid(text, uid):
    """返回 (新文本, 是否改动)。已有 uid 则原样返回。"""
    if read_uid(text):
        return text, False
    m = FM_RE.match(text)
    if m:
        head = m.group(1)
        new_head = head + "\n" + "%s: %s" % (UID_FIELD, uid)
        return text[:m.start(1)] + new_head + text[m.end(1):], True
    return "---\n%s: %s\n---\n" % (UID_FIELD, uid) + text, True


# ---------- 解析 ----------

HL_RE = re.compile(r"==(?!=)(.+?)(?<!=)==", re.S)
# 加粗标记：挖空内容里要清掉（插件自己会加粗，叠加会变成 ****…****）
# ⚠️ 2026-09-20 起只作回溯/自测用，正式路径改由 strip_inline_md() 统一处理
BOLD_RE = re.compile(r"\*\*|__")
# 行内公式 `$…$`：**整段原样保护**（2026-09-20 广哥定）—— 公式里的 `*` `_`
# （乘号、下标）是数学内容不是格式，误删就毁了。保护必须在清格式之前做。
MATH_RE = re.compile(r"\$[^$\n]+?\$")
# 行内代码 `` `…` ``：**整段原样保留**（2026-09-20 广哥定「行内代码和 HTML 标签不要改」）
# —— 连里面的 `_` `*` 一起保（`` `file_name` `` 里的下划线是代码不是斜体标记）。
CODE_RE = re.compile(r"`[^`\n]+`")
# 其余行内格式：挖空内容与提问里**全部清掉、只留纯文字**（2026-09-20 广哥定：
# 「文本格式都清掉，只保留文字，再在高亮的位置补高亮」—— 否则这些标记和脚本
# 补的 `==` 叠在一起，卡面在 CM6 里经常渲染坏）。
# ⚠️ 顺序不能改：`**` `__` 必须排在单 `*` 单 `_` 前面，否则会被当成两个单字符先删。
# ⚠️ 范围**只到文本格式**：行内代码（`` ` ``）与 HTML 标签（`<b>` 等）**原样不动**
# （广哥 2026-09-20 定：代码是内容、不是格式；HTML 标签删了会丢语义/丢样式）。
INLINE_MD_RE = re.compile(r"\*\*|__|~~|\*|_")
# Word Joiner（U+2060）：不可见、Unicode 类别 Cf —— **既不是空白也不是标点**。
# 用途见 cloze_fill()：夹在挖空内容两端，保证插件答案面那对 `**` 一定能开闭。
WJ = "\u2060"
# 挖空内容外面套的标记（2026-09-17 广哥定，第二版）：`==…==`，给 CSS 一个**只命中挖空**的钩子。
# 为什么不能只靠 `strong`：插件那对 `**` 的加粗和用户自己画的 **粗体** 在 DOM 上分不开，
# CSS 一染就误伤（全库 157 张 cloze 卡里 48 张含非挖空粗体）。
#
# ⚠️ 为什么第一版 `<span class="tr-cloze">` 不行（2026-09-17 晚，源码级查实）：
#   卡面不是 MarkdownRenderer 渲染的，而是 **Obsidian 的 CM6 编辑器（实时预览）**
#   （插件源码 Oa 组件 → EmbeddableEditor；styles.css 里 `.true-recall-review-answer
#    .cm-editor .cm-content` 也印证）。实时预览有两个后果：
#     ① `**x**` 渲染成 `<span class="cm-strong">`，**不是 `<strong>`** → 染 strong 永远不中；
#     ② 行内 HTML 按**单个标签**逐个走 `HtmlWidget`（`createEl("span","cm-html-embed")`
#        + `sanitizeHTMLToDom`），`<span …>` 与 `</span>` 被拆成两个孤立 widget，
#        开标签单独清洗后自动闭合 → 得到一个**空 span**，文字落在它外面 → 钩子抓不住。
#   而 `==` 是 Obsidian 原生语法，实时预览渲染成 `span.cm-highlight`（在编辑器内、
#   包住真正的文字），阅读视图渲染成 `<mark>` —— 两种模式都有钩子。
# ⚠️ WJ 要放**两处**（2026-09-17 补第二处，实现见 cloze_fill()）：
#    ① 外层（`WJ + ==…== + WJ`）：插件答案面那对 `**` 后面必须紧跟 WJ 才能「开」
#       ——`**` 后面若紧跟 `=`（Unicode 标点）就开不了 → 星号字面显示。
#    ② 内层（`== + WJ + … + WJ + ==`，仅当内容首/尾是标点/符号时）：`==` 自己也吃
#       flanking，内容以引号、括号、`$`、`→` 这类字符开头/结尾时，`==` 贴着标点
#       既开不了也闭不了 → 两个 `==` 原样露成字面量。实测（教育学 207 那三处，
#       2026-09-17）：`=="组织起来…"归斯宾塞(内容说)==` 在卡面上显示成
#       `==“组织起来…”归斯宾塞(内容说)==`。
CLOZE_MARK = "=="
# 没有 `%%提问%%` 时给挖空填的**默认第三段**（2026-09-17 广哥定，全库批量补过一次）。
# 目的：问题面的占位符不是插件吐的 `[...]` 而是本串 —— CM6 会把 `==…==` 渲染成
# `span.cm-highlight`，于是三个点**黄底**，一眼能看见挖空在哪。
#   · 为什么必须做：`[...]` 是 `GS()` 拼的**纯文本**（`s ? '['+s+']' : "[...]"`），
#     在 CM6 里是裸文本节点，CSS 没有任何元素可选 ⇒ 只能从数据侧下手。
#   · 形态与原占位符视觉一致（三个点），只是外面套了 `==`；WJ 放 `==` 内侧（`.` 是
#     标点 Po，`==` 贴标点会 flanking 失败）。
#   · ⚠️ 它进的是**第三段**（hint），而 `_render_cloze()` 算幂等键时**含第三段**
#     ⇒ 改这里等于改幂等键：库里旧卡必须同步补同样的串（一次性脚本
#     `tmp\tr_add_placeholder_hint_20260917.py` 已跑完 185 处），否则重跑 hl2tr
#     会认为「库里没有这些卡」→ 重复建批。
#   · 置空字符串即整体关闭（但已改过的库要一起回滚，见上）。
#   · 2026-09-19 起**语义 hint 也走同一形态**：`mark_hint()` 给 `%%提问%%` 那一路
#     包同样的 `==…==` ⇒ 两条 hint 来源在问题面上样式统一（该改动同样动幂等键，
#     库里已有语义 hint 的卡需同步，见 mark_hint() 的 ⚠️）。
# ⛔ 2026-10-12 广哥定：**彻底走官方原生** —— hint 段不再包 `==`，退回裸 `...`。
#    · 旧值 = `CLOZE_MARK + WJ + "..." + WJ + CLOZE_MARK`（`==⁠...⁠==`，黄底三个点）；
#      新值 = `"..."`。视觉上**与不填第三段完全一致**（插件 `GS()` 是
#      `s ? '['+s+']' : "[...]"`，填 `...` 与不填都渲染成 `[...]`），
#      但保留了「每个挖空都带第三段」的结构，将来想加回 `==` 只改这一行常量。
#    · ⚠️ 幂等键 = `card_fields_key(_render_cloze(Text), Extra)`，而 `_render_cloze`
#      只取第三段(hint)、**丢掉第二段(内容)** ⇒ 改这里**等于改幂等键**：
#      库里 156 张存量 cloze 卡必须同步洗掉 hint 的 `==`，否则下次重跑 hl2tr
#      字段键全不命中 → 重复建一整批。迁移脚本见 `scripts/tr_unwrap_cloze_eq.py`。
#    · 内容侧那层 `==` 由 `cloze_fill(mark=...)` 控制，本次一并默认关闭；
#      它**不进幂等键**（第二段被丢弃），所以光关它不会引起重复建批。
DEFAULT_HINT = "..."


# 紧贴 `==` 的字符算不算「标点/符号」——决定要不要把 WJ 塞到标记内侧。
# 用 Unicode 大类：P*（标点）与 S*（符号，如 $ + → ± × ÷）。
# 空白不在内（内容进来前已 strip）；WJ 自己（Cf 类）也不在内。
def is_edge_punct(ch):
    if not ch:
        return False
    return unicodedata.category(ch)[0] in ("P", "S")


def strip_inline_md(s, keep_math=True):
    """清掉挖空内容 / 提问里的**所有行内格式标记**，只留纯文字；`$…$` 公式整段原样。

    ⚠️ 2026-09-20 广哥定（由旧的「只去加粗」升级）：挖空前先把**文本格式**都清掉，只保留
    文字，再在高亮的位置补高亮 —— 否则 `**` `~~` `*` `_` 这些标记和脚本补的 `==`
    叠在一起，卡面（CM6 实时预览）经常渲染坏。覆盖范围：
      `**加粗**` / `__加粗__` / `*斜体*` / `_斜体_` / `~~删除线~~`

    ⚠️ 2026-09-20 广哥补定：**行内代码 `` `…` `` 与 HTML 标签（`<b>` `<sub>` …）原样不动**
    —— 代码是内容不是格式（`` `file_name` `` 的下划线是标识符），HTML 标签删了丢语义。
    ⚠️ **公式必须保护**：`$x_1 * y$` 里的 `_` `*` 是数学符号，清掉就毁了 ⇒ 先把它（以及
    行内代码）抠出来用 `\\x00N\\x00` 占位（该字符不会被格式正则命中、也不影响空格压缩），
    清完再原样还原。裸 `$`（不是成对公式）不受影响。
    ⚠️ 顺带把删标记后留下的连续空格压成一个（如 `**A** **B**` → `A B`）。
    ⚠️ 幂等：清过的内容再清一次结果完全相同。
    ⚠️ 只用于「笔记 → 卡面」这一步，**不动 source_text**（它要与笔记正文逐字一致）。
    """
    s = s or ""
    slots = []

    def _keep(m):
        slots.append(m.group(0))
        return "\x00%d\x00" % (len(slots) - 1)
    s = CODE_RE.sub(_keep, s)          # 行内代码整段原样（连内部的 _ * 一起保）
    if keep_math:
        s = MATH_RE.sub(_keep, s)      # 公式整段原样
    s = INLINE_MD_RE.sub("", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    if slots:
        s = re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m.group(1))], s)
    return s.strip()


def mark_hint(text, mark=False):
    """第三段(hint / 提问) → 套一层 `==…==`，与 DEFAULT_HINT 同款形态。

    ⛔ 2026-10-12 广哥定：**彻底走官方原生** ⇒ `mark` 默认改为 **False**，hint 不再包 `==`
    （只保留 `strip_inline_md()` 的清格式），问题面回退成插件原生的黑字 `[提问]` / `[...]`。
    传 `mark=True` 可复原旧行为。⚠️ 该值进幂等键，翻转它必须同步洗库，见 DEFAULT_HINT 注释。

    ⚠️ 2026-09-19 广哥定：**语义提问也要包**。此前只有**占位符** hint 带 `==`
    （问题面 `[==⁠...⁠==]` → 黄底），而 `%%提问%%` 生成的语义 hint 是裸文本
    （问题面 `[这个原则叫什么]` → 黑字）⇒ 同一个问题面上两套样式。
    包上之后问题面成 `[==提问==]`：`GS()` 拼的方括号留在外面、`==` 被 CM6 渲染成
    `span.cm-highlight` ⇒ 黄底，与占位符逐像素同款（复用 CSS 片段第 1 条规则，
    片段本身不用改）。**笔记一个字不动** —— 只改「笔记 → 卡面」这一步的转换。

    形态 = `==` + 内容 + `==`，**内层 WJ** 按 `is_edge_punct()` 判据补（`==` 自己吃
    flanking，内容首 / 尾是标点、符号时会露字面量）；**不加外层 WJ** —— 那一层是给
    插件答案面那对 `**` 用的，而 hint 只出现在问题面、不进答案面。

    幂等与三个边界：
      · 已以 `==` 开头且结尾 → 原样返回（`DEFAULT_HINT` 正靠这条被放过，不二次包裹）；
      · 内容首 / 尾本身就是 `=` → 不包（`==A===` 会被解析坏，与内容侧同判据）；
      · 内容中间含 `==` → 不包并打 WARN（里面那个 `==` 会提前闭合，渲染坏）。
    ⚠️ 它进**第三段**而 `_render_cloze()` 算幂等键时含第三段 ⇒ **改这里 = 改幂等键**：
    库里旧卡必须同步补同样的串，否则重跑 hl2tr 会认为「库里没有这些卡」→ 重复建批
    （与 2026-09-17 补占位符 hint 同一套路，见 DEFAULT_HINT 注释）。
    """
    s = strip_inline_md(text or "")
    if not s:
        return s
    if not mark:                      # ⛔ 2026-10-12 起默认走原生：只清格式，不包 ==
        return s
    if s.startswith(CLOZE_MARK) and s.endswith(CLOZE_MARK) and len(s) > 2 * len(CLOZE_MARK):
        return s
    if s.startswith("=") or s.endswith("="):
        return s
    if CLOZE_MARK in s:
        WARN.append("提问里含 `==`，已跳过包裹：%r" % s)
        return s
    body = s
    if is_edge_punct(body[0]) and not body.startswith(WJ):
        body = WJ + body
    if is_edge_punct(body[-1]) and not body.endswith(WJ):
        body = body + WJ
    return CLOZE_MARK + body + CLOZE_MARK


# 高亮 + Obsidian 行内注释 %%…%% 一起扫，一次拿全位置，才能做「同行归属」
# （group(1)=高亮内容 / group(2)=整段注释含两侧 %%）
TOKEN_RE = re.compile(r"==(?!=)(.+?)(?<!=)==|(%%(?:(?!%%).)*?%%)", re.S)

# 生成期的软告警（hint 含 `}` 之类），main() 收尾统一打印
WARN = []


def classify(line):
    s = line.rstrip()
    if not s.strip():
        return "blank"
    st = s.lstrip()
    if st.startswith("#"):
        return "heading"
    if st.startswith("```") or st.startswith("~~~"):
        return "fence"
    # 列表项:`- `/`* `/`+ `/`1. `/`1) `;并容忍 `1.**粗体**` 这种无空格的写法
    if re.match(r"^\s*(?:[-*+]|\d+[.)])\s*", s) and not re.match(r"^\s*\d+\.\d", s):
        return "list"
    if st.startswith(">"):
        return "quote"
    if st.startswith("|"):
        return "table"
    return "para"


def is_indent(line):
    """行首是否带缩进(空格或制表符)。用于「缩进行归属上方最近的未缩进行」判定。

    2026-09-17 广哥定:缩进的行与它上面那个未缩进的父行是一体的,合成一张卡。
    """
    return line[:1] in (" ", "\t")


# 缩进归属总开关(默认开;`--no-indent-merge` 关掉即退回「每行独立成块」的旧行为)
MERGE_INDENT = True


def build_units(lines):
    """返回 units: [{'start':i,'end':j}],以及 code_flags(每行是否在代码块内)。

    缩进归属(2026-09-17 起默认):凡行首带缩进的行,一律并入上方最近的「未缩进行」
    所在的块,不另起一块;多级缩进也一路归到同一个父块。行首无缩进的行才开新块。
    """
    n = len(lines)
    code = [False] * n
    in_code = False
    kinds = []
    for i, ln in enumerate(lines):
        k = classify(ln)
        if k == "fence":
            in_code = not in_code
            code[i] = True
            kinds.append("fence")
            continue
        code[i] = in_code
        kinds.append("code" if in_code else k)

    units = []
    cur = None      # 当前块
    top = None      # 上方最近的「未缩进行」所属块 —— 缩进行的归属目标
    for i, k in enumerate(kinds):
        if k in ("blank", "heading", "fence", "code"):
            cur = None
            top = None
            continue
        # 缩进行 = 上方未缩进行的续体:只并入该块,不另起一块(多级缩进归同一父块)
        if MERGE_INDENT and is_indent(lines[i]) and top is not None:
            top["end"] = i
            cur = top
            continue
        if k in ("list", "table"):
            cur = {"start": i, "end": i}
            units.append(cur)
            top = cur
            continue
        # para / quote:连续同类合并
        if cur is not None and kinds[cur["end"]] == k:
            cur["end"] = i
        else:
            cur = {"start": i, "end": i}
            units.append(cur)
        top = cur
    return units, code


def find_highlights(lines, code):
    """返回 [(start_line, end_line)]"""
    text = "\n".join(lines)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln) + 1)

    def pos(o):
        for i in range(len(lines)):
            if offs[i] <= o < offs[i + 1]:
                return i, o - offs[i]
        return len(lines) - 1, 0

    out = []
    for m in HL_RE.finditer(text):
        s = m.start()
        e = m.end()
        sl, _ = pos(s)
        el, _ = pos(e - 1)
        if code[sl] if sl < len(code) else True:
            continue
        out.append((sl, el))
    return out


def build_blocks(lines):
    """返回含高亮的块:[{'start':i,'end':j}]"""
    units, code = build_units(lines)
    if not units:
        return []
    spans = find_highlights(lines, code)
    if not spans:
        return []

    idx_of = {}
    for ui, u in enumerate(units):
        for i in range(u["start"], u["end"] + 1):
            idx_of[i] = ui

    parent = list(range(len(units)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    hit = set()
    for sl, el in spans:
        a = idx_of.get(sl)
        b = idx_of.get(el)
        if a is None or b is None:
            continue
        for k in range(a, b + 1):
            union(a, k)
        hit.add(find(a))

    blocks = []
    for r in sorted(hit):
        members = [units[i] for i in range(len(units)) if find(i) == r]
        blocks.append({"start": min(m["start"] for m in members),
                       "end": max(m["end"] for m in members)})
    blocks.sort(key=lambda b: b["start"])
    return blocks


# ---------- 生成卡片 ----------

def cloze_fill(inner, hint=None, strip_bold=True, wj=True, mark=False):
    """挖空内容 → {{c1::...}}（有提问时 → {{c1::...::提问}}），内容先清掉**所有行内格式**（`$…$` 公式原样保留）。

    ⛔ 2026-10-12 广哥定：`mark` 默认改为 **False** —— 挖空内容外面**不再包 `==`**。
    官方 2.10.0 渲染答案面时会自己把内容包成 `**…**`（常量 `gYe=t=>**${t}**`），
    叠加脚本的 `==` 就成「粗体 + 黄底」的冗余效果，现彻底回退官方原生（只留粗体）。
    ⚠️ 内容侧这层 `==` **不进幂等键**（`_render_cloze` 只取第三段、丢掉第二段）
    ⇒ 单关它不会引起重复建批；但 hint 侧那层进幂等键，翻转要同步洗库。

    2026-09-20 广哥定：清格式的范围从「只去 `**`/`__`」扩到**全部文本格式**
    （`**` `__` `*` `_` `~~`），实现见 `strip_inline_md()`。
    ⚠️ 行内代码 `` `…` `` 与 HTML 标签**不在清理范围**（广哥 2026-09-20 补定：原样保留）。

    为什么必须去掉加粗：插件渲染「揭示答案」时自己会把挖空内容包成 `**...**`
    （源码 zS()：`t.replace(r,(n,i,o)=>parseInt(i,10)===e?`**${o}**`:o)`）。若内容里
    本来就有用户画的 `**`，叠加后就是 `****内容****`，CommonMark 实测渲染成
    <strong><strong>…</strong></strong> 的嵌套加粗——冗余且脆弱（一旦标记不成对
    就会把字面 `**` 显示出来）。所以挖空内部只留纯文本，加粗交给插件那一层。

    ⚠️ wj=True（默认，2026-09-17 定）：在内容两端各插一个 **Word Joiner(U+2060)**。
    为什么需要它：**去掉 `**` 之后仍然有 6.3% 的卡加粗会失效、星号字面显示** ——
    根因是 CommonMark 的 flanking 规则，插件那对 `**` 要能「开」要求紧跟着的不是
    空白，且（不是标点 或 前一个是空白/标点）；要能「闭」同理反过来看前一个字符。
    于是内容**首尾是标点**、**外侧又紧贴文字**时就开不了/闭不了，典型两种：
       · 内容以 `$` 开头（数学公式）+ 前面紧贴中文  → 开不了：`若**$A$**经`
       · 内容以 `。` `）` `,` 结尾 + 后面紧贴中文    → 闭不了：`是**重要。**在`
    全库 4989 个高亮实测：失效 314 个（6.3%），其中「尾标点+后贴字」179、
    「首标点+前贴字」109、跨行 21（2026-09-17 用 markdown-it 逐条渲染核过）。
    U+2060 是 Cf 类，**既不算空白也不算标点**，夹在两端后 `**` 永远能开能闭，
    且它不可见、在 `$…$` 之外（不干扰 MathJax）。
    ⚠️ 外层 / 内层 WJ 都只加在挖空**内容**上，`source_text` 与提示(hint)都不加
    （hint 自己那份内层 WJ 由 `mark_hint()` 负责，是另一处）。
    ⚠️ **内外两处都要**（2026-09-17 补第二处）：外层 WJ 是给插件那对 `**` 用的；
    `==` 标记自己也吃 flanking，内容首/尾是标点/符号（引号、括号、`$`、`→`）时
    还要在 `==` **内侧**各补一个 WJ，否则两个 `==` 会原样露字面量。判据 `is_edge_punct()`。
    视觉零差异（U+2060 不可见），且在内侧不干扰 `$…$` 之外的 MathJax。

    ⚠️ mark=True（**2026-10-12 起不再是默认**，原默认见下）：把挖空**内容**套一层 `==…==`。
    目的只有一个 —— 给 CSS 一个**只命中挖空**的选择器。插件渲染答案面时会在内容外再包
    一对 `**`，而块内用户自己画的 `**粗体**` 也是同一套加粗，两者在 DOM 上分不开；只靠
    加粗染色会把用户粗体一起染绿（157 张现存卡里 48 张中招）。
    ⚠️ 第一版用的是 `<span class="tr-cloze">`，**实测无效**，原因见 CLOZE_MARK 常量注释
    （卡面是 CM6 实时预览编辑器：`**` → `.cm-strong` 不是 `<strong>`；行内 HTML 按单标签
    走 HtmlWidget，开闭标签被拆开 → 只剩一个空 span）。改用 `==` 后：
      · 复习界面（实时预览）→ `span.cm-highlight`（包住文字）
      · 阅读视图 → `<mark>`
    配套 CSS：~~`<vault>/.obsidian/snippets/true-recall-挖空-高亮黄加粗.css`~~
    （2026-09-17 由 `true-recall-答案面挖空-去加粗改颜色.css` 改名 —— 原名与现行效果正好相反）。
    ⛔ **2026-10-12：该片段连同「去加粗」补丁一并删除，并彻底走官方原生**
    —— 于是内容侧这层 `==` 也一起停（默认 `mark=False`）；hint 侧那层见 `mark_hint()`。
    幂等：已用 `==` 包好的内容不再二次包裹；`--cloze-mark` 可重新开启。
    ⚠️ **WJ 在标记内外各一处**（2026-09-17 定）：外层给插件那对 `**`、内层给 `==`
    自己（内容贴标点时），详见常量注释与 wj 段。

    hint（提问）为什么能直接拼在第三段：插件的 cloze 正则是
    `/\\{\\{c(\\d+)::([^}]*?)(?:::([^}]*?))?\\}\\}/g`，渲染函数 GS() 里
    `s ? \\`[${s}]\\` : "[...]"` —— 有第三段时问题面显示第三段原文（现在恒为 `==` 形态：语义提问 `[==提问==]`、占位符三个点 `[==…==]`）、没有时才是裸 `[...]`；
    答案面 zS() 只用第二段，提问不会漏到答案里。
    标记与提问的关系（2026-09-19 更新）：`mark` **只包第二段**（内容），第三段(hint)
    由 `mark_hint()` 单独包一层同样的 `==…==` —— 于是问题面上「语义提问」与「占位符
    三个点」样式一致（都是原生高亮黄底、不加粗；2026-09-20 起去粗）。

    注意：只处理 Text（卡面），**不动 source_text**（它要与笔记正文逐字一致，跳转才找得到）。
    """
    s = inner.strip()
    if strip_bold:
        # 2026-09-20 升级：不只去加粗，而是清掉**所有行内格式**（$…$ 公式原样保留），
        # 只留纯文字 —— 再在下面套 `==` 高亮。旧口径（只删 `**|__`）见 BOLD_RE。
        s = strip_inline_md(s)
    if s:
        # 幂等判据：已带 `==` 标记（不论 WJ 在里还是在外）就不再套
        has_mark = s.startswith(CLOZE_MARK) or (WJ + CLOZE_MARK) in s
        # 内容首/尾本身就是 `=` 时不包（`==A===` 会被解析坏）
        if mark and not has_mark and not s.startswith("=") and not s.endswith("="):
            s = CLOZE_MARK + s + CLOZE_MARK
            has_mark = True
        if wj and not s.startswith(WJ):
            s = WJ + s + WJ                     # ① 外层 WJ：给插件答案面那对 `**`
        if wj and has_mark:
            # ② 内层 WJ：内容紧贴 `==` 的字符是标点/符号时补上，否则 `==` 会露字面量
            m = re.match(r"^(%s%s)(.*?)(%s%s)$" % (WJ, CLOZE_MARK, CLOZE_MARK, WJ), s, re.S)
            if m:
                body = m.group(2)
                if body:
                    if is_edge_punct(body[0]) and not body.startswith(WJ):
                        body = WJ + body
                    if is_edge_punct(body[-1]) and not body.endswith(WJ):
                        body = body + WJ
                    s = m.group(1) + body + m.group(3)
    if not hint:
        return "{{c1::%s}}" % s
    h = hint.strip()
    if "}" in h:
        # 插件第三段是 [^}]*?，含 `}` 会让**整个** cloze 失配 → 卡面直接露出 {{c1::…}}
        WARN.append("提问里含 `}`，已剔除：%r" % h)
        h = h.replace("}", "")
    # 第三段：**⛔ 2026-10-12 起不再包 `==`**（广哥定，彻底走官方原生）⇒ 问题面回退成
    # 插件 `GS()` 原生的黑字 `[提问]` / `[...]`。
    # 旧口径（`==…==` 黄底，2026-09-19 定）与幂等键影响见 `mark_hint()` 与 `DEFAULT_HINT`。
    h = mark_hint(h, mark)
    return "{{c1::%s::%s}}" % (s, h)


def norm_link_gap(text):
    """把 `}}` 与其后**紧邻**的 wikilink 之间的间距统一成**两个空格**。

    现象（广哥 2026-09-19 报，卡面实测）：问题面上插件 `GS()` 把第三段原样拼成
    `[hint]`，于是卡面成了 `[==学习动机==] [[x.pdf#page=55|pdf]]` —— 中间只有**一个**
    空格时，Obsidian 的解析会把 `[hint]` 吃成**链接文字**（广哥原话：「把学习动机变成
    链接了」），补成两个空格即恢复正常。⇒ 只要 hint 后面跟着链接，一个空格就不够。
    ⚠️ 机制未在源码级定论（怀疑是 `[text] [ref]` 形态被当引用式链接解析），
    按**实测口径**执行：一空格中招、两空格正常。
    ⚠️ hint 拼进方括号这一点是 2026-09-17 引入占位符时就有了 ⇒ 这是**老问题**，
    只是语义 hint 被包 `==` 后（2026-09-19）这两类更显眼。
    ⚠️ **只规范 `}}` + `[[`**；`}} ![[`（嵌入）按广哥 2026-09-19 的指令**保持原样**。
    幂等：已经是两个及以上空格的不再匹配。**不动 source_text**（它要与笔记逐字一致）。
    """
    return re.sub(r"\}\} (\[\[)", r"}}  \1", text or "")


def _line_starts(raw):
    offs = [0]
    for i, ch in enumerate(raw):
        if ch == "\n":
            offs.append(i + 1)
    return offs


def _line_of(offs, pos):
    lo, hi = 0, len(offs) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offs[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo


def plan_cloze(raw, strip_bold=True, use_hint=True, wj=True, mark=False):
    """块原文 → 卡面 Text；返回 (text, {'hints':n, 'orphan':[...]})。

    `use_hint=False`（命令行 `--no-hint`）时完全退回旧行为：`%%…%%` 一律原样留在卡面，
    挖空**也不填**默认占位符。

    ⛔ 2026-10-12 广哥定（彻底走官方原生）：`mark` 默认改 **False** ⇒ 内容侧与 hint 侧
    **都不再包 `==`**；问题面占位符回退成插件原生 `[...]`、语义提问回退成 `[提问]`。

    ⚠️ 没有 `%%提问%%` 的挖空现在会被填上 `DEFAULT_HINT`（现在恒为裸 `...`；
    旧的 `::==⁠...⁠==` 黄底形态见 DEFAULT_HINT 常量注释）。
    ⚠️ 第三段(hint)的两条来源：没有 `%%提问%%` 的填 `DEFAULT_HINT`；有的填提问原文。
    2026-09-17~2026-10-12 期间两条来源都被包成 `==…==`（黄底），
    ⛔ 2026-10-12 起彻底走原生 ⇒ 两条都是裸文本（黑字 `[...]` / `[提问]`）。
    第三段是**幂等键的一部分**：改了它，库里旧卡必须同步补同样的串。

    `%%提问%%` 的归属规则（2026-09-17 广哥定）：
      1. **只在同行生效** —— 注释必须和它归属的那个 `==高亮==` 在同一行
         （判据：注释起始行 == 高亮结束行；跨行高亮按结束行算）；
      2. 归属**该行内它前面最近**的一个高亮；那个高亮若已有提问，再往前找一个同行的；
      3. 同行前面没有高亮（含注释单独成行）→ **不生效**，注释在卡面里原样保留，
         并在预览里列出来（orphan）供人工核对；
      4. 被消费掉的注释从卡面 Text 里删除（内容已进第三段，留在正文会重复），
         但 `source_text` 仍是块原文，逐字含 `%%`，跳转不受影响。
    """
    if not use_hint:
        return (norm_link_gap(
                    HL_RE.sub(lambda m: cloze_fill(m.group(1), None, strip_bold, wj, mark), raw)),
                {"hints": 0, "orphan": []})

    offs = _line_starts(raw)
    hl, note = [], []
    for m in TOKEN_RE.finditer(raw):
        (hl if m.group(1) is not None else note).append(m)

    hints, consumed, orphan = {}, [], []
    for nm in note:
        ln = _line_of(offs, nm.start())
        idx = None
        for i in range(len(hl) - 1, -1, -1):
            h = hl[i]
            if h.end() > nm.start():          # 高亮必须在注释之前
                continue
            if _line_of(offs, h.end() - 1) != ln:   # 不同行 → 再往前只会更远
                break
            if i in hints:                    # 这个高亮已有提问
                continue
            idx = i
            break
        if idx is None:
            orphan.append(nm.group(2))
        else:
            hints[idx] = nm.group(2)[2:-2].strip()
            consumed.append(nm)

    ops = []
    for i, h in enumerate(hl):
        # 有 `%%提问%%` 用它；没有则填 DEFAULT_HINT
        # （⛔ 2026-10-12 起恒为裸 `...`；旧的黄底 `==…==` 形态见 DEFAULT_HINT 常量注释）
        ops.append((h.start(), h.end(),
                    cloze_fill(h.group(1), hints.get(i) or DEFAULT_HINT, strip_bold, wj, mark)))
    for nm in consumed:
        # 注释被吃掉后，它左边紧邻的水平空白也一并吞掉，否则卡面会留下 `内容}} ` 这种
        # 多余空格（只吞空格/制表符，不吃换行，免得动到行首缩进）
        s = nm.start()
        while s > 0 and raw[s - 1] in " \t":
            s -= 1
        # ⚠️ 右侧紧贴「会粘住」的字符时**必须回填一个空格**（2026-09-17 广哥报「题面粘连」）。
        # 反例：`==**组织策略**== %%学习策略%%[[x.pdf#page=72|pdf]]` —— 注释与链接之间本来就没空格
        # （靠左侧那个空格当分隔），两处空白一起吞掉后卡面成了 `[学习策略][[…|pdf]]`，
        # 插件 `GS()` 把第三段渲染成 `[提问]`，于是题面读起来是「学习策略pdf 视频」。
        # 只在 `[` / `!` / 字母数字前补：`==A==%%Q%%.`（句点）、`}}经`（中文）这类不该多出空格。
        # ⚠️ 2026-09-19 追加：这里回填的仍是**一个**空格（只解决"粘连"）；而 `}} [[` 之间的
        # 间距由收尾的 `norm_link_gap()` 再补成**两个** —— 一个空格时问题面上的 `[hint]` 会被
        # 解析成链接文字（广哥原话「把学习动机变成链接了」），见该函数。
        tail = raw[nm.end():]
        rep = " " if tail and (tail[0] in "[!"
                            or (tail[0].isascii() and tail[0].isalnum())) else ""
        ops.append((s, nm.end(), rep))
    ops.sort(key=lambda x: x[0])

    out, pos = [], 0
    for s, e, rep in ops:
        out.append(raw[pos:s])
        out.append(rep)
        pos = e
    out.append(raw[pos:])
    # 收尾：`}}` 与紧邻的 `[[` 之间补成两个空格（2026-09-19，见 norm_link_gap）
    return norm_link_gap("".join(out)), {"hints": len(hints), "orphan": orphan}


def block_label(base, n):
    return "《%s》·第 %d 块" % (base, n)


def block_anchor(lines, b):
    s = (lines[b["start"]] or "").strip()
    return s[:ANCHOR_LEN] if s else None


def block_extra(lines, b, base, n, rel_path, url_extra=True, anchor_on=True):
    """卡片 Extra(= 卡面最后那行)。默认写成可点行链接。"""
    label = block_label(base, n)
    if not url_extra:
        return label
    uri = line_uri(rel_path, b["start"] + 1,
                   block_anchor(lines, b) if anchor_on else None)
    return "[%s](%s)" % (label, uri)


def block_cards(lines, blocks, base, rel_path,
                url_extra=True, anchor_on=True,
                use_source_text=True, strip_bold=True, use_hint=True, wj=True, mark=True):
    cards = []
    for n, b in enumerate(blocks, 1):
        raw = "\n".join(lines[b["start"]:b["end"] + 1]).strip()
        if not raw or "{{c" in raw:
            continue
        if not HL_RE.search(raw):
            continue
        text, info = plan_cloze(raw, strip_bold, use_hint, wj, mark)
        cards.append({"block": n, "line": b["start"] + 1,
                      "Text": text,
                      "Extra": block_extra(lines, b, base, n, rel_path,
                                           url_extra, anchor_on),
                      "source_text": raw if use_source_text else None,
                      "hints": info["hints"], "orphan": info["orphan"]})
    return cards


# ---------- 写库(旧路线:直接 SQLite) ----------

def apply_cards_sqlite(cards, uid, db, prune):
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = os.path.join(BACKUP_DIR, "true-recall-backup-%s.db" % ts)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    shutil.copy2(db, bak)
    print("已备份数据库:", bak)

    now_ms = int(time.time() * 1000)
    due = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        ("%03dZ" % (now_ms % 1000))
    con = sqlite3.connect(db)
    cur = con.cursor()
    added = skipped = pruned = 0
    try:
        cur.execute("begin")
        keep = set()
        for c in cards:
            fields = json.dumps({"Text": c["Text"], "Extra": c["Extra"]}, ensure_ascii=False)
            keep.add(fields)
            cur.execute("select count(*) from notes where fields_json=? and deleted_at is null",
                        (fields,))
            if cur.fetchone()[0] > 0:
                skipped += 1
                continue
            nid = str(uuid.uuid4())
            cur.execute(
                "insert into notes (id,note_type_id,fields_json,tags,source_uid,source_text,"
                "user_comment,created_via,created_at,updated_at,deleted_at,edit_count,"
                "ai_edit_count,content_edited_at) values (?,?,?,?,?,?,?,?,?,?,NULL,0,0,NULL)",
                (nid, CLOZE_TYPE, fields, "", uid, c.get("source_text") or "",
                 None, "import", now_ms, now_ms))
            cur.execute(
                "insert into cards (id,note_id,template_ord,due,stability,difficulty,reps,lapses,"
                "state,last_review,scheduled_days,learning_step,suspended,buried_until,"
                "created_at,updated_at,deleted_at,source_uid) "
                "values (?,?,1,?,0,0,0,0,0,NULL,0,0,0,NULL,?,?,NULL,?)",
                (str(uuid.uuid4()), nid, due, now_ms, now_ms, uid))
            added += 1
        if prune:
            rows = list(cur.execute(
                "select id, fields_json from notes where source_uid=? and deleted_at is null "
                "and created_via='import'", (uid,)))
            for nid, fj in rows:
                if fj in keep:
                    continue
                cur.execute("update notes set deleted_at=? where id=?", (now_ms, nid))
                cur.execute("update cards set deleted_at=? where note_id=?", (now_ms, nid))
                pruned += 1
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        cur.execute("select count(*) from notes where deleted_at is null")
        n = cur.fetchone()[0]
        cur.execute("select count(*) from cards where deleted_at is null")
        cc = cur.fetchone()[0]
        con.close()
    print("新增 %d 张 / 已存在跳过 %d 张 / 清理旧卡 %d 张" % (added, skipped, pruned))
    print("库现状: notes=%d cards=%d" % (n, cc))


# ---------- 写库(默认路线:插件 Local API) ----------

def _norm_fields(s):
    """把 fields_json 归一化:解析后按「紧凑 + 键排序」重新序列化。

    插件落库用的是紧凑 JSON(`{"Text":"..."}`,冒号后无空格),而 Python
    json.dumps 默认会写成 `{"Text": "..."}`(有空格)——两者解析后完全相等、
    字符串却不相等,若直接拿字符串当幂等键就永远匹配不上、每跑一次重建一批
    (2026-09-14 实测踩了两次)。
    """
    try:
        return json.dumps(json.loads(s), ensure_ascii=False,
                          separators=(",", ":"), sort_keys=True)
    except Exception:
        return s


# ⚠️ 第三组(hint)必须一起认:插件的 GS() 是 `s ? `[${s}]` : "[...]"`,
# 若这里仍把所有 cloze 一律渲染成 `[...]`,带提问的卡就与插件展示态对不上 →
# 幂等键永不命中 → 每跑一次多一整批卡(2026-09-15 同类血案的翻版)。
# 2026-09-17 起**每个**挖空都带第三段（语义提问或 DEFAULT_HINT 占位符）⇒ 正常情况下
# 渲染态里不会再出现裸 `[...]`；`_render_cloze` 的 `[...]` 分支只兜历史/漏网的卡。
CLOZE_RE = re.compile(r"\{\{c\d+::(.*?)(?:::(.*?))?\}\}", re.S)


def _render_cloze(text):
    """把本地 Text 里的 `{{c1::内容}}` / `{{c1::内容::提问}}` 渲染成插件展示态。

    ⚠️ 用途只有一个:降级查卡(GET /notes/cards)拿回来的 `question` 是**展示态**,
    要比幂等就必须让本地侧也走到同一形态(2026-09-15 实测)。
    """
    def rep(m):
        return "[%s]" % m.group(2) if m.group(2) else "[...]"
    return CLOZE_RE.sub(rep, text or "")


def _extra_from_answer(ans):
    """从卡面 answer 里切出**真 Extra**。

    cloze 卡型的答案面是 `{{cloze:Text}}<br>{{Extra}}`,所以接口给的 `answer`
    = 渲染后的 Text + `<br>` + Extra。切法:先按最后一个 `<br>` 取尾段并校验开头,
    不行再用正则兜底找行链接(链接式 `[《…》·第 N 块](obsidian://…)` / 纯文字式)。
    """
    ans = ans or ""
    if "<br>" in ans:
        cand = ans.rsplit("<br>", 1)[1]
        if cand.startswith("[《") or cand.startswith("《"):
            return cand
    m = re.search(r"\[《[^\]]*》·第\s*\d+\s*块\]\(obsidian://[^\s)]*\)", ans)
    if m:
        return m.group(0)
    m = re.search(r"《[^》]*》·第\s*\d+\s*块", ans)
    if m:
        return m.group(0)
    return ""


def card_fields_key(text, extra):
    return _norm_fields(json.dumps({"Text": text, "Extra": extra}, ensure_ascii=False))


def existing_keys(db=None, uid=None):
    """只读查出"真正活着"的卡片对应的两类幂等键:(字段键集合, source_text 集合)。

    优先走插件 Local API 的 /query(读的是插件自己那条 DB 连接,写入后**立即可见**);
    v2.5.0 起 /query 常被设置项 apiEnableSqlQuery(默认关)挡成 403,此时降级走
    GET /notes/cards?source_uid=…(只返活卡,再逐张 /cards/:id 补 sourceText);
    都不通再退回只读开 SQLite(注意:插件落盘有延迟,建完卡马上重跑会读到旧状态)。

    ⚠️ 键的形态必须与调用方一致:本地侧用 `card_fields_key(_render_cloze(Text), Extra)`
    和块的 `source_text` 去比,否则就是"每跑一次多一整批"(2026-09-15 实测血案)。

    ⚠️ 降级路径只比对**本笔记**名下的卡(/notes/cards 按 uid 查),/query 则是比全库。
    语义差别:同一段高亮文字在两篇笔记里都有时,降级后会各建一张 —— 这反倒更正确。

    幂等键必须是「note 未删 **且** 它的 card 未删」;只查 notes 会把"孤儿 note"误判成
    已存在,导致整批跳过、一张卡都不建。
    """
    if uid and not sql_query_ok():
        try:
            rows = cards_by_uid(uid, with_source_text=True)
            have_fields = {card_fields_key(f.get("Text", ""), f.get("Extra", "")) for _, f in rows}
            have_st = {f["SourceText"].strip() for _, f in rows if f.get("SourceText")}
            return have_fields, have_st
        except Exception as e:
            print("  (按 uid 查卡失败,退回读磁盘:%s)" % e)
    sql = ("select n.fields_json from notes n join cards c on c.note_id = n.id "
           "where n.deleted_at is null and c.deleted_at is null")
    try:
        d = api_call("/query", {"sql": sql})
        out = set()
        for r in d.get("rows", []):
            try:
                fj = json.loads(r["fields_json"])
            except Exception:
                continue
            out.add(card_fields_key(_render_cloze(fj.get("Text", "")), fj.get("Extra", "")))
        return out, set()
    except Exception as e:
        print("  (API 幂等查询失败,退回读磁盘:%s)" % e)
    try:
        db = db or find_db()
        con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
        cur = con.cursor()
        out = set()
        for r in cur.execute(sql):
            try:
                fj = json.loads(r[0])
            except Exception:
                continue
            out.add(card_fields_key(_render_cloze(fj.get("Text", "")), fj.get("Extra", "")))
        con.close()
        return out, set()
    except Exception as e:
        print("  (只读查库失败,跳过幂等检查:%s)" % e)
        return set(), set()


def apply_cards_api(cards, uid):
    data = api_call("/status")
    print("Local API 在线:", json.dumps(data, ensure_ascii=False)[:120])

    have_fields, have_st = existing_keys(uid=uid)
    todo = []
    for c in cards:
        st = (c.get("source_text") or "").strip()
        if st and st in have_st:
            continue
        if card_fields_key(_render_cloze(c["Text"]), c["Extra"]) in have_fields:
            continue
        todo.append(c)

    skipped = len(cards) - len(todo)
    if not todo:
        print("新增 0 张 / 已存在跳过 %d 张 / 失败 0 张" % skipped)
        return

    # 一次请求批量提交(单张循环也可,但批量更快且少一半中间态)
    payload = {
        "cards": [{
            "question": c["Text"],
            "answer": c["Extra"],
            "card_type": "cloze",
            "source_uid": uid,
            "source_text": c.get("source_text") or "",
        } for c in todo],
        "source_uid": uid,
    }
    try:
        res = api_call("/cards", payload)
        added = int(res.get("created") or 0)
        failed = len(todo) - added
    except RuntimeError as e:
        print("  批量建卡失败,退回逐张:%s" % e)
        added = failed = 0
        for c in todo:
            p = {"cards": [{"question": c["Text"], "answer": c["Extra"],
                            "card_type": "cloze", "source_uid": uid,
                            "source_text": c.get("source_text") or ""}],
                 "source_uid": uid}
            try:
                added += int(api_call("/cards", p).get("created") or 0)
            except RuntimeError as e2:
                failed += 1
                print("  建卡失败(第 %d 块):%s" % (c["block"], e2))
    print("新增 %d 张 / 已存在跳过 %d 张 / 失败 %d 张" % (added, skipped, failed))

    if sql_query_ok():
        try:
            d = api_call("/query", {"sql":
                        "select count(*) as n from cards where deleted_at is null"})
            print("复核:库内活跃卡片数 =", d["rows"][0]["n"])
        except Exception:
            pass


# ---------- 就地改 Extra:把"第 N 块"变成可点行链接 ----------

BLOCK_NO_RE = re.compile(r"第\s*(\d+)\s*块")


def card_rows(uid):
    """返回 [(card_id, fields_dict)]:该 uid 名下活着的卡。

    优先走 API 的 /query(插件自己的连接,立即可见);/query 被关时降级走
    GET /notes/cards?source_uid=…(同样只返活卡);都不行再退回只读开 SQLite
    (只读,不会与插件打架),这样哪怕 Obsidian 关着也能先出预览。
    """
    if not sql_query_ok():
        try:
            return cards_by_uid(uid)
        except Exception as e:
            print("  (按 uid 查卡不可用,退回只读读库:%s)" % str(e).splitlines()[0])
    sql = ("select c.id as card_id, n.fields_json as fj from cards c "
           "join notes n on n.id = c.note_id "
           "where c.deleted_at is null and n.deleted_at is null "
           "and n.source_uid = '%s' order by n.created_at" % uid)
    try:
        d = api_call("/query", {"sql": sql})
        return [(r["card_id"], json.loads(r["fj"])) for r in d.get("rows", [])]
    except Exception as e:
        print("  (API 查卡不可用,退回只读读库:%s)" % str(e).splitlines()[0])
    con = sqlite3.connect("file:%s?mode=ro" % find_db().replace("\\", "/"), uri=True)
    try:
        return [(r[0], json.loads(r[1])) for r in con.execute(sql)]
    finally:
        con.close()


def relink_cards(cards, uid, apply_):
    """把已建卡片的 Extra 就地换成新版(默认=可点行链接)。

    只动 notes.fields_json 里的 Extra:Text 不变、source_text 不变、FSRS 调度不变,
    所以是幂等且无损的;不新建 note,也就不会再攒"孤儿 note"。
    """
    by_block = {c["block"]: c["Extra"] for c in cards}
    rows = card_rows(uid)
    print("库里属于本笔记的活跃卡:%d 张(本次按块号 %d 个对照)"
          % (len(rows), len(by_block)))
    same = nomatch = 0
    todo = []
    for cid, f in rows:
        # 降级路径(cards_by_uid)给的是整面 answer(渲染 Text + <br> + Extra),
        # /query 与 SQLite 路径给的是纯 Extra —— 用子串判定,两条路都对。
        hay = f.get("Answer") or f.get("Extra") or ""
        m = BLOCK_NO_RE.search(hay)
        if not m or int(m.group(1)) not in by_block:
            nomatch += 1
            continue
        want = by_block[int(m.group(1))]
        if want in hay:
            same += 1
            continue
        todo.append((cid, int(m.group(1)), hay, want))

    print("需改 %d 张 / 已是最新 %d 张 / 认不出块号跳过 %d 张"
          % (len(todo), same, nomatch))
    for cid, n, old, new in todo[:3]:
        print("   第 %-3d 块 旧: %s" % (n, old[:60]))
        print("             新: %s" % new[:110] + ("…" if len(new) > 110 else ""))
    if len(todo) > 3:
        print("   ...(其余 %d 张同形)" % (len(todo) - 3))

    if not todo or not apply_:
        if todo:
            print("\n[预览] 未写回。加 --apply 才真正更新(需 Obsidian 在跑 + Local API 开着)。")
        return
    ok = fail = 0
    for cid, n, old, new in todo:
        try:
            api_call("/cards/%s/update" % cid, {"answer": new})
            ok += 1
        except RuntimeError as e:
            fail += 1
            print("   第 %d 块更新失败:%s" % (n, e))
    print("已更新 %d 张 / 失败 %d 张" % (ok, fail))
    if sql_query_ok():
        try:
            d = api_call("/query", {"sql":
                        "select count(*) as n from cards where deleted_at is null"})
            print("复核:库内活跃卡片数 =", d["rows"][0]["n"])
        except Exception:
            pass


# ---------- 主 ----------

def main():
    argv = sys.argv[1:]
    apply = "--apply" in argv
    prune = "--prune" in argv
    force = "--force" in argv
    use_sqlite = "--sqlite" in argv
    relink = "--relink" in argv
    use_source_text = "--no-source-text" not in argv
    strip_bold = "--keep-cloze-bold" not in argv
    use_hint = "--no-hint" not in argv
    wj = "--no-wj" not in argv
    # ⛔ 2026-10-12 广哥定：彻底走官方原生 ⇒ `==` 包裹默认**关闭**，
    #    开关语义随之翻转：`--cloze-mark` 才是开启（旧开关 `--no-cloze-mark` 已作废）。
    mark = "--cloze-mark" in argv
    if mark and not wj:
        # 实测（markdown-it）：`**==…==` 的 `**` 后面紧跟 `=`（Unicode 标点），
        # 夹在文字中间时**开不了** → 星号字面显示。mark 与 WJ 是绑定的。
        WARN.append("`--no-wj` 与 `==` 包裹冲突（`**` 后紧跟 `=` 是标点，开不了），"
                    "已自动关闭 == 包裹")
        mark = False
    url_extra = "--plain-extra" not in argv
    anchor_on = "--no-anchor" not in argv
    limit = 20
    global MERGE_INDENT
    MERGE_INDENT = "--no-indent-merge" not in argv
    if not MERGE_INDENT:
        print("缩进归属: 已关闭(--no-indent-merge),缩进行各自独立成块")
    for a in argv:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        raise SystemExit(__doc__)
    path = paths[0]

    # v2.5.0 起 Local API 要鉴权:非 sqlite 路线先探一次活。
    # 401(token 缺失/不对)直接停 —— 静默降级只会让人以为是"没建卡";
    # 单纯的连不上(Obsidian 没开)只警告,预览模式本来就允许退回只读读库。
    if not use_sqlite:
        try:
            st = api_call("/status", timeout=5)
            print("Local API 在线:", json.dumps(st, ensure_ascii=False)[:120])
        except RuntimeError as e:
            msg = str(e)
            if "401" in msg or "token" in msg:
                raise SystemExit(msg)
            print("  (Local API 未连上,本次按只读读库预览:%s)" % msg.splitlines()[0])

    if not os.path.isabs(path):
        path = os.path.join(VAULT, path)
    if not os.path.exists(path):
        raise SystemExit("文件不存在: %s" % path)

    text = open(path, encoding="utf-8").read()
    lines = text.split("\n")
    base = os.path.splitext(os.path.basename(path))[0]
    rel_path = os.path.relpath(path, VAULT).replace("\\", "/")

    uid = read_uid(text)
    uid_new = uid is None
    if uid_new:
        uid = gen_uid()

    blocks = build_blocks(lines)
    cards = block_cards(lines, blocks, base, rel_path,
                        url_extra, anchor_on, use_source_text, strip_bold, use_hint, wj, mark)

    route = "直接写 SQLite" if use_sqlite else "插件 Local API(端口 %d)" % api_port()
    print("文件:", rel_path)
    print("flashcard_uid:", uid, "(新生成,尚未写入)" if uid_new else "(已存在于 frontmatter)")
    print("知识块(含高亮):%d 个 → 拟建卡 %d 张" % (len(blocks), len(cards)))
    print("写入路线:", route, "| source_text:", "写入(可跳回原文)" if use_source_text else "不写",
          "| 挖空内加粗:", "已清除(推荐)" if strip_bold else "保留原文")
    print("卡面 Extra:", "可点行链接" + ("(带 anchor 自愈)" if anchor_on else "(不带 anchor)")
          if url_extra else "纯文字", "| vault id:", vault_id() or "(读不到,已省略)")
    _n_hint = sum(c.get("hints", 0) for c in cards)
    _orph = [(c["block"], x) for c in cards for x in (c.get("orphan") or [])]
    print("行内提问 %%…%%:%s 绑定 %d 处 / 未归属(不生效,卡面原样保留) %d 处"
          % (" 已用 --no-hint 关闭 |" if not use_hint else "", _n_hint, len(_orph)))
    for _b, _x in _orph[:5]:
        print("    [块%-3d] %s" % (_b, _x[:70].replace("\n", " ⏎ ")))
    if len(_orph) > 5:
        print("    ...(其余 %d 处省略)" % (len(_orph) - 5))
    if WARN:
        for _w in dict.fromkeys(WARN):
            print("  ⚠ %s" % _w)
    print()

    if relink:
        print("== --relink:只改已建卡片的 Extra,不新建卡 ==")
        relink_cards(cards, uid, apply)
        return

    for c in cards[:limit]:
        t = c["Text"].replace("\n", " ⏎ ")
        print("  [块%-3d L%-4d] %s" % (c["block"], c["line"], t[:110]))
        if len(t) > 110:
            print("                  ...%s" % t[-40:])
        if url_extra and c["block"] <= 2:
            print("        Extra → %s" % c["Extra"])
    if len(cards) > limit:
        print("  ...(其余 %d 条省略, 用 --limit=N 调整)" % (len(cards) - limit))

    if not apply:
        print()
        print("[预览] 未做任何写入。确认无误后加 --apply。")
        return

    if use_sqlite and obsidian_running() and not force:
        print()
        print("!! 旧路线(SQLite 直写)要求完全退出 Obsidian:插件的内存数据会在 flush 时覆盖写入。")
        print("!! 建议改用默认的 Local API 路线(无需退出);确有把握可加 --force。")
        raise SystemExit(2)

    if uid_new:
        new_text, changed = set_uid(text, uid)
        if changed:
            open(path, "w", encoding="utf-8", newline="").write(new_text)
            print("已为笔记写入 frontmatter:", UID_FIELD + ":", uid)
    print("(frontmatter 若刚写入,等 Obsidian 索引进完再建卡更稳)")

    if use_sqlite:
        apply_cards_sqlite(cards, uid, find_db(), prune)
    else:
        apply_cards_api(cards, uid)


if __name__ == "__main__":
    main()
