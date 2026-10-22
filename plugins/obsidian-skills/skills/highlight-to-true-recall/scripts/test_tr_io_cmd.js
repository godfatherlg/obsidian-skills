// 离线测试：TR制作蒙板.js v5（truerecall制作蒙板.js）
// 目标：不启动 Obsidian 也能证明「右键图片 → 打开编辑器时图片已带上」这条链路
// 跑法：node test_io_cmd.js
"use strict";

const SCRIPT = process.env.TR_IO_SCRIPT || "<vault>\\Scripts\\truerecall制作蒙板.js";

let pass = 0, fail = 0;
const ok = (cond, name, extra) => {
    if (cond) { pass++; console.log("  PASS  " + name); }
    else { fail++; console.log("  FAIL  " + name + (extra ? "  → " + extra : "")); }
};

// ---------- mock DOM ----------
const listeners = {};
global.document = {
    addEventListener: (t, fn, cap) => { listeners[t] = fn; },
    removeEventListener: (t) => { delete listeners[t]; },
};

function el(tag, classes, attrs, parent) {
    const e = {
        tagName: tag,
        classList: (classes || []).slice(),
        isConnected: true,
        parentElement: parent || null,
        _img: null,
        getAttribute(k) { return attrs && attrs[k] != null ? attrs[k] : null; },
        querySelector(sel) {
            if (sel === "img") return e._img || null;
            return null;
        },
        closest(sel) {
            const parts = String(sel).split(",").map((s) => s.trim());
            let cur = e;
            while (cur) {
                for (const p of parts) {
                    if (p.charAt(0) === ".") {
                        if (cur.classList && cur.classList.indexOf(p.slice(1)) >= 0) return cur;
                    } else if (cur.tagName && cur.tagName.toLowerCase() === p.toLowerCase()) {
                        return cur;
                    }
                }
                cur = cur.parentElement;
            }
            return null;
        },
        contains() { return false; },
    };
    return e;
}

// ---------- mock app ----------
const IMG = "images/皮亚杰认知发展四阶段对比.png";
const PDF_LINK = "最后一遍疯狂刷题-科目一单选题.pdf";                       // 链接里写的 linkpath（裸文件名）
const PDF_VPATH = "2026上数学教资/冲刺班/科一/最后一遍疯狂刷题-科目一单选题.pdf"; // 库内真实路径

function mkApp() {
    const handlers = {};
    const calls = [];
    const fms = {
        _uid: "",
        pending: null,
        async getSourceNoteUid() { return this._uid; },
        generateUid() { return "uid-generated-1"; },
        async setSourceNoteUid(p, u) { this._uid = u; },
    };
    const tr = {
        flashcardManager: { getFrontmatterService: () => fms },
        openImageOcclusionEditor(args) { calls.push({ op: "openEditor", args }); return Promise.resolve({}); },
        openImageOcclusionEditorForActiveNote() { calls.push({ op: "openForActiveNote" }); return Promise.resolve({}); },
    };
    const app = {
        vault: {
            adapter: {
                append: async () => {},
                read: async () => "",
                write: async () => {},
            },
            getFiles: () => [{ path: PDF_VPATH, name: PDF_LINK, extension: "pdf" }],
            getAbstractFileByPath: (p) => (p === PDF_VPATH ? { path: PDF_VPATH, extension: "pdf" } : null),
        },
        commands: {
            _c: {},
            addCommand(c) { this._c[c.id] = c; },
            removeCommand(id) { delete this._c[id]; },
            findCommand(id) { return this._c[id]; },
        },
        workspace: {
            on(evt, fn) { const ref = { evt, fn }; handlers[evt] = ref; return ref; },
            offref(ref) { if (ref && handlers[ref.evt] === ref) delete handlers[ref.evt]; },
            getActiveFile() { return { path: "临时/皮亚杰感知运动阶段汇总 1.md", extension: "md" }; },
        },
        metadataCache: {
            getFirstLinkpathDest(link) {
                if (link === IMG) return { path: IMG, name: "皮亚杰认知发展四阶段对比.png", extension: "png" };
                if (link === PDF_LINK) return { path: PDF_VPATH, name: PDF_LINK, extension: "pdf" };
                return null;
            },
        },
        plugins: { plugins: { "true-recall": tr } },
    };
    return { app, handlers, calls, fms, tr };
}

