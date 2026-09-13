// ============================================================
// main.js — całość logiki ControlPanel
// ============================================================

document.addEventListener("DOMContentLoaded", init);

async function init() {
    bindStaticButtons();
    initHoneyBattle();
    await loadFavorites();
    await loadUiSettings();
    await loadNameCache();
    await loadHoneyBattleScoresGlobal();
    await loadPersonLinksGlobal();
    await loadFavoriteCardsGlobal();
    await loadMaps();
    await loadFolders();
    await loadCards();
    renderSlots();
    startStatusPolling();
}

// ------------------------------------------------------------
// Status polling (InH / InEditor / editorPhase / hscenePhase)
// ------------------------------------------------------------
function startStatusPolling() {
    updateStatus();
    setInterval(updateStatus, 1500);
}

let lastIsBusy = null; // null = jeszcze nie wiemy (pierwszy poll), potem true/false
let lastConnectionOk = null;
let statusPollInFlight = false;

async function updateStatus() {
    if (statusPollInFlight) return;
    statusPollInFlight = true;
    try {
        const state = await Api.getState();

        setConnectionDot(true);
        setSimpleDot("dot-ready", state.isBusy ? "loading" : "active");
        setSimpleDot("dot-ineditor", state.inEditor ? "active" : "inactive");
        setSimpleDot("dot-hscene", state.inH ? "active" : "inactive");
        // HomeScene: placeholder, brak sygnału z backendu na razie.
        setSimpleDot("dot-homescene", "unknown");

        handleBusyTransition(state);

        const runBtn = document.getElementById("run-h-btn");
        runBtn.disabled = state.inH || state.hscenePhase === "Loading";
    } catch (e) {
        setConnectionDot(false);
    } finally {
        statusPollInFlight = false;
    }
}

function setSimpleDot(elId, mode) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.classList.remove("active", "inactive", "loading", "unknown");
    el.classList.add(mode);
}

function setConnectionDot(ok) {
    setSimpleDot("dot-connection", ok ? "active" : "inactive");
    lastConnectionOk = ok;
}

// Wykrywa przejście isBusy: true -> false, czyli moment w którym scena/editor
// właśnie skończyły się ładować. Backend już wie CO się skończyło ładować
// (editorPhase/hscenePhase), ale nie ma osobnego kanału push do przeglądarki
// (panel komunikuje się wyłącznie przez HTTP polling), więc wykrywamy to
// po stronie frontendu porównując poprzedni i aktualny stan.
function handleBusyTransition(state) {
    const wasBusy = lastIsBusy;
    lastIsBusy = state.isBusy;

    if (wasBusy === true && state.isBusy === false) {
        const label = state.hscenePhase === "Ready" ? "H scene is ready."
            : state.editorPhase === "Ready" ? "Editor is ready."
            : "Scene finished loading.";
        ActivityLog.push(label);
        onSceneLoaded();
    }
}

function onSceneLoaded() {
    if (AppState.uiSettings.focusOnLoadedScene) {
        Api.focusGame().catch(() => {});
    }
    if (AppState.uiSettings.soundOnLoadedScene) {
        playNotificationSound();
    }
}

async function loadUiSettings() {
    try {
        const saved = await Api.getUiSettings();
        AppState.uiSettings = { ...AppState.uiSettings, ...saved };
    } catch (e) {
        console.warn("Could not load UI settings (is GameBridge running?)", e);
    }

    AppState.showOnlyFavoriteMaps = !!AppState.uiSettings.showOnlyFavoriteMaps;
    AppState.showOnlyFavoriteFolders = !!AppState.uiSettings.showOnlyFavoriteFolders;

    document.getElementById("show-fav-maps").checked = AppState.showOnlyFavoriteMaps;
    document.getElementById("show-fav-folders").checked = AppState.showOnlyFavoriteFolders;
    document.getElementById("toggle-focus-on-loaded").checked = !!AppState.uiSettings.focusOnLoadedScene;
    document.getElementById("toggle-sound-on-loaded").checked = !!AppState.uiSettings.soundOnLoadedScene;
    document.getElementById("hb-favorites-only-toggle").checked = !!AppState.uiSettings.honeyBattleFavoritesOnly;
    document.getElementById("sort-select").value = AppState.uiSettings.cardSortMode || "name";
    applyTopPanelState();
    applyFolderColumnState();
}

function persistUiSettings() {
    Api.saveUiSettings(AppState.uiSettings);
}

function playNotificationSound() {
    try {
        const audio = new Audio(NOTIFICATION_SOUND_URL);
        audio.play().catch(() => {});
    } catch (e) {
        // Autoplay/format issue — fail silently, this is a non-critical alert.
    }
}


function setDot(elId, active) {
    const el = document.getElementById(elId);
    if (el) el.classList.toggle("active", !!active);
}

function setPhase(dotId, textId, phase) {
    const dot = document.getElementById(dotId);
    const text = document.getElementById(textId);
    if (text) text.textContent = phase;
    if (dot) {
        dot.classList.remove("active", "loading");
        if (phase === "Ready") dot.classList.add("active");
        else if (phase === "Loading") dot.classList.add("loading");
    }
}

// ------------------------------------------------------------
// Favorites
// ------------------------------------------------------------
async function loadFavorites() {
    try {
        const favs = await Api.getFavorites();
        AppState.favorites = favs;
    } catch (e) {
        console.warn("Could not load favorites (is GameBridge running?)", e);
    }

    document.getElementById("show-fav-maps").addEventListener("change", (e) => {
        AppState.showOnlyFavoriteMaps = e.target.checked;
        AppState.uiSettings.showOnlyFavoriteMaps = e.target.checked;
        persistUiSettings();
        renderMapOptions();
    });
    document.getElementById("show-fav-folders").addEventListener("change", (e) => {
        AppState.showOnlyFavoriteFolders = e.target.checked;
        AppState.uiSettings.showOnlyFavoriteFolders = e.target.checked;
        persistUiSettings();
        renderFolders();
    });
}

async function persistFavorites() {
    await Api.saveFavorites(AppState.favorites);
}

function toggleFavoriteMap(mapId) {
    const list = AppState.favorites.favoriteMaps;
    const idx = list.indexOf(mapId);
    if (idx === -1) list.push(mapId); else list.splice(idx, 1);
    persistFavorites();
    renderMapOptions();
}

function toggleFavoriteFolder(sex, folderName) {
    const list = AppState.favorites.favoriteFolders[sex];
    const idx = list.indexOf(folderName);
    if (idx === -1) list.push(folderName); else list.splice(idx, 1);
    persistFavorites();
    renderFolders();
}

function toggleFavoriteAll() {
    AppState.favorites.favoriteAll = !AppState.favorites.favoriteAll;
    persistFavorites();
    renderFolders();
}

// ------------------------------------------------------------
// Name cache (nazwy postaci pod kartami)
// ------------------------------------------------------------
async function loadNameCache() {
    try {
        AppState.nameCache = await Api.getNameCache();
    } catch (e) {
        console.warn("Could not load name cache (is GameBridge running?)", e);
        AppState.nameCache = {};
    }
}

