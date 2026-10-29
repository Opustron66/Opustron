import React, { useState, useEffect, useMemo } from "react";
import Timeline from "./components/Timeline";
import EntityCard from "./components/EntityCard";
import ChatPanel from "./components/ChatPanel";
import EgressLog from "./components/EgressLog";
import DateDiff from "./components/DateDiff";
import Icon from "./components/Icon";
import ContextGuide from "./components/ContextGuide";
import { getEntities, getFacts, getSpan, getConfig, isTrueAt } from "./services/api";
import { formatDay } from "./services/memoryView";
import "./styles.css";

const INITIAL = { source: 'loading', facts: [], entities: [] };
const day = (iso) => new Date(`${iso.slice(0, 10)}T00:00:00Z`);
const filters = [['all', 'Everything'], ['owns', 'Ownership'], ['deadline', 'Dates & deadlines'], ['history', 'Past facts']];

function mentionedEntities(facts, named) {
  const mentions = new Map();
  facts.forEach((f) => {
    const names = new Set([f.subject]);
    if (named.has(f.object)) names.add(f.object);
    names.forEach((name) => mentions.set(name, (mentions.get(name) || 0) + 1));
  });
  return mentions;
}

async function loadMemory(signal) {
  const [facts, entities, span, config] = await Promise.all([
    getFacts({ signal }), getEntities({ signal }), getSpan({ signal }), getConfig({ signal }),
  ]);
  const claims = facts.filter((f) => (!f.kind || f.kind === 'claim') && f.subject && f.object);
  if (!claims.length || !span.start || !span.end) return { source: 'empty', facts: [], entities: [], config };
  // The reading period comes from the source documents, not a malformed extracted date.
  return { source: 'live', facts: claims, entities, config,
    start: day(config.corpus_start || span.start), end: day(config.corpus_end || span.end) };
}

function Brand() {
  return <div className="app-logo"><span className="brand-symbol"><Icon name="memory" size={23} /></span><span className="app-title">Chronicle<span className="brand-dot">.</span></span></div>;
}

function initialTheme() {
  try { return localStorage.getItem('chronicle.theme') === 'light' ? 'light' : 'dark'; } catch { return 'dark'; }
}

