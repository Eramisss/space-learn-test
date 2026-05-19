import { useState, useEffect, useCallback } from "react";

/* ═══════════════════════════════════════════════════
   SM-2 Algorithm (client-side for demo mode)
   ═══════════════════════════════════════════════════ */
function sm2(card, quality) {
  let { ef = 2.5, interval = 0, reps = 0 } = card;
  const newEf = Math.max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)));
  let newInterval, newReps;
  if (quality >= 3) {
    newReps = reps + 1;
    if (newReps === 1) newInterval = 1;
    else if (newReps === 2) newInterval = 6;
    else newInterval = Math.round(interval * newEf);
  } else {
    newReps = 0;
    newInterval = 1;
  }
  const nextReview = new Date();
  nextReview.setDate(nextReview.getDate() + newInterval);
  return { ef: Math.round(newEf * 100) / 100, interval: newInterval, reps: newReps, nextReview: nextReview.toISOString().split("T")[0] };
}

/* ═══════════════════════════════════════════════════
   Demo Data
   ═══════════════════════════════════════════════════ */
const DEMO_DECKS = [
  {
    id: 1, title: "Python — основы", description: "Базовые понятия языка Python", isPublic: false,
    cards: [
      { id: 1, front: "Что такое Python?", back: "Высокоуровневый интерпретируемый язык программирования общего назначения" },
      { id: 2, front: "Что такое PEP 8?", back: "Руководство по стилю написания кода на Python" },
      { id: 3, front: "Что такое list comprehension?", back: "Синтаксическая конструкция для создания списков: [x for x in range(10)]" },
      { id: 4, front: "Разница между list и tuple?", back: "list — изменяемый (mutable), tuple — неизменяемый (immutable)" },
      { id: 5, front: "Что делает декоратор @staticmethod?", back: "Определяет метод класса, не требующий доступа к экземпляру (self) или классу (cls)" },
      { id: 6, front: "Что такое GIL?", back: "Global Interpreter Lock — механизм, позволяющий выполнять только один поток Python-кода одновременно" },
    ]
  },
  {
    id: 2, title: "Django — фреймворк", description: "Ключевые концепции Django", isPublic: false,
    cards: [
      { id: 7, front: "Что такое ORM?", back: "Object-Relational Mapping — работа с БД через объекты Python вместо SQL" },
      { id: 8, front: "Паттерн MVT в Django?", back: "Model-View-Template: Model — данные, View — логика, Template — отображение" },
      { id: 9, front: "Что такое миграция?", back: "Скрипт для обновления структуры БД в соответствии с изменениями моделей" },
      { id: 10, front: "Для чего нужен middleware?", back: "Промежуточный слой обработки запросов/ответов (аутентификация, CORS, CSRF)" },
    ]
  },
  {
    id: 3, title: "Базы данных", description: "SQL и реляционные БД", isPublic: true,
    cards: [
      { id: 11, front: "Что такое ACID?", back: "Atomicity, Consistency, Isolation, Durability — свойства транзакций" },
      { id: 12, front: "Разница между INNER JOIN и LEFT JOIN?", back: "INNER JOIN — только совпадения; LEFT JOIN — все из левой + совпадения из правой" },
      { id: 13, front: "Что такое индекс в БД?", back: "Структура данных для ускорения поиска (B-tree, Hash, GiST)" },
    ]
  },
];

/* ═══════════════════════════════════════════════════
   Icons (inline SVG)
   ═══════════════════════════════════════════════════ */
