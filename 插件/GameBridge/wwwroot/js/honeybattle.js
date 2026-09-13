// ============================================================
// honeybattle.js — "Honey Battle" mini-game (attractiveness ranking).
// Independent from GameBridge state — only reads card lists/thumbnails from
// it. All battle scoring lives in ControlPanel.Server's own honeybattle.json.
// ============================================================

// Mirrors the constants in HoneyBattleStore.cs — kept in sync manually so the
// hover preview shown here matches what the server will actually compute.
const HB_MIN_SCORE = 0.1;
const HB_MAX_SCORE = 99.9;
const HB_UNRANKED_DELTA = 0.1;
const HB_ELO_SPREAD = 15.0;
const HB_ELO_K = 1.0;
const HB_TOP_CHALLENGE_MIN_DELTA = 1.0;
const HB_TOP_CHALLENGE_K = 3.0;
const HB_BOSS_POOL_FRACTION = 0.1;
const HB_REIGN_LIMITS = { "ranked-random": 3 };

// Dynamic K-factor tiers — mirrors HoneyBattleStore.cs's KFactorFor exactly, so the
// hover preview matches what the server will actually compute.
const HB_PROVISIONAL_MATCH_THRESHOLD = 5;
const HB_SETTLING_MATCH_THRESHOLD = 15;
const HB_PROVISIONAL_K = 2.5;
const HB_SETTLING_K = 1.5;

// Purely cosmetic progress layer — never feeds back into score math. A card with no
// Honey Battle record at all is "NG" (No Grade); everything else is looked up against
// HB_GRADE_THRESHOLDS, highest qualifying tier wins.
const HB_GRADE_THRESHOLDS = [
    { grade: "D", min: 0.1 },
    { grade: "C", min: 1.0 },
    { grade: "B", min: 3.0 },
    { grade: "A", min: 5.0 },
    { grade: "S", min: 8.0 },
    { grade: "SS", min: 14.0 },
    { grade: "SSS", min: 22.0 },
    { grade: "SR", min: 40.0 },
    { grade: "SSR", min: 74.0 }
];

function honeyBattleGradeFor(score) {
    if (score === undefined || score === null) return "NG";
    let grade = "NG";
    for (const tier of HB_GRADE_THRESHOLDS) {
        if (score >= tier.min) grade = tier.grade;
    }
    return grade;
}

function honeyBattleGradeClass(grade) {
    return "hb-grade-" + grade.toLowerCase();
}

function honeyBattleKFactorFor(card) {
    const matches = HoneyBattle.scores[honeyBattleKey(card)]?.matches ?? 0;
    if (matches < HB_PROVISIONAL_MATCH_THRESHOLD) return HB_PROVISIONAL_K;
    if (matches < HB_SETTLING_MATCH_THRESHOLD) return HB_SETTLING_K;
    return HB_ELO_K;
}


const HoneyBattle = {
    sex: null,      // "male" | "female"
    mode: null,      // "unranked" | "ranked" | "ranked-random"
    scores: {},      // reference to the global HoneyBattleScores object
    pool: [],        // candidate cards of the chosen sex for this session
    champion: null,  // current winning card object, or null
    championSide: null,     // "left" | "right" — which side the current champion is displayed on
    topChallengeActive: false, // true when this round is a forced champion-vs-highest-score match
    reignStreak: 0,  // Ranked Fight Random only: how many rounds the current champion has been defending
   lastBossPairKeys: [], // Boss Fight only: the two card keys from the previous round, excluded from the next draw
    lastTopChallengePairKeys: [], // Ranked Fight only: the two card keys from the previous top-challenge round, excluded from the next draw
    left: null,
    right: null,
    busy: false      // true while a result POST is in flight, blocks double-clicks
};

const HB_MODE_INFO_TEXT = {
    unranked: "Unranked Fight matches cards that don't have a score yet. Each win adds 0.1 and each loss subtracts 0.1, so a card can reach a maximum score of 1.0 in this mode. It's just a quick way to give every card its first rating.",
    ranked: "Ranked Fight only matches cards that already have a score. Winning against a much weaker card barely moves your score, while beating a stronger one can swing it a lot. This mode is what actually sharpens the ranking over time.",
    "ranked-random": "Ranked Fight Random only matches cards that already have a score, using the same scoring as Ranked Fight. The difference is the reigning card only stays on screen for 3 rounds in a row, then a fresh random card takes over, so no single card can dominate the whole session.",
    boss: "Boss Fight only matches cards from the top 10% by score. It's a single round each time, win or lose, so the same card never keeps fighting. Every match swings the score harder than normal since these are already the best of the best, and the same pair can't be drawn twice in a row."
};



