// 离线测试：TR跳原图.js（truerecall跳原图.js）
// 只验纯函数 —— 「按图名反推 PDF + 页」「在源笔记里找 PDF 嵌入行」「行文本取渲染态别名」，
// 以及原有「找图片行」的口径没被改坏。
// 跑法：node test_tr_img_jump.js
"use strict";

const SCRIPT = process.env.TR_IMG_JUMP_SCRIPT || "<vault>\\Scripts\\truerecall跳原图.js";

let pass = 0, fail = 0;
const ok = (cond, name, extra) => {
    if (cond) { pass++; console.log("  PASS  " + name); }
    else { fail++; console.log("  FAIL  " + name + (extra ? "  → " + extra : "")); }
};

const PDF = "最后一遍疯狂刷题-科目一单选题.pdf";
const PNG = "images/最后一遍疯狂刷题-科目一单选题-p68.png";
const IMG = "images/皮亚杰认知发展四阶段对比.png";

// 一份贴近真实的源笔记：第 4 行是 PDF 嵌入块，第 6 行是普通图片
const NOTE = [
    "---",
    "flashcard_uid: 27ed00f3",
    "---",
    "![[最后一遍疯狂刷题-科目一单选题.pdf#page=68|最后一遍疯狂刷题-科目一单选题, p.68]]",
    "",
    "![[images/皮亚杰认知发展四阶段对比.png]]",
].join("\n");

async function main() {
    globalThis.__TR_IMG_JUMP_TEST = 1;          // 只暴露纯函数即返回，不注册观察器
    const mod = require(SCRIPT);                // eslint-disable-line
    await mod({});
    const T = globalThis.__trImgJump && globalThis.__trImgJump._test;
    ok(!!T, "暴露了 _test 调试口");
    ok(globalThis.__trImgJump.version === "2026-09-15.4",
       "版本号 " + (globalThis.__trImgJump && globalThis.__trImgJump.version));
    if (!T) { console.log("\n================ " + pass + " PASS / " + fail + " FAIL ================"); process.exit(1); }

    console.log("\n[1] 图名反推：<pdf基名>-pN.png → {stem, page}");
    const a = T.pdfFromPngName(PNG);
    ok(!!a && a.stem === "最后一遍疯狂刷题-科目一单选题" && a.page === 68,
       "常规命名 → stem/page", JSON.stringify(a));
    ok(T.pdfFromPngName("images/皮亚杰认知发展四阶段对比.png") === null, "普通图片 → null");
    ok(T.pdfFromPngName("images/x-p0.png") === null, "p0 不算（页码从 1 起）");
    ok(T.pdfFromPngName("images/x.pdf-p12.PNG").page === 12, "大小写与扩展名不敏感");
    ok(T.pdfFromPngName("images/a-p1-p9.png").page === 9, "多段 -pN 取最后一段（贪心）");
    ok(T.pdfFromPngName("") === null, "空路径 → null");
    ok(T.pdfFromPngName("images/最后一遍疯狂刷题-科目一单选题-p68.png").stem === "最后一遍疯狂刷题-科目一单选题",
       "stem 里的中文原样保留");

    console.log("\n[2] 行里抠页码");
    ok(T.pageInLine("![[a.pdf#page=68|x, p.68]]") === 68, "#page=68 → 68");
    ok(T.pageInLine("![[a.pdf]]") === 0, "没写页码 → 0");
    ok(T.pageInLine("") === 0, "空行 → 0");

    console.log("\n[3] 源笔记里找「PDF 嵌入行」");
    const hit = T.findPdfEmbedLine(NOTE, PDF, 68);
    ok(!!hit && hit.line === 4, "页码一致的嵌入行 → 第 4 行", JSON.stringify(hit));
    ok(T.findPdfEmbedLine(NOTE, PDF, 12) === null, "页码对不上、且该行写了别的页码 → null（不猜行）");
    ok(T.findPdfEmbedLine(NOTE, "别的.pdf", 68) === null, "没有这个 PDF → null");
    const NOTE2 = "看这个 [[" + PDF + "]] 吧";
    ok(T.findPdfEmbedLine(NOTE2, PDF, 68).line === 1, "没写 #page 的引用行 → 作备选命中");
    ok(T.findPdfEmbedLine(NOTE2, PDF, 68).text === "看这个 [[" + PDF + "]] 吧", "命中行原文一并返回");

    console.log("\n[4] 行原文 → 渲染态别名（给按行文本对齐用）");
    ok(T.sourceNeedleFor("![[a.pdf#page=68|最后一遍疯狂刷题-科目一单选题, p.68]]") === "最后一遍疯狂刷题-科目一单选题, p.68",
       "取 | 之后的别名", T.sourceNeedleFor("![[a.pdf#page=68|最后一遍疯狂刷题-科目一单选题, p.68]]"));
    ok(T.sourceNeedleFor("![[images/a.png]]") === "images/a.png", "没别名 → 取链接目标");
    ok(T.sourceNeedleFor("普通文本") === "普通文本", "不是链接 → 原样");

    console.log("\n[5] 回归：原有「找图片行」口径没被改坏");
    const ih = T.findImageLine(NOTE, IMG);
    ok(!!ih && ih.line === 6, "普通图片仍在第 6 行", JSON.stringify(ih));
    ok(T.findImageLine(NOTE, PNG) === null,
       "PDF 生成的 png 在笔记里没有引用 → 找不到行（这正是要回退到 PDF 反推的场景）");
    ok(T.findImageLine("前言 ![[images/a.png|300]] 后语", "images/a.png").line === 1, "带 |300 也算");

    console.log("\n================ " + pass + " PASS / " + fail + " FAIL ================");
    process.exit(fail ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(1); });