const Icon = ({ name, size = 20, className = "" }) => {
  const icons = {
    cards: <path d="M4 4h16v16H4z M8 2v2 M16 2v2 M8 20v2 M16 20v2" strokeWidth="1.5" stroke="currentColor" fill="none"/>,
    plus: <><line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" strokeWidth="2"/><line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" strokeWidth="2"/></>,
    back: <polyline points="15 18 9 12 15 6" stroke="currentColor" strokeWidth="2" fill="none"/>,
    check: <polyline points="20 6 9 17 4 12" stroke="currentColor" strokeWidth="2" fill="none"/>,
    chart: <><rect x="3" y="12" width="4" height="8" fill="currentColor" opacity="0.5"/><rect x="10" y="8" width="4" height="12" fill="currentColor" opacity="0.7"/><rect x="17" y="4" width="4" height="16" fill="currentColor"/></>,
    play: <polygon points="8,5 20,12 8,19" fill="currentColor"/>,
    trash: <><polyline points="3 6 5 6 21 6" stroke="currentColor" strokeWidth="1.5" fill="none"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" stroke="currentColor" strokeWidth="1.5" fill="none"/></>,
    edit: <><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" stroke="currentColor" strokeWidth="1.5" fill="none"/><path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="1.5" fill="none"/></>,
    brain: <><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.5" fill="none"/><path d="M12 3c0 4-3 5-3 9s3 5 3 9M8 7c2 1 6 1 8 0M8 17c2-1 6-1 8 0" stroke="currentColor" strokeWidth="1" fill="none" opacity="0.6"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" className={className}>{icons[name]}</svg>;
};

/* ═══════════════════════════════════════════════════
   Main App Component
   ═══════════════════════════════════════════════════ */
export default function App() {
  const [page, setPage] = useState("decks"); // decks | deck-detail | review | stats | add-card | edit-card
  const [decks, setDecks] = useState(DEMO_DECKS);
  const [selectedDeck, setSelectedDeck] = useState(null);
  const [reviewState, setReviewState] = useState(null);
  const [reviewHistory, setReviewHistory] = useState([]);
  const [cardProgress, setCardProgress] = useState({});
  const [editingCard, setEditingCard] = useState(null);
  const [showAnswer, setShowAnswer] = useState(false);
  const [sessionStats, setSessionStats] = useState(null);

  // ── Navigation ──
  const goDecks = () => { setPage("decks"); setSelectedDeck(null); };
  const goDeck = (deck) => { setSelectedDeck(deck); setPage("deck-detail"); };

  // ── Start Review ──
  const startReview = (deck) => {
    const today = new Date().toISOString().split("T")[0];
    const cardsToReview = deck.cards.filter(c => {
      const prog = cardProgress[c.id];
      if (!prog) return true;
      return prog.nextReview <= today;
    });
    if (cardsToReview.length === 0) {
      alert("Все карточки повторены! Возвращайтесь завтра.");
      return;
    }
    setReviewState({ deck, cards: cardsToReview, index: 0, results: [] });
    setShowAnswer(false);
    setPage("review");
  };

  // ── Submit Review Answer ──
  const submitAnswer = (quality) => {
    const card = reviewState.cards[reviewState.index];
    const prev = cardProgress[card.id] || { ef: 2.5, interval: 0, reps: 0 };
    const result = sm2(prev, quality);

    setCardProgress(p => ({ ...p, [card.id]: result }));
    setReviewHistory(h => [...h, { cardId: card.id, quality, date: new Date().toISOString(), ...result }]);

    const newResults = [...reviewState.results, { card, quality, ...result }];
    const nextIndex = reviewState.index + 1;

    if (nextIndex >= reviewState.cards.length) {
      setSessionStats({ deck: reviewState.deck, results: newResults });
      setPage("stats");
      setReviewState(null);
    } else {
      setReviewState({ ...reviewState, index: nextIndex, results: newResults });
      setShowAnswer(false);
    }
  };

  // ── Card CRUD ──
  const addCard = (deckId, front, back) => {
    const newId = Math.max(...decks.flatMap(d => d.cards.map(c => c.id)), 0) + 1;
    setDecks(ds => ds.map(d => d.id === deckId ? { ...d, cards: [...d.cards, { id: newId, front, back }] } : d));
  };
  const updateCard = (cardId, front, back) => {
    setDecks(ds => ds.map(d => ({ ...d, cards: d.cards.map(c => c.id === cardId ? { ...c, front, back } : c) })));
  };
  const deleteCard = (deckId, cardId) => {
    setDecks(ds => ds.map(d => d.id === deckId ? { ...d, cards: d.cards.filter(c => c.id !== cardId) } : d));
  };

  // ── Deck CRUD ──
  const addDeck = (title, desc) => {
    const newId = Math.max(...decks.map(d => d.id), 0) + 1;
    setDecks(ds => [...ds, { id: newId, title, description: desc, isPublic: false, cards: [] }]);
  };
  const deleteDeck = (deckId) => {
    setDecks(ds => ds.filter(d => d.id !== deckId));
    goDecks();
  };

  // keep selectedDeck in sync
  useEffect(() => {
    if (selectedDeck) {
      const updated = decks.find(d => d.id === selectedDeck.id);
      if (updated) setSelectedDeck(updated);
    }
  }, [decks]);

  const getDueCount = (deck) => {
    const today = new Date().toISOString().split("T")[0];
    return deck.cards.filter(c => { const p = cardProgress[c.id]; return !p || p.nextReview <= today; }).length;
  };

  /* ═══════════════════════════════════════════
     Render Pages
     ═══════════════════════════════════════════ */
  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%)", color: "#e8e6f0", fontFamily: "'Segoe UI', system-ui, sans-serif" }}>
      {/* ── Header ── */}
      <header style={{ background: "rgba(255,255,255,0.03)", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", backdropFilter: "blur(20px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }} onClick={goDecks}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg, #6c63ff, #3f51b5)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Icon name="brain" size={20}/>
          </div>
          <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.02em" }}>SpaceLearn</span>
          <span style={{ fontSize: 11, background: "rgba(108,99,255,0.2)", color: "#a78bfa", padding: "2px 8px", borderRadius: 20, fontWeight: 600 }}>SM-2</span>
        </div>
        <div style={{ fontSize: 12, color: "#888" }}>
          Всего повторений: {reviewHistory.length}
        </div>
      </header>

      <main style={{ maxWidth: 900, margin: "0 auto", padding: "24px 16px" }}>
        {page === "decks" && <DecksPage decks={decks} getDueCount={getDueCount} goDeck={goDeck} startReview={startReview} addDeck={addDeck}/>}
        {page === "deck-detail" && selectedDeck && <DeckDetailPage deck={selectedDeck} cardProgress={cardProgress} startReview={startReview} goBack={goDecks} addCard={addCard} updateCard={updateCard} deleteCard={deleteCard} deleteDeck={deleteDeck} editingCard={editingCard} setEditingCard={setEditingCard} setPage={setPage}/>}
        {page === "review" && reviewState && <ReviewPage state={reviewState} showAnswer={showAnswer} setShowAnswer={setShowAnswer} submitAnswer={submitAnswer} cardProgress={cardProgress}/>}
        {page === "stats" && sessionStats && <StatsPage stats={sessionStats} reviewHistory={reviewHistory} cardProgress={cardProgress} goDecks={goDecks}/>}
        {page === "add-card" && selectedDeck && <CardFormPage deck={selectedDeck} addCard={addCard} goBack={() => goDeck(selectedDeck)}/>}
      </main>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Decks List Page
   ═══════════════════════════════════════════════════ */
function DecksPage({ decks, getDueCount, goDeck, startReview, addDeck }) {
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");

  const handleAdd = () => {
    if (!title.trim()) return;
    addDeck(title, desc);
    setTitle(""); setDesc(""); setShowForm(false);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, margin: 0 }}>Мои колоды</h1>
        <button onClick={() => setShowForm(!showForm)} style={btnPrimary}>
          <Icon name="plus" size={16}/> Новая колода
        </button>
      </div>

      {showForm && (
        <div style={cardStyle}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Название колоды" style={inputStyle}/>
          <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Описание (необязательно)" style={{ ...inputStyle, marginTop: 8 }}/>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button onClick={handleAdd} style={btnPrimary}>Создать</button>
            <button onClick={() => setShowForm(false)} style={btnSecondary}>Отмена</button>
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))", gap: 16 }}>
        {decks.map(deck => {
          const due = getDueCount(deck);
          return (
            <div key={deck.id} style={{ ...cardStyle, cursor: "pointer", transition: "transform 0.15s, box-shadow 0.15s" }}
              onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "0 8px 30px rgba(108,99,255,0.15)"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "none"; }}
              onClick={() => goDeck(deck)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600 }}>{deck.title}</h3>
                {due > 0 && <span style={{ background: "linear-gradient(135deg, #6c63ff, #3f51b5)", color: "#fff", borderRadius: 20, padding: "2px 10px", fontSize: 12, fontWeight: 700, whiteSpace: "nowrap" }}>{due} к повторению</span>}
              </div>
              <p style={{ color: "#888", fontSize: 13, margin: "8px 0 16px" }}>{deck.description || "Без описания"}</p>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, color: "#666" }}>{deck.cards.length} карточек</span>
                {due > 0 && (
                  <button onClick={e => { e.stopPropagation(); startReview(deck); }} style={{ ...btnPrimary, padding: "6px 14px", fontSize: 13 }}>
                    <Icon name="play" size={12}/> Учить
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Deck Detail Page
   ═══════════════════════════════════════════════════ */
function DeckDetailPage({ deck, cardProgress, startReview, goBack, addCard, updateCard, deleteCard, deleteDeck, setPage }) {
  const [editId, setEditId] = useState(null);
  const [editFront, setEditFront] = useState("");
  const [editBack, setEditBack] = useState("");

  const startEdit = (card) => { setEditId(card.id); setEditFront(card.front); setEditBack(card.back); };
  const saveEdit = () => { updateCard(editId, editFront, editBack); setEditId(null); };

  return (
    <div>
      <button onClick={goBack} style={{ ...btnSecondary, marginBottom: 16, display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Icon name="back" size={16}/> Назад
      </button>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0 }}>{deck.title}</h1>
          <p style={{ color: "#888", fontSize: 14, margin: "4px 0 0" }}>{deck.description} · {deck.cards.length} карточек</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => startReview(deck)} style={btnPrimary}>
            <Icon name="play" size={14}/> Начать повторение
          </button>
          <button onClick={() => setPage("add-card")} style={btnSecondary}>
            <Icon name="plus" size={14}/> Добавить
          </button>
          <button onClick={() => { if (confirm("Удалить колоду?")) deleteDeck(deck.id); }} style={{ ...btnSecondary, color: "#ef4444" }}>
            <Icon name="trash" size={14}/>
          </button>
        </div>
      </div>

      {deck.cards.length === 0 && (
        <div style={{ ...cardStyle, textAlign: "center", padding: 48, color: "#666" }}>
          <p style={{ fontSize: 16 }}>Колода пуста</p>
          <button onClick={() => setPage("add-card")} style={btnPrimary}>Добавить первую карточку</button>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {deck.cards.map(card => {
          const prog = cardProgress[card.id];
          if (editId === card.id) {
            return (
              <div key={card.id} style={cardStyle}>
                <input value={editFront} onChange={e => setEditFront(e.target.value)} style={inputStyle} placeholder="Вопрос"/>
                <input value={editBack} onChange={e => setEditBack(e.target.value)} style={{ ...inputStyle, marginTop: 8 }} placeholder="Ответ"/>
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button onClick={saveEdit} style={btnPrimary}>Сохранить</button>
                  <button onClick={() => setEditId(null)} style={btnSecondary}>Отмена</button>
                </div>
              </div>
            );
          }
          return (
            <div key={card.id} style={{ ...cardStyle, display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 18px" }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>{card.front}</div>
                <div style={{ fontSize: 13, color: "#888", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{card.back}</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: 12, flexShrink: 0 }}>
                {prog && <span style={{ fontSize: 11, color: "#6c63ff", background: "rgba(108,99,255,0.1)", padding: "2px 8px", borderRadius: 10 }}>EF {prog.ef}</span>}
                <button onClick={() => startEdit(card)} style={btnIcon}><Icon name="edit" size={14}/></button>
                <button onClick={() => deleteCard(deck.id, card.id)} style={{ ...btnIcon, color: "#ef4444" }}><Icon name="trash" size={14}/></button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Review Page — Main learning screen
   ═══════════════════════════════════════════════════ */
function ReviewPage({ state, showAnswer, setShowAnswer, submitAnswer, cardProgress }) {
  const card = state.cards[state.index];
  const progress = ((state.index) / state.cards.length) * 100;

  const qualityButtons = [
    { q: 0, label: "Забыл", color: "#ef4444", sub: "Сброс" },
    { q: 1, label: "Плохо", color: "#f97316", sub: "1 день" },
    { q: 2, label: "Неуд.", color: "#eab308", sub: "1 день" },
    { q: 3, label: "Удовл.", color: "#84cc16", sub: "Повтор" },
    { q: 4, label: "Хорошо", color: "#22c55e", sub: "Далее" },
    { q: 5, label: "Отлично!", color: "#06b6d4", sub: "Легко" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", minHeight: "70vh" }}>
      {/* Progress bar */}
      <div style={{ width: "100%", maxWidth: 600, marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#888", marginBottom: 6 }}>
          <span>{state.deck.title}</span>
          <span>{state.index + 1} / {state.cards.length}</span>
        </div>
        <div style={{ height: 4, borderRadius: 2, background: "rgba(255,255,255,0.08)" }}>
          <div style={{ height: "100%", borderRadius: 2, background: "linear-gradient(90deg, #6c63ff, #06b6d4)", width: `${progress}%`, transition: "width 0.3s" }}/>
        </div>
      </div>

      {/* Card */}
      <div style={{ width: "100%", maxWidth: 600, minHeight: 280, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16, padding: 32, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", backdropFilter: "blur(10px)" }}>
        <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1.5, color: "#6c63ff", marginBottom: 12, fontWeight: 600 }}>
          {showAnswer ? "Ответ" : "Вопрос"}
        </div>
        <div style={{ fontSize: 22, fontWeight: 600, lineHeight: 1.5, marginBottom: 16 }}>
          {card.front}
        </div>

        {showAnswer && (
          <div style={{ marginTop: 8 }}>
            <div style={{ width: 60, height: 1, background: "rgba(255,255,255,0.1)", margin: "0 auto 16px" }}/>
            <div style={{ fontSize: 18, color: "#a78bfa", lineHeight: 1.5 }}>
              {card.back}
            </div>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div style={{ marginTop: 24, width: "100%", maxWidth: 600 }}>
        {!showAnswer ? (
          <button onClick={() => setShowAnswer(true)} style={{ ...btnPrimary, width: "100%", padding: "14px 24px", fontSize: 16, borderRadius: 12 }}>
            Показать ответ
          </button>
        ) : (
          <div>
            <p style={{ textAlign: "center", fontSize: 13, color: "#888", marginBottom: 12 }}>Оцените качество вашего ответа:</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6 }}>
              {qualityButtons.map(({ q, label, color, sub }) => (
                <button key={q} onClick={() => submitAnswer(q)} style={{
                  background: "rgba(255,255,255,0.04)", border: `1px solid ${color}33`, borderRadius: 10,
                  padding: "12px 4px", cursor: "pointer", color, textAlign: "center", transition: "all 0.15s",
                  display: "flex", flexDirection: "column", alignItems: "center", gap: 2,
                }}
                onMouseEnter={e => { e.currentTarget.style.background = `${color}18`; e.currentTarget.style.transform = "translateY(-2px)"; }}
                onMouseLeave={e => { e.currentTarget.style.background = "rgba(255,255,255,0.04)"; e.currentTarget.style.transform = "translateY(0)"; }}>
                  <span style={{ fontSize: 20, fontWeight: 700 }}>{q}</span>
                  <span style={{ fontSize: 11, fontWeight: 600 }}>{label}</span>
                  <span style={{ fontSize: 10, opacity: 0.6 }}>{sub}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Session Stats Page
   ═══════════════════════════════════════════════════ */
function StatsPage({ stats, reviewHistory, cardProgress, goDecks }) {
  const { results } = stats;
  const avgQ = results.reduce((s, r) => s + r.quality, 0) / results.length;
  const avgEf = results.reduce((s, r) => s + r.ef, 0) / results.length;
  const success = results.filter(r => r.quality >= 3).length;
  const failed = results.filter(r => r.quality < 3).length;

  // Distribution of quality scores
  const dist = [0, 1, 2, 3, 4, 5].map(q => results.filter(r => r.quality === q).length);
  const maxDist = Math.max(...dist, 1);

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>
          {avgQ >= 4 ? "🎉" : avgQ >= 3 ? "👍" : "💪"}
        </div>
        <h2 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 8px" }}>Сессия завершена!</h2>
        <p style={{ color: "#888", fontSize: 14 }}>{stats.deck.title} · {results.length} карточек</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
        {[
          { label: "Средняя оценка", value: avgQ.toFixed(1), color: "#6c63ff" },
          { label: "Успешно", value: `${success}/${results.length}`, color: "#22c55e" },
          { label: "Средний EF", value: avgEf.toFixed(2), color: "#06b6d4" },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ ...cardStyle, textAlign: "center", padding: 16 }}>
            <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
            <div style={{ fontSize: 12, color: "#888", marginTop: 4 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Quality distribution */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Распределение оценок</h3>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 100 }}>
          {dist.map((count, q) => (
            <div key={q} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <span style={{ fontSize: 11, color: "#888" }}>{count}</span>
              <div style={{
                width: "100%", borderRadius: 4,
                height: `${Math.max(4, (count / maxDist) * 80)}px`,
                background: q < 3 ? `rgba(239,68,68,${0.3 + q * 0.1})` : `rgba(108,99,255,${0.3 + (q - 2) * 0.2})`,
                transition: "height 0.5s",
              }}/>
              <span style={{ fontSize: 12, fontWeight: 600 }}>{q}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Per-card results */}
      <div style={{ ...cardStyle, marginTop: 12 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Результаты по карточкам</h3>
        {results.map((r, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: i < results.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
            <span style={{ fontSize: 13, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.card.front}</span>
            <div style={{ display: "flex", gap: 8, flexShrink: 0, marginLeft: 8 }}>
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 8, background: r.quality >= 3 ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)", color: r.quality >= 3 ? "#22c55e" : "#ef4444" }}>q={r.quality}</span>
              <span style={{ fontSize: 11, color: "#888" }}>→ {r.interval}д</span>
            </div>
          </div>
        ))}
      </div>

      <button onClick={goDecks} style={{ ...btnPrimary, width: "100%", marginTop: 20, padding: "14px 24px", fontSize: 15, borderRadius: 12 }}>
        Вернуться к колодам
      </button>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Add Card Form
   ═══════════════════════════════════════════════════ */
function CardFormPage({ deck, addCard, goBack }) {
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [added, setAdded] = useState(0);

  const handleAdd = () => {
    if (!front.trim() || !back.trim()) return;
    addCard(deck.id, front, back);
    setFront(""); setBack(""); setAdded(a => a + 1);
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto" }}>
      <button onClick={goBack} style={{ ...btnSecondary, marginBottom: 16, display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Icon name="back" size={16}/> Назад к «{deck.title}»
      </button>

      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 20 }}>Добавить карточку</h2>

      <div style={cardStyle}>
        <label style={labelStyle}>Лицевая сторона (вопрос)</label>
        <textarea value={front} onChange={e => setFront(e.target.value)} style={{ ...inputStyle, minHeight: 80, resize: "vertical" }} placeholder="Введите вопрос или термин..."/>

        <label style={{ ...labelStyle, marginTop: 16 }}>Оборотная сторона (ответ)</label>
        <textarea value={back} onChange={e => setBack(e.target.value)} style={{ ...inputStyle, minHeight: 80, resize: "vertical" }} placeholder="Введите ответ или определение..."/>

        <div style={{ display: "flex", gap: 8, marginTop: 16, alignItems: "center" }}>
          <button onClick={handleAdd} style={btnPrimary}>
            <Icon name="plus" size={14}/> Добавить
          </button>
          {added > 0 && <span style={{ fontSize: 13, color: "#22c55e" }}>✓ Добавлено: {added}</span>}
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════
   Shared Styles
   ═══════════════════════════════════════════════════ */
const cardStyle = {
  background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)",
  borderRadius: 14, padding: 20, marginBottom: 12,
};
const btnPrimary = {
  background: "linear-gradient(135deg, #6c63ff, #3f51b5)", color: "#fff",
  border: "none", borderRadius: 10, padding: "10px 18px", fontSize: 14,
  fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 6,
  transition: "opacity 0.15s", boxShadow: "0 2px 12px rgba(108,99,255,0.3)",
};
const btnSecondary = {
  background: "rgba(255,255,255,0.06)", color: "#ccc",
  border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
  padding: "10px 18px", fontSize: 14, fontWeight: 500, cursor: "pointer",
  display: "inline-flex", alignItems: "center", gap: 6, transition: "all 0.15s",
};
const btnIcon = {
  background: "none", border: "none", color: "#888", cursor: "pointer",
  padding: 6, borderRadius: 6, display: "flex", transition: "color 0.15s",
};
const inputStyle = {
  width: "100%", background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 8, padding: "10px 14px", fontSize: 14, color: "#e8e6f0",
  outline: "none", boxSizing: "border-box", fontFamily: "inherit",
};
const labelStyle = {
  display: "block", fontSize: 12, fontWeight: 600, color: "#888",
  marginBottom: 6, textTransform: "uppercase", letterSpacing: 0.5,
};