function initHoneyBattle() {
    document.querySelectorAll(".hb-choice-btn[data-sex]").forEach(btn => {
        btn.addEventListener("click", () => selectHoneyBattleSex(btn.dataset.sex));
    });
    document.querySelectorAll(".hb-choice-btn[data-mode]").forEach(btn => {
        if (btn.disabled) return;
        btn.addEventListener("click", () => selectHoneyBattleMode(btn.dataset.mode));
    });
     document.querySelectorAll(".hb-choice-btn[data-mode]").forEach(btn => {
        const info = HB_MODE_INFO_TEXT[btn.dataset.mode];
        if (!info) return;
        btn.addEventListener("mouseenter", () => showHoneyBattleModeInfo(info));
        btn.addEventListener("mouseleave", hideHoneyBattleModeInfo);
    });
     document.getElementById("hb-start-btn").addEventListener("click", playFightIntroThenStart);
    document.getElementById("hb-favorites-only-toggle").addEventListener("change", (e) => {
        AppState.uiSettings.honeyBattleFavoritesOnly = e.target.checked;
        persistUiSettings();
    });
    document.getElementById("hb-clear-scores-btn").addEventListener("click", openClearScoresModal);
    document.getElementById("hb-clear-confirm-cancel-btn").addEventListener("click", closeClearScoresModal);
    document.getElementById("hb-clear-confirm-delete-btn").addEventListener("click", confirmClearAllScores);
    document.getElementById("hb-back-btn").addEventListener("click", exitHoneyBattle);
    document.getElementById("hb-empty-back-btn").addEventListener("click", exitHoneyBattle);
    document.getElementById("hb-link-same-person-btn").addEventListener("click", linkCurrentMatchAsSamePerson);
}

function showHoneyBattleModeInfo(text) {
    const el = document.getElementById("hb-mode-info");
    el.textContent = text;
    el.classList.add("visible");
}

function hideHoneyBattleModeInfo() {
    document.getElementById("hb-mode-info").classList.remove("visible");
}

function openClearScoresModal() {
    document.getElementById("hb-clear-confirm-modal").style.display = "flex";
}

function closeClearScoresModal() {
    document.getElementById("hb-clear-confirm-modal").style.display = "none";
}

async function confirmClearAllScores() {
    const btn = document.getElementById("hb-clear-confirm-delete-btn");
    btn.disabled = true;
    try {
        await Api.clearHoneyBattleScores();
        await loadHoneyBattleScoresGlobal();
        HoneyBattle.scores = HoneyBattleScores;
        ActivityLog.push("Cleared all Honey Battle scores.");
        renderCards();
    } catch (e) {
        ActivityLog.push("Failed to clear Honey Battle scores: " + e);
    } finally {
        btn.disabled = false;
        closeClearScoresModal();
    }
}

function selectHoneyBattleSex(sex) {
    HoneyBattle.sex = sex;
    document.querySelectorAll(".hb-choice-btn[data-sex]").forEach(btn => btn.classList.toggle("selected", btn.dataset.sex === sex));
    updateHoneyBattleStartButton();
}

function selectHoneyBattleMode(mode) {
    HoneyBattle.mode = mode;
    document.querySelectorAll(".hb-choice-btn[data-mode]").forEach(btn => btn.classList.toggle("selected", btn.dataset.mode === mode));
    updateHoneyBattleStartButton();
}

function updateHoneyBattleStartButton() {
    document.getElementById("hb-start-btn").disabled = !(HoneyBattle.sex && HoneyBattle.mode);
}

async function startHoneyBattle() {
    await ensureCharactersLoaded();
    await loadHoneyBattleScoresGlobal();
    HoneyBattle.scores = HoneyBattleScores; // same object reference — mutations stay in sync with Cards view

    const sexCards = allCharacters[HoneyBattle.sex];
    const favoritesOnly = !!AppState.uiSettings.honeyBattleFavoritesOnly;
    const eligibleCards = favoritesOnly ? sexCards.filter(isCardFavorited) : sexCards;

    const isRankedPool = HoneyBattle.mode === "ranked" || HoneyBattle.mode === "ranked-random" || HoneyBattle.mode === "boss";
    HoneyBattle.pool = isRankedPool ? eligibleCards.filter(c => !isUnranked(c)) : eligibleCards.slice();

    HoneyBattle.champion = null;
    HoneyBattle.championSide = null;
    HoneyBattle.topChallengeActive = false;
     HoneyBattle.reignStreak = 0;
    HoneyBattle.lastBossPairKeys = [];
    HoneyBattle.lastTopChallengePairKeys = [];
    showHoneyBattleScreen("hb-fight");
    nextHoneyBattleRound();
}


const HB_FIGHT_INTRO_MS = 900;
const HB_FIGHT_HOLD_MS = 1200;

// Plays the "clash" intro (buttons fade out, banners slide together, FIGHT! flashes)
// before actually starting the session. Purely cosmetic — startHoneyBattle() still does
// all the real matchmaking work once the animation finishes.
function playFightIntroThenStart() {
    const setupEl = document.getElementById("hb-setup");
    if (setupEl.classList.contains("hb-fighting")) return;
    document.getElementById("hb-start-btn").disabled = true;
    setupEl.classList.add("hb-fighting");
    setTimeout(() => {
        setTimeout(() => {
            setupEl.classList.remove("hb-fighting");
            startHoneyBattle();
        }, HB_FIGHT_HOLD_MS);
    }, HB_FIGHT_INTRO_MS);
}