async function loadHoneyBattleScoresGlobal() {
    try {
        HoneyBattleScores = await Api.getHoneyBattle();
    } catch (e) {
        console.warn("Could not load Honey Battle scores", e);
        HoneyBattleScores = {};
    }
}

async function loadPersonLinksGlobal() {
    try {
        PersonLinks = await Api.getPersonLinks();
    } catch (e) {
        console.warn("Could not load person links", e);
        PersonLinks = {};
    }
    try {
        PersonLinkMains = await Api.getPersonLinkMains();
    } catch (e) {
        console.warn("Could not load person link main cards", e);
        PersonLinkMains = {};
    }
}

async function loadFavoriteCardsGlobal() {
    try {
        AppState.favoriteCards = await Api.getFavoriteCards();
    } catch (e) {
        console.warn("Could not load favorite cards", e);
        AppState.favoriteCards = [];
    }
}

function isFavoriteCard(card) {
    return AppState.favoriteCards.includes(card.sex + "/" + card.relativePath);
}


// Klucze w favoritecards.json, do których nie ma już pliku karty na dysku.
// Nie czyścimy ich automatycznie: karta może być chwilowo niewidoczna (np. jeszcze
// nie doładowana), a ciche skasowanie ulubionego byłoby gorsze niż zostawienie sieroty.
function orphanedFavoriteKeys() {
    return AppState.favoriteCards.filter(k => findCardByKey(k) === null);
}

async function toggleFavoriteCard(card) {
    const key = card.sex + "/" + card.relativePath;
    try {
        const result = await Api.toggleFavoriteCard(key);
        if (result.favorite) AppState.favoriteCards.push(key);
        else AppState.favoriteCards = AppState.favoriteCards.filter(k => k !== key);
    } catch (e) {
        ActivityLog.push("Failed to toggle favorite: " + e);
        return;
    }
    renderFolders();
    renderCards();
}

// Zwraca listę NAZW folderów bezpośrednio pod UserData/chara/<sex>, bez zagnieżdżonych
// podfolderów w głąb — traktujemy tylko pierwszy segment ścieżki jako "folder" na liście,
// żeby lista pozostała płaska i przewidywalna nawet gdy ktoś ma karty zagnieżdżone głębiej.
function extractTopFolders(cards) {
    const set = new Set();
    for (const card of cards) {
        const parts = card.relativePath.split(/[\\/]/);
        if (parts.length > 1) set.add(parts[0]);
    }
    return Array.from(set).sort();
}

// Karta jest "w root" danej płci jeśli relativePath nie zawiera żadnego separatora ścieżki.
function isRootCard(card) {
    return !/[\\/]/.test(card.relativePath);
}

// Karta należy do danego folderu top-level jeśli jej pierwszy segment ścieżki się zgadza.
function cardInTopFolder(card, folderName) {
    const parts = card.relativePath.split(/[\\/]/);
    return parts.length > 1 && parts[0] === folderName;
}


// Kolejka asynchronicznego dociągania nazw — jedna karta na raz, żeby nie
// zalać GameBridge setkami równoległych zapytań przy dużym folderze.
let nameFetchQueue = [];
const nameFetchQueued = new Set();
let nameFetchRunning = false;

function queueNameFetch(card) {
    const key = card.sex + "/" + card.relativePath;
    if (AppState.nameCache[key] !== undefined) return;
    if (nameFetchQueued.has(key)) return;
    nameFetchQueued.add(key);
    nameFetchQueue.push({ card, key });
    if (!nameFetchRunning) processNameFetchQueue();
}


async function processNameFetchQueue() {
    nameFetchRunning = true;
    while (nameFetchQueue.length > 0) {
        const { card, key } = nameFetchQueue.shift();
        nameFetchQueued.delete(key);
        if (AppState.nameCache[key] !== undefined) continue;
        try {
            const stats = await Api.getStats(card.sex, card.relativePath);
            const fullName = (stats && stats.fullName) ? stats.fullName : "";
            AppState.nameCache[key] = fullName;
            if (fullName) await Api.saveNameCacheEntry(key, fullName);
            updateCardLabel(key, fullName);
        } catch (e) {
            AppState.nameCache[key] = "";
        }
        scheduleResortIfNameArrived();
    }
    nameFetchRunning = false;
}

function updateCardLabel(key, fullName) {
    if (!fullName) return;
    const el = document.querySelector(`.card-thumb[data-namekey="${cssEscape(key)}"] .card-label`);
    if (el) el.textContent = fullName;
}

function cssEscape(str) {
    return str.replace(/[^a-zA-Z0-9_-]/g, c => "\\" + c);
}

// ------------------------------------------------------------
// Maps dropdown
// ------------------------------------------------------------
let allMaps = [];

async function loadMaps() {
    try {
        allMaps = await Api.getMaps();
    } catch (e) {
        console.warn("Could not load maps (is GameBridge running?)", e);
        allMaps = [];
    }
    renderMapOptions();
}

function renderMapOptions() {
    const select = document.getElementById("map-select");
    select.innerHTML = "";
    const favIds = new Set(AppState.favorites.favoriteMaps);
    const list = AppState.showOnlyFavoriteMaps ? allMaps.filter(m => favIds.has(m.id)) : allMaps;

    for (const map of list) {
        const opt = document.createElement("option");
        opt.value = map.id;
        const star = favIds.has(map.id) ? "★ " : "";
        opt.textContent = star + map.name + " (" + map.id + ")";
        select.appendChild(opt);
    }

    const favBtn = document.getElementById("toggle-fav-map-btn");
    favBtn.onclick = () => {
        const mapId = parseInt(select.value, 10);
        if (!isNaN(mapId)) toggleFavoriteMap(mapId);
    };
}

// ------------------------------------------------------------
// Folder column (osobno male/female)
// ------------------------------------------------------------
let allCharacters = { male: [], female: [] };
let HoneyBattleScores = {};
let PersonLinks = {};
let PersonLinkMains = {};

async function loadFolders() {
    await ensureCharactersLoaded();
    renderFolders();
}

async function ensureCharactersLoaded() {
    if (allCharacters.male.length || allCharacters.female.length) return;
    try {
        allCharacters.female = await Api.getCharacters("female");
        allCharacters.male = await Api.getCharacters("male");
    } catch (e) {
        console.warn("Could not load characters (is GameBridge running?)", e);
    }
}

// Pełne przeładowanie listy kart z dysku — ensureCharactersLoaded ma guard na
// niepustą tablicę, więc bez wyzerowania nic by nie pobrał ponownie.
async function refreshCards() {
    const btn = document.getElementById("refresh-cards-btn");
    if (btn) btn.disabled = true;
    allCharacters = { male: [], female: [] };
    try {
        await ensureCharactersLoaded();
        await loadFavoriteCardsGlobal();
        await loadPersonLinksGlobal();
        ActivityLog.push("Card list refreshed (" + (allCharacters.male.length + allCharacters.female.length) + " cards).");
    } catch (e) {
        ActivityLog.push("Failed to refresh cards: " + e);
    } finally {
        if (btn) btn.disabled = false;
    }
    renderFolders();
    renderCards();
    renderSlots();
}

