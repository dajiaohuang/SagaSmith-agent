"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
type Campaign = { id: string; name: string; description: string };
type Character = { id: string; character_name: string; data: any; version: number };
type Message = { role: "player" | "dm"; text: string; details?: string };

async function call(path: string, options?: RequestInit) {
  const isForm = options?.body instanceof FormData;
  const response = await fetch(`${API}${path}`, {
    headers: { ...(isForm ? {} : { "Content-Type": "application/json" }), ...(options?.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

export default function Home() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignId, setCampaignId] = useState("campaign_001");
  const [character, setCharacter] = useState<Character | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    { role: "dm", text: "北境之门矗立在暮色中。守卫举起火把，审视着你。你要怎么做？" },
  ]);
  const [input, setInput] = useState("我喝一瓶治疗药水。");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("等待初始化");

  const hp = character?.data?.combat;
  const potions = character?.data?.inventory?.find((x: any) => x.item_id === "potion_healing")?.quantity ?? 0;
  const hpPercent = useMemo(() => hp ? Math.round((hp.current_hp / hp.max_hp) * 100) : 0, [hp]);

  async function refresh() {
    const nextCampaigns = await call("/campaigns");
    setCampaigns(nextCampaigns);
    const chosen = nextCampaigns.find((x: Campaign) => x.id === campaignId) || nextCampaigns[0];
    if (chosen) {
      setCampaignId(chosen.id);
      const chars = await call(`/campaigns/${chosen.id}/characters`);
      setCharacter(chars[0] || null);
    }
  }

  useEffect(() => { refresh().catch(() => setStatus("请先初始化示例数据")); }, []);

  async function bootstrap() {
    setBusy(true);
    try {
      await Promise.all([
        call("/demo/bootstrap", { method: "POST" }),
        call("/ingest/compendium", { method: "POST" }),
        call("/ingest/rules", { method: "POST" }),
      ]);
      await refresh();
      setStatus("示例战役、规则和图鉴已就绪");
    } catch (error) {
      setStatus(`初始化失败：${String(error)}`);
    } finally { setBusy(false); }
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!input.trim() || !character) return;
    const text = input.trim();
    setMessages((old) => [...old, { role: "player", text }]);
    setInput("");
    setBusy(true);
    try {
      let message = text;
      if (files.length) {
        const form = new FormData();
        files.forEach((file) => form.append("files", file));
        const parsed = await call("/parse/files", { method: "POST", body: form });
        if (parsed.content) message += `\n\n玩家同时发送了以下附件内容：\n${parsed.content}`;
      }
      const result = await call(`/chat/${campaignId}`, {
        method: "POST",
        body: JSON.stringify({ session_id: "session_001", character_id: character.id, message }),
      });
      const details = [
        ...(result.rolls || []).map((x: any) => `${x.formula} = ${x.total}`),
        ...(result.state_changes || []).map((x: any) => x.type),
      ].join(" · ");
      setMessages((old) => [...old, { role: "dm", text: result.narration, details }]);
      await refresh();
      setFiles([]);
      setStatus("行动已写入事件日志");
    } catch (error) {
      setMessages((old) => [...old, { role: "dm", text: `行动处理失败：${String(error)}` }]);
    } finally { setBusy(false); }
  }

  async function summarize() {
    const result = await call(`/campaigns/${campaignId}/summaries?session_id=session_001`, { method: "POST" });
    setMessages((old) => [...old, { role: "dm", text: "Session Summary", details: result.summary }]);
  }

  return (
    <main>
      <header>
        <div>
          <span className="eyebrow">LOCAL DUNGEON MASTER</span>
          <h1>暮色编年史</h1>
        </div>
        <div className="header-actions">
          <span className="status"><i />{status}</span>
          <button className="secondary" onClick={bootstrap} disabled={busy}>初始化示例数据</button>
        </div>
      </header>

      <section className="layout">
        <aside className="panel character-panel">
          <p className="label">当前角色</p>
          <h2>{character?.character_name || "尚未创建"}</h2>
          <p className="muted">Human Fighter · Level 3</p>
          <div className="portrait">A</div>
          <div className="stat-line"><span>生命值</span><strong>{hp?.current_hp ?? "-"}/{hp?.max_hp ?? "-"}</strong></div>
          <div className="hp-track"><span style={{ width: `${hpPercent}%` }} /></div>
          <div className="stats">
            <div><small>AC</small><strong>{character?.data?.combat?.armor_class ?? "-"}</strong></div>
            <div><small>药水</small><strong>{potions}</strong></div>
            <div><small>版本</small><strong>v{character?.version ?? "-"}</strong></div>
          </div>
          <div className="inventory">
            <p className="label">随身物品</p>
            {character?.data?.inventory?.map((item: any) => (
              <div className="item" key={item.item_id}><span>{item.name}</span><b>× {item.quantity}</b></div>
            )) || <p className="muted">初始化后显示</p>}
          </div>
        </aside>

        <section className="panel chat-panel">
          <div className="scene-head">
            <div><p className="label">当前场景</p><h2>{campaigns.find((x) => x.id === campaignId)?.name || "北境之门"}</h2></div>
            <button className="secondary" onClick={summarize} disabled={!character}>生成总结</button>
          </div>
          <div className="messages">
            {messages.map((message, index) => (
              <article className={message.role} key={index}>
                <span>{message.role === "dm" ? "DM" : character?.character_name || "YOU"}</span>
                <p>{message.text}</p>
                {message.details && <pre>{message.details}</pre>}
              </article>
            ))}
          </div>
          <form onSubmit={send}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="描述你的行动……" />
            <label className="file-button">
              附件{files.length ? ` ${files.length}` : ""}
              <input type="file" multiple onChange={(event) => setFiles(Array.from(event.target.files || []))} />
            </label>
            <button disabled={busy || !character}>{busy ? "裁定中…" : "行动"}</button>
          </form>
          {files.length > 0 && <div className="file-list">{files.map((file) => file.name).join(" · ")}</div>}
          <div className="quick">
            {["我喝一瓶治疗药水。", "我想说服守卫放我们进城。", "我进行一次长休。"].map((text) => (
              <button className="chip" key={text} onClick={() => setInput(text)}>{text}</button>
            ))}
          </div>
        </section>

        <aside className="panel ledger">
          <p className="label">DM 控制台</p>
          <h2>规则与记录</h2>
          <div className="rule-card">
            <small>CANONICAL STATE</small>
            <strong>PostgreSQL JSONB</strong>
            <p>角色状态由数据库管理，LLM 不能直接修改。</p>
          </div>
          <div className="rule-card">
            <small>RULE RETRIEVAL</small>
            <strong>SRD MVP</strong>
            <p>规则文本使用本地 BGE-M3 向量检索，并保留关键词降级。</p>
          </div>
          <div className="rule-card">
            <small>AUDIT TRAIL</small>
            <strong>Change Log + Events</strong>
            <p>所有状态变化和剧情推进均可追踪。</p>
          </div>
        </aside>
      </section>
    </main>
  );
}