function honeyBattleKey(card) {
    return card.sex + "/" + card.relativePath;
}

function isUnranked(card) {
    return HoneyBattle.scores[honeyBattleKey(card)] === undefined;
}

function honeyBattleScoreOf(card) {
    return HoneyBattle.scores[honeyBattleKey(card)]?.score;
}

// Unranked Fight: candidates are cards WITHOUT a score yet (filtered live,
// since scores change mid-session as unranked cards get their first result).
// Ranked Fight: candidates are simply everything left in the pre-filtered pool.
// Cards linked as "same person" as excludeCard are always skipped, in both modes.
function pickRandomOpponent(excludeCard) {
    const excludeKey = excludeCard ? honeyBattleKey(excludeCard) : null;
    const excludedKeys = new Set(excludeCard ? [excludeKey, ...honeyBattleSiblingKeysOf(excludeCard)] : []);
    const candidates = HoneyBattle.pool.filter(c => {
        if (excludedKeys.has(honeyBattleKey(c))) return false;
        if (!honeyBattleIsRepresentative(c)) return false;
        return (HoneyBattle.mode === "ranked" || HoneyBattle.mode === "ranked-random") ? true : isUnranked(c);
    });
    if (candidates.length === 0) return null;

    // Prefer cards that have fought the fewest times, so matchmaking naturally spreads
    // across the whole collection instead of repeatedly picking the same few cards.
    const matchesOf = c => HoneyBattle.scores[honeyBattleKey(c)]?.matches ?? 0;
    const minMatches = Math.min(...candidates.map(matchesOf));
    const leastPlayed = candidates.filter(c => matchesOf(c) === minMatches);

    return leastPlayed[Math.floor(Math.random() * leastPlayed.length)];
}

function honeyBattleSiblingKeysOf(card) {
    return PersonLinks[honeyBattleKey(card)] || [];
}

// Only ONE card per "same person" link group may ever be drawn into a match — the group's
// designated "Main Card" (set explicitly in Preview, persisted in personlinks.json's
// mainKey field). This guarantees a persona's rating is always anchored to a single card
// the user chose, instead of drifting between variants as their scores change over time.
// If no main card has been set yet (e.g. PersonLinkMains hasn't loaded), falls back to the
// old highest-score heuristic so matchmaking still works deterministically in the meantime.
function honeyBattleIsRepresentative(card) {
    const key = honeyBattleKey(card);
    const siblingKeys = honeyBattleSiblingKeysOf(card);
    if (siblingKeys.length === 0) return true;

    const mainKey = PersonLinkMains[key] || PersonLinkMains[siblingKeys[0]];
    if (mainKey) return mainKey === key;

    const myScore = honeyBattleScoreOf(card) ?? -Infinity;
    for (const siblingKey of siblingKeys) {
        const siblingScore = HoneyBattle.scores[siblingKey]?.score ?? -Infinity;
        if (siblingScore > myScore) return false;
        if (siblingScore === myScore && siblingKey < key) return false;
    }
    return true;
}


// Ranked "top challenge" opponent pool: instead of always the single #1 card, draws
// randomly from the top 10% of the same-sex pool by score (minimum 1 card), so a long
// winning streak doesn't get stuck facing the exact same opponent round after round.
function pickTopChallengeOpponent(excludeCard) {
    const excludeKey = excludeCard ? honeyBattleKey(excludeCard) : null;
    const baseExcluded = new Set(excludeCard ? [excludeKey, ...honeyBattleSiblingKeysOf(excludeCard)] : []);
    const ranked = HoneyBattle.pool
        .filter(c => !baseExcluded.has(honeyBattleKey(c)) && honeyBattleScoreOf(c) !== undefined && honeyBattleIsRepresentative(c))
        .sort((a, b) => honeyBattleScoreOf(b) - honeyBattleScoreOf(a));
    if (ranked.length === 0) return null;
    const topCount = Math.max(1, Math.ceil(ranked.length * 0.1));
    const topPoolFull = ranked.slice(0, topCount);

    const withGuard = new Set(HoneyBattle.lastTopChallengePairKeys);
    let topPool = topPoolFull.filter(c => !withGuard.has(honeyBattleKey(c)));
    if (topPool.length === 0) topPool = topPoolFull;
    return topPool[Math.floor(Math.random() * topPool.length)];
}