function extractFolders(cards) {
    const set = new Set();
    for (const card of cards) {
        const parts = card.relativePath.split(/[\\/]/);
        if (parts.length > 1) set.add(parts.slice(0, -1).join("\\"));
    }
    return Array.from(set).sort();
}

function appendSelectableFolderItem(container, sex, selectionKey, label, favKey, isFav) {
    const item = document.createElement("div");
    item.className = "folder-item" + (AppState.selection === selectionKey ? " selected" : "");

    const labelEl = document.createElement("span");
    labelEl.textContent = (isFav ? "★ " : "") + label;
    item.appendChild(labelEl);

    item.addEventListener("click", () => selectFolder(selectionKey));

    const favBtn = document.createElement("button");
    favBtn.className = "folder-fav-btn";
    favBtn.textContent = isFav ? "★" : "☆";
    favBtn.title = "Toggle favorite";
    favBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (favKey === "__all__") toggleFavoriteAll();
        else toggleFavoriteFolder(sex, favKey);
    });
    item.appendChild(favBtn);

    container.appendChild(item);
}



function renderFolders() {
    const container = document.getElementById("folder-list");
    container.innerHTML = "";

    if (AppState.favoriteCards.length > 0) {
        const favItem = document.createElement("div");
        favItem.className = "folder-item" + (AppState.selection === "__favcards__" ? " selected" : "");
        const favLabel = document.createElement("span");
        favLabel.textContent = "★ Favorite Cards (" + AppState.favoriteCards.length + ")";
        favItem.appendChild(favLabel);
        favItem.addEventListener("click", () => selectFolder("__favcards__"));
        container.appendChild(favItem);
    }

    appendSelectableFolderItem(container, null, "all", "(all)", "__all__", !!AppState.favorites.favoriteAll);

    for (const sex of ["male", "female"]) {
        const header = document.createElement("div");
        header.className = "folder-sex-header";
        header.textContent = sex === "male" ? "Male folders" : "Female folders";
        container.appendChild(header);

        const favSet = new Set(AppState.favorites.favoriteFolders[sex]);

        appendSelectableFolderItem(container, sex, sex, sex === "male" ? "Male" : "Female", "__sex__", favSet.has("__sex__"));
        appendSelectableFolderItem(container, sex, sex + ":__root__", "(root)", "__root__", favSet.has("__root__"));

        const topFolders = extractTopFolders(allCharacters[sex]);
        const visibleFolders = AppState.showOnlyFavoriteFolders ? topFolders.filter(f => favSet.has(f)) : topFolders;

        for (const folder of visibleFolders) {
            appendSelectableFolderItem(container, sex, sex + ":" + folder, folder, folder, favSet.has(folder));
        }
    }
}

function toggleTopPanel() {
    AppState.uiSettings.topPanelCollapsed = !AppState.uiSettings.topPanelCollapsed;
    applyTopPanelState();
    persistUiSettings();
}

function applyTopPanelState() {
    const collapsed = !!AppState.uiSettings.topPanelCollapsed;
    document.getElementById("top-panel").classList.toggle("collapsed", collapsed);
    const btn = document.getElementById("top-panel-toggle-btn");
    btn.textContent = collapsed ? "▼" : "▲";
    btn.title = collapsed ? "Expand control panel" : "Collapse control panel";
}

function toggleFolderColumn() {
    AppState.uiSettings.folderPanelCollapsed = !AppState.uiSettings.folderPanelCollapsed;
    applyFolderColumnState();
    persistUiSettings();
}

function applyFolderColumnState() {
    const collapsed = !!AppState.uiSettings.folderPanelCollapsed;
    document.getElementById("folder-column").classList.toggle("collapsed", collapsed);
    const btn = document.getElementById("folder-toggle-btn");
    btn.textContent = collapsed ? "▶" : "◀";
    btn.title = collapsed ? "Expand folder list" : "Collapse folder list";
}

// ------------------------------------------------------------
// Card panel (prawy panel)
// ------------------------------------------------------------
async function loadCards() {
    await ensureCharactersLoaded();
    renderCards();
}

function cardMatchesFolder(card, folder) {
    if (folder === null) return true;
    return card.relativePath.split(/[\\/]/).slice(0, -1).join("\\") === folder;
}

function cardMatchesSelection(card, sex) {
    const sel = AppState.selection;
    if (sel === "__favcards__") return isFavoriteCard(card);
    if (sel === "all") {
        // Gdy aktywny jest toggle "Show only favorite folders", wybór "(all)"
        // nie oznacza już dosłownie wszystkiego — pokazujemy wszystkie karty,
        // ale tylko z folderów oznaczonych jako favorite (obu płci).
        if (AppState.showOnlyFavoriteFolders) return isCardFavorited(card);
        return true;
    }
    if (sel === sex) return true;
    if (sel === sex + ":__root__") return isRootCard(card);
    if (sel.startsWith(sex + ":")) return cardInTopFolder(card, sel.substring(sex.length + 1));
    return false;
}

function cardMatchesSearch(card) {
    const q = AppState.searchQuery.trim().toLowerCase();
    if (!q) return true;
    const fileName = card.relativePath.split(/[\\/]/).pop().toLowerCase();
    const key = card.sex + "/" + card.relativePath;
    const fullName = (AppState.nameCache[key] || "").toLowerCase();
    return fileName.includes(q) || fullName.includes(q) || card.relativePath.toLowerCase().includes(q);
}

const HB_GRADE_ORDER = ["NG", "D", "C", "B", "A", "S", "SS", "SSS", "SR", "SSR"];

function cardFileName(card) {
    return card.relativePath.split(/[\\/]/).pop();
}

function cardDisplayName(card) {
    const key = card.sex + "/" + card.relativePath;
    const cached = AppState.nameCache[key];
    return cached ? cached : cardFileName(card);
}

const cardCollator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function cardSortKey(card) {
    const name = cardDisplayName(card);
    const stripped = name.replace(/^[^\p{L}\p{N}]+/u, "").trim();
    return stripped || name;
}

function cardHbScore(card) {
    const key = card.sex + "/" + card.relativePath;
    return HoneyBattleScores[key]?.score;
}

function cardHbGrade(card) {
    return honeyBattleGradeFor(cardHbScore(card));
}

// Zwraca kartę reprezentującą personę tej karty: główną kartę grupy (jeśli
// zalinkowana), albo samą siebie. Sortowanie po tym daje realne grupowanie
// person po imieniu, zamiast po surowej ścieżce pliku.
function personaRepresentativeCard(card) {
    const key = card.sex + "/" + card.relativePath;
    const mainKey = PersonLinkMains[key];
    if (!mainKey || mainKey === key) return card;
    return findCardByKey(mainKey) || card;
}

