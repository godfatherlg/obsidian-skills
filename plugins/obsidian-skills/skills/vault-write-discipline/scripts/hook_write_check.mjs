#!/usr/bin/env node
/**
 * vault-write-discipline hook
 * 触发: PostToolUse / PreToolUse, matcher = Write|Edit
 * 行为: 当写入/改动的 .md 位于 J:\OB vault 内时, 调用 verify_discipline.py --all 检查
 *   BLOCK_MODE=false(默认, 安全): 仅把违规项作为 systemMessage 回传, 永不拦截写入
 *   BLOCK_MODE=true(升级拦截用): 有 FAIL 时回传 decision:block, 阻止本次写入
 *
 * 输入: WorkBuddy 通过 stdin 注入 JSON { hook_event_name, tool_name, tool_input:{file_path,...} }
 * 输出: stdout 回 JSON。Claude Code 兼容协议: {} 放行; {decision:"block",systemMessage} 拦截
 */
import { spawnSync } from "node:child_process";

const PY = process.env.WB_PYTHON || "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe";
const VERIFY = "C:/Users/Administrator/.workbuddy/skills/vault-write-discipline/scripts/verify_discipline.py";
const VAULT = "j:/ob/";
const TEMP_DIR = "J:/OB/临时";
const BLOCK_MODE = process.env.VAULT_WRITE_BLOCK === "1";

function emit(obj) {
  process.stdout.write(JSON.stringify(obj));
  process.stdout.write("\n");
}

async function readStdin() {
  let data = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

async function main() {
  let raw = "";
  try { raw = await readStdin(); } catch {}
  let payload = {};
  try { payload = raw ? JSON.parse(raw) : {}; } catch {}

  const event = payload.hook_event_name || "";
  const toolName = payload.tool_name || "";
  const file = payload.tool_input && payload.tool_input.file_path ? payload.tool_input.file_path : "";

  // 只处理 vault 内的 .md 写入/编辑
  if (event && event !== "PostToolUse" && event !== "PreToolUse") return emit({});
  if (toolName !== "Write" && toolName !== "Edit") return emit({});
  if (!file) return emit({});
  const norm = file.replace(/\\/g, "/").toLowerCase();
  if (!norm.endsWith(".md")) return emit({});
  if (!norm.startsWith(VAULT)) return emit({});

  // 本次新增文本: Write 传 content(整篇), Edit 传 new_string(纯新增)。
  // 走 stdin 传 —— Windows 命令行上限约 32767 字符, 笔记文件常超限。
  const ti = payload.tool_input || {};
  const newText = toolName === "Edit" ? (ti.new_string || "") : (ti.content || "");

  let r;
  try {
    // 临时目录图片只判"最近 N 分钟内"新增的(默认 180 分钟, 覆盖一次任务时长),
    // 避免把用户自己放在临时目录的历史图片判成 FAIL 并诱导 AI 去删改用户文件。
    // 需要更长窗口时设环境变量 VAULT_TEMP_SINCE_MIN(分钟); 设为 0 等同于全扫。
    const sinceMin = process.env.VAULT_TEMP_SINCE_MIN || "180";
    const argv = [VERIFY, "--all", "--temp-dir", TEMP_DIR, "--since-min", sinceMin];
    if (newText) argv.push("--new-text-stdin", "--new-text-tool", toolName);
    argv.push(file);
    r = spawnSync(PY, argv, {
      encoding: "utf8", timeout: 60000,
      maxBuffer: 8 * 1024 * 1024,   // 默认 1MB, 长违规清单会被 ENOBUFS 截断
      input: newText || undefined,  // 只有带 --new-text-stdin 时 python 才读
    });
  } catch (e) {
    // 检查脚本自身异常: 绝不因此拦截用户写入, 但必须显式报出来(历史上静默失灵过)
    return emit({ systemMessage: "[vault-write-discipline] hook 自身异常: " +
                  (e && e.message ? e.message : String(e)) + " (检查 node/python 路径)" });
  }

  // spawnSync 不 throw: ENOENT 之类落在 r.error 上, 必须显式判定, 否则自动兜底静默失灵
  if (r.error) {
    return emit({ systemMessage: "[vault-write-discipline] hook 自身异常: " +
                  r.error.message + " (检查 node/python 路径)" });
  }

  const out = (r.stdout || "") + (r.stderr || "");
  // rc=0 但有 WARN 也要回显 —— 否则 WARN 级检查在自动路径下完全不可见
  if (r.status === 0 && !/\[!! /.test(out)) {
    return emit({}); // ALL PASS, 静默放行
  }

  // 提取违规/告警行(verify 用 [XX ] 标 FAIL, [!! ] 标 WARN, 后跟细节行)
  const allLines = out.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
  const picked = [];
  const failRe = /^\[XX |^\[!! /;
  for (let i = 0; i < allLines.length; i++) {
    if (failRe.test(allLines[i])) {
      picked.push(allLines[i]);
      if (i + 1 < allLines.length && !/^\[[A-Z!]{2} \]/.test(allLines[i + 1])) {
        picked.push(allLines[i + 1]);
        i++;
      }
    }
  }
  const msg =
    "[vault-write-discipline] 文件 " + file + " 未通过纪律检查:\n" + picked.join("\n");

  if (BLOCK_MODE) {
    return emit({ decision: "block", systemMessage: msg });
  }
  return emit({ systemMessage: msg });
}

main().catch(() => emit({}));