// Boss Fight: candidates are restricted to the top 10% of the whole pool by score
// (minimum 2 cards), recomputed every round so a card climbing into the top decile
// mid-session can immediately be drawn into a match. Also excludes both cards from
// the immediately previous round so the same pair can't repeat back-to-back — unless
// that guard would empty the pool entirely, in which case it's dropped for this pick
// rather than getting the session stuck.
function pickBossOpponent(excludeCard) {
    const excludeKey = excludeCard ? honeyBattleKey(excludeCard) : null;
    const baseExcluded = new Set(excludeCard ? [excludeKey, ...honeyBattleSiblingKeysOf(excludeCard)] : []);
    const representativePool = HoneyBattle.pool.filter(honeyBattleIsRepresentative);
    const rankedBySexScore = representativePool.slice().sort((a, b) => honeyBattleScoreOf(b) - honeyBattleScoreOf(a));
    if (rankedBySexScore.length === 0) return null;
    const topCount = Math.max(2, Math.ceil(rankedBySexScore.length * HB_BOSS_POOL_FRACTION));
    const topDecile = rankedBySexScore.slice(0, topCount);

    const withGuard = new Set(baseExcluded);
    for (const k of HoneyBattle.lastBossPairKeys) withGuard.add(k);
    let topPool = topDecile.filter(c => !withGuard.has(honeyBattleKey(c)));
    if (topPool.length === 0) topPool = topDecile.filter(c => !baseExcluded.has(honeyBattleKey(c)));
    if (topPool.length === 0) return null;

    const matchesOf = c => HoneyBattle.scores[honeyBattleKey(c)]?.matches ?? 0;
    const minMatches = Math.min(...topPool.map(matchesOf));
    const leastPlayed = topPool.filter(c => matchesOf(c) === minMatches);
    return leastPlayed[Math.floor(Math.random() * leastPlayed.length)];
}

function nextHoneyBattleRound() {
    try {
        nextHoneyBattleRoundUnsafe();
    } catch (e) {
        console.error("Honey Battle round failed:", e);
        ActivityLog.push("Honey Battle: something went wrong setting up the next round (" + e.message + "). Check the browser console for details.");
        showHoneyBattleEmptyState();
    }
}

function nextHoneyBattleRoundUnsafe() {
    const championScore = HoneyBattle.champion ? honeyBattleScoreOf(HoneyBattle.champion) : undefined;

    // Unranked Fight: a champion that's climbed past 0.9 is "retired" for this
    // session instead of being allowed to keep winning indefinitely — we drop
    // back to two fresh, unscored cards just like the very first round.
    const championRetired = HoneyBattle.mode === "unranked" && HoneyBattle.champion && championScore !== undefined && championScore > 0.9;

    // Ranked Fight: a champion above 9.9 gets pitted against the single
    // highest-scored card in the deck instead of a random challenger.
    const wantsTopChallenge = HoneyBattle.mode === "ranked" && HoneyBattle.champion && championScore !== undefined && championScore > 9.9;

    // Ranked Fight: a champion that just won a top-challenge match and ended up
    // above 29.9 is "exhausted" — its score is banked, but it doesn't keep
    // defending the title. Matchmaking resets to two fresh random cards, same
    // as if the user had just started a new ranked session.
     const championExhausted = HoneyBattle.mode === "ranked" && HoneyBattle.champion && championScore !== undefined && championScore > 29.9;

    // Ranked Fight Random: the reigning champion is forced out after a fixed number of
    // consecutive defense rounds (see HB_REIGN_LIMITS), win or lose, so no single card
    // can dominate a whole session.
    const reignLimit = HB_REIGN_LIMITS[HoneyBattle.mode];
    const reignExpired = reignLimit !== undefined && HoneyBattle.champion && HoneyBattle.reignStreak >= reignLimit;

    // Boss Fight never carries a champion between rounds — every round is a single,
    // fresh matchup, so this is always true in that mode.
    const bossAlwaysFresh = HoneyBattle.mode === "boss";

     if (!HoneyBattle.champion || championRetired || championExhausted || reignExpired || bossAlwaysFresh) {
        const first = HoneyBattle.mode === "boss" ? pickBossOpponent(null) : pickRandomOpponent(null);
        if (!first) { showHoneyBattleEmptyState(); return; }
        const second = HoneyBattle.mode === "boss" ? pickBossOpponent(first) : pickRandomOpponent(first);
        if (!second) { showHoneyBattleEmptyState(); return; }
        HoneyBattle.left = first;
        HoneyBattle.right = second;
        HoneyBattle.champion = null;
        HoneyBattle.championSide = null;
        HoneyBattle.topChallengeActive = false;
        HoneyBattle.reignStreak = 0;
    } else {
        let challenger = wantsTopChallenge ? pickTopChallengeOpponent(HoneyBattle.champion) : null;
        HoneyBattle.topChallengeActive = wantsTopChallenge && challenger !== null;
        if (!challenger) challenger = pickRandomOpponent(HoneyBattle.champion);
        if (!challenger) { showHoneyBattleEmptyState(); return; }
        if (reignLimit !== undefined) HoneyBattle.reignStreak++;

        // Keep the champion on the side it just won on, so the winning card
        // doesn't visually jump left/right between rounds.
        if (HoneyBattle.championSide === "right") {
            HoneyBattle.right = HoneyBattle.champion;
            HoneyBattle.left = challenger;
        } else {
            HoneyBattle.left = HoneyBattle.champion;
            HoneyBattle.right = challenger;
        }
    }
    renderHoneyBattleRound();
}

function hbClamp(score) {
    return Math.max(HB_MIN_SCORE, Math.min(HB_MAX_SCORE, score));
}

