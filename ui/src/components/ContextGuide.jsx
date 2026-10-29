import React, { useRef, useState } from 'react';
import Icon from './Icon';

// Reference answers from NVIDIA's corpus_a/questions/answers.jsonl.
const QUESTIONS = [
  {
    kind: 'Find a person',
    context: 'Two people own different parts of Beacon’s evaluation work.',
    question: 'Who owns Beacon’s eval framework, and who owns the evaluator metric decision?',
    answer: 'Anya Volkov owns the framework. Jin Oh owns the metric decision.',
  },
  {
    kind: 'Check progress',
    context: 'Beacon is being released gradually.',
    question: 'What is Beacon’s current rollout progress, and what comes next?',
    answer: '50% has been reached. 75% is the next target; it has not happened yet.',
  },
  {
    kind: 'Understand a changed plan',
    context: 'Quillon’s launch was pushed back.',
    question: 'When was Quillon v2 originally meant to launch, what is the new date, and why?',
    answer: 'June 30 → July 14, 2026, to include stronger request-rate protections (rate-limit hardening).',
  },
  {
    kind: 'Check the latest news',
    context: 'The team is hiring an engineer.',
    question: 'Has the senior backend engineer candidate accepted, and when do they start?',
    answer: 'Yes. The candidate has accepted and starts on 8 June 2026.',
  },
  {
    kind: 'Look into the past',
    context: 'That hiring decision was not always settled.',
    question: 'As of 15 May 2026, had the senior backend engineer candidate accepted?',
    answer: 'No. The role was still at the offer stage; acceptance came later.',
  },
  {
    kind: 'Compare old and new',
    context: 'Processing messages became cheaper.',
    question: 'What was the earlier peak cost per message, and what is the latest cost?',
    answer: '0.71 cents at the earlier peak → 0.42 cents now. These are fictional company figures, not your chat charges.',
  },
  {
    kind: 'Check honesty',
    context: 'Ask about something that is not recorded.',
    question: 'What is Project Phoenix about, and who leads it?',
    answer: 'The corpus does not record that project. Chronicle should say it does not know, rather than invent a project or leader.',
  },
];

export default function ContextGuide() {
  const dialog = useRef(null);
  const [notice, setNotice] = useState('');

  function openGuide() {
    setNotice('');
    dialog.current.showModal();
    dialog.current.querySelector('.guide-content').scrollTop = 0;
  }

  function keepFocus(event) {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.current.querySelectorAll('button, summary, [href], [tabindex]')]
      .filter((element) => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length);
    const first = controls[0], last = controls.at(-1);
    if (!first) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  }

  async function copyQuestion(question, number) {
    try {
      await navigator.clipboard.writeText(question);
      setNotice(`Question ${number} copied. Paste it into Ask Chronicle when ready.`);
    } catch {
      setNotice('Copy is unavailable here. You can select and copy the question text instead.');
    }
  }

  return <>
    <button className="guide-trigger" aria-haspopup="dialog" onClick={openGuide}>
      <Icon name="help" size={16} /><span>Demo guide</span>
    </button>
    <dialog ref={dialog} className="context-guide" aria-labelledby="guide-title" aria-describedby="guide-intro" onKeyDown={keepFocus}>
      <header className="guide-header">
        <div><span className="eyebrow">NEW HERE? START HERE.</span><h2 id="guide-title">Meet the story behind the memory.</h2></div>
        <button className="icon-button" aria-label="Close demo guide" onClick={() => dialog.current.close()}><Icon name="close" /></button>
      </header>
      <div className="guide-content">
        <p id="guide-intro">Imagine joining a fictional software team. They’re building products, hiring people, and changing plans. Chronicle remembers their emails and team chats.</p>
        <div className="guide-setting"><span><strong>Corpus A</strong> · 425 documents</span><span>16 April–27 May 2026</span></div>
        <p className="guide-explainer">Atlas, Beacon, and Quillon are project names. You don’t need to know them already—the questions below introduce the important stories.</p>
        <section className="guide-start" aria-label="How to use the guide">
          <h3>Try it in three steps</h3>
          <ol><li>Set the <strong>Memory Time Machine to 27 May 2026</strong>.</li><li>Copy a question below and paste it into <strong>Ask Chronicle</strong>.</li><li>Compare the answer with the reference answer, then open <strong>Why?</strong> where available to check the evidence.</li></ol>
          <p>Reading this guide and copying questions is free. Sending a question in live chat uses the demo’s shared AI budget.</p>
        </section>
        <section className="guide-questions" aria-label="Guided questions">
          {QUESTIONS.map((item, index) => <article className="guide-question" key={item.kind}>
            <div className="guide-question-heading"><span className="guide-number">{index + 1}</span><div><h3>{item.kind}</h3><p>{item.context}</p></div></div>
            <p className="guide-prompt">{item.question}</p>
            <div className="guide-question-actions"><details><summary>Expected answer</summary><p>{item.answer}</p></details>
              <button className="guide-copy" aria-label={`Copy question ${index + 1}`} onClick={() => copyQuestion(item.question, index + 1)}>Copy question <Icon name="copy" size={14} /></button></div>
          </article>)}
        </section>
        <p className="guide-reference">These reference answers come from Corpus A’s published answer key. The questions use simpler wording; chat may phrase its answers differently. Plans are not completed events, and an earlier date can have a different answer.</p>
      </div>
      <footer className="guide-footer"><p role="status">{notice || 'Nothing is sent to chat until you submit a question yourself.'}</p><button className="guide-done" onClick={() => dialog.current.close()}>Got it</button></footer>
    </dialog>
  </>;
}
