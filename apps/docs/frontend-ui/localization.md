# Interface localization

## Background and root cause

The renderer originally embedded Chinese copy in Vue templates, JavaScript UI labels and dynamic status messages. Electron dialogs also embedded Chinese titles. Replacing these strings inside business logic would change comparison values, task payloads and game-facing identifiers.

## Implementation (2026-10-29)

- `language` is persisted by `normalizeSettings()` and the existing settings load/save path. Supported values are `en-US` and `zh-CN`; missing or invalid values use English.
- Settings → Startup and checks → Interface language switches immediately. `src/i18n/index.js` owns the reactive locale, updates the HTML `lang` attribute and installs `$t`. The game's language setting is independent.
- `scripts/localize-vue.mjs` runs before the Vue Vite plugin in development and production. It localizes template text, display attributes and display expressions, without changing event handlers, model values, keys, conditions or API payloads. Chinese remains the source language.
- `electron/locales/en.json` is the shared, offline English catalog. `electron/localization.mjs` matches complete entries and anchored messages with `{0}`, `{1}`, etc. Parameters retain their original content. Unknown messages fall back verbatim. No translation service or network access is used.
- Direct metadata fields (names, filenames, paths, authors, tags and versions) bypass translation. For expressions combining such fields with fallback text, only Chinese fallback literals are translated. Use explicit `$t` for new interface expressions when needed; never translate user data.
- Electron open/save/message dialogs translate copy through `showLocalizedDialog()`. Suggested filenames, filters' extensions and selected paths are preserved.
- Locale-sensitive sorting and date/number formatters use the selected locale where applicable. Stored resource data remains unchanged.
- The ordinary top bar gives the task column a smaller minimum width in English, leaving enough room for the longer action labels at the existing desktop minimum width. Item category and outfit toolbars keep their own layouts.

## Maintaining the catalog

Run from `apps/`:

```powershell
npm run check:translations
npm run test:i18n
npm run test:electron
npm run build
```

`node scripts/check-translations.mjs --list` lists uncatalogued Chinese script strings. Add a complete source-to-English entry for each new UI string, preserving every placeholder index. `check:translations` requires coverage of template text and Vue script literals. This is a source-coverage check, not proof that every possible backend response is translated.

Use `$t` only at display boundaries. Keep raw source values for status comparisons and game/backend communication. For new components that display user metadata, use direct field expressions or explicitly opt out with `v-pre` for fully static content. Do not use broad substring replacement or DOM mutation observers.

## Validation and boundaries

Validation on 2026-10-29: all 9 localization tests and all 20 existing Electron tests passed. Tests cover switching locales reactively, invalid locale normalization, exact and parameterized messages, whitespace, unknown messages, user metadata preservation, dialog options, placeholder parity and Vue compilation/rendering. The actual Electron settings normalization/load/save functions were exercised against an isolated temporary settings file and retained the saved language across a simulated restart while preserving Chinese game paths. The 2,131-entry catalog passed strict Vue source coverage with zero missing entries. `npm run build`, `node --check electron/main.cjs` and `git diff --check` passed; Vite reported its existing Lottie `eval` and bundle-size warnings.

The built interface was opened in a browser to inspect the English settings layout and switch to Chinese immediately. The initial packaging preflight identified a missing remote index; the subsequent Windows build recovered the upstream index, installed the required build runtimes and produced the complete application and ZIP. The actual packaged executable passed renderer startup and backend health smoke checks. Game operations remain unverified. Build inputs, provenance, dependency warnings and results are recorded in [Windows packaging](../packaging-windows.md#english-build-verification-2026-10-29).

The catalog covers the current Vue interface and known application messages, with additional native-dialog and achievement copy. Unknown backend errors, low-level task logs, game/mod/plugin descriptions, user-created tags, names and detailed technical documents can remain in their original language. Raw runtime logs are retained for diagnosis; translating the interface does not translate stored logs or resource files.

The renderer output is `apps/dist/`. A distributable Windows executable additionally requires all packaging inputs described in [Windows packaging](../packaging-windows.md), including `backend/runtime/remote/remote_zipmod_index.sqlite`; an absent index must not be replaced with a fabricated empty database.