// Mirrors HoneyBattleStore.cs so the hover preview matches what the server
// will actually compute if this card wins the current round.
function computeHoneyBattlePreview(winnerCard, loserCard) {
    const winnerScore = honeyBattleScoreOf(winnerCard);
    const loserScore = honeyBattleScoreOf(loserCard);

    if (HoneyBattle.mode === "unranked") {
        const reference = Math.max(winnerScore ?? 0, loserScore ?? 0);
        return hbClamp(reference + HB_UNRANKED_DELTA);
    }

    if (HoneyBattle.topChallengeActive || HoneyBattle.mode === "boss") {
        const w = winnerScore ?? HB_MIN_SCORE;
        const l = loserScore ?? HB_MIN_SCORE;
        const expectedWinner = 1.0 / (1.0 + Math.pow(10, (l - w) / HB_ELO_SPREAD));
        const delta = Math.max(HB_TOP_CHALLENGE_MIN_DELTA, HB_TOP_CHALLENGE_K * (1.0 - expectedWinner));
        return hbClamp(w + delta);
    }

    const w = winnerScore ?? HB_MIN_SCORE;
    const l = loserScore ?? HB_MIN_SCORE;
    const expectedWinner = 1.0 / (1.0 + Math.pow(10, (l - w) / HB_ELO_SPREAD));
    const delta = honeyBattleKFactorFor(winnerCard) * (1.0 - expectedWinner);
    return hbClamp(w + delta);
}

// Same match, but returns what loserCard's score becomes if it LOSES to winnerCard.
function computeHoneyBattleLossPreview(winnerCard, loserCard) {
    const winnerScore = honeyBattleScoreOf(winnerCard);
    const loserScore = honeyBattleScoreOf(loserCard);

    if (HoneyBattle.mode === "unranked") {
        if (loserScore === undefined) return null;
        const reference = Math.max(winnerScore ?? 0, loserScore);
        return hbClamp(reference - HB_UNRANKED_DELTA);
    }

    if (HoneyBattle.topChallengeActive || HoneyBattle.mode === "boss") {
        const w = winnerScore ?? HB_MIN_SCORE;
        const l = loserScore ?? HB_MIN_SCORE;
        const expectedWinner = 1.0 / (1.0 + Math.pow(10, (l - w) / HB_ELO_SPREAD));
        const delta = Math.max(HB_TOP_CHALLENGE_MIN_DELTA, HB_TOP_CHALLENGE_K * (1.0 - expectedWinner));
        return hbClamp(l - delta);
    }

    const w = winnerScore ?? HB_MIN_SCORE;
    const l = loserScore ?? HB_MIN_SCORE;
    const expectedWinner = 1.0 / (1.0 + Math.pow(10, (l - w) / HB_ELO_SPREAD));
    const delta = honeyBattleKFactorFor(loserCard) * (1.0 - expectedWinner);
    return hbClamp(l - delta);
}



function renderHoneyBattleRound() {
    const leftWinPreview = computeHoneyBattlePreview(HoneyBattle.left, HoneyBattle.right);
    const leftLossPreview = computeHoneyBattleLossPreview(HoneyBattle.right, HoneyBattle.left);
    const rightWinPreview = computeHoneyBattlePreview(HoneyBattle.right, HoneyBattle.left);
    const rightLossPreview = computeHoneyBattleLossPreview(HoneyBattle.left, HoneyBattle.right);

    renderHoneyBattleCard("hb-card-left", HoneyBattle.left, leftWinPreview, leftLossPreview);
    renderHoneyBattleCard("hb-card-right", HoneyBattle.right, rightWinPreview, rightLossPreview);

    const leftEl = document.getElementById("hb-card-left");
    const rightEl = document.getElementById("hb-card-right");
    leftEl.onmouseenter = () => setHoneyBattleHoverPreview("left");
    leftEl.onmouseleave = () => setHoneyBattleHoverPreview(null);
    rightEl.onmouseenter = () => setHoneyBattleHoverPreview("right");
    rightEl.onmouseleave = () => setHoneyBattleHoverPreview(null);
    document.getElementById("hb-boss-badge").style.display = (HoneyBattle.topChallengeActive || HoneyBattle.mode === "boss") ? "block" : "none";

    const reignBadge = document.getElementById("hb-reign-badge");
    const reignLimit = HB_REIGN_LIMITS[HoneyBattle.mode];
    const showReignBadge = reignLimit !== undefined && HoneyBattle.champion && HoneyBattle.reignStreak > 0;
    reignBadge.style.display = showReignBadge ? "block" : "none";
    if (showReignBadge) reignBadge.textContent = "Defending: " + HoneyBattle.reignStreak + "/" + reignLimit;

    buildHoneyBattleSideButtons(document.getElementById("hb-side-buttons-left"), HoneyBattle.left);
    buildHoneyBattleSideButtons(document.getElementById("hb-side-buttons-right"), HoneyBattle.right);
}

