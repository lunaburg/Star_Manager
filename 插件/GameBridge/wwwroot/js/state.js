const AppState = {
    slots: {
        male: null,
        female1: null,
        female2: null,
        male2: null
    },
    selection: "all",
    favorites: { favoriteMaps: [], favoriteFolders: { male: [], female: [] }, favoriteAll: false },
    showOnlyFavoriteMaps: false,
    showOnlyFavoriteFolders: false,
    currentView: "main",
    mainView: "cards",
    nameCache: {},
    searchQuery: "",
    linkModeActive: false,
    linkSelection: [],
    favoriteCards: [],
    uiSettings: {
    focusOnLoadedScene: false,
    soundOnLoadedScene: false,
    topPanelCollapsed: false,
    folderPanelCollapsed: false,
    honeyBattleFavoritesOnly: false,
    cardSortMode: "name",
    defaultMale: null,
    defaultFemale: null
}
};