function cardPersonaSortName(card) {
    return cardDisplayName(personaRepresentativeCard(card));
}

function cardPersonaMainKey(card) {
    const key = card.sex + "/" + card.relativePath;
    if ((PersonLinks[key] || []).length === 0) return null;
    return PersonLinkMains[key] || key;
}

function cardIsPersonaMain(card) {
    const key = card.sex + "/" + card.relativePath;
    return cardPersonaMainKey(card) === key;
}

function cardPersonaSortKey(card) {
    const rep = personaRepresentativeCard(card);
    return cardSortKey(rep);
}

// GameBridge nie zawsze zwraca znaczniki czasu — próbujemy kilku popularnych
// nazw pól; jeśli żadnego nie ma, karta ląduje na końcu sortowania.
function cardDateValue(card, kind) {
    const fields = kind === "created"
        ? ["createdUtc", "createdAtUtc", "createdAt", "creationTimeUtc"]
        : ["lastEditedUtc", "lastModifiedUtc", "modifiedUtc", "modifiedAtUtc", "lastWriteTimeUtc"];
    for (const f of fields) {
        if (card[f]) {
            const t = new Date(card[f]).getTime();
            if (!isNaN(t)) return t;
        }
    }
    return null;
}



function sortCards(cards) {
    const mode = AppState.uiSettings.cardSortMode || "name";
    const sorted = cards.slice();

    switch (mode) {
        case "score":
            sorted.sort((a, b) => (cardHbScore(b) ?? -1) - (cardHbScore(a) ?? -1));
            break;
        case "grade":
            sorted.sort((a, b) => HB_GRADE_ORDER.indexOf(cardHbGrade(b)) - HB_GRADE_ORDER.indexOf(cardHbGrade(a)));
            break;
        case "lastEdited":
            sorted.sort((a, b) => (cardDateValue(b, "edited") ?? -Infinity) - (cardDateValue(a, "edited") ?? -Infinity));
            break;
        case "created":
            sorted.sort((a, b) => (cardDateValue(b, "created") ?? -Infinity) - (cardDateValue(a, "created") ?? -Infinity));
            break;
        case "persona":
    sorted.sort((a, b) => {
        const aMain = cardPersonaMainKey(a);
        const bMain = cardPersonaMainKey(b);
        if ((aMain === null) !== (bMain === null)) return aMain === null ? 1 : -1;
        const byPersona = cardCollator.compare(cardPersonaSortKey(a), cardPersonaSortKey(b));
        if (byPersona !== 0) return byPersona;
        if (aMain !== null && aMain === bMain) {
            const aIsMain = cardIsPersonaMain(a);
            const bIsMain = cardIsPersonaMain(b);
            if (aIsMain !== bIsMain) return aIsMain ? -1 : 1;
        }
        return cardCollator.compare(cardSortKey(a), cardSortKey(b)) || cardCollator.compare(cardFileName(a), cardFileName(b));
    });
    break;
        case "name":
default:
    sorted.sort((a, b) => cardCollator.compare(cardSortKey(a), cardSortKey(b)) || cardCollator.compare(cardFileName(a), cardFileName(b)));
    break;
    }
    return sorted;
}

// Tryby sortowania zależne od realnych imion (nameCache) — dociąga się
// asynchronicznie, więc pierwszy render bywa niepełny. Gdy kolejna nazwa
// doładuje się w tle, przerysowujemy listę (z debounce), żeby kolejność
// sama się "domknęła" do poprawnej bez akcji użytkownika.
const NAME_DEPENDENT_SORT_MODES = ["name", "persona"];
let resortDebounceTimer = null;
let resortMaxTimer = null;
function scheduleResortIfNameArrived() {
    const mode = AppState.uiSettings.cardSortMode || "name";
    if (!NAME_DEPENDENT_SORT_MODES.includes(mode)) return;
    if (AppState.currentView !== "main") return;

    clearTimeout(resortDebounceTimer);
    resortDebounceTimer = setTimeout(doResort, 250);
    if (resortMaxTimer === null) resortMaxTimer = setTimeout(doResort, 3000);
}

function doResort() {
    clearTimeout(resortDebounceTimer);
    clearTimeout(resortMaxTimer);
    resortDebounceTimer = null;
    resortMaxTimer = null;
    renderCards();
}

function renderCards() {
    const panel = document.getElementById("card-panel");
    panel.innerHTML = "";

    const searching = AppState.searchQuery.trim().length > 0;
    const matched = [];

    for (const sex of ["male", "female"]) {
        for (const card of allCharacters[sex]) {
            if (!cardMatchesSearch(card)) continue;
            if (!searching && !cardMatchesSelection(card, sex)) continue;
            matched.push(card);
        }
    }

    for (const card of sortCards(matched)) {
        appendCardThumb(panel, card);
    }
}

function appendCardThumb(panel, card) {
    const key = card.sex + "/" + card.relativePath;
    const fileName = card.relativePath.split(/[\\/]/).pop();
    const cachedName = AppState.nameCache[key];

    const thumb = document.createElement("div");
    thumb.className = "card-thumb";
    thumb.setAttribute("data-namekey", key);
    if (AppState.linkModeActive && AppState.linkSelection.includes(key)) thumb.classList.add("selected-for-link");

    const img = document.createElement("img");
    img.src = Api.thumbnailUrl(card.sex, card.relativePath);
    img.loading = "lazy";
    thumb.appendChild(img);

    const favBtn = document.createElement("button");
    favBtn.className = "card-fav-btn" + (isFavoriteCard(card) ? " is-favorite" : "");
    favBtn.textContent = isFavoriteCard(card) ? "★" : "☆";
    favBtn.title = "Toggle favorite";
    favBtn.addEventListener("click", (e) => { e.stopPropagation(); toggleFavoriteCard(card); });
    thumb.appendChild(favBtn);

    const heartBtn = document.createElement("button");
    heartBtn.className = "card-heart-btn";
    heartBtn.textContent = "♥";
    heartBtn.addEventListener("click", (e) => e.stopPropagation());
    thumb.appendChild(heartBtn);

     const hbScore = HoneyBattleScores[key]?.score;
    if (hbScore !== undefined) {
        const grade = honeyBattleGradeFor(hbScore);

        const gradeBadge = document.createElement("div");
        gradeBadge.className = "hb-grade-corner-badge " + honeyBattleGradeClass(grade);
        gradeBadge.textContent = grade;
        thumb.appendChild(gradeBadge);

        const scoreBadge = document.createElement("div");
        scoreBadge.className = "hb-score-badge";
        scoreBadge.textContent = hbScore.toFixed(1);
        thumb.appendChild(scoreBadge);
    }

    const siblingCount = (PersonLinks[key] || []).length;
    if (siblingCount > 0) {
        const linkBadge = document.createElement("div");
        linkBadge.className = "hb-link-badge";
        linkBadge.textContent = "🔗";
        linkBadge.title = "Linked to " + siblingCount + " other card(s) of the same person";
        thumb.appendChild(linkBadge);
    }

    const label = document.createElement("div");
    label.className = "card-label";
    label.textContent = cachedName ? cachedName : fileName;
    thumb.appendChild(label);

    thumb.addEventListener("click", () => {
        if (AppState.linkModeActive) { toggleCardLinkSelection(card); return; }
        openPreview(card);
    });
    panel.appendChild(thumb);

    if (cachedName === undefined) queueNameFetch(card);
}