function renderHoneyBattleCard(elId, card, winPreview, lossPreview) {
    const el = document.getElementById(elId);
    const key = honeyBattleKey(card);
    const record = HoneyBattle.scores[key];
    const fileName = card.relativePath.split(/[\\/]/).pop();
    const cachedName = AppState.nameCache[key];

    el.innerHTML = "";
    el.onclick = () => resolveHoneyBattleRound(card);

    const img = document.createElement("img");
    img.src = Api.thumbnailUrl(card.sex, card.relativePath);
    el.appendChild(img);

    const label = document.createElement("div");
    label.className = "hb-card-label";
    label.textContent = cachedName ? cachedName : fileName;
    el.appendChild(label);

    const grade = record ? honeyBattleGradeFor(record.score) : "NG";
    const scoreEl = document.createElement("div");
    scoreEl.className = "hb-card-score";

    const gradeBadge = document.createElement("span");
    gradeBadge.className = "hb-grade-badge " + honeyBattleGradeClass(grade);
    gradeBadge.textContent = grade;
    scoreEl.appendChild(gradeBadge);

    scoreEl.appendChild(document.createTextNode(" " + (record ? record.score.toFixed(1) : "Unranked")));

    const winEl = document.createElement("span");
    winEl.className = "hb-card-preview hb-card-preview-win";
    winEl.textContent = " → " + winPreview.toFixed(1);
    scoreEl.appendChild(winEl);

    const lossEl = document.createElement("span");
    lossEl.className = "hb-card-preview hb-card-preview-loss";
    lossEl.textContent = lossPreview === null ? " → Unranked" : " → " + lossPreview.toFixed(1);
    scoreEl.appendChild(lossEl);

    el.appendChild(scoreEl);
}

function buildHoneyBattleSideButtons(container, card) {
    container.innerHTML = "";

    const previewBtn = makeHoneyBattleSideButton("Preview", () => openPreview(card));
    previewBtn.classList.add("hb-side-btn-preview");
    container.appendChild(previewBtn);

    if (card.sex === "male") {
        container.appendChild(makeHoneyBattleSideButton("Select as Male", () => {
            AppState.slots.male = card;
            renderSlots();
        }));
        container.appendChild(makeHoneyBattleSideButton("Select as Male 2", () => {
            AppState.slots.male2 = card;
            AppState.slots.female2 = null;
            renderSlots();
        }));
    } else {
        container.appendChild(makeHoneyBattleSideButton("Select as Female 1", () => {
            AppState.slots.female1 = card;
            renderSlots();
        }));
        container.appendChild(makeHoneyBattleSideButton("Select as Female 2", () => {
            AppState.slots.female2 = card;
            AppState.slots.male2 = null;
            renderSlots();
        }));
    }

    container.appendChild(makeHoneyBattleSideButton("Edit", async () => {
        ActivityLog.push("Opening editor for " + card.relativePath.split(/[\\/]/).pop());
        if (card.sex === "male") await Api.editMale(card.relativePath);
        else await Api.editFemale(card.relativePath);
    }));

    container.appendChild(makeHoneyBattleSideButton("Show in Explorer", async () => {
        ActivityLog.push("Opening Explorer for " + card.relativePath.split(/[\\/]/).pop());
        const result = await Api.showInExplorer(card.sex, card.relativePath);
        ActivityLog.push(result.result || "Explorer request sent.");
    }));

    const stripSide = container.id === "hb-side-buttons-left" ? "left" : "right";
    const strip = buildHoneyBattleGalleryStripShell(stripSide);
    container.appendChild(strip);
    renderHoneyBattleGalleryStrip(strip, card);
}

// ------------------------------------------------------------
// Honey Battle side gallery strips — mirrors the Preview screen's photo strip
// (see main.js renderPreviewPhotoStrip), but sized dynamically to fill whatever
// empty space sits outside the side-buttons column at the current window width
// (see updateHoneyBattleGalleryStripWidths).
// ------------------------------------------------------------
function buildHoneyBattleGalleryStripShell(side) {
    const strip = document.createElement("div");
    strip.className = "hb-gallery-strip";
    strip.id = "hb-gallery-strip-" + side;

    const leftArrow = document.createElement("button");
    leftArrow.className = "hb-gallery-strip-arrow hb-gallery-strip-arrow-left";
    leftArrow.textContent = "◀";
    leftArrow.addEventListener("click", (e) => { e.stopPropagation(); scrollHoneyBattleGalleryStrip(strip, -1); });

    const track = document.createElement("div");
    track.className = "hb-gallery-strip-track";
    track.addEventListener("scroll", () => updateHoneyBattleGalleryStripArrows(strip));

    const rightArrow = document.createElement("button");
    rightArrow.className = "hb-gallery-strip-arrow hb-gallery-strip-arrow-right";
    rightArrow.textContent = "▶";
    rightArrow.addEventListener("click", (e) => { e.stopPropagation(); scrollHoneyBattleGalleryStrip(strip, 1); });

    strip.appendChild(leftArrow);
    strip.appendChild(track);
    strip.appendChild(rightArrow);
    return strip;
}

function scrollHoneyBattleGalleryStrip(strip, direction) {
    const track = strip.querySelector(".hb-gallery-strip-track");
    track.scrollBy({ left: direction * (track.clientWidth * 0.8), behavior: "smooth" });
}

