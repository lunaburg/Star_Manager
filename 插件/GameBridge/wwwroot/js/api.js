const Api = {
    async getCharacters(sex) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/characters${sex ? "?sex=" + sex : ""}`;
        const res = await fetch(url);
        return res.json();
    },

    async getStats(sex, path) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/stats?sex=${sex}&path=${encodeURIComponent(path)}`;
        const res = await fetch(url);
        if (!res.ok) return null;
        return res.json();
    },

    async showInExplorer(sex, path) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/showInExplorer?sex=${sex}&path=${encodeURIComponent(path)}`;
        const res = await fetch(url);
        return res.json();
    },

    async pingCharacterEditor() {
    try {
        const res = await fetch(`${CHARACTER_EDITOR_BASE_URL}/api/ping`);
        if (!res.ok) return null;
        return res.json();
    } catch (e) {
        return null;
    }
},

    async getState() {
        const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/state`);
        return res.json();
    },

    async getMaps() {
        const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/maps`);
        return res.json();
    },

    async getFavorites() {
        const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/favorites`);
        return res.json();
    },

    async saveFavorites(favoritesObj) {
        const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/favorites`, {
            method: "POST",
            body: JSON.stringify(favoritesObj)
        });
        return res.json();
    },
 async takeScreenshot() {
        const url = `${GAMEBRIDGE_BASE_URL}/api/screenshot`;
        const res = await fetch(url);
        return res.json();
    },

    screenshotFileUrl(fileName) {
        return `${GAMEBRIDGE_BASE_URL}/api/screenshotFile?name=${encodeURIComponent(fileName)}`;
    },

    async getPhotoGallery(key) {
        const res = await fetch(`/api/photoGallery?key=${encodeURIComponent(key)}`);
        return res.json();
    },

    async addPhotoToGallery(key, fileName, thumbFileName) {
        const res = await fetch(`/api/photoGallery/add`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, fileName, thumbFileName })
        });
        return res.json();
    },

    async removePhotoFromGallery(key, fileName) {
        const res = await fetch(`/api/photoGallery/remove`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key, fileName })
        });
        return res.json();
    },


    async focusGame() {
    const url = `${GAMEBRIDGE_BASE_URL}/api/command?cmd=focusGame`;
    const res = await fetch(url);
    return res.json();
},

async getUiSettings() {
    const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/uiSettings`);
    return res.json();
},

async saveUiSettings(settingsObj) {
    const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/uiSettings`, {
        method: "POST",
        body: JSON.stringify(settingsObj)
    });
    return res.json();
},

    async getNameCache() {
        const res = await fetch(`${GAMEBRIDGE_BASE_URL}/api/nameCache`);
        return res.json();
    },

    async saveNameCacheEntry(key, name) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/nameCache?key=${encodeURIComponent(key)}&name=${encodeURIComponent(name)}`;
        const res = await fetch(url, { method: "POST" });
        return res.json();
    },

    async loadHScene(male, female1, mapId) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/loadHScene?male=${encodeURIComponent(male)}&female1=${encodeURIComponent(female1)}&mapId=${mapId}`;
        const res = await fetch(url);
        return res.json();
    },

    async loadHTrioScene(male, female1, female2, mapId) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/loadHTrioScene?male=${encodeURIComponent(male)}&female1=${encodeURIComponent(female1)}&female2=${encodeURIComponent(female2)}&mapId=${mapId}`;
        const res = await fetch(url);
        return res.json();
    },

    async loadHMaleTrioScene(male, female1, male2, mapId) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/loadHMaleTrioScene?male=${encodeURIComponent(male)}&female1=${encodeURIComponent(female1)}&male2=${encodeURIComponent(male2)}&mapId=${mapId}`;
        const res = await fetch(url);
        return res.json();
    },

    async editFemale(path) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/editFemale?path=${encodeURIComponent(path)}`;
        const res = await fetch(url);
        return res.json();
    },
    async getHoneyBattle() {
        const res = await fetch(`/api/honeybattle`);
        return res.json();
    },

    async postHoneyBattleResult(winnerKey, loserKey, mode, useHalfDiffRule) {
        const res = await fetch(`/api/honeybattle/result`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ winnerKey, loserKey, mode, useHalfDiffRule: !!useHalfDiffRule })
        });
        return res.json();
    },

    async clearHoneyBattleScores() {
        const res = await fetch(`/api/honeybattle/clear`, { method: "POST" });
        return res.json();
    },

    async getPersonLinks() {
        const res = await fetch(`/api/personLinks`);
        return res.json();
    },
     async getPersonLinkMains() {
        const res = await fetch(`/api/personLinks/mains`);
        return res.json();
    },

    async setPersonLinkMain(key) {
        const res = await fetch(`/api/personLinks/setMain`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key })
        });
        return res.json();
    },

    async linkSamePerson(keys) {
        const res = await fetch(`/api/personLinks/link`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ keys })
        });
        return res.json();
    },

    async unlinkSamePerson(key) {
        const res = await fetch(`/api/personLinks/unlink`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key })
        });
        return res.json();
    },

    async editMale(path) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/editMale?path=${encodeURIComponent(path)}`;
        const res = await fetch(url);
        return res.json();
    },

    async createNew(sex) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/createNew?sex=${sex}`;
        const res = await fetch(url);
        return res.json();
    },

    async setChill(on) {
        const url = `${GAMEBRIDGE_BASE_URL}/api/command?cmd=chill%20${on ? "on" : "off"}`;
        const res = await fetch(url);
        return res.json();
    },

    thumbnailUrl(sex, path) {
        return `${GAMEBRIDGE_BASE_URL}/api/thumbnail?sex=${sex}&path=${encodeURIComponent(path)}`;
    },


async getFavoriteCards() {
        const res = await fetch(`/api/favoriteCards`);
        return res.json();
    },

    async toggleFavoriteCard(key) {
        const res = await fetch(`/api/favoriteCards/toggle`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key })
        });
        return res.json();
    },

};