function selectFolder(selectionKey) {
    AppState.selection = selectionKey;
    if (selectionKey === "__favcards__") {
        const orphans = orphanedFavoriteKeys();
        if (orphans.length > 0) ActivityLog.push("Favorite Cards contains " + orphans.length + " entry/entries whose card file no longer exists on disk. To clear them, delete favoritecards.json (it sits next to ControlPanel.Server.exe) this resets ALL favorites.");
    }
    renderFolders();
    renderCards();
}

// ------------------------------------------------------------
// Link Same Person mode (mark multiple cards as the same character)
// ------------------------------------------------------------
function toggleLinkMode() {
    AppState.linkModeActive = !AppState.linkModeActive;
    AppState.linkSelection = [];
    updateLinkModeUI();
    renderCards();
}

function updateLinkModeUI() {
    const toggleBtn = document.getElementById("link-same-person-btn");
    const confirmBtn = document.getElementById("link-confirm-btn");
    toggleBtn.classList.toggle("active", AppState.linkModeActive);
    toggleBtn.textContent = AppState.linkModeActive ? "Cancel Selection" : "🔗 Link Persona";
    confirmBtn.style.display = AppState.linkModeActive ? "inline-block" : "none";
    confirmBtn.textContent = "Confirm Link (" + AppState.linkSelection.length + ")";
    confirmBtn.disabled = AppState.linkSelection.length < 2;
}

function toggleCardLinkSelection(card) {
    const key = card.sex + "/" + card.relativePath;
    const idx = AppState.linkSelection.indexOf(key);
    if (idx === -1) AppState.linkSelection.push(key); else AppState.linkSelection.splice(idx, 1);
    updateLinkModeUI();
    renderCards();
}

async function confirmLinkSelection() {
    if (AppState.linkSelection.length < 2) return;
    try {
        await Api.linkSamePerson(AppState.linkSelection);
        // The server may have just synced every group member to the group's max score
        // (see PersonLinkStore.LinkKeys / StaticFileServer.HandlePersonLinksLink) — reload
        // HoneyBattleScores too, not just the links, or the newly-linked cards keep showing
        // their pre-link score/grade badges until a manual page refresh.
        await loadHoneyBattleScoresGlobal();
        await loadPersonLinksGlobal();
        await loadFavoriteCardsGlobal();
        ActivityLog.push("Linked " + AppState.linkSelection.length + " cards as the same person.");
    } catch (e) {
        ActivityLog.push("Failed to link cards: " + e);
    }
    AppState.linkModeActive = false;
    AppState.linkSelection = [];
    updateLinkModeUI();
    renderCards();
}

function findCardByKey(key) {
    const slashIdx = key.indexOf("/");
    if (slashIdx === -1) return null;
    const sex = key.substring(0, slashIdx);
    const relativePath = key.substring(slashIdx + 1);
    return (allCharacters[sex] || []).find(c => c.relativePath === relativePath) || null;
}



let currentPreviewCard = null;

async function openPreview(card) {
    currentPreviewCard = card;
    AppState.currentView = "preview";
    document.getElementById("main-view").classList.add("hidden");
    document.getElementById("preview-view").classList.add("active");
    await renderPreviewCardPanel(card);
}