// 触发菜单：把 addItem 收到的项抓出来并点它
function fireMenu(fn, ...args) {
    const items = [];
    const menu = {
        addItem(cb) {
            const item = {
                title: "",
                setTitle(t) { item.title = t; return item; },
                setIcon() { return item; },
                onClick(h) { item._click = h; return item; },
            };
            cb(item);
            items.push(item);
        },
    };
    fn(menu, ...args);
    return items;
}

async function main() {
    require(SCRIPT);           // eslint-disable-line
    const mod = require(SCRIPT);
    const { app, handlers, calls, fms } = mkApp();
    await mod({ app });

    const T = globalThis.__trIoMakeCard._test;
    ok(!!T, "暴露了 _test 调试口");

    // ---------- 1. 纯函数 ----------
    console.log("\n[1] 纯函数：路径解析");
    ok(T.matchPath("xx ![" + "[images/a.png]] yy") === "images/a.png", "wiki 嵌入");
    ok(T.matchPath("![[images/a.png|300]]") === "images/a.png", "wiki 嵌入带 |300");
    ok(T.matchPath("![](images/b.jpeg)") === "images/b.jpeg", "markdown 嵌入");
    ok(T.matchPath("![](images/b.png#abc)") === "images/b.png", "markdown 嵌入带 #锚");
    ok(T.matchPath("普通文字没有图片") === "", "无图片→空");
    ok(T.cleanPath("app://local/x.png") === "", "app:// 绝对 URL 被剔");
    ok(T.cleanPath("images/%E7%9A%AE.png") === "images/皮.png", "URL 解码");

    const embed = el("DIV", ["internal-embed", "image-embed"], { src: IMG });
    const img = el("IMG", [], {}, embed);
    embed._img = img;
    ok(T.pathFromEl(img) === IMG, "pathFromEl：img 向上找到 .internal-embed[src]");
    ok(T.isImageTarget(img) === true, "isImageTarget：img 命中");
    ok(T.pathFromEl(el("DIV", ["cm-line"], {})) === "", "pathFromEl：普通 div → 空");

    const editor = {
        getSelection: () => "",
        getCursor: () => ({ line: 3 }),
        getLine: (n) => (n === 3 ? "![[images/皮亚杰认知发展四阶段对比.png]]" : ""),
    };
    ok(T.pathFromEditor(editor) === IMG, "pathFromEditor：光标行正则");

    // ---------- 2. file-menu 通道（右键渲染图） ----------
    console.log("\n[2] file-menu 通道：右键渲染图 → 带图打开");
    calls.length = 0;
    const before = T.getCtx();
    T.setCtx({ path: "", el: null });           // 清掉 DOM 线索，只靠 explicit
    let items = fireMenu(handlers["file-menu"].fn, { path: IMG, extension: "png" }, "link-context-menu", null);
    ok(items.length === 1 && items[0].title === "制作图片蒙板", "出现菜单项");
    items[0]._click();
    await new Promise((r) => setTimeout(r, 30));
    ok(calls.length === 1 && calls[0].op === "openEditor", "调用 openImageOcclusionEditor（不是空白入口）", JSON.stringify(calls));
    if (calls[0] && calls[0].op === "openEditor") {
        ok(calls[0].args.mode === "add", "mode=add");
        ok(calls[0].args.imagePath === IMG, "imagePath 正确", JSON.stringify(calls[0].args));
        ok(calls[0].args.sourceUid === "uid-generated-1", "自动补 sourceUid", JSON.stringify(calls[0].args));
    }
    ok(fms._uid === "uid-generated-1", "sourceUid 已写回笔记 frontmatter");

    // 非 link 来源（左侧文件列表）不出现
    calls.length = 0;
    items = fireMenu(handlers["file-menu"].fn, { path: IMG, extension: "png" }, "file-explorer-context-menu", null);
    ok(items.length === 0, "左侧文件列表右键不出现（source 不同）");
    // 非图片文件不出现
    items = fireMenu(handlers["file-menu"].fn, { path: "a.md", extension: "md" }, "link-context-menu", null);
    ok(items.length === 0, "非图片文件不出现");

    // file 为字符串路径时也认（个别版本/路径不传 TFile）
    calls.length = 0;
    items = fireMenu(handlers["file-menu"].fn, IMG, "link-context-menu", null);
    ok(items.length === 1, "file 是字符串也能出菜单项");
    items[0]._click();
    await new Promise((r) => setTimeout(r, 30));
    ok(calls.length === 1 && calls[0].args && calls[0].args.imagePath === IMG,
       "字符串 file 也带图", JSON.stringify(calls));

    T.setCtx(before);

    // ---------- 3. file-menu 但 file 为空 → 靠 DOM / 行文本兜底 ----------
    console.log("\n[3] file-menu 无 file 参数 → DOM 兜底");
    calls.length = 0;
    T.setCtx({ path: IMG, el: img });
    items = fireMenu(handlers["file-menu"].fn, null, "link-context-menu", null);
    ok(items.length === 0, "file 为空时菜单项不出现（isImageFile 假）→ 走不到，符合预期");

    // ---------- 4. editor-menu 通道（右键源码行） ----------
    console.log("\n[4] editor-menu 通道：右键 ![[…]] 文本 → 带图打开");
    calls.length = 0;
    T.setCtx({ path: "", el: null, t: Date.now(), isImage: false });
    items = fireMenu(handlers["editor-menu"].fn, editor, null);
    ok(items.length === 1, "出现菜单项");
    items[0]._click();
    await new Promise((r) => setTimeout(r, 30));
    ok(calls.length === 1 && calls[0].op === "openEditor"
       && calls[0].args.imagePath === IMG, "走 editor 行正则带图", JSON.stringify(calls));

    // ---------- 5. 命令面板（无线索）→ 退回空白编辑器入口 ----------
    console.log("\n[5] 命令面板：无图片线索 → 退回空白入口（旧行为）");
    calls.length = 0;
    T.setCtx({ path: "", el: null });
    const cmd = app.commands.findCommand("tr-io-tools:create-image-occlusion-card");
    ok(!!cmd, "命令在注册表");
    cmd.callback();
    await new Promise((r) => setTimeout(r, 30));
    ok(calls.length === 1 && calls[0].op === "openForActiveNote", "退回 openImageOcclusionEditorForActiveNote", JSON.stringify(calls));

    // ---------- 6. 热更新不叠加 ----------
    console.log("\n[6] 重跑脚本 = 上一代卸载");
    const app2 = mkApp();
    await mod({ app: app2.app });
    ok(globalThis.__trIoMakeCard.version === "2026-09-15.9", "版本号 " + globalThis.__trIoMakeCard.version);
    ok(!!app2.handlers["file-menu"] && !!app2.handlers["editor-menu"], "新实例两条监听都在");

    console.log("\n[7] PDF 嵌入（![[x.pdf#page=N]]）：抠页码 + 文件类型判定");
    ok(T.pdfPageFromText("x.pdf#page=68|x, p.68") === 68, "wiki 链接文本 → 68", String(T.pdfPageFromText("x.pdf#page=68|x, p.68")));
    ok(T.pdfPageFromText("[[a.pdf#page=12]]") === 12, "带 [[ ]] → 12");
    ok(T.pdfPageFromText("x.pdf") === 0, "没有 #page → 0");
    ok(T.pdfPageFromText("") === 0, "空文本 → 0");
    ok(T.isPdfFile({ path: "a/b.pdf" }) === true, "isPdfFile 认 .pdf");
    ok(T.isPdfFile({ path: "a/b.png" }) === false, "isPdfFile 不认 .png");
    ok(T.isPdfFile({ path: "a/b.pdfx" }) === false, "isPdfFile 不认 .pdfx");
    ok(T.isPdfFile("a/b.pdf") === true, "file 传字符串也认");
    T.setCtx({ el: null });
    const none = T.pickPdfPage({});
    ok(none.page === 0 && none.from === "none", "无 DOM、无 editor → 拿不到页码（应中止不渲染）");
    ok(T.pickPdfPage({ editor: { getSelection: () => "[[a.pdf#page=7]]" } }).page === 7, "editor 选中文本 → 7");

    console.log("\n[8] 嵌入 PDF 的路径解析（.7 修的 bug：linkpath ≠ vault 路径）");
    ok(T.toAbsPath("images/a.png") === "<vault>\\images\\a.png", "toAbsPath：正斜杠", T.toAbsPath("images/a.png"));
    ok(T.toAbsPath("2026上数学教资/冲刺班/科一/x.pdf") === "<vault>\\2026上数学教资\\冲刺班\\科一\\x.pdf",
       "toAbsPath：中文多级目录", T.toAbsPath("2026上数学教资/冲刺班/科一/x.pdf"));
    ok(T.toAbsPath("a\\b/c.png") === "<vault>\\a\\b\\c.png", "toAbsPath：混用分隔符归一", T.toAbsPath("a\\b/c.png"));
    ok(T.resolveVaultFile(PDF_LINK, "临时/x.md").path === PDF_VPATH,
       "resolveVaultFile：裸文件名经元数据缓存解析成真实路径", JSON.stringify(T.resolveVaultFile(PDF_LINK, "临时/x.md")));
    ok(T.resolveVaultFile("不存在.pdf", "临时/x.md") === null, "resolveVaultFile：解析不到返回 null（应中止不渲染）");
    ok(T.resolveVaultFile("", "临时/x.md") === null, "resolveVaultFile：空 linkpath → null");
    // 元数据缓存失灵时按文件名兜底
    const bak = app.metadataCache.getFirstLinkpathDest;
    app.metadataCache.getFirstLinkpathDest = () => null;
    ok(T.resolveVaultFile(PDF_LINK, "临时/x.md").path === PDF_VPATH, "兜底：getFiles() 按文件名唯一匹配");
    app.metadataCache.getFirstLinkpathDest = bak;

    console.log("\n[9] 页号取「右键落点那一页」（.8 修「常常落到上面一页」）");
    // 纸盒式 DOM stub：只实现用得到的 closest / getAttribute
    const pageBox = (n) => ({
        _n: String(n),
        getAttribute: (k) => (k === "data-page-number" ? String(n) : null),
        closest(sel) { return sel === "[data-page-number]" ? this : null; },
    });
    const insidePage = (n, tag) => {
        const box = pageBox(n);
        return {
            tagName: tag || "SPAN",
            getAttribute: () => null,
            closest(sel) { return sel === "[data-page-number]" ? box : null; },
        };
    };
    ok(T.pdfPageFromTarget(insidePage(66)) === 66, "点在第 66 页内容上 → 66",
       String(T.pdfPageFromTarget(insidePage(66))));
    ok(T.pdfPageFromTarget(pageBox(7)) === 7, "直接点在页方块上 → 7");
    ok(T.pdfPageFromTarget(insidePage(0)) === 0, "data-page-number=0 不认");
    ok(T.pdfPageFromTarget(null) === 0, "null → 0");
    ok(T.pdfPageFromTarget({ closest: () => null }) === 0, "不在任何页里 → 0");
    // 优先级：落点页 > 视图持久化状态（老 bug 就是被状态带偏的）
    T.setCtx({ el: insidePage(66) });
    const picked = T.pickPdfPage({ el: insidePage(66), editor: null });
    ok(picked.page === 66 && picked.from === "embed-dom-page",
       "嵌入块没写 #page= 时按「此刻显示的那页」取", JSON.stringify(picked));
    T.setCtx({ el: null });

    console.log("\n================ " + pass + " PASS / " + fail + " FAIL ================");
    process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