export default function App() {
  const [memory, setMemory] = useState(INITIAL);
  const [connecting, setConnecting] = useState(true);
  const [reload, setReload] = useState(0);
  const [asOf, setAsOf] = useState(new Date('2026-05-10'));
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [selected, setSelected] = useState(null);
  const [view, setView] = useState('memory');
  const [visible, setVisible] = useState(60);
  const [theme, setTheme] = useState(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('chronicle.theme', theme); } catch {}
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    let retryTimer, controller, timeout;
    async function attempt(number = 0) {
      if (cancelled) return;
      setConnecting(true);
      controller = new AbortController();
      timeout = setTimeout(() => controller.abort(), 20000);
      try {
        const loaded = await loadMemory(controller.signal);
        if (cancelled) return;
        setMemory(loaded);
        if (loaded.source === 'live') setAsOf(loaded.end);
      } catch {
        if (cancelled) return;
        setMemory((previous) => previous.source === 'live' ? previous : { ...INITIAL, source: 'error' });
        if (number < 3) retryTimer = setTimeout(() => attempt(number + 1), [2000, 5000, 10000][number]);
      } finally {
        clearTimeout(timeout);
        controller.abort();
        if (!cancelled) setConnecting(false);
      }
    }
    attempt();
    return () => { cancelled = true; clearTimeout(retryTimer); clearTimeout(timeout); controller?.abort(); };
  }, [reload]);

  const { facts, entities } = memory;
  const named = useMemo(() => new Map(entities.map((e) => [e.name, e])), [entities]);
  const entityCount = useMemo(() => mentionedEntities(facts, named).size, [facts, named]);
  const filteredFacts = useMemo(() => facts.filter((f) => filter === 'owns' ? ['owns', 'leads', 'manages', 'maintains'].includes(f.predicate)
    : filter === 'deadline' ? ['deadline', 'due', 'scheduled_for'].includes(f.predicate)
    : filter === 'history' ? f.valid_to && new Date(f.valid_to) <= asOf : true), [facts, filter, asOf]);
  const cards = useMemo(() => {
    const mentions = mentionedEntities(filteredFacts, named);
    return [...mentions.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({
      ...(named.get(name) || { entity_id: name, name, entity_type: 'unknown' }), count,
    }));
  }, [filteredFacts, named]);
  const shown = cards.filter((e) => e.name.toLowerCase().includes(query.trim().toLowerCase()));
  const current = shown.find((e) => e.name === selected) || shown[0];
  const activeCount = facts.filter((f) => isTrueAt(f, asOf)).length;
  const sourceCount = memory.config?.document_count || new Set(facts.map((f) => f.doc_id).filter(Boolean)).size;
  const explore = (key) => { setFilter(key); setQuery(''); setSelected(null); setView('memory'); };

  return <div className="app">
    <header className="app-header"><div className="header-inner"><Brand /><span className="app-tagline">A little context. A longer memory.</span><div className="app-header-right">
      <ContextGuide />
      <span className={`app-corpus-label source-${memory.source}`}><i />{connecting ? 'Connecting to memory' : memory.source === 'live' ? 'Live memory' : memory.source === 'empty' ? 'Waiting for memory' : 'Memory unavailable'}</span>
      <button className="icon-button theme-toggle" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
    </div></div></header>

    <main className="workspace">
      <section className="workspace-intro"><div><span className="eyebrow">YOUR MEMORY WORKSPACE</span><h1>Connect the dots.<br className="mobile-break" /> Across time.</h1><p>Find the people, decisions, and details. See how the story changed.</p></div><div className="workspace-caption"><Icon name="shield" /><span>Source-backed memory<br /><strong>Every fact has a story.</strong></span></div></section>
      {['loading', 'error'].includes(memory.source) ? <section className="empty-workspace connection-state" aria-live="polite" aria-busy={connecting}>
        <Icon name="memory" size={40} /><h2>{connecting ? 'Connecting to saved memory…' : 'Saved memory is temporarily unavailable.'}</h2>
        <p>{connecting ? 'Waiting for the service to respond. No sample facts are shown.' : 'A memory request failed. This does not mean your corpus was deleted. We retry briefly; you can also reconnect below.'}</p>
        <button className="text-button" onClick={() => setReload((value) => value + 1)} disabled={connecting}>Retry connection</button>
      </section> : memory.source === 'empty' ? <section className="empty-workspace"><Icon name="memory" size={40} /><h2>Your memory starts here.</h2><p>The service is connected but has no facts yet. Once the saved dataset is added, people, projects, and their history will appear here.</p></section> : <>
        <section className="overview-strip" aria-label="Memory overview">
          <div><span className="stat-icon"><Icon name="folder" /></span><span><strong>{sourceCount.toLocaleString()}</strong><small>Source documents</small></span></div>
          <div><span className="stat-icon"><Icon name="memory" /></span><span><strong>{facts.length.toLocaleString()}</strong><small>Remembered facts</small></span></div>
          <div><span className="stat-icon"><Icon name="person" /></span><span><strong>{entityCount.toLocaleString()}</strong><small>People & things</small></span></div>
          <div className="overview-period"><span className="eyebrow">READING PERIOD</span><strong>{formatDay(memory.start)} <span>—</span> {formatDay(memory.end)}</strong></div>
        </section>
        <section className="app-timeline-section"><Timeline startDate={memory.start} endDate={memory.end} value={asOf} onChange={setAsOf} facts={facts} /><div className="timeline-caption"><span><i />{activeCount.toLocaleString()} facts true on this day</span><span>Move through time. The evidence stays.</span></div></section>

        <div className="workspace-tabs" role="tablist" aria-label="Workspace view"><button role="tab" aria-selected={view === 'memory'} onClick={() => setView('memory')}><Icon name="memory" />Memory explorer</button><button role="tab" aria-selected={view === 'compare'} onClick={() => setView('compare')}><Icon name="compare" />Compare dates</button></div>
        {view === 'compare' ? <DateDiff key={`${memory.source}-${memory.start}`} facts={facts} startDate={memory.start} endDate={memory.end} /> : <div className="app-body">
          <aside className="app-sidebar" aria-label="Memory browser"><div className="browser-heading"><h2>People & things</h2><span className="count-pill">{shown.length}</span></div>
            <label className="entity-search"><Icon name="search" size={16} /><input type="search" aria-label="Search entities" placeholder="Find a person or project…" value={query} onChange={(e) => { setQuery(e.target.value); setVisible(60); }} /></label>
            <select className="entity-filter" aria-label="Filter memory" value={filter} onChange={(e) => explore(e.target.value)}>{filters.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
            <div className="entity-list">{shown.slice(0, visible).map((entity) => <button className={`entity-option ${current?.name === entity.name ? 'selected' : ''}`} key={entity.entity_id} onClick={() => setSelected(entity.name)} aria-pressed={current?.name === entity.name}><span className={`entity-avatar ${entity.entity_type === 'person' ? 'is-person' : ''}`}><Icon name={entity.entity_type === 'person' ? 'person' : 'folder'} size={16} /></span><span className="entity-option-copy"><strong>{entity.name}</strong><small>{entity.count} {entity.count === 1 ? 'fact' : 'facts'}</small></span><Icon name="chevron" size={14} /></button>)}
              {!shown.length && <p className="empty-note">No matches. Try another name or filter.</p>}
              {shown.length > visible && <button className="text-button" onClick={() => setVisible(visible + 60)}>Show more ({shown.length - visible})</button>}
            </div>
          </aside>
          <section className="memory-detail" aria-label="Selected memory"><div className="detail-eyebrow"><span className="eyebrow">THE DETAILS</span><span className="detail-date"><Icon name="clock" size={13} />{formatDay(asOf)}</span></div>
            {current ? <EntityCard key={current.name} entity={current} allFacts={filteredFacts} asOf={asOf} /> : <div className="detail-empty"><Icon name="search" size={30} /><h3>A little exploring goes a long way.</h3><p>Choose a person or project to see their facts and sources.</p></div>}
          </section>
          <section className="app-main"><ChatPanel facts={facts} asOf={asOf} enabled={memory.source === 'live' && memory.config?.chat_enabled === true} onExplore={explore} /></section>
        </div>}
      </>}
      <footer className="app-footer"><EgressLog /></footer>
      <div className="workspace-footnote"><span>Chronicle · Memory with a sense of time.</span><span>{memory.source === 'live'
        ? memory.config?.chat_enabled === true ? 'Live chat · uses paid model calls' : 'Browse-only demo · chat disabled'
        : connecting ? 'Connecting to saved memory' : memory.source === 'empty' ? 'No saved memory loaded' : 'Saved memory unavailable'}</span></div>
    </main>
  </div>;
}