async function renderPreviewCardPanel(card) {
    const panel = document.getElementById("preview-card-panel");
    panel.innerHTML = "<p>Loading stats...</p>";

    const stats = await Api.getStats(card.sex, card.relativePath);

    if (stats && stats.fullName) {
        const cacheKey = card.sex + "/" + card.relativePath;
        if (AppState.nameCache[cacheKey] !== stats.fullName) {
            AppState.nameCache[cacheKey] = stats.fullName;
            Api.saveNameCacheEntry(cacheKey, stats.fullName);
            updateCardLabel(cacheKey, stats.fullName);
        }
    }

    panel.innerHTML = "";

    const img = document.createElement("img");
    img.src = Api.thumbnailUrl(card.sex, card.relativePath);
    img.className = "preview-image";
    panel.appendChild(img);

    const info = document.createElement("div");
    info.className = "preview-info";
    if (stats) {
        info.innerHTML = `
            <h2>${escapeHtml(stats.fullName)}</h2>
            <p class="preview-filename">${escapeHtml(card.relativePath.split(/[\\/]/).pop())}</p>
            <p>State: ${escapeHtml(stats.nowState)} (${escapeHtml(stats.nowDrawState)})</p>
            <p>Favor: ${stats.favor} | Enjoyment: ${stats.enjoyment} | Aversion: ${stats.aversion}</p>
            <p>Slavery: ${stats.slavery} | Broken: ${stats.broken} | Dependence: ${stats.dependence}</p>
            <p>Resist H: ${stats.resistH} | Pain: ${stats.resistPain} | Anal: ${stats.resistAnal}</p>
            <p>H count: ${stats.hCount}</p>
        `;
    } else {
        info.innerHTML = `
            <p class="preview-filename">${escapeHtml(card.relativePath.split(/[\\/]/).pop())}</p>
            <p>Could not load stats (male cards may not expose gameinfo2 the same way).</p>
        `;
    }

    const hbScore = HoneyBattleScores[card.sex + "/" + card.relativePath]?.score;
    if (hbScore !== undefined) {
        const grade = honeyBattleGradeFor(hbScore);
        const hbP = document.createElement("p");
        hbP.innerHTML = `Honey Battle Score: <strong>${hbScore.toFixed(1)}</strong> <span class="hb-grade-badge ${honeyBattleGradeClass(grade)}">${grade}</span>`;
        info.appendChild(hbP);
    }

    const key = card.sex + "/" + card.relativePath;
    const siblingKeys = PersonLinks[key] || [];
    if (siblingKeys.length > 0) {
        const samePersonSection = document.createElement("div");
        samePersonSection.className = "same-person-section";

         const headingRow = document.createElement("div");
        headingRow.className = "same-person-heading-row";

        const heading = document.createElement("h3");
        heading.textContent = "Same person (" + siblingKeys.length + " other card" + (siblingKeys.length > 1 ? "s" : "") + ")";
        headingRow.appendChild(heading);

        if (PersonLinkMains[key] === key) {
            const badge = document.createElement("span");
            badge.className = "same-person-main-badge";
            badge.textContent = "★ Main Card";
            headingRow.appendChild(badge);
        } else {
            const setMainBtn = document.createElement("button");
            setMainBtn.className = "same-person-main-btn";
            setMainBtn.textContent = "Set as Main Card";
            setMainBtn.title = "This card will always represent the persona in Honey Battle";
            setMainBtn.addEventListener("click", async () => {
                try {
                    await Api.setPersonLinkMain(key);
                    await loadPersonLinksGlobal();
                    openPreview(card);
                } catch (e) {
                    ActivityLog.push("Failed to set main card: " + e);
                }
            });
            headingRow.appendChild(setMainBtn);
        }

        samePersonSection.appendChild(headingRow);

        const gallery = document.createElement("div");
        gallery.className = "same-person-gallery";
        for (const siblingKey of siblingKeys) {
            const siblingCard = findCardByKey(siblingKey);
            if (!siblingCard) continue;
            const siblingThumb = document.createElement("img");
            siblingThumb.className = "same-person-thumb";
            siblingThumb.src = Api.thumbnailUrl(siblingCard.sex, siblingCard.relativePath);
            siblingThumb.title = siblingCard.relativePath.split(/[\\/]/).pop();
            siblingThumb.addEventListener("click", () => openPreview(siblingCard));
            gallery.appendChild(siblingThumb);
        }
        samePersonSection.appendChild(gallery);
        info.appendChild(samePersonSection);
    }

     panel.appendChild(info);

    const photoStrip = buildPreviewPhotoStripShell();
    panel.appendChild(photoStrip);
    renderPreviewPhotoStrip(card);

    const buttons = document.createElement("div");
    buttons.className = "preview-buttons";

   if (card.sex === "male") {
        buttons.appendChild(makeSelectButton("Select as Male", () => {
            AppState.slots.male = card;
            renderSlots();
            closePreview();
        }));
        buttons.appendChild(makeSelectButton("Select as Male 2", () => {
            AppState.slots.male2 = card;
            AppState.slots.female2 = null;
            renderSlots();
            closePreview();
        }));
    } else {
        buttons.appendChild(makeSelectButton("Select as Female 1", () => {
            AppState.slots.female1 = card;
            renderSlots();
            closePreview();
        }));
        buttons.appendChild(makeSelectButton("Select as Female 2", () => {
            AppState.slots.female2 = card;
            AppState.slots.male2 = null;
            renderSlots();
            closePreview();
        }));
    }

    const editBtn = document.createElement("button");
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", async () => {
        ActivityLog.push("Opening editor for " + card.relativePath.split(/[\\/]/).pop());
        if (card.sex === "male") await Api.editMale(card.relativePath);
        else await Api.editFemale(card.relativePath);
    });
    buttons.appendChild(editBtn);

    const screenshotBtn = document.createElement("button");
    screenshotBtn.textContent = "Take a Screenshot";
    screenshotBtn.addEventListener("click", () => takeScreenshotFor(card, screenshotBtn));
    buttons.appendChild(screenshotBtn);

    const setDefaultBtn = document.createElement("button");
    const currentDefaultKey = card.sex === "male" ? AppState.uiSettings.defaultMale : AppState.uiSettings.defaultFemale;
    const isDefault = currentDefaultKey === key;
    setDefaultBtn.textContent = isDefault ? "★ Default " + card.sex : "Set as Default " + card.sex;
    setDefaultBtn.disabled = isDefault;
    setDefaultBtn.title = "This card will be loadable into the " + (card.sex === "male" ? "Male" : "Female 1") + " slot with one click";
    setDefaultBtn.addEventListener("click", () => {
        setAsDefaultCard(card);
        renderPreviewCardPanel(card);
    });
    buttons.appendChild(setDefaultBtn);

    const showInExplorerBtn = document.createElement("button");
    showInExplorerBtn.textContent = "Show in Explorer";
    showInExplorerBtn.addEventListener("click", async () => {
        ActivityLog.push("Opening Explorer for " + card.relativePath.split(/[\\/]/).pop());
        const result = await Api.showInExplorer(card.sex, card.relativePath);
        ActivityLog.push(result.result || "Explorer request sent.");
    });
    buttons.appendChild(showInExplorerBtn);

const characterEditorBtn = document.createElement("button");
characterEditorBtn.textContent = "Edit in Character Editor";
characterEditorBtn.disabled = true;
characterEditorBtn.title = "Checking for CharacterEditor.Server...";
buttons.appendChild(characterEditorBtn);
Api.pingCharacterEditor().then(ping => {
    if (ping && ping.status === "ok") {
        characterEditorBtn.disabled = false;
        characterEditorBtn.title = "Open this card in CharacterEditor (full body/face/clothes editing)";
        characterEditorBtn.addEventListener("click", () => {
            const url = `${CHARACTER_EDITOR_BASE_URL}/?sex=${card.sex}&path=${encodeURIComponent(card.relativePath)}`;
            window.open(url, "_blank");
        });
    } else {
        characterEditorBtn.title = "Install/run the CharacterEditor.Server companion app to enable full character editing";
    }
});

    if (siblingKeys.length > 0) {
        const unlinkBtn = document.createElement("button");
        unlinkBtn.textContent = "Unlink from same-person group";
        unlinkBtn.addEventListener("click", async () => {
            await Api.unlinkSamePerson(key);
            await loadHoneyBattleScoresGlobal();
            await loadPersonLinksGlobal();
            openPreview(card);
        });
        buttons.appendChild(unlinkBtn);
    }

    panel.appendChild(buttons);
}

function buildPreviewPhotoStripShell() {
    const strip = document.createElement("div");
    strip.id = "preview-photo-strip";
    strip.className = "preview-photo-strip";

    const leftArrow = document.createElement("button");
    leftArrow.className = "preview-strip-arrow preview-strip-arrow-left";
    leftArrow.textContent = "◀";
    leftArrow.addEventListener("click", () => scrollPreviewStrip(strip, -1));

    const track = document.createElement("div");
    track.className = "preview-photo-strip-track";
    track.addEventListener("scroll", () => updatePreviewStripArrows(strip));

    const rightArrow = document.createElement("button");
    rightArrow.className = "preview-strip-arrow preview-strip-arrow-right";
    rightArrow.textContent = "▶";
    rightArrow.addEventListener("click", () => scrollPreviewStrip(strip, 1));

    strip.appendChild(leftArrow);
    strip.appendChild(track);
    strip.appendChild(rightArrow);
    return strip;
}

function scrollPreviewStrip(strip, direction) {
    const track = strip.querySelector(".preview-photo-strip-track");
    track.scrollBy({ left: direction * (track.clientWidth * 0.8), behavior: "smooth" });
}

function updatePreviewStripArrows(strip) {
    const track = strip.querySelector(".preview-photo-strip-track");
    const leftArrow = strip.querySelector(".preview-strip-arrow-left");
    const rightArrow = strip.querySelector(".preview-strip-arrow-right");

    requestAnimationFrame(() => {
        const overflowing = track.scrollWidth > track.clientWidth + 2;
        leftArrow.classList.toggle("visible", overflowing && track.scrollLeft > 4);
        rightArrow.classList.toggle("visible", overflowing && track.scrollLeft < track.scrollWidth - track.clientWidth - 4);
    });
}