function updateHoneyBattleGalleryStripArrows(strip) {
    const track = strip.querySelector(".hb-gallery-strip-track");
    const leftArrow = strip.querySelector(".hb-gallery-strip-arrow-left");
    const rightArrow = strip.querySelector(".hb-gallery-strip-arrow-right");

    requestAnimationFrame(() => {
        const overflowing = track.scrollWidth > track.clientWidth + 2;
        leftArrow.classList.toggle("visible", overflowing && track.scrollLeft > 4);
        rightArrow.classList.toggle("visible", overflowing && track.scrollLeft < track.scrollWidth - track.clientWidth - 4);
    });
}

async function renderHoneyBattleGalleryStrip(strip, card) {
    const key = honeyBattleKey(card);
    const siblingKeys = honeyBattleSiblingKeysOf(card);
    const allKeys = [key, ...siblingKeys];

    let photos = [];
    try {
        const perKeyResults = await Promise.all(
            allKeys.map(k => Api.getPhotoGallery(k).then(list => (list || []).map(p => ({ ...p, ownerKey: k }))))
        );
        photos = perKeyResults.flat().sort((a, b) => new Date(b.takenAtUtc) - new Date(a.takenAtUtc));
    } catch (e) {
        ActivityLog.push("Failed to load photo gallery: " + e);
    }

    // The round may have already moved on to different cards while this was loading.
    if (HoneyBattle.left !== card && HoneyBattle.right !== card) return;

    const track = strip.querySelector(".hb-gallery-strip-track");
    track.innerHTML = "";

    if (photos.length === 0) {
        const empty = document.createElement("span");
        empty.className = "hb-gallery-strip-empty";
        empty.textContent = "No screenshots";
        track.appendChild(empty);
        strip.querySelector(".hb-gallery-strip-arrow-left").classList.remove("visible");
        strip.querySelector(".hb-gallery-strip-arrow-right").classList.remove("visible");
        updateHoneyBattleGalleryStripWidths();
        return;
    }

    for (const photo of photos) {
        const wrap = document.createElement("div");
        wrap.className = "hb-gallery-thumb-wrap";

        const img = document.createElement("img");
        img.className = "hb-gallery-thumb";
        img.src = Api.screenshotFileUrl(photo.thumbFileName);
        img.loading = "lazy";
        img.addEventListener("click", (e) => { e.stopPropagation(); openLightbox(Api.screenshotFileUrl(photo.fileName)); });
        wrap.appendChild(img);

        track.appendChild(wrap);
    }

    updateHoneyBattleGalleryStripArrows(strip);
    updateHoneyBattleGalleryStripWidths();
}

// Sizes each side's strip to fill the empty space between the side-buttons column
// and the edge of the window at the CURRENT window width — recomputed on resize and
// after every render, since #hb-fight-cards is centered and the spare space on each
// side changes with the viewport.
function updateHoneyBattleGalleryStripWidths() {
    const margin = 24;
    const minWidth = 170;

    const leftButtons = document.getElementById("hb-side-buttons-left");
    const rightButtons = document.getElementById("hb-side-buttons-right");
    const leftStrip = document.getElementById("hb-gallery-strip-left");
    const rightStrip = document.getElementById("hb-gallery-strip-right");

    if (leftButtons && leftStrip) {
        const rect = leftButtons.getBoundingClientRect();
        leftStrip.style.width = Math.max(minWidth, rect.right - margin) + "px";
    }
    if (rightButtons && rightStrip) {
        const rect = rightButtons.getBoundingClientRect();
        rightStrip.style.width = Math.max(minWidth, window.innerWidth - rect.left - margin) + "px";
    }
}

window.addEventListener("resize", updateHoneyBattleGalleryStripWidths);

function makeHoneyBattleSideButton(label, onClick) {
    const btn = document.createElement("button");
    btn.className = "hb-side-btn";
    btn.textContent = label;
    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        onClick();
    });
    return btn;
}

// hoveredSide is the card the user is about to click (the would-be winner);
// the other card shows its would-be loss preview instead. Passing null hides both.
function setHoneyBattleHoverPreview(hoveredSide) {
    const leftEl = document.getElementById("hb-card-left");
    const rightEl = document.getElementById("hb-card-right");

    leftEl.classList.toggle("hb-preview-win", hoveredSide === "left");
    leftEl.classList.toggle("hb-preview-loss", hoveredSide === "right");
    rightEl.classList.toggle("hb-preview-win", hoveredSide === "right");
    rightEl.classList.toggle("hb-preview-loss", hoveredSide === "left");
}