// Gallery is the union of this card's own screenshots plus every card linked to it
// as the "same person" (see PersonLinkStore) — mirrors the "Same person" section
// shown above it in the preview.
async function renderPreviewPhotoStrip(card) {
    const key = card.sex + "/" + card.relativePath;
    const siblingKeys = PersonLinks[key] || [];
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

    // Preview may have moved on to a different card while this was loading.
    if (currentPreviewCard !== card) return;

    const strip = document.getElementById("preview-photo-strip");
    if (!strip) return;
    const track = strip.querySelector(".preview-photo-strip-track");
    track.innerHTML = "";

    if (photos.length === 0) {
        const empty = document.createElement("span");
        empty.className = "preview-photo-strip-empty";
        empty.textContent = "No screenshots yet.";
        track.appendChild(empty);
        strip.querySelector(".preview-strip-arrow-left").classList.remove("visible");
        strip.querySelector(".preview-strip-arrow-right").classList.remove("visible");
        return;
    }

    for (const photo of photos) {
        const wrap = document.createElement("div");
        wrap.className = "preview-strip-thumb-wrap";

        const img = document.createElement("img");
        img.className = "preview-strip-thumb";
        img.src = Api.screenshotFileUrl(photo.thumbFileName);
        img.loading = "lazy";
        img.addEventListener("click", () => openLightbox(Api.screenshotFileUrl(photo.fileName)));
        wrap.appendChild(img);

        const removeBtn = document.createElement("button");
        removeBtn.className = "preview-strip-remove-btn";
        removeBtn.textContent = "✕";
        removeBtn.title = "Remove from gallery";
        removeBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            try {
                await Api.removePhotoFromGallery(photo.ownerKey, photo.fileName);
                renderPreviewPhotoStrip(card);
            } catch (err) {
                ActivityLog.push("Failed to remove photo: " + err);
            }
        });
        wrap.appendChild(removeBtn);

        track.appendChild(wrap);
    }

    updatePreviewStripArrows(strip);
}

window.addEventListener("resize", () => {
    const strip = document.getElementById("preview-photo-strip");
    if (strip) updatePreviewStripArrows(strip);
});

// Shared by both the "Take a Screenshot" button on the card side and the one on the
// gallery side, so either place gives the same capture + save + feedback behavior.
async function takeScreenshotFor(card, triggerBtn) {
    const key = card.sex + "/" + card.relativePath;
    if (triggerBtn) triggerBtn.disabled = true;
    try {
        const result = await Api.takeScreenshot();
        if (result && result.result === "ok") {
            await Api.addPhotoToGallery(key, result.fileName, result.thumbFileName);
            ActivityLog.push("Screenshot saved to gallery for " + card.relativePath.split(/[\\/]/).pop());
            showScreenshotToast();
            if (currentPreviewCard === card) renderPreviewPhotoStrip(card);
        } else {
            ActivityLog.push("Failed to take screenshot: " + (result && result.error ? result.error : "unknown error"));
        }
    } catch (e) {
        ActivityLog.push("Failed to take screenshot: " + e);
    } finally {
        if (triggerBtn) triggerBtn.disabled = false;
    }
}

let screenshotToastTimeout = null;
function showScreenshotToast() {
    const toast = document.getElementById("screenshot-toast");
    toast.classList.add("visible");
    clearTimeout(screenshotToastTimeout);
    screenshotToastTimeout = setTimeout(() => toast.classList.remove("visible"), 1600);
}

function openLightbox(url) {
    document.getElementById("lightbox-img").src = url;
    document.getElementById("lightbox-overlay").classList.add("active");
}

function closeLightbox() {
    document.getElementById("lightbox-overlay").classList.remove("active");
    document.getElementById("lightbox-img").src = "";
}

function makeSelectButton(label, onClick) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.addEventListener("click", onClick);
    return btn;
}

function closePreview() {
    AppState.currentView = "main";
    currentPreviewCard = null;
    document.getElementById("main-view").classList.remove("hidden");
    document.getElementById("preview-view").classList.remove("active");
}

// Merged across every card linked as the "same person" (see PersonLinkStore), so
// screenshots taken from any of a persona's card variants show up in one gallery —
// mirrors the "Same person" gallery already shown in this preview screen.
async function openPhotoGallery(card) {
    const key = card.sex + "/" + card.relativePath;
    const siblingKeys = PersonLinks[key] || [];
    const allKeys = [key, ...siblingKeys];

    const modal = document.getElementById("photo-gallery-modal");
    const grid = document.getElementById("photo-gallery-grid");
    const emptyMsg = document.getElementById("photo-gallery-empty");
    const title = document.getElementById("photo-gallery-title");
    const fileName = card.relativePath.split(/[\\/]/).pop();
    const cachedName = AppState.nameCache[key];
    title.textContent = "Photo Gallery — " + (cachedName ? cachedName : fileName);

    modal.style.display = "flex";
    grid.innerHTML = "";
    emptyMsg.style.display = "none";

    let photos = [];
    try {
        const perKeyResults = await Promise.all(
            allKeys.map(k => Api.getPhotoGallery(k).then(list => (list || []).map(p => ({ ...p, ownerKey: k }))))
        );
        photos = perKeyResults.flat().sort((a, b) => new Date(b.takenAtUtc) - new Date(a.takenAtUtc));
    } catch (e) {
        ActivityLog.push("Failed to load photo gallery: " + e);
    }

    if (photos.length === 0) {
        emptyMsg.style.display = "block";
        return;
    }

    for (const photo of photos) {
        const item = document.createElement("div");
        item.className = "photo-gallery-item";

        const img = document.createElement("img");
        img.src = Api.screenshotFileUrl(photo.thumbFileName);
        img.loading = "lazy";
        item.appendChild(img);

        item.addEventListener("click", () => window.open(Api.screenshotFileUrl(photo.fileName), "_blank"));

        const removeBtn = document.createElement("button");
        removeBtn.className = "photo-gallery-remove-btn";
        removeBtn.textContent = "✕";
        removeBtn.title = "Remove from gallery";
        removeBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            try {
                await Api.removePhotoFromGallery(photo.ownerKey, photo.fileName);
                openPhotoGallery(card);
            } catch (err) {
                ActivityLog.push("Failed to remove photo: " + err);
            }
        });
        item.appendChild(removeBtn);

        grid.appendChild(item);
    }
}