async function resolveHoneyBattleRound(winnerCard) {
    if (HoneyBattle.busy) return;
    HoneyBattle.busy = true;

    const winnerSide = winnerCard === HoneyBattle.left ? "left" : "right";
    const loserCard = winnerCard === HoneyBattle.left ? HoneyBattle.right : HoneyBattle.left;
    const winnerKey = honeyBattleKey(winnerCard);
    const loserKey = honeyBattleKey(loserCard);
    const useHalfDiffRule = HoneyBattle.topChallengeActive || HoneyBattle.mode === "boss";

    try {
        await Api.postHoneyBattleResult(winnerKey, loserKey, HoneyBattle.mode, useHalfDiffRule);
        // The server may have just synced OTHER cards too (siblings in the winner's/loser's
        // "same person" link group — see StaticFileServer.HandleHoneyBattleResult), not just
        // winnerKey/loserKey. Re-fetching the full score set instead of only patching those two
        // keys locally is what keeps those sibling scores from going stale until a manual refresh.
        await loadHoneyBattleScoresGlobal();
        HoneyBattle.scores = HoneyBattleScores;
        if (HoneyBattle.mode === "boss") {
            HoneyBattle.lastBossPairKeys = [winnerKey, loserKey];
            HoneyBattle.champion = null;
            HoneyBattle.championSide = null;
        } else {
            if (HB_REIGN_LIMITS[HoneyBattle.mode] !== undefined && HoneyBattle.champion !== winnerCard) HoneyBattle.reignStreak = 0;
            HoneyBattle.lastTopChallengePairKeys = HoneyBattle.topChallengeActive ? [winnerKey, loserKey] : [];
            HoneyBattle.champion = winnerCard;
            HoneyBattle.championSide = winnerSide;
        }
        nextHoneyBattleRound();
    } catch (e) {
        ActivityLog.push("Honey Battle: failed to save match result: " + e);
    } finally {
        HoneyBattle.busy = false;
    }
}

// Marks the two cards currently on screen as the same character. Doesn't record
// a win/loss — just refreshes scores/links (the backend may have just synced
// their scores to each other) and draws a fresh matchup.
async function linkCurrentMatchAsSamePerson() {
    if (HoneyBattle.busy) return;
    HoneyBattle.busy = true;
    const btn = document.getElementById("hb-link-same-person-btn");
    btn.disabled = true;

    const leftKey = honeyBattleKey(HoneyBattle.left);
    const rightKey = honeyBattleKey(HoneyBattle.right);

    try {
        await Api.linkSamePerson([leftKey, rightKey]);
        // loadHoneyBattleScoresGlobal() reassigns the global HoneyBattleScores
        // object (doesn't mutate the old one), so HoneyBattle.scores has to be
        // re-pointed at the fresh object or it'd keep reading stale, pre-link scores.
        await loadHoneyBattleScoresGlobal();
        HoneyBattle.scores = HoneyBattleScores;
        await loadPersonLinksGlobal();
        ActivityLog.push("Linked cards as the same person — they won't be matched against each other again.");
    } catch (e) {
        ActivityLog.push("Failed to link cards: " + e);
    }

    HoneyBattle.champion = null;
    HoneyBattle.championSide = null;
    HoneyBattle.topChallengeActive = false;
    HoneyBattle.reignStreak = 0;
    HoneyBattle.lastBossPairKeys = [];
    HoneyBattle.lastTopChallengePairKeys = [];
    HoneyBattle.busy = false;
    btn.disabled = false;
    nextHoneyBattleRound();
}

function showHoneyBattleScreen(screenId) {
    document.querySelectorAll("#view-honeybattle .hb-screen").forEach(el => el.classList.toggle("active", el.id === screenId));
}

function showHoneyBattleEmptyState() {
    const msg = document.getElementById("hb-empty-message");
    const favoritesOnly = !!AppState.uiSettings.honeyBattleFavoritesOnly;
    const favHint = favoritesOnly ? " Try turning off \"Favorites only\" for more cards." : "";
    msg.textContent = ((HoneyBattle.mode === "ranked" || HoneyBattle.mode === "ranked-random" || HoneyBattle.mode === "boss")
        ? "Not enough ranked cards yet — play Unranked Fight first to give cards their initial scores."
        : "No unranked cards left for this sex.") + favHint;
    showHoneyBattleScreen("hb-empty-state");
}

function exitHoneyBattle() {
    HoneyBattle.sex = null;
    HoneyBattle.mode = null;
    HoneyBattle.champion = null;
    HoneyBattle.championSide = null;
    HoneyBattle.topChallengeActive = false;
    HoneyBattle.reignStreak = 0;
    HoneyBattle.lastBossPairKeys = [];
    HoneyBattle.lastTopChallengePairKeys = [];
    document.querySelectorAll(".hb-choice-btn").forEach(btn => btn.classList.remove("selected"));
    document.getElementById("hb-setup").classList.remove("hb-fighting");
    updateHoneyBattleStartButton();
    showHoneyBattleScreen("hb-setup");
    renderCards();
}

// Odpowiada na "czy ta karta ma być widoczna przy włączonym filtrze ulubionych" —
// czyli albo jest ulubiona sama z siebie (favoritecards.json), albo leży w folderze
// oznaczonym jako ulubiony. "__sex__" = cała płeć, "__root__" = karty w korzeniu.
function isCardFavorited(card) {
    if (isFavoriteCard(card)) return true;
    const favSet = new Set(AppState.favorites.favoriteFolders[card.sex] || []);
    if (favSet.has("__sex__")) return true;
    if (isRootCard(card)) return favSet.has("__root__");
    const parts = card.relativePath.split(/[\\/]/);
    const topFolder = parts.length > 1 ? parts[0] : null;
    return topFolder !== null && favSet.has(topFolder);
}