function closePhotoGallery() {
    document.getElementById("photo-gallery-modal").style.display = "none";
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ------------------------------------------------------------
// Slots (male / female1 / female2 \ male2)
// ------------------------------------------------------------
function renderSlots() {
    applySlotVisual("male", AppState.slots.male);
    applySlotVisual("female1", AppState.slots.female1);
    applySlotVisual("extra", AppState.slots.male2 || AppState.slots.female2);
}

function defaultSlotSettingKey(slotName) {
    if (slotName === "male") return "defaultMale";
    if (slotName === "female1") return "defaultFemale";
    return null;
}

function getDefaultCardFor(slotName) {
    const settingKey = defaultSlotSettingKey(slotName);
    if (!settingKey) return null;
    const cardKey = AppState.uiSettings[settingKey];
    if (!cardKey) return null;
    return findCardByKey(cardKey);
}

function loadDefaultIntoSlot(slotName) {
    const card = getDefaultCardFor(slotName);
    if (!card) {
        ActivityLog.push("Default card for " + slotName + " no longer exists on disk, open a card in Preview and set a new default.");
        return;
    }
    AppState.slots[slotName] = card;
    renderSlots();
    ActivityLog.push("Loaded default " + slotName + ": " + cardDisplayName(card));
}

function setAsDefaultCard(card) {
    const settingKey = card.sex === "male" ? "defaultMale" : "defaultFemale";
    AppState.uiSettings[settingKey] = card.sex + "/" + card.relativePath;
    persistUiSettings();
    renderSlots();
    ActivityLog.push("Set " + cardDisplayName(card) + " as default " + card.sex + ".");
}

function applySlotVisual(slotName, card) {
    const el = document.getElementById("slot-" + slotName);
    const defaultBtn = el.querySelector(".slot-default-btn");
    if (card) {
        el.classList.add("filled");
        el.style.backgroundImage = `url(${Api.thumbnailUrl(card.sex, card.relativePath)})`;
        el.querySelector(".slot-label").style.display = "none";
        if (defaultBtn) defaultBtn.style.display = "none";
    } else {
        el.classList.remove("filled");
        el.style.backgroundImage = "";
        el.querySelector(".slot-label").style.display = "block";
        if (slotName === "extra") el.querySelector(".slot-label").textContent = "Female 2 / Male 2 (optional)";
        if (defaultBtn) defaultBtn.style.display = defaultSlotSettingKey(slotName) && AppState.uiSettings[defaultSlotSettingKey(slotName)] ? "block" : "none";
    }
}

// ------------------------------------------------------------
// Static buttons (RUN H, chill, create new, back, slot click)
// ------------------------------------------------------------
function bindStaticButtons() {
     document.getElementById("back-to-main-btn").addEventListener("click", closePreview);
    document.getElementById("lightbox-close-btn").addEventListener("click", closeLightbox);
    document.getElementById("lightbox-overlay").addEventListener("click", (e) => {
        if (e.target.id === "lightbox-overlay") closeLightbox();
    });
    document.getElementById("top-panel-toggle-btn").addEventListener("click", toggleTopPanel);
    document.getElementById("folder-toggle-btn").addEventListener("click", toggleFolderColumn);
     document.getElementById("mainview-cards-btn").addEventListener("click", () => switchMainView("cards"));
    document.getElementById("mainview-honeybattle-btn").addEventListener("click", () => switchMainView("honeybattle"));
    document.getElementById("mainview-about-btn").addEventListener("click", () => switchMainView("about"));
    document.getElementById("photo-gallery-close-btn").addEventListener("click", closePhotoGallery);

    document.getElementById("chill-on-btn").addEventListener("click", async () => {
        await Api.setChill(true);
        ActivityLog.push("Chill mode ON(MaxFPS = 1)");
    });
    document.getElementById("chill-off-btn").addEventListener("click", async () => {
        await Api.setChill(false);
        ActivityLog.push("Chill mode OFF");
    });

    document.getElementById("create-new-male").addEventListener("click", async () => {
        await Api.createNew("male");
        ActivityLog.push("Creating new male character...");
    });
    document.getElementById("create-new-female").addEventListener("click", async () => {
        await Api.createNew("female");
        ActivityLog.push("Creating new female character...");
    });
    document.getElementById("refresh-cards-btn").addEventListener("click", refreshCards);

     document.getElementById("sort-select").addEventListener("change", (e) => {
        AppState.uiSettings.cardSortMode = e.target.value;
        persistUiSettings();
        renderCards();
    });

    document.getElementById("link-same-person-btn").addEventListener("click", toggleLinkMode);
    document.getElementById("link-confirm-btn").addEventListener("click", confirmLinkSelection);

    for (const slotName of ["male", "female1"]) {
        document.getElementById("slot-" + slotName).addEventListener("click", (e) => {
            if (e.target.closest(".slot-remove-btn")) return;
            const card = AppState.slots[slotName];
            if (card) openPreview(card);
        });
    }
    document.getElementById("slot-extra").addEventListener("click", (e) => {
        if (e.target.closest(".slot-remove-btn")) return;
        const card = AppState.slots.male2 || AppState.slots.female2;
        if (card) openPreview(card);
    });

    document.getElementById("status-search-btn").addEventListener("click", runSearch);
document.getElementById("status-search").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
});
document.getElementById("status-search-clear-btn").addEventListener("click", clearSearch);


document.getElementById("toggle-focus-on-loaded").addEventListener("change", (e) => {
        AppState.uiSettings.focusOnLoadedScene = e.target.checked;
        persistUiSettings();
    });
    document.getElementById("toggle-sound-on-loaded").addEventListener("change", (e) => {
        AppState.uiSettings.soundOnLoadedScene = e.target.checked;
        persistUiSettings();
    });

    document.querySelectorAll(".slot-remove-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            const slotName = btn.getAttribute("data-slot");
            if (slotName === "extra") { AppState.slots.female2 = null; AppState.slots.male2 = null; }
            else AppState.slots[slotName] = null;
            renderSlots();
        });
    });

     document.querySelectorAll(".slot-default-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            loadDefaultIntoSlot(btn.getAttribute("data-slot"));
        });
    });

    document.getElementById("run-h-btn").addEventListener("click", runH);
}

function switchMainView(view) {
    AppState.mainView = view;
    document.querySelectorAll(".main-content-view").forEach(el => {
        el.classList.toggle("active", el.id === "view-" + view);
    });
    document.querySelectorAll(".mainview-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.view === view);
    });
}


function runSearch() {
    const input = document.getElementById("status-search");
    AppState.searchQuery = input.value;
    renderCards();
}

function clearSearch() {
    AppState.searchQuery = "";
    document.getElementById("status-search").value = "";
    renderCards();
}

async function runH() {
    const { male, female1, female2, male2 } = AppState.slots;
    if (!male || !female1) {
        alert("Male and Female 1 slots must be filled before running.");
        return;
    }
    const mapId = parseInt(document.getElementById("map-select").value, 10) || 3;

    const btn = document.getElementById("run-h-btn");
    btn.disabled = true;
    btn.textContent = "Loading...";
    ActivityLog.push("Starting H scene...");

    try {
        let result;
        if (male2) {
            result = await Api.loadHMaleTrioScene(male.relativePath, female1.relativePath, male2.relativePath, mapId);
        } else if (female2) {
            result = await Api.loadHTrioScene(male.relativePath, female1.relativePath, female2.relativePath, mapId);
        } else {
            result = await Api.loadHScene(male.relativePath, female1.relativePath, mapId);
        }
        ActivityLog.push(result.result || "H scene requested.");
    } catch (e) {
        ActivityLog.push("Failed to run H scene: " + e);
        alert("Failed to run H scene: " + e);
    } finally {
        btn.textContent = "RUN H";
        btn.disabled = false;
    }
}