using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using AIChara;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using Sideloader;
using Sideloader.AutoResolver;
using UnityEngine;

namespace StarManager.GameItemProbe
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    [BepInDependency(Sideloader.Sideloader.GUID, BepInDependency.DependencyFlags.HardDependency)]
    public sealed class GameItemProbePlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "star.manager.gameitemprobe";
        public const string PluginName = "Star Manager Game Item Probe";
        public const string PluginVersion = "0.9.0";
        private const float MinimumCurrentPollSeconds = 1f;

        private ConfigEntry<int> port;
        private ConfigEntry<float> currentPollSeconds;
        private ConfigEntry<string> snapshotPath;
        private GameItemProbeServer server;
        private GameItemCommandQueue commandQueue;
        private float nextInitialScan;
        private float nextCurrentPoll;
        private float nextContextPoll;
        private int refreshRequested;
        private int currentRefreshRequested;
        private bool staticSnapshotCaptured;
        private SnapshotState snapshot;

        private void Awake()
        {
            port = Config.Bind("Server", "Port", 7880, "Loopback HTTP port for the item probe.");
            currentPollSeconds = Config.Bind(
                "Server",
                "CurrentPollSeconds",
                MinimumCurrentPollSeconds,
                "How often the lightweight current-character state is refreshed. "
                    + "The full item catalog is scanned once after initialization and only on /api/refresh. "
                    + "Values below one second are clamped to avoid unnecessary main-thread polling."
            );
            snapshotPath = Config.Bind(
                "Output",
                "SnapshotPath",
                Path.Combine(Paths.ConfigPath, "StarManager.GameItemProbe.items.json"),
                "UTF-8 JSON snapshot path. Relative paths are resolved from the game root."
            );

            commandQueue = new GameItemCommandQueue(Logger, this);
            server = new GameItemProbeServer(Logger, port.Value, RequestFullRefresh, commandQueue);
            server.Start();
            nextInitialScan = Time.realtimeSinceStartup + 2f;
            nextCurrentPoll = Time.realtimeSinceStartup + MinimumCurrentPollSeconds;
            nextContextPoll = Time.realtimeSinceStartup + 0.5f;
            Logger.LogInfo(
                $"Started item probe at http://127.0.0.1:{port.Value}/api/items"
            );
        }

        private void Update()
        {
            if (commandQueue != null)
            {
                commandQueue.ExecutePending(RequestCurrentRefresh);
            }

            bool explicitRefresh = Interlocked.Exchange(ref refreshRequested, 0) != 0;
            bool initialScanDue = !staticSnapshotCaptured
                && Time.realtimeSinceStartup >= nextInitialScan;
            if (explicitRefresh || initialScanDue)
            {
                nextInitialScan = Time.realtimeSinceStartup + 2f;
                try
                {
                    SnapshotState captured = GameItemSnapshotBuilder.Build(Logger);
                    snapshot = captured;
                    server.Publish(captured);
                    WriteSnapshotFile(captured);
                    staticSnapshotCaptured = captured.ListControlFound
                        && captured.Items != null
                        && captured.Items.Count > 0;
                    Logger.LogInfo(
                        $"Captured {captured.Items.Count} game items and "
                        + $"{captured.ResolverRecords.Count} resolver records; "
                        + $"listControl={captured.ListControlFound}; "
                        + $"catalogReady={staticSnapshotCaptured}."
                    );
                }
                catch (Exception exception)
                {
                    Logger.LogError($"Could not capture game item snapshot: {exception}");
                    SnapshotState errorSnapshot = SnapshotState.CreateError(exception);
                    server.Publish(errorSnapshot);
                    WriteSnapshotFile(errorSnapshot);
                }
            }

            if (staticSnapshotCaptured
                && (Interlocked.Exchange(ref currentRefreshRequested, 0) != 0
                    || Time.realtimeSinceStartup >= nextCurrentPoll))
            {
                nextCurrentPoll = Time.realtimeSinceStartup
                    + Math.Max(MinimumCurrentPollSeconds, currentPollSeconds.Value);
                RefreshCurrentState();
            }

            if (Time.realtimeSinceStartup >= nextContextPoll)
            {
                nextContextPoll = Time.realtimeSinceStartup + MinimumCurrentPollSeconds;
                RefreshContext();
            }
        }

        private void RequestFullRefresh()
        {
            Interlocked.Exchange(ref refreshRequested, 1);
        }

        private void RequestCurrentRefresh()
        {
            Interlocked.Exchange(ref currentRefreshRequested, 1);
        }

        private void RefreshCurrentState()
        {
            SnapshotState captured = snapshot;
            if (captured == null || captured.ResolverByKey == null)
            {
                return;
            }

            try
            {
                CurrentState current = GameItemSnapshotBuilder.BuildCurrent(
                    captured.ResolverByKey,
                    Logger
                );
                server.PublishCurrent(current);
            }
            catch (Exception exception)
            {
                Logger.LogDebug($"Could not refresh current character state: {exception.Message}");
            }
        }

        private void RefreshContext()
        {
            try
            {
                SnapshotState captured = snapshot;
                server.PublishContext(
                    GameItemSnapshotBuilder.BuildContext(
                        Logger,
                        captured == null ? null : captured.ResolverByKey
                    )
                );
            }
            catch (Exception exception)
            {
                Logger.LogDebug($"Could not refresh game context: {exception.Message}");
            }
        }

        private void WriteSnapshotFile(SnapshotState snapshot)
        {
            try
            {
                string configuredPath = snapshotPath == null ? null : snapshotPath.Value;
                if (string.IsNullOrWhiteSpace(configuredPath) || snapshot == null)
                {
                    return;
                }

                string fullPath = Path.IsPathRooted(configuredPath)
                    ? configuredPath
                    : Path.Combine(Paths.GameRootPath, configuredPath);
                string directory = Path.GetDirectoryName(fullPath);
                if (!string.IsNullOrEmpty(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                File.WriteAllText(fullPath, snapshot.FullJson ?? "{}", new UTF8Encoding(false));
            }
            catch (Exception exception)
            {
                Logger.LogWarning($"Could not write item snapshot: {exception.Message}");
            }
        }

        private void OnDestroy()
        {
            commandQueue?.Stop();
            if (server != null)
            {
                server.Stop();
                server = null;
            }
            commandQueue = null;
        }
    }

    internal static class GameItemSnapshotBuilder
    {
        private static readonly int[] ClothingCategories =
        {
            140, 141, 144, 147,
            240, 241, 242, 243, 244, 245, 246, 247,
        };

        private static readonly int[] HairCategories = { 300, 301, 302, 303 };

        private static readonly int[] FaceCategories =
        {
            110, 111, 112, 121,
            210, 211, 212,
            314, 315, 316, 317, 318, 319, 320, 322, 323,
        };

        private static readonly int[] BodyCategories =
        {
            8, 131, 132, 133,
            231, 232, 233, 313, 334, 335,
        };

        // ChaControl.ChangeHair uses the ChaFileHair.parts index. The four
        // hair list categories are intentionally kept as an explicit
        // category-to-slot contract instead of relying on enum arithmetic.
        private static readonly Dictionary<int, int> HairKindByCategory =
            new Dictionary<int, int>
            {
                { 300, 0 }, // HairBack
                { 301, 1 }, // HairFront
                { 302, 2 }, // HairSide
                { 303, 3 }, // HairOption
            };

        private static readonly int[] AccessoryCategories =
        {
            351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363,
        };

        // ChangeClothes uses the universal ChaFile clothing slot number. The
        // coordinate parts array uses the universal clothing slot number.
        // In particular, male gloves/shoes are at slots 4/7 rather than the
        // compact category positions 2/3.
        private static readonly Dictionary<int, int> ClothingKindByCategoryMale =
            new Dictionary<int, int>
            {
                { 140, 0 }, { 141, 1 }, { 144, 4 }, { 147, 7 },
            };

        private static readonly Dictionary<int, int> ClothingKindByCategoryFemale =
            new Dictionary<int, int>
            {
                { 240, 0 }, { 241, 1 }, { 242, 2 }, { 243, 3 },
                { 244, 4 }, { 245, 5 }, { 246, 6 }, { 247, 7 },
            };

        private static readonly Dictionary<int, int> ClothingCategoryByKindMale =
            new Dictionary<int, int>
            {
                { 0, 140 }, { 1, 141 }, { 4, 144 }, { 7, 147 },
            };

        private static readonly Dictionary<int, int> ClothingCategoryByKindFemale =
            new Dictionary<int, int>
            {
                { 0, 240 }, { 1, 241 }, { 2, 242 }, { 3, 243 },
                { 4, 244 }, { 5, 245 }, { 6, 246 }, { 7, 247 },
            };

        internal static SnapshotState Build(ManualLogSource logger)
        {
            DateTime capturedAt = DateTime.UtcNow;
            List<ResolverRecord> resolverRecords = ReadResolverRecords(logger);
            Dictionary<string, List<ResolverRecord>> resolverByKey =
                resolverRecords
                    .Where(record => record.CategoryNo.HasValue)
                    .GroupBy(record => MakeKey(record.CategoryNo.Value, record.LocalSlot))
                    .ToDictionary(group => group.Key, group => group.ToList());

            ChaListControl listControl = FindListControl(logger, out string listSource);
            var items = new List<ItemRecord>();
            if (listControl != null)
            {
                foreach (int categoryNumber in ClothingCategories
                    .Concat(HairCategories)
                    .Concat(BodyCategories)
                    .Concat(AccessoryCategories)
                    .Distinct())
                {
                    ReadCategory(
                        listControl,
                        categoryNumber,
                        resolverByKey,
                        items,
                        logger
                    );
                }
            }

            CurrentState current = ReadCurrentState(listControl, resolverByKey, logger);
            var snapshot = new SnapshotState
            {
                SchemaVersion = 3,
                CapturedAtUtc = capturedAt.ToString("O", CultureInfo.InvariantCulture),
                ListControlFound = listControl != null,
                ListControlSource = listSource,
                Items = items,
                ResolverRecords = resolverRecords,
                Current = current,
                Context = BuildContext(logger, resolverByKey),
                Error = null,
                ResolverByKey = resolverByKey,
            };
            snapshot.FullJson = SnapshotJson.Write(snapshot);
            return snapshot;
        }

        internal static CurrentState BuildCurrent(
            Dictionary<string, List<ResolverRecord>> resolverByKey,
            ManualLogSource logger
        )
        {
            ChaControl character = FindCurrentCharacter();
            ChaListControl listControl = GetListControl(character);
            return ReadCurrentState(listControl, resolverByKey, logger);
        }

        internal static ChaControl FindCurrentCharacter()
        {
            object customBase = GetSingletonInstance(typeof(CharaCustom.CustomBase));
            return GetPropertyValue(customBase, "chaCtrl") as ChaControl;
        }

        internal static ContextState BuildContext(
            ManualLogSource logger,
            Dictionary<string, List<ResolverRecord>> resolverByKey = null
        )
        {
            ChaControl editorCharacter = FindCurrentCharacter();
            HScene hScene = FindActiveHScene(logger);
            ChaListControl listControl = FindListControl(logger, out string listSource);
            var context = new ContextState
            {
                Available = false,
                Scene = "none",
                Editor = MakeContextCharacter(
                    editorCharacter,
                    -1,
                    null,
                    listControl,
                    resolverByKey,
                    logger,
                    "CharaCustom.CustomBase.chaCtrl"
                ),
                HScene = new HSceneContext
                {
                    Available = hScene != null,
                    Females = new List<ContextCharacter>(),
                    Males = new List<ContextCharacter>(),
                },
            };

            if (editorCharacter != null)
            {
                context.Editor.Available = true;
            }

            if (hScene != null)
            {
                try
                {
                    AddHSceneCharacters(
                        hScene.GetFemales(),
                        1,
                        context.HScene.Females,
                        listControl,
                        resolverByKey,
                        logger
                    );
                    AddHSceneCharacters(
                        hScene.GetMales(),
                        0,
                        context.HScene.Males,
                        listControl,
                        resolverByKey,
                        logger
                    );
                }
                catch (Exception exception)
                {
                    logger?.LogDebug($"Could not enumerate HScene characters: {exception.Message}");
                }
            }

            // HScene is the authoritative active context when it is present.
            // The editor object can remain alive during scene transitions, so
            // it must not mask an active HScene.
            if (context.HScene.Available)
            {
                context.Scene = "hscene";
            }
            else if (context.Editor.Available)
            {
                context.Scene = "editor";
            }
            context.Available = context.Scene != "none";
            context.HScene.FemaleCount = context.HScene.Females.Count;
            context.HScene.MaleCount = context.HScene.Males.Count;
            context.HScene.TotalCount =
                context.HScene.FemaleCount + context.HScene.MaleCount;
            return context;
        }

        private static void AddHSceneCharacters(
            ChaControl[] characters,
            int sex,
            List<ContextCharacter> output,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey,
            ManualLogSource logger
        )
        {
            if (characters == null || output == null)
            {
                return;
            }

            for (int index = 0; index < characters.Length; index++)
            {
                ChaControl character = characters[index];
                if (character == null)
                {
                    continue;
                }
                output.Add(
                    MakeContextCharacter(
                        character,
                        index,
                        sex,
                        listControl,
                        resolverByKey,
                        logger,
                        $"HScene.Get{(sex == 1 ? "Females" : "Males")}()[{index}]"
                    )
                );
            }
        }

        private static ContextCharacter MakeContextCharacter(
            ChaControl character,
            int characterIndex,
            int? expectedSex,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey,
            ManualLogSource logger,
            string source
        )
        {
            if (character == null)
            {
                return new ContextCharacter
                {
                    Available = false,
                    CharacterIndex = characterIndex,
                    Sex = expectedSex.GetValueOrDefault(-1),
                };
            }

            CurrentState current = ReadCurrentStateForCharacter(
                character,
                listControl,
                resolverByKey,
                logger,
                source
            );

            return new ContextCharacter
            {
                Available = true,
                CharacterIndex = characterIndex,
                CharacterId = SafeInt(() => character.chaID),
                Sex = SafeInt(() => character.sex),
                CharacterName = SafeString(
                    () => character.chaFile?.parameter?.fullname
                ),
                CharacterFileName = SafeString(
                    () => character.chaFile?.charaFileName
                ),
                Active = IsActiveUnityObject(character),
                Current = current,
            };
        }

        private static HScene FindActiveHScene(ManualLogSource logger)
        {
            HScene hScene = FindHSceneFromManager();
            if (IsActiveUnityObject(hScene))
            {
                return hScene;
            }

            try
            {
                UnityEngine.Object[] scenes = Resources.FindObjectsOfTypeAll(typeof(HScene));
                foreach (UnityEngine.Object sceneObject in scenes)
                {
                    HScene candidate = sceneObject as HScene;
                    if (IsActiveUnityObject(candidate))
                    {
                        return candidate;
                    }
                }
            }
            catch (Exception exception)
            {
                logger?.LogDebug($"Could not scan active HScene objects: {exception.Message}");
            }

            return null;
        }

        private static HScene FindHSceneFromManager()
        {
            object hSceneManager = GetSingletonInstance(typeof(Manager.HSceneManager));
            HScene hScene = GetFieldValue(hSceneManager, "Hscene") as HScene;
            if (hScene == null)
            {
                hScene = GetPropertyValue(hSceneManager, "Hscene") as HScene;
            }
            return hScene;
        }

        private static bool IsActiveUnityObject(UnityEngine.Object value)
        {
            if (value == null)
            {
                return false;
            }

            Component component = value as Component;
            return component != null
                && component.gameObject != null
                && component.gameObject.activeInHierarchy;
        }

        internal static HScene FindHScene(ManualLogSource logger)
        {
            HScene hScene = FindHSceneFromManager();
            if (hScene != null)
            {
                return hScene;
            }

            try
            {
                UnityEngine.Object[] scenes = Resources.FindObjectsOfTypeAll(typeof(HScene));
                foreach (UnityEngine.Object sceneObject in scenes)
                {
                    HScene candidate = sceneObject as HScene;
                    if (candidate != null)
                    {
                        return candidate;
                    }
                }
            }
            catch (Exception exception)
            {
                logger?.LogDebug($"Could not scan HScene objects: {exception.Message}");
            }

            return null;
        }

        internal static ChaControl FindHSceneCharacter(
            ApplyCommand command,
            ManualLogSource logger,
            out ApplyResult error
        )
        {
            error = null;
            HScene hScene = FindHScene(logger);
            if (hScene == null)
            {
                error = ApplyResult.Failure(
                    "not_in_hscene",
                    "The active HScene instance is not available. Enter an H scene first."
                );
                return null;
            }

            int sex = command.TargetSex.GetValueOrDefault(-1);
            ChaControl[] characters;
            try
            {
                characters = sex == 1 ? hScene.GetFemales() : hScene.GetMales();
            }
            catch (Exception exception)
            {
                error = ApplyResult.Failure("not_in_hscene", exception.Message);
                return null;
            }

            if (characters == null || characters.Length == 0)
            {
                error = ApplyResult.Failure(
                    "target_not_found",
                    $"The HScene has no {(sex == 1 ? "female" : "male")} character slots."
                );
                return null;
            }

            ChaControl character = null;
            int resolvedIndex = -1;
            if (command.TargetCharacterIndex.HasValue)
            {
                int requestedIndex = command.TargetCharacterIndex.Value;
                if (requestedIndex < 0 || requestedIndex >= characters.Length)
                {
                    error = ApplyResult.Failure(
                        "invalid_character_index",
                        $"characterIndex {requestedIndex} is outside the HScene {sex} character array."
                    );
                    return null;
                }
                character = characters[requestedIndex];
                resolvedIndex = requestedIndex;
            }

            if (command.TargetCharacterId.HasValue)
            {
                int requestedId = command.TargetCharacterId.Value;
                ChaControl idCharacter = null;
                int idIndex = -1;
                for (int index = 0; index < characters.Length; index++)
                {
                    ChaControl candidate = characters[index];
                    if (candidate != null && candidate.chaID == requestedId)
                    {
                        if (idCharacter != null)
                        {
                            error = ApplyResult.Failure(
                                "ambiguous_target",
                                $"targetCharacterId {requestedId} matches multiple HScene characters."
                            );
                            return null;
                        }
                        idCharacter = candidate;
                        idIndex = index;
                    }
                }

                if (idCharacter == null)
                {
                    error = ApplyResult.Failure(
                        "target_not_found",
                        $"No HScene character with targetCharacterId {requestedId} was found."
                    );
                    return null;
                }
                if (character != null && character != idCharacter)
                {
                    error = ApplyResult.Failure(
                        "target_mismatch",
                        "characterIndex and targetCharacterId refer to different HScene characters."
                    );
                    return null;
                }
                character = idCharacter;
                resolvedIndex = idIndex;
            }

            if (character == null)
            {
                error = ApplyResult.Failure(
                    "target_not_found",
                    "An HScene characterIndex or targetCharacterId is required."
                );
                return null;
            }
            if (character.sex != sex)
            {
                error = ApplyResult.Failure(
                    "target_gender_mismatch",
                    $"The selected HScene character has sex {character.sex}, not {sex}."
                );
                return null;
            }

            // When only one selector was supplied, return the resolved pair in
            // the command status so callers can cache a stable target identity.
            command.TargetCharacterIndex = resolvedIndex;
            command.TargetCharacterId = character.chaID;
            return character;
        }

        internal static bool TrySetCustomLoadGCClear(bool value)
        {
            object characterManager = GetSingletonInstance(typeof(Manager.Character));
            if (characterManager == null)
            {
                return false;
            }

            try
            {
                PropertyInfo property = characterManager.GetType().GetProperty(
                    "customLoadGCClear",
                    BindingFlags.Public
                        | BindingFlags.NonPublic
                        | BindingFlags.Instance
                        | BindingFlags.FlattenHierarchy
                );
                if (property == null || property.SetMethod == null)
                {
                    return false;
                }
                property.SetValue(characterManager, value, null);
                return true;
            }
            catch (Exception)
            {
                return false;
            }
        }

        internal static ChaListControl GetListControl(ChaControl character)
        {
            return GetPropertyValue(character, "lstCtrl") as ChaListControl;
        }

        internal static bool TryGetClothesKind(int sex, int category, out int kind)
        {
            kind = 0;
            Dictionary<int, int> map = sex == 0
                ? ClothingKindByCategoryMale
                : sex == 1
                    ? ClothingKindByCategoryFemale
                    : null;
            return map != null && map.TryGetValue(category, out kind);
        }

        internal static bool TryGetClothesCategory(int sex, int kind, out int category)
        {
            category = 0;
            Dictionary<int, int> map = sex == 0
                ? ClothingCategoryByKindMale
                : sex == 1
                    ? ClothingCategoryByKindFemale
                    : null;
            return map != null && map.TryGetValue(kind, out category);
        }

        internal static bool TryGetHairKind(int category, out int kind)
        {
            kind = 0;
            return HairKindByCategory.TryGetValue(category, out kind);
        }

        internal static bool TryGetHairCategory(int kind, out int category)
        {
            category = 0;
            if (kind < 0 || kind >= HairCategories.Length)
            {
                return false;
            }

            category = HairCategories[kind];
            return true;
        }

        internal static bool IsFaceCategory(int category)
        {
            return FaceCategories.Contains(category);
        }

        internal static bool IsFaceEyeCategory(int category)
        {
            return category == 317 || category == 318;
        }

        internal static bool IsBodyCategory(int category)
        {
            return BodyCategories.Contains(category);
        }

        internal static bool IsBodyPaintCategory(int category)
        {
            return category == 8 || category == 313;
        }

        internal static bool TryGetBodyPart(int sex, int category, out int part)
        {
            part = -1;
            if ((sex == 0 && category == 131) || (sex == 1 && category == 231))
            {
                part = 0; // body skin
            }
            else if ((sex == 0 && category == 132) || (sex == 1 && category == 232))
            {
                part = 1; // body detail
            }
            else if ((sex == 0 && category == 133) || (sex == 1 && category == 233))
            {
                part = 2; // sunburn
            }
            else if ((sex == 0 && category == 8) || (sex == 1 && category == 313))
            {
                part = 3; // body paint
            }
            else if (sex == 1 && category == 334)
            {
                part = 4; // nipple
            }
            else if (sex == 1 && category == 335)
            {
                part = 5; // underhair
            }
            return part >= 0;
        }

        internal static bool TryGetFacePart(int sex, int category, out int part)
        {
            part = -1;
            if ((sex == 0 && category == 110) || (sex == 1 && category == 210))
            {
                part = 0; // head
            }
            else if ((sex == 0 && category == 111) || (sex == 1 && category == 211))
            {
                part = 1; // face skin
            }
            else if ((sex == 0 && category == 112) || (sex == 1 && category == 212))
            {
                part = 2; // face detail
            }
            else if (sex == 0 && category == 121)
            {
                part = 3; // beard
            }
            else
            {
                switch (category)
                {
                    case 314: part = 4; break; // eyebrow
                    case 315: part = 5; break; // eyelashes
                    case 316: part = 6; break; // eyeshadow
                    case 317: part = 7; break; // pupil
                    case 318: part = 8; break; // black pupil
                    case 319: part = 9; break; // eye highlight
                    case 320: part = 10; break; // cheek
                    case 322: part = 11; break; // lip
                    case 323: part = 12; break; // mole
                }
            }
            return part >= 0;
        }

        internal static bool IsAccessoryCategory(int category)
        {
            return category == 350 || (category >= 351 && category <= 363);
        }

        private static List<ResolverRecord> ReadResolverRecords(ManualLogSource logger)
        {
            var output = new List<ResolverRecord>();
            IEnumerable<ResolveInfo> loaded = null;
            try
            {
                loaded = UniversalAutoResolver.LoadedResolutionInfo;
            }
            catch (Exception exception)
            {
                logger.LogWarning($"Could not read UAR LoadedResolutionInfo: {exception.Message}");
            }

            if (loaded == null)
            {
                return output;
            }

            foreach (ResolveInfo info in loaded)
            {
                if (info == null)
                {
                    continue;
                }

                try
                {
                    output.Add(new ResolverRecord
                    {
                        Guid = info.GUID,
                        Slot = info.Slot,
                        LocalSlot = info.LocalSlot,
                        Property = info.Property,
                        CategoryNo = (int)info.CategoryNo,
                        CategoryName = GetCategoryName((int)info.CategoryNo),
                        Author = info.Author,
                        Website = info.Website,
                        Name = info.Name,
                        ModVersion = GetManifestValue(info.GUID, manifest => manifest.Version),
                        ModName = GetManifestValue(info.GUID, manifest => manifest.Name),
                        ZipmodPath = GetZipmodPath(info.GUID),
                    });
                }
                catch (Exception exception)
                {
                    logger.LogWarning($"Could not read one UAR record: {exception.Message}");
                }
            }

            return output;
        }

        private static string GetManifestValue(string guid, Func<Manifest, string> selector)
        {
            if (string.IsNullOrWhiteSpace(guid) || selector == null)
            {
                return null;
            }

            try
            {
                Manifest manifest;
                if (Sideloader.Sideloader.Manifests.TryGetValue(guid, out manifest)
                    && manifest != null)
                {
                    return selector(manifest);
                }
            }
            catch (Exception)
            {
                // A malformed optional manifest must not prevent the rest of the dump.
            }

            return null;
        }

        private static string GetZipmodPath(string guid)
        {
            if (string.IsNullOrWhiteSpace(guid))
            {
                return null;
            }

            try
            {
                string archivePath;
                return Sideloader.Sideloader.ZipArchives.TryGetValue(guid, out archivePath)
                    ? archivePath
                    : null;
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static void ReadCategory(
            ChaListControl listControl,
            int categoryNumber,
            Dictionary<string, List<ResolverRecord>> resolverByKey,
            List<ItemRecord> output,
            ManualLogSource logger
        )
        {
            try
            {
                ChaListDefine.CategoryNo category = (ChaListDefine.CategoryNo)categoryNumber;
                Dictionary<int, ListInfoBase> categoryInfo = listControl.GetCategoryInfo(category);
                if (categoryInfo == null)
                {
                    return;
                }

                foreach (KeyValuePair<int, ListInfoBase> entry in categoryInfo.OrderBy(item => item.Key))
                {
                    ListInfoBase info = entry.Value;
                    if (info == null)
                    {
                        continue;
                    }

                    var item = new ItemRecord
                    {
                        CategoryNo = categoryNumber,
                        CategoryName = GetCategoryName(categoryNumber),
                        CategoryEnumName = category.ToString(),
                        ListIndex = SafeInt(() => info.ListIndex),
                        Distribution = SafeInt(() => info.Distribution),
                        LocalSlot = entry.Key,
                        ListId = SafeInt(() => info.Id),
                        Kind = SafeInt(() => info.Kind),
                        Name = SafeString(() => info.Name),
                        FontSize = SafeInt(() => info.FontSize),
                        IdField = GetInfo(info, ChaListDefine.KeyType.ID),
                        MainManifest = GetInfo(info, ChaListDefine.KeyType.MainManifest),
                        MainAB = GetInfo(info, ChaListDefine.KeyType.MainAB),
                        MainData = GetInfo(info, ChaListDefine.KeyType.MainData),
                        ThumbAB = GetInfo(info, ChaListDefine.KeyType.ThumbAB),
                        ThumbTex = GetInfo(info, ChaListDefine.KeyType.ThumbTex),
                        TexAB = GetInfo(info, ChaListDefine.KeyType.TexAB),
                        DictInfo = ReadDictInfo(info),
                    };

                    List<ResolverRecord> candidates;
                    if (resolverByKey.TryGetValue(
                        MakeKey(categoryNumber, item.LocalSlot),
                        out candidates))
                    {
                        item.ResolverRecords = candidates;
                    }
                    else
                    {
                        item.ResolverRecords = new List<ResolverRecord>();
                    }
                    item.OriginalId = InferOriginalId(item.LocalSlot, item.ResolverRecords);

                    output.Add(item);
                }
            }
            catch (Exception exception)
            {
                logger.LogWarning(
                    $"Could not read category {categoryNumber}: {exception.Message}"
                );
            }
        }

        private static Dictionary<string, string> ReadDictInfo(ListInfoBase info)
        {
            var output = new Dictionary<string, string>();
            IReadOnlyDictionary<int, string> dictInfo = info.dictInfo;
            if (dictInfo == null)
            {
                return output;
            }

            foreach (KeyValuePair<int, string> entry in dictInfo.OrderBy(item => item.Key))
            {
                string keyName;
                try
                {
                    keyName = ((ChaListDefine.KeyType)entry.Key).ToString();
                }
                catch (Exception)
                {
                    keyName = "Unknown";
                }

                output[$"{entry.Key}:{keyName}"] = entry.Value;
            }

            return output;
        }

        private static string GetInfo(ListInfoBase info, ChaListDefine.KeyType key)
        {
            try
            {
                return info.GetInfo(key);
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static int? InferOriginalId(
            int localSlot,
            IEnumerable<ResolverRecord> records
        )
        {
            List<int> originalIds = (records ?? Enumerable.Empty<ResolverRecord>())
                .Select(record => record.Slot)
                .Distinct()
                .ToList();
            if (originalIds.Count == 1)
            {
                return originalIds[0];
            }

            // Vanilla rows have no UAR record; in that case the native ID is
            // also the original ID. Multiple UAR candidates are intentionally
            // reported as ambiguous and must be resolved by the caller.
            return originalIds.Count == 0 ? localSlot : (int?)null;
        }

        internal static CurrentState ReadCurrentState(
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey,
            ManualLogSource logger
        )
        {
            return ReadCurrentStateForCharacter(
                FindCurrentCharacter(),
                listControl,
                resolverByKey,
                logger,
                "CharaCustom.CustomBase.chaCtrl"
            );
        }

        internal static CurrentState ReadCurrentStateForCharacter(
            ChaControl currentCharacter,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey,
            ManualLogSource logger,
            string source
        )
        {
            resolverByKey = resolverByKey
                ?? new Dictionary<string, List<ResolverRecord>>();
            if (currentCharacter == null)
            {
                return new CurrentState
                {
                    Available = false,
                    Source = source,
                    Hairs = new List<CurrentItem>(),
                    Clothes = new List<CurrentItem>(),
                    Faces = new List<CurrentItem>(),
                    Bodies = new List<CurrentItem>(),
                    Accessories = new List<CurrentItem>(),
                };
            }

            ChaListControl characterListControl = GetListControl(currentCharacter);
            if (characterListControl != null)
            {
                listControl = characterListControl;
            }

            var current = new CurrentState
            {
                Available = true,
                Source = source,
                CharacterId = SafeInt(() => currentCharacter.chaID),
                Sex = SafeInt(() => currentCharacter.sex),
                CharacterName = SafeString(() => currentCharacter.chaFile?.parameter?.fullname),
                CharacterFileName = SafeString(() => currentCharacter.chaFile?.charaFileName),
                Clothes = new List<CurrentItem>(),
                Hairs = new List<CurrentItem>(),
                Faces = new List<CurrentItem>(),
                Bodies = new List<CurrentItem>(),
                Accessories = new List<CurrentItem>(),
            };

            ChaFileCoordinate coordinate = null;
            try
            {
                coordinate = currentCharacter.nowCoordinate;
            }
            catch (Exception exception)
            {
                logger.LogDebug($"Could not read current coordinate: {exception.Message}");
            }

            try
            {
                ReadFaceState(
                    currentCharacter.fileFace,
                    current.Sex,
                    current,
                    listControl,
                    resolverByKey
                );
            }
            catch (Exception exception)
            {
                logger.LogWarning($"Could not read current face: {exception.Message}");
            }

            try
            {
                ReadBodyState(
                    currentCharacter.fileBody,
                    current.Sex,
                    current,
                    listControl,
                    resolverByKey
                );
            }
            catch (Exception exception)
            {
                logger.LogWarning($"Could not read current body: {exception.Message}");
            }

            try
            {
                ChaFileHair hair = currentCharacter.fileHair;
                if (hair != null && hair.parts != null)
                {
                    for (int index = 0; index < hair.parts.Length; index++)
                    {
                        int category;
                        if (!TryGetHairCategory(index, out category))
                        {
                            continue;
                        }

                        current.Hairs.Add(
                            MakeCurrentItem(
                                "hair",
                                index,
                                category,
                                hair.parts[index].id,
                                listControl,
                                resolverByKey
                            )
                        );
                    }
                }
            }
            catch (Exception exception)
            {
                logger.LogWarning($"Could not read current hair: {exception.Message}");
            }

            if (coordinate == null)
            {
                return current;
            }

            current.CoordinateName = coordinate.coordinateName;
            int sex = current.Sex;
            try
            {
                if (coordinate.clothes != null && coordinate.clothes.parts != null)
                {
                    for (int index = 0; index < coordinate.clothes.parts.Length; index++)
                    {
                        int category;
                        if (!TryGetClothesCategory(sex, index, out category))
                        {
                            continue;
                        }
                        current.Clothes.Add(
                            MakeCurrentItem(
                                "clothes",
                                index,
                                category,
                                coordinate.clothes.parts[index].id,
                                listControl,
                                resolverByKey
                            )
                        );
                    }
                }
            }
            catch (Exception exception)
            {
                logger.LogWarning($"Could not read current clothes: {exception.Message}");
            }

            try
            {
                if (coordinate.accessory != null && coordinate.accessory.parts != null)
                {
                    for (int index = 0; index < coordinate.accessory.parts.Length; index++)
                    {
                        var part = coordinate.accessory.parts[index];
                        current.Accessories.Add(
                            MakeCurrentItem(
                                "accessory",
                                index,
                                part.type,
                                part.id,
                                listControl,
                                resolverByKey
                            )
                        );
                    }
                }
            }
            catch (Exception exception)
            {
                logger.LogWarning($"Could not read current accessories: {exception.Message}");
            }

            return current;
        }

        private static void ReadFaceState(
            ChaFileFace face,
            int sex,
            CurrentState current,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey
        )
        {
            if (face == null || current == null)
            {
                return;
            }

            int baseCategory = sex == 0 ? 110 : 210;
            AddCurrentItem(current.Faces, "face", 0, baseCategory, face.headId, listControl, resolverByKey);
            AddCurrentItem(current.Faces, "face", 1, baseCategory + 1, face.skinId, listControl, resolverByKey);
            AddCurrentItem(current.Faces, "face", 2, baseCategory + 2, face.detailId, listControl, resolverByKey);

            if (sex == 0)
            {
                AddCurrentItem(current.Faces, "face", 3, 121, face.beardId, listControl, resolverByKey);
            }

            AddCurrentItem(current.Faces, "face", 4, 314, face.eyebrowId, listControl, resolverByKey);
            AddCurrentItem(current.Faces, "face", 5, 315, face.eyelashesId, listControl, resolverByKey);

            ChaFileFace.MakeupInfo makeup = face.makeup;
            if (makeup != null)
            {
                AddCurrentItem(current.Faces, "face", 6, 316, makeup.eyeshadowId, listControl, resolverByKey);
                AddCurrentItem(current.Faces, "face", 7, 320, makeup.cheekId, listControl, resolverByKey);
                AddCurrentItem(current.Faces, "face", 8, 322, makeup.lipId, listControl, resolverByKey);
            }

            AddCurrentItem(current.Faces, "face", 9, 319, face.hlId, listControl, resolverByKey);
            AddCurrentItem(current.Faces, "face", 10, 323, face.moleId, listControl, resolverByKey);

            if (face.pupil != null)
            {
                for (int index = 0; index < face.pupil.Length; index++)
                {
                    ChaFileFace.EyesInfo eye = face.pupil[index];
                    if (eye == null)
                    {
                        continue;
                    }

                    CurrentItem pupil = MakeCurrentItem(
                        "face",
                        20 + index,
                        317,
                        eye.pupilId,
                        listControl,
                        resolverByKey
                    );
                    pupil.PartLabel = index == 0 ? "左眼" : "右眼";
                    current.Faces.Add(pupil);

                    CurrentItem black = MakeCurrentItem(
                        "face",
                        30 + index,
                        318,
                        eye.blackId,
                        listControl,
                        resolverByKey
                    );
                    black.PartLabel = index == 0 ? "左眼" : "右眼";
                    current.Faces.Add(black);
                }
            }
        }

        private static void ReadBodyState(
            ChaFileBody body,
            int sex,
            CurrentState current,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey
        )
        {
            if (body == null || current == null)
            {
                return;
            }

            int baseCategory = sex == 0 ? 131 : 231;
            AddCurrentItem(current.Bodies, "body", 0, baseCategory, body.skinId, listControl, resolverByKey);
            AddCurrentItem(current.Bodies, "body", 1, baseCategory + 1, body.detailId, listControl, resolverByKey);
            AddCurrentItem(current.Bodies, "body", 2, baseCategory + 2, body.sunburnId, listControl, resolverByKey);
            if (sex == 1)
            {
                AddCurrentItem(current.Bodies, "body", 3, 334, body.nipId, listControl, resolverByKey);
                AddCurrentItem(current.Bodies, "body", 4, 335, body.underhairId, listControl, resolverByKey);
            }

            if (body.paintInfo == null)
            {
                return;
            }

            int paintCategory = sex == 0 ? 8 : 313;
            for (int index = 0; index < body.paintInfo.Length; index++)
            {
                AIChara.PaintInfo paint = body.paintInfo[index];
                if (paint == null)
                {
                    continue;
                }

                int currentPaintSlot = sex == 0 ? paint.layoutId : paint.id;
                CurrentItem item = MakeCurrentItem(
                    "body",
                    10 + index,
                    paintCategory,
                    currentPaintSlot,
                    listControl,
                    resolverByKey
                );
                item.PartLabel = $"彩绘 {index + 1}";
                current.Bodies.Add(item);
            }
        }

        private static void AddCurrentItem(
            List<CurrentItem> target,
            string partType,
            int index,
            int category,
            int localSlot,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey
        )
        {
            if (target == null || category < 0)
            {
                return;
            }

            target.Add(
                MakeCurrentItem(
                    partType,
                    index,
                    category,
                    localSlot,
                    listControl,
                    resolverByKey
                )
            );
        }

        private static CurrentItem MakeCurrentItem(
            string partType,
            int index,
            int category,
            int localSlot,
            ChaListControl listControl,
            Dictionary<string, List<ResolverRecord>> resolverByKey
        )
        {
            var item = new CurrentItem
            {
                PartType = partType,
                PartIndex = index,
                CategoryNo = category,
                LocalSlot = localSlot,
                ListId = localSlot,
                ResolverRecords = new List<ResolverRecord>(),
            };

            if (localSlot == 0)
            {
                return item;
            }

            List<ResolverRecord> candidates;
            if (resolverByKey.TryGetValue(MakeKey(category, localSlot), out candidates))
            {
                item.ResolverRecords = candidates;
            }
            item.OriginalId = InferOriginalId(item.LocalSlot, item.ResolverRecords);

            if (listControl == null || category < 0)
            {
                return item;
            }

            try
            {
                ListInfoBase info = listControl.GetListInfo(
                    (ChaListDefine.CategoryNo)category,
                    localSlot
                );
                item.Name = info == null ? null : SafeString(() => info.Name);
                item.Kind = info == null ? 0 : SafeInt(() => info.Kind);
                item.ListId = info == null ? localSlot : SafeInt(() => info.Id);
            }
            catch (Exception)
            {
                // Current coordinate information remains useful even without a list row.
            }

            return item;
        }

        internal static ChaListControl FindListControl(
            ManualLogSource logger,
            out string source
        )
        {
            source = null;
            foreach (Type singletonType in new[]
            {
                typeof(Manager.Character),
                typeof(CharaCustom.CustomBase),
            })
            {
                object instance = GetSingletonInstance(singletonType);
                ChaListControl list = GetListControlFrom(instance);
                if (list != null)
                {
                    source = singletonType.FullName + ".Instance";
                    return list;
                }
            }

            try
            {
                UnityEngine.Object[] characters = Resources.FindObjectsOfTypeAll(
                    typeof(Manager.Character)
                );
                foreach (UnityEngine.Object character in characters)
                {
                    ChaListControl list = GetListControlFrom(character);
                    if (list != null)
                    {
                        source = "Resources.FindObjectsOfTypeAll(Manager.Character)";
                        return list;
                    }
                }
            }
            catch (Exception exception)
            {
                logger.LogDebug($"Could not scan Manager.Character: {exception.Message}");
            }

            try
            {
                UnityEngine.Object[] characters = Resources.FindObjectsOfTypeAll(
                    typeof(ChaControl)
                );
                foreach (UnityEngine.Object character in characters)
                {
                    ChaListControl list = GetPropertyValue(character, "lstCtrl") as ChaListControl;
                    if (list != null)
                    {
                        source = "Resources.FindObjectsOfTypeAll(ChaControl)";
                        return list;
                    }
                }
            }
            catch (Exception exception)
            {
                logger.LogDebug($"Could not scan ChaControl: {exception.Message}");
            }

            return null;
        }

        private static ChaListControl GetListControlFrom(object instance)
        {
            if (instance == null)
            {
                return null;
            }

            ChaListControl list = GetPropertyValue(instance, "chaListCtrl") as ChaListControl;
            if (list != null)
            {
                return list;
            }

            object chaControl = GetPropertyValue(instance, "chaCtrl");
            return GetPropertyValue(chaControl, "lstCtrl") as ChaListControl;
        }

        private static object GetSingletonInstance(Type type)
        {
            for (Type current = type; current != null; current = current.BaseType)
            {
                try
                {
                    PropertyInfo property = current.GetProperty(
                        "Instance",
                        BindingFlags.Public
                            | BindingFlags.NonPublic
                            | BindingFlags.Static
                            | BindingFlags.FlattenHierarchy
                    );
                    if (property != null && property.GetMethod != null && property.GetMethod.IsStatic)
                    {
                        object value = property.GetValue(null, null);
                        if (value != null)
                        {
                            return value;
                        }
                    }
                }
                catch (Exception)
                {
                    // The singleton may not have been initialized in the current scene.
                }
            }

            return null;
        }

        private static object GetPropertyValue(object instance, string name)
        {
            if (instance == null || string.IsNullOrEmpty(name))
            {
                return null;
            }

            try
            {
                PropertyInfo property = instance.GetType().GetProperty(
                    name,
                    BindingFlags.Public
                        | BindingFlags.NonPublic
                        | BindingFlags.Instance
                        | BindingFlags.FlattenHierarchy
                );
                return property == null ? null : property.GetValue(instance, null);
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static object GetFieldValue(object instance, string name)
        {
            if (instance == null || string.IsNullOrEmpty(name))
            {
                return null;
            }

            try
            {
                FieldInfo field = instance.GetType().GetField(
                    name,
                    BindingFlags.Public
                        | BindingFlags.NonPublic
                        | BindingFlags.Instance
                        | BindingFlags.FlattenHierarchy
                );
                return field == null ? null : field.GetValue(instance);
            }
            catch (Exception)
            {
                return null;
            }
        }

        private static string GetCategoryName(int category)
        {
            try
            {
                return ChaListDefine.GetCategoryName(category);
            }
            catch (Exception)
            {
                return ((ChaListDefine.CategoryNo)category).ToString();
            }
        }

        private static int SafeInt(Func<int> getter)
        {
            try
            {
                return getter();
            }
            catch (Exception)
            {
                return 0;
            }
        }

        private static string SafeString(Func<string> getter)
        {
            try
            {
                return getter();
            }
            catch (Exception)
            {
                return null;
            }
        }

        internal static string MakeKey(int category, int localSlot)
        {
            return category.ToString(CultureInfo.InvariantCulture)
                + ":"
                + localSlot.ToString(CultureInfo.InvariantCulture);
        }
    }

    internal sealed class SnapshotState
    {
        internal int SchemaVersion;
        internal string CapturedAtUtc;
        internal bool ListControlFound;
        internal string ListControlSource;
        internal List<ItemRecord> Items;
        internal List<ResolverRecord> ResolverRecords;
        internal CurrentState Current;
        internal ContextState Context;
        internal string Error;
        internal string FullJson;
        internal Dictionary<string, List<ResolverRecord>> ResolverByKey;

        internal static SnapshotState CreateError(Exception exception)
        {
            var snapshot = new SnapshotState
            {
                SchemaVersion = 3,
                CapturedAtUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                ListControlFound = false,
                ListControlSource = null,
                Items = new List<ItemRecord>(),
                ResolverRecords = new List<ResolverRecord>(),
                Current = new CurrentState
                {
                    Available = false,
                    Hairs = new List<CurrentItem>(),
                    Clothes = new List<CurrentItem>(),
                    Faces = new List<CurrentItem>(),
                    Bodies = new List<CurrentItem>(),
                    Accessories = new List<CurrentItem>(),
                },
                Context = new ContextState
                {
                    Available = false,
                    Scene = "none",
                    Editor = new ContextCharacter
                    {
                        CharacterIndex = -1,
                        Sex = -1,
                    },
                    HScene = new HSceneContext
                    {
                        Females = new List<ContextCharacter>(),
                        Males = new List<ContextCharacter>(),
                    },
                },
                Error = exception == null ? "Unknown error" : exception.ToString(),
                ResolverByKey = new Dictionary<string, List<ResolverRecord>>(),
            };
            snapshot.FullJson = SnapshotJson.Write(snapshot);
            return snapshot;
        }
    }

    internal sealed class ItemRecord
    {
        internal int CategoryNo;
        internal string CategoryName;
        internal string CategoryEnumName;
        internal int ListIndex;
        internal int Distribution;
        internal int LocalSlot;
        internal int ListId;
        internal int? OriginalId;
        internal int Kind;
        internal string Name;
        internal int FontSize;
        internal string IdField;
        internal string MainManifest;
        internal string MainAB;
        internal string MainData;
        internal string ThumbAB;
        internal string ThumbTex;
        internal string TexAB;
        internal Dictionary<string, string> DictInfo;
        internal List<ResolverRecord> ResolverRecords;
    }

    internal sealed class ResolverRecord
    {
        internal string Guid;
        internal int Slot;
        internal int LocalSlot;
        internal string Property;
        internal int? CategoryNo;
        internal string CategoryName;
        internal string Author;
        internal string Website;
        internal string Name;
        internal string ModVersion;
        internal string ModName;
        internal string ZipmodPath;
    }

    internal sealed class CurrentState
    {
        internal bool Available;
        internal string Source;
        internal int CharacterId;
        internal int Sex;
        internal string CharacterName;
        internal string CharacterFileName;
        internal string CoordinateName;
        internal List<CurrentItem> Hairs;
        internal List<CurrentItem> Clothes;
        internal List<CurrentItem> Faces;
        internal List<CurrentItem> Bodies;
        internal List<CurrentItem> Accessories;
    }

    internal sealed class ContextState
    {
        internal bool Available;
        internal string Scene;
        internal ContextCharacter Editor;
        internal HSceneContext HScene;
    }

    internal sealed class HSceneContext
    {
        internal bool Available;
        internal int FemaleCount;
        internal int MaleCount;
        internal int TotalCount;
        internal List<ContextCharacter> Females;
        internal List<ContextCharacter> Males;
    }

    internal sealed class ContextCharacter
    {
        internal bool Available;
        internal bool Active;
        internal int CharacterIndex;
        internal int CharacterId;
        internal int Sex;
        internal string CharacterName;
        internal string CharacterFileName;
        internal CurrentState Current;
    }

    internal sealed class CurrentItem
    {
        internal string PartType;
        internal int PartIndex;
        internal int CategoryNo;
        internal int LocalSlot;
        internal int ListId;
        internal int? OriginalId;
        internal int Kind;
        internal string Name;
        internal string PartLabel;
        internal List<ResolverRecord> ResolverRecords;
    }

    internal sealed class ApplyCommand
    {
        internal readonly object StateGate = new object();
        internal string CommandId;
        internal string Type;
        internal string Target;
        internal int? TargetSex;
        internal int? TargetCharacterIndex;
        internal int? TargetCharacterId;
        internal string Guid;
        internal int? CategoryNo;
        internal int? LocalSlot;
        internal int? OriginalSlot;
        internal int? AccessorySlotNo;
        internal int? HairSlotNo;
        internal int? FacePartNo;
        internal int? BodyPartNo;
        internal string ParentKey;
        internal string CardPath;
        internal bool CardFace;
        internal bool CardBody;
        internal bool CardHair;
        internal bool CardParameter;
        internal bool CardClothes;
        internal bool CardAccessory;
        internal string Status;
        internal string ErrorCode;
        internal string Error;
        internal string AcceptedAtUtc;
        internal string StartedAtUtc;
        internal string CompletedAtUtc;
        internal int? ResolvedLocalSlot;
        internal DateTime ExpiresAtUtc;

        internal void MarkExecuting()
        {
            lock (StateGate)
            {
                Status = "executing";
                StartedAtUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture);
            }
        }

        internal void Complete(
            string status,
            string errorCode,
            string error,
            int? resolvedLocalSlot
        )
        {
            lock (StateGate)
            {
                Status = status;
                ErrorCode = errorCode;
                Error = error;
                ResolvedLocalSlot = resolvedLocalSlot;
                CompletedAtUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture);
            }
        }
    }

    internal sealed class ApplyResult
    {
        internal bool Succeeded;
        internal string ErrorCode;
        internal string Error;
        internal int? ResolvedLocalSlot;
        internal DeferredApply DeferredWork;

        internal static ApplyResult Success(int? localSlot)
        {
            return new ApplyResult
            {
                Succeeded = true,
                ResolvedLocalSlot = localSlot,
            };
        }

        internal static ApplyResult Failure(string code, string message)
        {
            return new ApplyResult
            {
                Succeeded = false,
                ErrorCode = code,
                Error = message,
            };
        }

        internal static ApplyResult Defer(
            IEnumerator routine,
            Func<ApplyResult> completed,
            Action recover = null,
            float timeoutSeconds = 0f
        )
        {
            return new ApplyResult
            {
                DeferredWork = new DeferredApply
                {
                    Routine = routine,
                    Completed = completed,
                    Recover = recover,
                    TimeoutSeconds = timeoutSeconds,
                },
            };
        }
    }

    internal sealed class DeferredApply
    {
        internal IEnumerator Routine;
        internal Func<ApplyResult> Completed;
        internal Action Recover;
        internal float TimeoutSeconds;
    }

    internal sealed class GameItemCommandQueue
    {
        private const int MaxPendingCommands = 32;
        private const int MaxRetainedCommands = 256;
        private const float DeferredCommandTimeoutSeconds = 12f;
        private static readonly TimeSpan CommandLifetime = TimeSpan.FromSeconds(15);

        private readonly ManualLogSource logger;
        private readonly MonoBehaviour coroutineHost;
        private readonly ConcurrentQueue<ApplyCommand> pending =
            new ConcurrentQueue<ApplyCommand>();
        private readonly Dictionary<string, ApplyCommand> commands =
            new Dictionary<string, ApplyCommand>(StringComparer.OrdinalIgnoreCase);
        private readonly Queue<string> commandOrder = new Queue<string>();
        private readonly object commandGate = new object();
        private int pendingCount;
        private bool deferredCommandActive;
        private volatile bool stopping;

        internal GameItemCommandQueue(
            ManualLogSource logSource,
            MonoBehaviour coroutineRunner
        )
        {
            logger = logSource;
            coroutineHost = coroutineRunner;
        }

        internal bool TryEnqueue(
            string body,
            out ApplyCommand command,
            out string errorCode,
            out string error
        )
        {
            command = null;
            errorCode = null;
            error = null;
            if (stopping)
            {
                errorCode = "stopping";
                error = "The game item command queue is stopping.";
                return false;
            }

            if (!ApplyCommandParser.TryParse(body, out command, out errorCode, out error))
            {
                return false;
            }

            int count = Interlocked.Increment(ref pendingCount);
            if (count > MaxPendingCommands)
            {
                Interlocked.Decrement(ref pendingCount);
                command = null;
                errorCode = "queue_full";
                error = "Too many game item commands are waiting to run.";
                return false;
            }

            command.CommandId = Guid.NewGuid().ToString("N");
            command.Status = "queued";
            command.AcceptedAtUtc = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture);
            command.ExpiresAtUtc = DateTime.UtcNow.Add(CommandLifetime);
            pending.Enqueue(command);
            lock (commandGate)
            {
                commands[command.CommandId] = command;
                commandOrder.Enqueue(command.CommandId);
                while (commandOrder.Count > MaxRetainedCommands)
                {
                    string oldId = commandOrder.Dequeue();
                    commands.Remove(oldId);
                }
            }
            return true;
        }

        internal bool TryGet(string commandId, out ApplyCommand command)
        {
            command = null;
            if (string.IsNullOrWhiteSpace(commandId))
            {
                return false;
            }

            lock (commandGate)
            {
                return commands.TryGetValue(commandId, out command);
            }
        }

        internal void ExecutePending(Action requestRefresh)
        {
            if (deferredCommandActive)
            {
                return;
            }

            for (int index = 0; index < 8; index++)
            {
                ApplyCommand command;
                if (!pending.TryDequeue(out command))
                {
                    return;
                }
                Interlocked.Decrement(ref pendingCount);

                if (DateTime.UtcNow > command.ExpiresAtUtc)
                {
                    command.Complete(
                        "expired",
                        "command_expired",
                        "The command was not executed before its 15 second lifetime expired.",
                        null
                    );
                    continue;
                }

                command.MarkExecuting();
                ApplyResult result;
                try
                {
                    result = GameItemCommandExecutor.Execute(command, logger);
                }
                catch (Exception exception)
                {
                    result = ApplyResult.Failure("execution_error", exception.Message);
                    logger.LogError($"Game item command {command.CommandId} failed: {exception}");
                }

                if (result != null && result.DeferredWork != null)
                {
                    deferredCommandActive = true;
                    try
                    {
                        coroutineHost.StartCoroutine(
                            CompleteDeferred(
                                command,
                                result.DeferredWork,
                                requestRefresh
                            )
                        );
                    }
                    catch (Exception exception)
                    {
                        deferredCommandActive = false;
                        logger.LogError(
                            $"Could not start deferred game item command {command.CommandId}: {exception}"
                        );
                        command.Complete(
                            "failed",
                            "execution_error",
                            exception.Message,
                            null
                        );
                    }
                    return;
                }

                command.Complete(
                    result.Succeeded ? "succeeded" : "failed",
                    result.ErrorCode,
                    result.Error,
                    result.ResolvedLocalSlot
                );
                if (result.Succeeded)
                {
                    requestRefresh?.Invoke();
                }
            }
        }

        private IEnumerator CompleteDeferred(
            ApplyCommand command,
            DeferredApply deferred,
            Action requestRefresh
        )
        {
            ApplyResult result = null;
            Exception failure = null;
            float startedAt = Time.realtimeSinceStartup;
            while (deferred != null && deferred.Routine != null)
            {
                float timeoutSeconds = deferred.TimeoutSeconds > 0f
                    ? deferred.TimeoutSeconds
                    : DeferredCommandTimeoutSeconds;
                if (Time.realtimeSinceStartup - startedAt > timeoutSeconds)
                {
                    failure = new TimeoutException(
                        $"The deferred game item command exceeded its {timeoutSeconds:0.#} second timeout."
                    );
                    break;
                }

                bool hasNext;
                object current = null;
                try
                {
                    hasNext = deferred.Routine.MoveNext();
                    if (hasNext)
                    {
                        current = deferred.Routine.Current;
                    }
                }
                catch (Exception exception)
                {
                    hasNext = false;
                    failure = exception;
                }

                if (!hasNext)
                {
                    break;
                }
                yield return current;
            }

            if (failure == null)
            {
                try
                {
                    result = deferred == null || deferred.Completed == null
                        ? ApplyResult.Success(null)
                        : deferred.Completed();
                }
                catch (Exception exception)
                {
                    failure = exception;
                }
            }

            if (failure != null)
            {
                try
                {
                    deferred?.Recover?.Invoke();
                }
                catch (Exception recoveryException)
                {
                    logger.LogWarning(
                        $"Could not recover deferred game item command {command.CommandId}: {recoveryException.Message}"
                    );
                }
                logger.LogError(
                    $"Deferred game item command {command.CommandId} failed: {failure}"
                );
                result = ApplyResult.Failure("execution_error", failure.Message);
            }
            if (result == null)
            {
                result = ApplyResult.Failure(
                    "execution_error",
                    "The deferred game item command did not produce a result."
                );
            }

            deferredCommandActive = false;
            command.Complete(
                result.Succeeded ? "succeeded" : "failed",
                result.ErrorCode,
                result.Error,
                result.ResolvedLocalSlot
            );
            if (result.Succeeded)
            {
                requestRefresh?.Invoke();
            }
        }

        internal void Stop()
        {
            stopping = true;
        }
    }

    internal static class ApplyCommandParser
    {
        internal static bool TryParse(
            string body,
            out ApplyCommand command,
            out string errorCode,
            out string error
        )
        {
            command = null;
            errorCode = null;
            error = null;
            Dictionary<string, string> values;
            if (!SimpleJsonObject.TryParse(body, out values, out error))
            {
                errorCode = "invalid_json";
                return false;
            }

            string target = "editor";
            string requestedTarget;
            if (values.TryGetValue("target", out requestedTarget)
                && !string.IsNullOrWhiteSpace(requestedTarget))
            {
                target = requestedTarget.Trim().ToLowerInvariant();
            }
            if (target != "editor" && target != "hscene")
            {
                errorCode = "invalid_target";
                error = "target must be editor or hscene.";
                return false;
            }

            string type;
            if (!values.TryGetValue("type", out type) || string.IsNullOrWhiteSpace(type))
            {
                errorCode = "invalid_command";
                error = "type must be card, clothes, hair, face, body or accessory.";
                return false;
            }
            type = type.Trim().ToLowerInvariant();
            if (type == "card")
            {
                if (target != "editor")
                {
                    errorCode = "invalid_target";
                    error = "Character-card loading is only supported for the editor target.";
                    return false;
                }
                return TryParseCard(values, out command, out errorCode, out error);
            }

            if (type != "clothes" && type != "hair" && type != "face" && type != "body" && type != "accessory")
            {
                errorCode = "invalid_command";
                error = "type must be card, clothes, hair, face, body or accessory.";
                return false;
            }

            int? targetSex = null;
            int parsedTargetSex;
            if (target == "hscene")
            {
                if (!TryGetInt(values, "sex", out parsedTargetSex)
                    || (parsedTargetSex != 0 && parsedTargetSex != 1))
                {
                    errorCode = "invalid_target_sex";
                    error = "sex must be 0 (male) or 1 (female) for the hscene target.";
                    return false;
                }
                targetSex = parsedTargetSex;
            }

            int targetCharacterIndex;
            bool hasTargetCharacterIndex = TryGetInt(
                values,
                "characterIndex",
                out targetCharacterIndex
            );
            if (hasTargetCharacterIndex && targetCharacterIndex < 0)
            {
                errorCode = "invalid_character_index";
                error = "characterIndex must not be negative.";
                return false;
            }

            int targetCharacterId;
            bool hasTargetCharacterId = TryGetInt(
                values,
                "targetCharacterId",
                out targetCharacterId
            );
            if (hasTargetCharacterId && targetCharacterId < 0)
            {
                errorCode = "invalid_character_id";
                error = "targetCharacterId must not be negative.";
                return false;
            }
            if (target == "hscene" && !hasTargetCharacterIndex && !hasTargetCharacterId)
            {
                errorCode = "invalid_target";
                error = "characterIndex or targetCharacterId is required for the hscene target.";
                return false;
            }

            int category;
            if (!TryGetRequiredInt(values, "categoryNo", out category))
            {
                errorCode = "invalid_command";
                error = "categoryNo must be an integer.";
                return false;
            }

            string guid = null;
            values.TryGetValue("guid", out guid);
            guid = string.IsNullOrWhiteSpace(guid) ? null : guid.Trim();
            int localSlot;
            bool hasLocalSlot = TryGetInt(values, "localSlot", out localSlot);
            int originalSlot;
            bool hasOriginalSlot = TryGetInt(values, "slot", out originalSlot);
            if (!hasLocalSlot && string.IsNullOrWhiteSpace(guid))
            {
                errorCode = "invalid_command";
                error = "localSlot or guid plus slot is required.";
                return false;
            }
            if (!string.IsNullOrWhiteSpace(guid) && !hasOriginalSlot)
            {
                errorCode = "invalid_command";
                error = "slot is required when guid is supplied.";
                return false;
            }
            if (hasLocalSlot && localSlot < 0)
            {
                errorCode = "invalid_command";
                error = "localSlot must not be negative.";
                return false;
            }

            int slotNo = 0;
            int hairSlotNo = 0;
            int facePartNo = 0;
            int bodyPartNo = 0;
            string parentKey = null;
            if (type == "hair")
            {
                if (!TryGetRequiredInt(values, "hairSlotNo", out hairSlotNo)
                    || hairSlotNo < 0
                    || hairSlotNo > 3)
                {
                    errorCode = "invalid_hair_slot";
                    error = "hairSlotNo must be an integer from 0 through 3.";
                    return false;
                }

                int expectedHairSlot;
                if (!GameItemSnapshotBuilder.TryGetHairKind(category, out expectedHairSlot))
                {
                    errorCode = "invalid_category";
                    error = "categoryNo must be one of the hair categories 300 through 303.";
                    return false;
                }
                if (hairSlotNo != expectedHairSlot)
                {
                    errorCode = "invalid_hair_slot";
                    error =
                        $"hairSlotNo {hairSlotNo} does not match categoryNo {category}; "
                        + $"the expected hair slot is {expectedHairSlot}.";
                    return false;
                }
            }
            else if (type == "accessory")
            {
                if (!TryGetRequiredInt(values, "slotNo", out slotNo)
                    || slotNo < 0
                    || slotNo > 19)
                {
                    errorCode = "invalid_command";
                    error = "accessory slotNo must be an integer from 0 through 19.";
                    return false;
                }
                values.TryGetValue("parentKey", out parentKey);
            }
            else if (type == "face")
            {
                if (!GameItemSnapshotBuilder.IsFaceCategory(category))
                {
                    errorCode = "invalid_category";
                    error = "categoryNo is not one of the supported face categories.";
                    return false;
                }
                if (GameItemSnapshotBuilder.IsFaceEyeCategory(category))
                {
                    if (!TryGetRequiredInt(values, "facePartNo", out facePartNo)
                        || facePartNo < 0
                        || facePartNo > 1)
                    {
                        errorCode = "invalid_face_slot";
                        error = "facePartNo must be an integer from 0 through 1 for eye-specific face items.";
                        return false;
                    }
                }
            }
            else if (type == "body")
            {
                if (!GameItemSnapshotBuilder.IsBodyCategory(category))
                {
                    errorCode = "invalid_category";
                    error = "categoryNo is not one of the supported body categories.";
                    return false;
                }
                if (GameItemSnapshotBuilder.IsBodyPaintCategory(category))
                {
                    if (!TryGetRequiredInt(values, "bodyPartNo", out bodyPartNo)
                        || bodyPartNo < 0
                        || bodyPartNo > 1)
                    {
                        errorCode = "invalid_body_slot";
                        error = "bodyPartNo must be an integer from 0 through 1 for body-paint items.";
                        return false;
                    }
                }
            }

            command = new ApplyCommand
            {
                Type = type,
                Target = target,
                TargetSex = targetSex,
                TargetCharacterIndex = hasTargetCharacterIndex
                    ? (int?)targetCharacterIndex
                    : null,
                TargetCharacterId = hasTargetCharacterId
                    ? (int?)targetCharacterId
                    : null,
                Guid = guid,
                CategoryNo = category,
                LocalSlot = hasLocalSlot ? (int?)localSlot : null,
                OriginalSlot = hasOriginalSlot ? (int?)originalSlot : null,
                AccessorySlotNo = type == "accessory" ? (int?)slotNo : null,
                HairSlotNo = type == "hair" ? (int?)hairSlotNo : null,
                FacePartNo = type == "face" && GameItemSnapshotBuilder.IsFaceEyeCategory(category)
                    ? (int?)facePartNo
                    : null,
                BodyPartNo = type == "body" && GameItemSnapshotBuilder.IsBodyPaintCategory(category)
                    ? (int?)bodyPartNo
                    : null,
                ParentKey = parentKey ?? string.Empty,
            };
            return true;
        }

        private static bool TryParseCard(
            Dictionary<string, string> values,
            out ApplyCommand command,
            out string errorCode,
            out string error
        )
        {
            command = null;
            errorCode = null;
            error = null;

            string path;
            if (!values.TryGetValue("path", out path) || string.IsNullOrWhiteSpace(path))
            {
                errorCode = "invalid_card_path";
                error = "path is required when type is card.";
                return false;
            }

            bool face;
            bool body;
            bool hair;
            bool parameter;
            bool clothes;
            bool accessory;
            if (!TryGetBool(values, "face", out face)
                || !TryGetBool(values, "body", out body)
                || !TryGetBool(values, "hair", out hair)
                || !TryGetBool(values, "parameter", out parameter)
                || !TryGetBool(values, "clothes", out clothes)
                || !TryGetBool(values, "accessory", out accessory))
            {
                errorCode = "invalid_card_selection";
                error = "face, body, hair, parameter, clothes and accessory must be booleans.";
                return false;
            }

            if (!face && !body && !hair && !parameter && !clothes && !accessory)
            {
                errorCode = "invalid_card_selection";
                error = "Select at least one character-card section to load.";
                return false;
            }

            command = new ApplyCommand
            {
                Type = "card",
                Target = "editor",
                CardPath = path.Trim(),
                CardFace = face,
                CardBody = body,
                CardHair = hair,
                CardParameter = parameter,
                CardClothes = clothes,
                CardAccessory = accessory,
            };
            return true;
        }

        private static bool TryGetRequiredInt(
            Dictionary<string, string> values,
            string key,
            out int value
        )
        {
            return TryGetInt(values, key, out value);
        }

        private static bool TryGetInt(
            Dictionary<string, string> values,
            string key,
            out int value
        )
        {
            value = 0;
            string raw;
            return values != null
                && values.TryGetValue(key, out raw)
                && int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static bool TryGetBool(
            Dictionary<string, string> values,
            string key,
            out bool value
        )
        {
            value = false;
            string raw;
            return values != null
                && values.TryGetValue(key, out raw)
                && bool.TryParse(raw, out value);
        }
    }

    internal static class GameItemCommandExecutor
    {
        internal static ApplyResult Execute(ApplyCommand command, ManualLogSource logger)
        {
            bool hSceneTarget = string.Equals(
                command.Target,
                "hscene",
                StringComparison.OrdinalIgnoreCase
            );
            ChaControl character;
            if (hSceneTarget)
            {
                ApplyResult targetError;
                character = GameItemSnapshotBuilder.FindHSceneCharacter(
                    command,
                    logger,
                    out targetError
                );
                if (character == null)
                {
                    return targetError ?? ApplyResult.Failure(
                        "target_not_found",
                        "The requested HScene character was not found."
                    );
                }
            }
            else
            {
                character = GameItemSnapshotBuilder.FindCurrentCharacter();
            }

            if (character == null)
            {
                return ApplyResult.Failure(
                    "not_in_editor",
                    "CharaCustom.CustomBase.chaCtrl is not available. Enter the character maker first."
                );
            }

            if (string.Equals(command.Type, "card", StringComparison.OrdinalIgnoreCase))
            {
                if (hSceneTarget)
                {
                    return ApplyResult.Failure(
                        "invalid_target",
                        "Character-card loading is only supported for the editor target."
                    );
                }
                return LoadCharacterCard(command, character, logger);
            }

            if (!command.CategoryNo.HasValue)
            {
                return ApplyResult.Failure("invalid_category", "categoryNo is required.");
            }
            int category = command.CategoryNo.Value;
            int localSlot;
            ApplyResult resolutionError;
            if (!TryResolveLocalSlot(command, category, out localSlot, out resolutionError))
            {
                return resolutionError;
            }

            ChaListControl listControl = GameItemSnapshotBuilder.GetListControl(character);
            if (listControl == null)
            {
                string listSource;
                listControl = GameItemSnapshotBuilder.FindListControl(logger, out listSource);
            }
            if (string.Equals(command.Type, "clothes", StringComparison.OrdinalIgnoreCase))
            {
                int kind;
                if (!GameItemSnapshotBuilder.TryGetClothesKind(character.sex, category, out kind))
                {
                    return ApplyResult.Failure(
                        "invalid_category",
                        $"categoryNo {category} is not a clothing category for character sex {character.sex}."
                    );
                }
                if (!HasListItem(listControl, category, localSlot))
                {
                    return ApplyResult.Failure(
                        "item_not_found",
                        $"No native game item exists for categoryNo {category}, localSlot {localSlot}."
                    );
                }

                try
                {
                    character.ChangeClothes(kind, localSlot, false);
                    return ApplyResult.Success(localSlot);
                }
                catch (Exception exception)
                {
                    logger.LogError($"ChangeClothes failed: {exception}");
                    return ApplyResult.Failure("execution_error", exception.Message);
                }
            }

            if (string.Equals(command.Type, "hair", StringComparison.OrdinalIgnoreCase))
            {
                int hairKind;
                if (!GameItemSnapshotBuilder.TryGetHairKind(category, out hairKind))
                {
                    return ApplyResult.Failure(
                        "invalid_category",
                        $"categoryNo {category} is not one of the supported hair categories."
                    );
                }
                if (!command.HairSlotNo.HasValue
                    || command.HairSlotNo.Value < 0
                    || command.HairSlotNo.Value > 3
                    || command.HairSlotNo.Value != hairKind)
                {
                    return ApplyResult.Failure(
                        "invalid_hair_slot",
                        $"hairSlotNo must be {hairKind} for categoryNo {category}."
                    );
                }
                if (!HasListItem(listControl, category, localSlot))
                {
                    return ApplyResult.Failure(
                        "item_not_found",
                        $"No native game item exists for hair categoryNo {category}, localSlot {localSlot}."
                    );
                }

                try
                {
                    character.ChangeHair(hairKind, localSlot, false);
                    return ApplyResult.Success(localSlot);
                }
                catch (Exception exception)
                {
                    logger.LogError($"ChangeHair failed: {exception}");
                    return ApplyResult.Failure("execution_error", exception.Message);
                }
            }

            if (string.Equals(command.Type, "face", StringComparison.OrdinalIgnoreCase))
            {
                return ApplyFace(command, character, listControl, category, localSlot, logger);
            }

            if (string.Equals(command.Type, "body", StringComparison.OrdinalIgnoreCase))
            {
                return ApplyBody(command, character, listControl, category, localSlot, logger);
            }

            if (!GameItemSnapshotBuilder.IsAccessoryCategory(category))
            {
                return ApplyResult.Failure(
                    "invalid_category",
                    $"categoryNo {category} is not an accessory category."
                );
            }
            if (!command.AccessorySlotNo.HasValue
                || command.AccessorySlotNo.Value < 0
                || command.AccessorySlotNo.Value > 19)
            {
                return ApplyResult.Failure(
                    "invalid_accessory_slot",
                    "Accessory slotNo must be between 0 and 19."
                );
            }
            // Category 350/id 0 is the game's explicit empty accessory entry.
            if (!(category == 350 && localSlot == 0)
                && !HasListItem(listControl, category, localSlot))
            {
                return ApplyResult.Failure(
                    "item_not_found",
                    $"No native game item exists for categoryNo {category}, localSlot {localSlot}."
                );
            }

            try
            {
                character.ChangeAccessory(
                    command.AccessorySlotNo.Value,
                    category,
                    localSlot,
                    command.ParentKey ?? string.Empty,
                    false
                );
                return ApplyResult.Success(localSlot);
            }
            catch (Exception exception)
            {
                logger.LogError($"ChangeAccessory failed: {exception}");
                return ApplyResult.Failure("execution_error", exception.Message);
            }
        }

        private static ApplyResult ApplyFace(
            ApplyCommand command,
            ChaControl character,
            ChaListControl listControl,
            int category,
            int localSlot,
            ManualLogSource logger
        )
        {
            int facePart;
            if (!GameItemSnapshotBuilder.TryGetFacePart(character.sex, category, out facePart))
            {
                return ApplyResult.Failure(
                    "invalid_category",
                    $"categoryNo {category} is not a face category for character sex {character.sex}."
                );
            }
            if (GameItemSnapshotBuilder.IsFaceEyeCategory(category)
                && (!command.FacePartNo.HasValue || command.FacePartNo.Value < 0 || command.FacePartNo.Value > 1))
            {
                return ApplyResult.Failure(
                    "invalid_face_slot",
                    "facePartNo must be between 0 and 1 for eye-specific face items."
                );
            }
            if (!HasListItem(listControl, category, localSlot))
            {
                return ApplyResult.Failure(
                    "item_not_found",
                    $"No native game item exists for face categoryNo {category}, localSlot {localSlot}."
                );
            }
            if (character.fileFace == null)
            {
                return ApplyResult.Failure("target_unavailable", "The current face data is not ready.");
            }

            try
            {
                switch (facePart)
                {
                    case 0:
                        character.ChangeHead(localSlot, false);
                        break;
                    case 1:
                        character.fileFace.skinId = localSlot;
                        character.AddUpdateCMFaceTexFlags(true, false, false, false, false, false, false);
                        if (!character.CreateFaceTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the face skin texture.");
                        }
                        break;
                    case 2:
                        character.fileFace.detailId = localSlot;
                        if (!character.ChangeFaceDetailKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the face-detail item.");
                        }
                        break;
                    case 3:
                        character.fileFace.beardId = localSlot;
                        if (!character.ChangeBeardKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the beard item.");
                        }
                        break;
                    case 4:
                        character.fileFace.eyebrowId = localSlot;
                        if (!character.ChangeEyebrowKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the eyebrow item.");
                        }
                        break;
                    case 5:
                        character.fileFace.eyelashesId = localSlot;
                        if (!character.ChangeEyelashesKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the eyelashes item.");
                        }
                        break;
                    case 6:
                        if (character.fileFace.makeup == null)
                        {
                            return ApplyResult.Failure("target_unavailable", "The current makeup data is not ready.");
                        }
                        character.fileFace.makeup.eyeshadowId = localSlot;
                        character.AddUpdateCMFaceTexFlags(false, true, false, false, false, false, false);
                        if (!character.CreateFaceTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the eyeshadow texture.");
                        }
                        break;
                    case 7:
                        if (!TrySetEyeItem(character, command.FacePartNo.Value, localSlot, false))
                        {
                            return ApplyResult.Failure("invalid_face_slot", "The selected eye slot is not available.");
                        }
                        if (!character.ChangeEyesKind(command.FacePartNo.Value))
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the pupil item.");
                        }
                        break;
                    case 8:
                        if (!TrySetEyeItem(character, command.FacePartNo.Value, localSlot, true))
                        {
                            return ApplyResult.Failure("invalid_face_slot", "The selected eye slot is not available.");
                        }
                        if (!character.ChangeBlackEyesKind(command.FacePartNo.Value))
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the pupil-shape item.");
                        }
                        break;
                    case 9:
                        character.fileFace.hlId = localSlot;
                        if (!character.ChangeEyesHighlightKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the eye-highlight item.");
                        }
                        break;
                    case 10:
                        if (character.fileFace.makeup == null)
                        {
                            return ApplyResult.Failure("target_unavailable", "The current makeup data is not ready.");
                        }
                        character.fileFace.makeup.cheekId = localSlot;
                        character.AddUpdateCMFaceTexFlags(false, false, false, false, true, false, false);
                        if (!character.CreateFaceTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the cheek texture.");
                        }
                        break;
                    case 11:
                        if (character.fileFace.makeup == null)
                        {
                            return ApplyResult.Failure("target_unavailable", "The current makeup data is not ready.");
                        }
                        character.fileFace.makeup.lipId = localSlot;
                        character.AddUpdateCMFaceTexFlags(false, false, false, false, false, true, false);
                        if (!character.CreateFaceTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the lip texture.");
                        }
                        break;
                    case 12:
                        character.fileFace.moleId = localSlot;
                        character.AddUpdateCMFaceTexFlags(false, false, false, false, false, false, true);
                        if (!character.CreateFaceTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the mole texture.");
                        }
                        break;
                    default:
                        return ApplyResult.Failure("invalid_category", $"Unsupported face part {facePart}.");
                }
                return ApplyResult.Success(localSlot);
            }
            catch (Exception exception)
            {
                logger.LogError($"Face item apply failed for category {category}: {exception}");
                return ApplyResult.Failure("execution_error", exception.Message);
            }
        }

        private static ApplyResult ApplyBody(
            ApplyCommand command,
            ChaControl character,
            ChaListControl listControl,
            int category,
            int localSlot,
            ManualLogSource logger
        )
        {
            int bodyPart;
            if (!GameItemSnapshotBuilder.TryGetBodyPart(character.sex, category, out bodyPart))
            {
                return ApplyResult.Failure(
                    "invalid_category",
                    $"categoryNo {category} is not a body category for character sex {character.sex}."
                );
            }
            if (GameItemSnapshotBuilder.IsBodyPaintCategory(category)
                && (!command.BodyPartNo.HasValue || command.BodyPartNo.Value < 0 || command.BodyPartNo.Value > 1))
            {
                return ApplyResult.Failure(
                    "invalid_body_slot",
                    "bodyPartNo must be between 0 and 1 for body-paint items."
                );
            }
            if (!HasListItem(listControl, category, localSlot))
            {
                return ApplyResult.Failure(
                    "item_not_found",
                    $"No native game item exists for body categoryNo {category}, localSlot {localSlot}."
                );
            }
            if (character.fileBody == null)
            {
                return ApplyResult.Failure("target_unavailable", "The current body data is not ready.");
            }

            try
            {
                switch (bodyPart)
                {
                    case 0:
                        character.fileBody.skinId = localSlot;
                        character.AddUpdateCMBodyTexFlags(true, false, false, false);
                        if (!character.CreateBodyTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the body-skin texture.");
                        }
                        break;
                    case 1:
                        character.fileBody.detailId = localSlot;
                        character.AddUpdateCMBodyTexFlags(true, false, false, false);
                        if (!character.CreateBodyTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the body-detail texture.");
                        }
                        break;
                    case 2:
                        character.fileBody.sunburnId = localSlot;
                        character.AddUpdateCMBodyTexFlags(false, false, false, true);
                        if (!character.CreateBodyTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the sunburn texture.");
                        }
                        break;
                    case 3:
                        int paintIndex = command.BodyPartNo.Value;
                        if (character.fileBody.paintInfo == null
                            || paintIndex < 0
                            || paintIndex >= character.fileBody.paintInfo.Length
                            || character.fileBody.paintInfo[paintIndex] == null)
                        {
                            return ApplyResult.Failure("invalid_body_slot", "The selected body-paint layer is not available.");
                        }
                        if (category == 8)
                        {
                            character.fileBody.paintInfo[paintIndex].layoutId = localSlot;
                            character.AddUpdateCMBodyLayoutFlags(paintIndex == 0, paintIndex == 1);
                        }
                        else
                        {
                            character.fileBody.paintInfo[paintIndex].id = localSlot;
                            character.AddUpdateCMBodyTexFlags(false, paintIndex == 0, paintIndex == 1, false);
                        }
                        if (!character.CreateBodyTexture())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not rebuild the body-paint texture.");
                        }
                        break;
                    case 4:
                        character.fileBody.nipId = localSlot;
                        if (!character.ChangeNipKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the nipple item.");
                        }
                        break;
                    case 5:
                        character.fileBody.underhairId = localSlot;
                        if (!character.ChangeUnderHairKind())
                        {
                            return ApplyResult.Failure("execution_error", "The game could not apply the underhair item.");
                        }
                        break;
                    default:
                        return ApplyResult.Failure("invalid_category", $"Unsupported body part {bodyPart}.");
                }
                return ApplyResult.Success(localSlot);
            }
            catch (Exception exception)
            {
                logger.LogError($"Body item apply failed for category {category}: {exception}");
                return ApplyResult.Failure("execution_error", exception.Message);
            }
        }

        private static bool TrySetEyeItem(ChaControl character, int eyeIndex, int localSlot, bool black)
        {
            if (eyeIndex < 0 || eyeIndex > 1 || character.fileFace.pupil == null || eyeIndex >= character.fileFace.pupil.Length)
            {
                return false;
            }
            ChaFileFace.EyesInfo eye = character.fileFace.pupil[eyeIndex];
            if (eye == null)
            {
                return false;
            }
            if (black)
            {
                eye.blackId = localSlot;
            }
            else
            {
                eye.pupilId = localSlot;
            }
            return true;
        }

        private static ApplyResult LoadCharacterCard(
            ApplyCommand command,
            ChaControl character,
            ManualLogSource logger
        )
        {
            string cardPath;
            int cardSex;
            ApplyResult pathError;
            if (!TryResolveCharacterCardPath(
                command.CardPath,
                out cardPath,
                out cardSex,
                out pathError
            ))
            {
                return pathError;
            }

            if (cardSex != character.sex)
            {
                return ApplyResult.Failure(
                    "card_sex_mismatch",
                    $"The card is for sex {cardSex}, but the current editor character is sex {character.sex}."
                );
            }

            ChaFileControl target = character.chaFile;
            if (target == null || target.custom == null || target.coordinate == null)
            {
                return ApplyResult.Failure(
                    "target_unavailable",
                    "The current editor character data is not ready."
                );
            }

            // The native character-card window keeps the top-level object
            // visible. ReloadAsync(asyncFlags: true) is a different internal
            // path that hides objTop and is not part of the native card-load
            // call chain. Do not enter that path here.
            try
            {
                character.SetActiveTop(true);
            }
            catch (Exception exception)
            {
                logger.LogDebug($"Could not restore character visibility before card load: {exception.Message}");
            }

            // LoadFileLimited is an in-place API: it reads a temporary ChaFile
            // internally and copies the requested sections into this control.
            // Calling it on a newly constructed ChaFileControl leaves the
            // destination sections uninitialized and makes every card load
            // report false. Preserve the unselected coordinate half because
            // the native API treats clothes and accessories as one block.
            ChaFile coordinateBackup = null;
            if (command.CardClothes != command.CardAccessory)
            {
                coordinateBackup = CloneCoordinate(target);
            }

            // Keep a section-level rollback copy. A failed mod resource load
            // must not leave the live ChaFile pointing at half of the new
            // card, because the next editor reload would then reconstruct an
            // empty or incomplete character from that state.
            ChaFile customBackup = null;
            ChaFile parameterBackup = null;
            if (command.CardFace || command.CardBody || command.CardHair)
            {
                customBackup = new ChaFile();
                customBackup.CopyCustom(target.custom);
            }
            if (command.CardParameter)
            {
                parameterBackup = new ChaFile();
                parameterBackup.CopyParameter(target.parameter);
                parameterBackup.CopyParameter2(target.parameter2);
            }
            if (command.CardClothes || command.CardAccessory)
            {
                coordinateBackup = CloneCoordinate(target);
            }

            Action recover = delegate
            {
                if (customBackup != null)
                {
                    if (command.CardFace)
                    {
                        target.custom.face = customBackup.custom.face;
                    }
                    if (command.CardBody)
                    {
                        target.custom.body = customBackup.custom.body;
                    }
                    if (command.CardHair)
                    {
                        target.custom.hair = customBackup.custom.hair;
                    }
                }
                if (parameterBackup != null)
                {
                    target.CopyParameter(parameterBackup.parameter);
                    target.CopyParameter2(parameterBackup.parameter2);
                }
                if (coordinateBackup != null)
                {
                    target.CopyCoordinate(coordinateBackup.coordinate);
                    character.ChangeNowCoordinate(false, true);
                }
                character.SetActiveTop(true);
            };

            bool loadResult;
            bool previousSkipRangeCheck = target.skipRangeCheck;
            try
            {
                target.skipRangeCheck = true;
                loadResult = target.LoadFileLimited(
                    cardPath,
                    (byte)cardSex,
                    command.CardFace,
                    command.CardBody,
                    command.CardHair,
                    command.CardParameter,
                    command.CardClothes || command.CardAccessory
                );
            }
            catch (Exception exception)
            {
                try
                {
                    recover();
                }
                catch (Exception recoveryException)
                {
                    logger.LogWarning($"Could not roll back card data after LoadFileLimited failure: {recoveryException.Message}");
                }
                logger.LogError($"LoadFileLimited failed for {cardPath}: {exception}");
                return ApplyResult.Failure("card_load_failed", exception.Message);
            }
            finally
            {
                target.skipRangeCheck = previousSkipRangeCheck;
            }

            if (coordinateBackup != null)
            {
                if (command.CardClothes && !command.CardAccessory)
                {
                    target.coordinate.accessory = coordinateBackup.coordinate.accessory;
                }
                else if (command.CardAccessory && !command.CardClothes)
                {
                    target.coordinate.clothes = coordinateBackup.coordinate.clothes;
                }
            }

            try
            {
                // This is the same call order used by CvsO_CharaLoad:
                // ChangeNowCoordinate(false, true), then Reload(...). The
                // five-argument Reload starts the native ReloadAsync(false,
                // ...) coroutine, which in turn invokes ChangeClothes(true)
                // and ChangeAccessory(true) with asyncFlags=false. Calling
                // the outer method is important because Slider Unlocker and
                // other game plugins patch Reload rather than ReloadAsync.
                character.ChangeNowCoordinate(false, true);

                bool nativeReloadResult;
                // CvsO_CharaLoad disables the custom-load GC cleanup while
                // the native reload is being scheduled, then restores it
                // immediately after Reload returns. Use the probe's
                // reflection compatibility layer so this assembly does not
                // acquire a hard dependency on the game's IL.dll.
                bool customLoadGCClearChanged =
                    GameItemSnapshotBuilder.TrySetCustomLoadGCClear(false);
                try
                {
                    nativeReloadResult = character.Reload(
                        !(command.CardClothes || command.CardAccessory),
                        !command.CardFace,
                        !command.CardHair,
                        !command.CardBody,
                        true
                    );
                }
                finally
                {
                    if (customLoadGCClearChanged)
                    {
                        GameItemSnapshotBuilder.TrySetCustomLoadGCClear(true);
                    }
                }

                try
                {
                    character.SetActiveTop(true);
                }
                catch (Exception exception)
                {
                    logger.LogDebug($"Could not restore character visibility after card reload: {exception.Message}");
                }

                logger.LogInfo(
                    $"Loaded character card {cardPath} sections: "
                        + $"face={command.CardFace}, body={command.CardBody}, hair={command.CardHair}, "
                        + $"parameter={command.CardParameter}, clothes={command.CardClothes}, "
                        + $"accessory={command.CardAccessory}, nativeLoadResult={loadResult}, "
                        + $"nativeReloadResult={nativeReloadResult}, "
                        + "reloadPath=ChangeNowCoordinate+Reload."
                );
                return ApplyResult.Success(null);
            }
            catch (Exception exception)
            {
                try
                {
                    recover();
                }
                catch (Exception visibilityException)
                {
                    logger.LogWarning($"Could not recover character data after card-load failure: {visibilityException.Message}");
                }
                logger.LogError($"Applying character card failed: {exception}");
                return ApplyResult.Failure("execution_error", exception.Message);
            }
        }

        private static ChaFile CloneCoordinate(ChaFile source)
        {
            var copy = new ChaFile();
            copy.CopyCoordinate(source.coordinate);
            return copy;
        }

        private static bool TryResolveCharacterCardPath(
            string requestedPath,
            out string fullPath,
            out int sex,
            out ApplyResult error
        )
        {
            fullPath = null;
            sex = -1;
            error = null;
            if (string.IsNullOrWhiteSpace(requestedPath))
            {
                error = ApplyResult.Failure("invalid_card_path", "Character-card path is required.");
                return false;
            }

            try
            {
                string candidate = requestedPath.Trim();
                fullPath = Path.GetFullPath(
                    Path.IsPathRooted(candidate)
                        ? candidate
                        : Path.Combine(Paths.GameRootPath, candidate)
                );
                string cardRoot = Path.GetFullPath(
                    Path.Combine(Paths.GameRootPath, "UserData", "chara")
                ).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                string rootPrefix = cardRoot + Path.DirectorySeparatorChar;
                if (!fullPath.StartsWith(rootPrefix, StringComparison.OrdinalIgnoreCase))
                {
                    error = ApplyResult.Failure(
                        "invalid_card_path",
                        "Character-card path must be inside UserData/chara."
                    );
                    return false;
                }

                string relative = fullPath.Substring(rootPrefix.Length);
                string[] parts = relative.Split(
                    new[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar },
                    StringSplitOptions.RemoveEmptyEntries
                );
                if (parts.Length < 2
                    || (!string.Equals(parts[0], "female", StringComparison.OrdinalIgnoreCase)
                        && !string.Equals(parts[0], "male", StringComparison.OrdinalIgnoreCase))
                    || !string.Equals(Path.GetExtension(fullPath), ".png", StringComparison.OrdinalIgnoreCase)
                    || !File.Exists(fullPath))
                {
                    error = ApplyResult.Failure(
                        "invalid_card_path",
                        "A PNG character card inside the female or male folder is required."
                    );
                    return false;
                }

                sex = string.Equals(parts[0], "female", StringComparison.OrdinalIgnoreCase) ? 1 : 0;
                return true;
            }
            catch (Exception exception)
            {
                error = ApplyResult.Failure("invalid_card_path", exception.Message);
                return false;
            }
        }

        private static bool HasListItem(ChaListControl listControl, int category, int localSlot)
        {
            if (listControl == null)
            {
                return false;
            }
            try
            {
                return listControl.GetListInfo(
                    (ChaListDefine.CategoryNo)category,
                    localSlot
                ) != null;
            }
            catch (Exception)
            {
                return false;
            }
        }

        private static bool TryResolveLocalSlot(
            ApplyCommand command,
            int category,
            out int localSlot,
            out ApplyResult error
        )
        {
            localSlot = 0;
            error = null;
            List<int> candidates = new List<int>();
            if (!string.IsNullOrWhiteSpace(command.Guid))
            {
                IEnumerable<ResolveInfo> loaded;
                try
                {
                    loaded = UniversalAutoResolver.LoadedResolutionInfo;
                }
                catch (Exception exception)
                {
                    error = ApplyResult.Failure("item_not_found", exception.Message);
                    return false;
                }

                foreach (ResolveInfo info in loaded ?? Enumerable.Empty<ResolveInfo>())
                {
                    if (info == null
                        || !string.Equals(info.GUID, command.Guid, StringComparison.OrdinalIgnoreCase)
                        || (int)info.CategoryNo != category
                        || !command.OriginalSlot.HasValue
                        || info.Slot != command.OriginalSlot.Value)
                    {
                        continue;
                    }
                    if (!candidates.Contains(info.LocalSlot))
                    {
                        candidates.Add(info.LocalSlot);
                    }
                }

                if (candidates.Count == 0)
                {
                    error = ApplyResult.Failure(
                        "item_not_found",
                        "No resolver record matches guid, categoryNo and slot."
                    );
                    return false;
                }
                if (candidates.Count > 1)
                {
                    error = ApplyResult.Failure(
                        "ambiguous_mapping",
                        "The resolver data maps this guid/categoryNo/slot to multiple localSlot values."
                    );
                    return false;
                }
                localSlot = candidates[0];
                if (command.LocalSlot.HasValue && command.LocalSlot.Value != localSlot)
                {
                    error = ApplyResult.Failure(
                        "ambiguous_mapping",
                        "localSlot does not agree with the resolver record selected by guid and slot."
                    );
                    return false;
                }
                return true;
            }

            if (!command.LocalSlot.HasValue)
            {
                error = ApplyResult.Failure(
                    "item_not_found",
                    "localSlot is required when guid is not supplied."
                );
                return false;
            }
            localSlot = command.LocalSlot.Value;
            return true;
        }
    }

    internal static class SimpleJsonObject
    {
        internal static bool TryParse(
            string json,
            out Dictionary<string, string> values,
            out string error
        )
        {
            values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            error = null;
            int index = 0;
            SkipWhitespace(json, ref index);
            if (!Consume(json, ref index, '{'))
            {
                error = "Request body must be a JSON object.";
                return false;
            }

            SkipWhitespace(json, ref index);
            if (Consume(json, ref index, '}'))
            {
                return true;
            }
            while (index < (json ?? string.Empty).Length)
            {
                string key;
                if (!ReadString(json, ref index, out key))
                {
                    error = "JSON object property names must be strings.";
                    return false;
                }
                SkipWhitespace(json, ref index);
                if (!Consume(json, ref index, ':'))
                {
                    error = "A colon is required after every JSON property name.";
                    return false;
                }
                SkipWhitespace(json, ref index);
                string value;
                if (!ReadValue(json, ref index, out value))
                {
                    error = "Command values must be strings, numbers, booleans or null.";
                    return false;
                }
                values[key] = value;
                SkipWhitespace(json, ref index);
                if (Consume(json, ref index, '}'))
                {
                    SkipWhitespace(json, ref index);
                    if (index != (json ?? string.Empty).Length)
                    {
                        error = "Unexpected data after the JSON object.";
                        return false;
                    }
                    return true;
                }
                if (!Consume(json, ref index, ','))
                {
                    error = "A comma is required between JSON properties.";
                    return false;
                }
                SkipWhitespace(json, ref index);
            }
            error = "JSON object is incomplete.";
            return false;
        }

        private static bool ReadValue(string json, ref int index, out string value)
        {
            value = null;
            if (index >= (json ?? string.Empty).Length)
            {
                return false;
            }
            if (json[index] == '"')
            {
                return ReadString(json, ref index, out value);
            }
            int start = index;
            while (index < json.Length
                && !char.IsWhiteSpace(json[index])
                && json[index] != ','
                && json[index] != '}')
            {
                if (json[index] == '{' || json[index] == '[')
                {
                    return false;
                }
                index++;
            }
            if (start == index)
            {
                return false;
            }
            string token = json.Substring(start, index - start);
            if (token == "null")
            {
                value = null;
                return true;
            }
            if (token == "true" || token == "false"
                || int.TryParse(token, NumberStyles.Integer, CultureInfo.InvariantCulture, out _))
            {
                value = token;
                return true;
            }
            return false;
        }

        private static bool ReadString(string json, ref int index, out string value)
        {
            value = null;
            if (index >= (json ?? string.Empty).Length || json[index] != '"')
            {
                return false;
            }
            index++;
            var builder = new StringBuilder();
            while (index < json.Length)
            {
                char character = json[index++];
                if (character == '"')
                {
                    value = builder.ToString();
                    return true;
                }
                if (character != '\\')
                {
                    builder.Append(character);
                    continue;
                }
                if (index >= json.Length)
                {
                    return false;
                }
                char escaped = json[index++];
                switch (escaped)
                {
                    case '"': builder.Append('"'); break;
                    case '\\': builder.Append('\\'); break;
                    case '/': builder.Append('/'); break;
                    case 'b': builder.Append('\b'); break;
                    case 'f': builder.Append('\f'); break;
                    case 'n': builder.Append('\n'); break;
                    case 'r': builder.Append('\r'); break;
                    case 't': builder.Append('\t'); break;
                    case 'u':
                        if (index + 4 > json.Length)
                        {
                            return false;
                        }
                        int code;
                        if (!int.TryParse(
                            json.Substring(index, 4),
                            NumberStyles.HexNumber,
                            CultureInfo.InvariantCulture,
                            out code
                        ))
                        {
                            return false;
                        }
                        builder.Append((char)code);
                        index += 4;
                        break;
                    default: return false;
                }
            }
            return false;
        }

        private static bool Consume(string json, ref int index, char expected)
        {
            if (index < (json ?? string.Empty).Length && json[index] == expected)
            {
                index++;
                return true;
            }
            return false;
        }

        private static void SkipWhitespace(string json, ref int index)
        {
            while (index < (json ?? string.Empty).Length && char.IsWhiteSpace(json[index]))
            {
                index++;
            }
        }
    }

    internal sealed class GameItemProbeServer
    {
        private readonly ManualLogSource logger;
        private readonly int port;
        private readonly Action requestRefresh;
        private readonly GameItemCommandQueue commandQueue;
        private readonly object stateGate = new object();
        private TcpListener listener;
        private Thread listenerThread;
        private SnapshotState state;
        private ContextState context;
        private volatile bool stopping;

        internal GameItemProbeServer(
            ManualLogSource logSource,
            int listenPort,
            Action refreshCallback,
            GameItemCommandQueue commandCommandQueue
        )
        {
            logger = logSource;
            port = listenPort;
            requestRefresh = refreshCallback;
            commandQueue = commandCommandQueue;
        }

        internal void Start()
        {
            listener = new TcpListener(IPAddress.Loopback, port);
            listener.Start();
            listenerThread = new Thread(ListenLoop)
            {
                IsBackground = true,
                Name = "StarManager.GameItemProbe.Http",
            };
            listenerThread.Start();
        }

        internal void Stop()
        {
            stopping = true;
            try
            {
                listener?.Stop();
            }
            catch (Exception)
            {
                // The listener is already closed.
            }

            if (listenerThread != null && listenerThread.IsAlive)
            {
                listenerThread.Join(1000);
            }
            listenerThread = null;
        }

        internal void Publish(SnapshotState newState)
        {
            lock (stateGate)
            {
                state = newState;
                context = newState == null ? null : newState.Context;
            }
        }

        internal void PublishCurrent(CurrentState current)
        {
            lock (stateGate)
            {
                if (state != null)
                {
                    state.Current = current;
                }
            }
        }

        internal void PublishContext(ContextState context)
        {
            lock (stateGate)
            {
                if (state != null)
                {
                    state.Context = context;
                }
                this.context = context;
            }
        }

        private void ListenLoop()
        {
            while (!stopping)
            {
                TcpClient client = null;
                try
                {
                    client = listener.AcceptTcpClient();
                    ThreadPool.QueueUserWorkItem(HandleClient, client);
                }
                catch (SocketException)
                {
                    client?.Close();
                    if (!stopping)
                    {
                        logger.LogWarning("Game item probe listener stopped unexpectedly.");
                    }
                }
                catch (ObjectDisposedException)
                {
                    client?.Close();
                }
                catch (Exception exception)
                {
                    client?.Close();
                    if (!stopping)
                    {
                        logger.LogWarning($"Game item probe listener error: {exception.Message}");
                    }
                }
            }
        }

        private void HandleClient(object clientObject)
        {
            using (var client = clientObject as TcpClient)
            {
                if (client == null)
                {
                    return;
                }

                try
                {
                    client.ReceiveTimeout = 2000;
                    client.SendTimeout = 5000;
                    using (NetworkStream stream = client.GetStream())
                    {
                        string request = ReadRequest(stream);
                        HttpRequestLine line = HttpRequestLine.Parse(request);
                        HttpResponse response = Route(line);
                        WriteResponse(stream, response);
                    }
                }
                catch (Exception exception)
                {
                    logger.LogDebug($"Game item probe request failed: {exception.Message}");
                }
            }
        }

        private HttpResponse Route(HttpRequestLine request)
        {
            if (request == null)
            {
                return HttpResponse.Json(400, "{\"error\":\"Invalid HTTP request.\"}");
            }

            if (string.Equals(request.Method, "OPTIONS", StringComparison.OrdinalIgnoreCase))
            {
                return HttpResponse.NoContent(204);
            }

            if (string.Equals(request.Method, "POST", StringComparison.OrdinalIgnoreCase)
                && request.Path == "/api/apply")
            {
                ApplyCommand command;
                string errorCode = null;
                string error = null;
                if (commandQueue == null
                    || !commandQueue.TryEnqueue(request.Body, out command, out errorCode, out error))
                {
                    return HttpResponse.Json(
                        400,
                        SnapshotJson.WriteCommandError(errorCode, error)
                    );
                }
                return HttpResponse.Json(202, SnapshotJson.WriteCommand(command));
            }

            if (!string.Equals(request.Method, "GET", StringComparison.OrdinalIgnoreCase))
            {
                return HttpResponse.Json(405, "{\"error\":\"Only GET and POST /api/apply are supported.\"}");
            }

            if (request.Path == "/api/refresh")
            {
                requestRefresh?.Invoke();
                return HttpResponse.Json(202, "{\"ok\":true,\"message\":\"refresh queued\"}");
            }

            if (request.Path == "/api/command")
            {
                string commandId;
                if (!request.Query.TryGetValue("id", out commandId)
                    || string.IsNullOrWhiteSpace(commandId))
                {
                    return HttpResponse.Json(400, "{\"error\":\"id is required.\"}");
                }
                ApplyCommand command;
                return commandQueue != null
                    && commandQueue.TryGet(commandId, out command)
                    ? HttpResponse.Json(200, SnapshotJson.WriteCommand(command))
                    : HttpResponse.Json(404, "{\"error\":\"command not found\"}");
            }

            SnapshotState current;
            ContextState currentContext;
            lock (stateGate)
            {
                current = state;
                currentContext = context;
            }

            if (request.Path == "/api/status")
            {
                return HttpResponse.Json(200, SnapshotJson.WriteStatus(current));
            }

            if (request.Path == "/api/current")
            {
                return HttpResponse.Json(200, SnapshotJson.WriteCurrent(current));
            }

            if (request.Path == "/api/context")
            {
                return HttpResponse.Json(200, SnapshotJson.WriteContext(currentContext));
            }

            if (request.Path == "/api/items")
            {
                return HttpResponse.Json(200, SnapshotJson.WriteFilteredItems(current, request.Query));
            }

            if (request.Path == "/api/item")
            {
                return RouteSingleItem(current, request.Query);
            }

            if (request.Path == "/api/resolve")
            {
                return RouteResolve(current, request.Query);
            }

                return HttpResponse.Json(
                200,
                "{\"name\":\"Star Manager Game Item Probe\"," 
                    + "\"endpoints\":[\"/api/items\",\"/api/item?category=240&localSlot=100017053\"," 
                    + "\"/api/resolve?category=240&localSlot=100017053\",\"/api/current\"," 
                    + "\"/api/context\",\"/api/status\",\"/api/refresh\",\"POST /api/apply\"," 
                    + "\"/api/command?id=<commandId>\"]}"
            );
        }

        private static HttpResponse RouteSingleItem(
            SnapshotState snapshot,
            Dictionary<string, string> query
        )
        {
            int category;
            int localSlot;
            if (!TryGetInt(query, "category", out category)
                || !TryGetInt(query, "localSlot", out localSlot))
            {
                return HttpResponse.Json(
                    400,
                    "{\"error\":\"category and localSlot are required integers.\"}"
                );
            }

            ItemRecord item = snapshot?.Items?.FirstOrDefault(
                candidate => candidate.CategoryNo == category && candidate.LocalSlot == localSlot
            );
            return item == null
                ? HttpResponse.Json(404, "{\"error\":\"item not found\"}")
                : HttpResponse.Json(200, SnapshotJson.WriteItem(item));
        }

        private static HttpResponse RouteResolve(
            SnapshotState snapshot,
            Dictionary<string, string> query
        )
        {
            IEnumerable<ResolverRecord> records = snapshot?.ResolverRecords
                ?? Enumerable.Empty<ResolverRecord>();
            int number;
            if (TryGetInt(query, "category", out number))
            {
                records = records.Where(record => record.CategoryNo == number);
            }
            if (TryGetInt(query, "localSlot", out number))
            {
                records = records.Where(record => record.LocalSlot == number);
            }
            if (TryGetInt(query, "slot", out number))
            {
                records = records.Where(record => record.Slot == number);
            }
            string guid;
            if (query.TryGetValue("guid", out guid) && !string.IsNullOrWhiteSpace(guid))
            {
                records = records.Where(
                    record => string.Equals(record.Guid, guid, StringComparison.OrdinalIgnoreCase)
                );
            }

            return HttpResponse.Json(200, SnapshotJson.WriteResolverList(records));
        }

        private static bool TryGetInt(
            Dictionary<string, string> query,
            string name,
            out int value
        )
        {
            value = 0;
            string raw;
            return query != null
                && query.TryGetValue(name, out raw)
                && int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }

        private static string ReadRequest(NetworkStream stream)
        {
            using (var data = new MemoryStream())
            {
                var buffer = new byte[8192];
                int headerEnd = -1;
                int contentLength = 0;
                while (data.Length < 65536 && headerEnd < 0)
                {
                    int read = stream.Read(buffer, 0, buffer.Length);
                    if (read <= 0)
                    {
                        break;
                    }
                    data.Write(buffer, 0, read);
                    byte[] bytes = data.ToArray();
                    headerEnd = FindHeaderEnd(bytes);
                    if (headerEnd >= 0)
                    {
                        string headers = Encoding.ASCII.GetString(bytes, 0, headerEnd);
                        contentLength = ReadContentLength(headers);
                        if (contentLength < 0 || contentLength > 32768)
                        {
                            return Encoding.UTF8.GetString(bytes, 0, bytes.Length);
                        }
                    }
                }

                if (headerEnd < 0)
                {
                    return Encoding.UTF8.GetString(data.ToArray());
                }

                int required = headerEnd + 4 + contentLength;
                while (data.Length < required)
                {
                    int remaining = required - (int)data.Length;
                    int read = stream.Read(buffer, 0, Math.Min(buffer.Length, remaining));
                    if (read <= 0)
                    {
                        break;
                    }
                    data.Write(buffer, 0, read);
                }
                return Encoding.UTF8.GetString(data.ToArray());
            }
        }

        private static int FindHeaderEnd(byte[] data)
        {
            for (int index = 3; index < data.Length; index++)
            {
                if (data[index - 3] == 13
                    && data[index - 2] == 10
                    && data[index - 1] == 13
                    && data[index] == 10)
                {
                    return index - 3;
                }
            }
            return -1;
        }

        private static int ReadContentLength(string headers)
        {
            foreach (string line in (headers ?? string.Empty).Split(new[] { "\r\n", "\n" }, StringSplitOptions.None))
            {
                int colon = line.IndexOf(':');
                if (colon < 0 || !string.Equals(line.Substring(0, colon).Trim(), "Content-Length", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                int length;
                return int.TryParse(line.Substring(colon + 1).Trim(), NumberStyles.None, CultureInfo.InvariantCulture, out length)
                    ? length
                    : -1;
            }
            return 0;
        }

        private static void WriteResponse(NetworkStream stream, HttpResponse response)
        {
            byte[] body = Encoding.UTF8.GetBytes(response.Body ?? "{}");
            string headers = "HTTP/1.1 " + response.StatusCode.ToString(CultureInfo.InvariantCulture)
                + " " + response.StatusText + "\r\n"
                + "Content-Type: application/json; charset=utf-8\r\n"
                + "Access-Control-Allow-Origin: *\r\n"
                + "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                + "Access-Control-Allow-Headers: Content-Type\r\n"
                + "Cache-Control: no-store\r\n"
                + "Content-Length: " + body.Length.ToString(CultureInfo.InvariantCulture) + "\r\n"
                + "Connection: close\r\n\r\n";
            byte[] prefix = Encoding.ASCII.GetBytes(headers);
            stream.Write(prefix, 0, prefix.Length);
            stream.Write(body, 0, body.Length);
        }
    }

    internal sealed class HttpRequestLine
    {
        internal string Method;
        internal string Path;
        internal Dictionary<string, string> Query;
        internal string Body;

        internal static HttpRequestLine Parse(string raw)
        {
            string firstLine = (raw ?? string.Empty)
                .Split(new[] { "\r\n", "\n" }, StringSplitOptions.None)
                .FirstOrDefault();
            string[] parts = (firstLine ?? string.Empty).Split(' ');
            if (parts.Length < 2)
            {
                return null;
            }

            string target = parts[1];
            int question = target.IndexOf('?');
            string path = question < 0 ? target : target.Substring(0, question);
            string queryString = question < 0 ? null : target.Substring(question + 1);
            string body = string.Empty;
            int bodyStart = raw == null ? -1 : raw.IndexOf("\r\n\r\n", StringComparison.Ordinal);
            if (bodyStart >= 0)
            {
                body = raw.Substring(bodyStart + 4);
            }
            return new HttpRequestLine
            {
                Method = parts[0],
                Path = Uri.UnescapeDataString(path),
                Query = ParseQuery(queryString),
                Body = body,
            };
        }

        private static Dictionary<string, string> ParseQuery(string query)
        {
            var output = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            if (string.IsNullOrEmpty(query))
            {
                return output;
            }

            foreach (string part in query.Split('&'))
            {
                if (string.IsNullOrEmpty(part))
                {
                    continue;
                }

                int equals = part.IndexOf('=');
                string rawKey = equals < 0 ? part : part.Substring(0, equals);
                string rawValue = equals < 0 ? string.Empty : part.Substring(equals + 1);
                output[Uri.UnescapeDataString(rawKey.Replace('+', ' '))]
                    = Uri.UnescapeDataString(rawValue.Replace('+', ' '));
            }
            return output;
        }
    }

    internal sealed class HttpResponse
    {
        internal int StatusCode;
        internal string StatusText;
        internal string Body;

        internal static HttpResponse Json(int statusCode, string body)
        {
            return new HttpResponse
            {
                StatusCode = statusCode,
                StatusText = statusCode == 200
                    ? "OK"
                    : statusCode == 202
                        ? "Accepted"
                        : statusCode == 400
                            ? "Bad Request"
                            : statusCode == 404
                                ? "Not Found"
                                : statusCode == 405
                                    ? "Method Not Allowed"
                                    : "Error",
                Body = body,
            };
        }

        internal static HttpResponse NoContent(int statusCode)
        {
            return new HttpResponse
            {
                StatusCode = statusCode,
                StatusText = "No Content",
                Body = string.Empty,
            };
        }
    }

    internal static class SnapshotJson
    {
        internal static string WriteCommand(ApplyCommand command)
        {
            var writer = new JsonWriter();
            lock (command?.StateGate ?? new object())
            {
                writer.BeginObject();
                writer.Property("accepted"); writer.Bool(command != null);
                writer.Property("commandId"); writer.String(command?.CommandId);
                writer.Property("status"); writer.String(command?.Status);
                writer.Property("type"); writer.String(command?.Type);
                writer.Property("target"); writer.String(command?.Target);
                writer.Property("sex"); writer.NullableInt(command?.TargetSex);
                writer.Property("characterIndex"); writer.NullableInt(command?.TargetCharacterIndex);
                writer.Property("targetCharacterId"); writer.NullableInt(command?.TargetCharacterId);
                writer.Property("guid"); writer.String(command?.Guid);
                writer.Property("categoryNo"); writer.NullableInt(command?.CategoryNo);
                writer.Property("localSlot"); writer.NullableInt(command?.LocalSlot);
                writer.Property("slot"); writer.NullableInt(command?.OriginalSlot);
                writer.Property("slotNo"); writer.NullableInt(command?.AccessorySlotNo);
                writer.Property("hairSlotNo"); writer.NullableInt(command?.HairSlotNo);
                writer.Property("facePartNo"); writer.NullableInt(command?.FacePartNo);
                writer.Property("bodyPartNo"); writer.NullableInt(command?.BodyPartNo);
                writer.Property("path"); writer.String(command?.CardPath);
                writer.Property("face"); writer.Bool(command != null && command.CardFace);
                writer.Property("body"); writer.Bool(command != null && command.CardBody);
                writer.Property("hair"); writer.Bool(command != null && command.CardHair);
                writer.Property("parameter"); writer.Bool(command != null && command.CardParameter);
                writer.Property("clothes"); writer.Bool(command != null && command.CardClothes);
                writer.Property("accessory"); writer.Bool(command != null && command.CardAccessory);
                writer.Property("resolvedLocalSlot"); writer.NullableInt(command?.ResolvedLocalSlot);
                writer.Property("errorCode"); writer.String(command?.ErrorCode);
                writer.Property("error"); writer.String(command?.Error);
                writer.Property("acceptedAtUtc"); writer.String(command?.AcceptedAtUtc);
                writer.Property("startedAtUtc"); writer.String(command?.StartedAtUtc);
                writer.Property("completedAtUtc"); writer.String(command?.CompletedAtUtc);
                writer.EndObject();
            }
            return writer.ToString();
        }

        internal static string WriteCommandError(string errorCode, string error)
        {
            var writer = new JsonWriter();
            writer.BeginObject();
            writer.Property("accepted"); writer.Bool(false);
            writer.Property("errorCode"); writer.String(errorCode);
            writer.Property("error"); writer.String(error);
            writer.EndObject();
            return writer.ToString();
        }

        internal static string Write(SnapshotState snapshot)
        {
            var writer = new JsonWriter();
            writer.BeginObject();
            writer.Property("schemaVersion"); writer.Int(snapshot?.SchemaVersion ?? 3);
            writer.Property("capturedAtUtc"); writer.String(snapshot?.CapturedAtUtc);
            writer.Property("listControlFound"); writer.Bool(snapshot != null && snapshot.ListControlFound);
            writer.Property("listControlSource"); writer.String(snapshot?.ListControlSource);
            writer.Property("error"); writer.String(snapshot?.Error);
            writer.Property("items"); WriteItems(writer, snapshot?.Items);
            writer.Property("resolverRecords"); WriteResolvers(writer, snapshot?.ResolverRecords);
            writer.Property("current"); WriteCurrentObject(writer, snapshot?.Current);
            writer.EndObject();
            return writer.ToString();
        }

        internal static string WriteStatus(SnapshotState snapshot)
        {
            var writer = new JsonWriter();
            writer.BeginObject();
            writer.Property("schemaVersion"); writer.Int(snapshot?.SchemaVersion ?? 3);
            writer.Property("capturedAtUtc"); writer.String(snapshot?.CapturedAtUtc);
            writer.Property("listControlFound"); writer.Bool(snapshot != null && snapshot.ListControlFound);
            writer.Property("listControlSource"); writer.String(snapshot?.ListControlSource);
            writer.Property("itemCount"); writer.Int(snapshot?.Items?.Count ?? 0);
            writer.Property("resolverRecordCount"); writer.Int(snapshot?.ResolverRecords?.Count ?? 0);
            writer.Property("error"); writer.String(snapshot?.Error);
            writer.EndObject();
            return writer.ToString();
        }

        internal static string WriteFilteredItems(
            SnapshotState snapshot,
            Dictionary<string, string> query
        )
        {
            IEnumerable<ItemRecord> items = snapshot?.Items ?? Enumerable.Empty<ItemRecord>();
            int category;
            if (TryGetInt(query, "category", out category))
            {
                items = items.Where(item => item.CategoryNo == category);
            }
            string guid;
            if (query != null && query.TryGetValue("guid", out guid) && !string.IsNullOrWhiteSpace(guid))
            {
                items = items.Where(
                    item => item.ResolverRecords.Any(
                        record => string.Equals(record.Guid, guid, StringComparison.OrdinalIgnoreCase)
                    )
                );
            }

            var writer = new JsonWriter();
            writer.BeginObject();
            writer.Property("capturedAtUtc"); writer.String(snapshot?.CapturedAtUtc);
            writer.Property("count");
            List<ItemRecord> materialized = items.ToList();
            writer.Int(materialized.Count);
            writer.Property("items"); WriteItems(writer, materialized);
            writer.EndObject();
            return writer.ToString();
        }

        internal static string WriteItem(ItemRecord item)
        {
            var writer = new JsonWriter();
            WriteItemObject(writer, item);
            return writer.ToString();
        }

        internal static string WriteResolverList(IEnumerable<ResolverRecord> records)
        {
            var writer = new JsonWriter();
            writer.BeginObject();
            writer.Property("count");
            List<ResolverRecord> materialized = (records ?? Enumerable.Empty<ResolverRecord>()).ToList();
            writer.Int(materialized.Count);
            writer.Property("records"); WriteResolvers(writer, materialized);
            writer.EndObject();
            return writer.ToString();
        }

        internal static string WriteCurrent(SnapshotState snapshot)
        {
            var writer = new JsonWriter();
            WriteCurrentObject(writer, snapshot?.Current);
            return writer.ToString();
        }

        internal static string WriteContext(ContextState context)
        {
            var writer = new JsonWriter();
            WriteContextObject(writer, context);
            return writer.ToString();
        }

        private static void WriteItems(JsonWriter writer, IEnumerable<ItemRecord> items)
        {
            writer.BeginArray();
            foreach (ItemRecord item in items ?? Enumerable.Empty<ItemRecord>())
            {
                WriteItemObject(writer, item);
            }
            writer.EndArray();
        }

        private static void WriteItemObject(JsonWriter writer, ItemRecord item)
        {
            writer.BeginObject();
            writer.Property("categoryNo"); writer.Int(item?.CategoryNo ?? 0);
            writer.Property("categoryName"); writer.String(item?.CategoryName);
            writer.Property("categoryEnumName"); writer.String(item?.CategoryEnumName);
            writer.Property("listIndex"); writer.Int(item?.ListIndex ?? 0);
            writer.Property("distribution"); writer.Int(item?.Distribution ?? 0);
            writer.Property("localSlot"); writer.Int(item?.LocalSlot ?? 0);
            writer.Property("resolvedId"); writer.Int(item?.LocalSlot ?? 0);
            writer.Property("listId"); writer.Int(item?.ListId ?? 0);
            writer.Property("originalId"); writer.NullableInt(item?.OriginalId);
            writer.Property("kind"); writer.Int(item?.Kind ?? 0);
            writer.Property("name"); writer.String(item?.Name);
            writer.Property("fontSize"); writer.Int(item?.FontSize ?? 0);
            writer.Property("idField"); writer.String(item?.IdField);
            writer.Property("mainManifest"); writer.String(item?.MainManifest);
            writer.Property("mainAB"); writer.String(item?.MainAB);
            writer.Property("mainData"); writer.String(item?.MainData);
            writer.Property("thumbAB"); writer.String(item?.ThumbAB);
            writer.Property("thumbTex"); writer.String(item?.ThumbTex);
            writer.Property("texAB"); writer.String(item?.TexAB);
            writer.Property("dictInfo"); WriteStringDictionary(writer, item?.DictInfo);
            writer.Property("resolverRecords"); WriteResolvers(writer, item?.ResolverRecords);
            writer.EndObject();
        }

        private static void WriteResolvers(JsonWriter writer, IEnumerable<ResolverRecord> records)
        {
            writer.BeginArray();
            foreach (ResolverRecord record in records ?? Enumerable.Empty<ResolverRecord>())
            {
                writer.BeginObject();
                writer.Property("guid"); writer.String(record?.Guid);
                writer.Property("slot"); writer.Int(record?.Slot ?? 0);
                writer.Property("localSlot"); writer.Int(record?.LocalSlot ?? 0);
                writer.Property("property"); writer.String(record?.Property);
                writer.Property("categoryNo"); writer.NullableInt(record?.CategoryNo);
                writer.Property("categoryName"); writer.String(record?.CategoryName);
                writer.Property("author"); writer.String(record?.Author);
                writer.Property("website"); writer.String(record?.Website);
                writer.Property("name"); writer.String(record?.Name);
                writer.Property("modName"); writer.String(record?.ModName);
                writer.Property("modVersion"); writer.String(record?.ModVersion);
                writer.Property("zipmodPath"); writer.String(record?.ZipmodPath);
                writer.EndObject();
            }
            writer.EndArray();
        }

        private static void WriteCurrentObject(JsonWriter writer, CurrentState current)
        {
            writer.BeginObject();
            writer.Property("available"); writer.Bool(current != null && current.Available);
            writer.Property("source"); writer.String(current?.Source);
            writer.Property("characterId"); writer.Int(current?.CharacterId ?? 0);
            writer.Property("sex"); writer.Int(current?.Sex ?? 0);
            writer.Property("characterName"); writer.String(current?.CharacterName);
            writer.Property("characterFileName"); writer.String(current?.CharacterFileName);
            writer.Property("coordinateName"); writer.String(current?.CoordinateName);
            writer.Property("hairs"); WriteCurrentItems(writer, current?.Hairs);
            writer.Property("clothes"); WriteCurrentItems(writer, current?.Clothes);
            writer.Property("faces"); WriteCurrentItems(writer, current?.Faces);
            writer.Property("bodies"); WriteCurrentItems(writer, current?.Bodies);
            writer.Property("accessories"); WriteCurrentItems(writer, current?.Accessories);
            writer.EndObject();
        }

        private static void WriteContextObject(JsonWriter writer, ContextState context)
        {
            writer.BeginObject();
            writer.Property("available"); writer.Bool(context != null && context.Available);
            writer.Property("scene"); writer.String(context?.Scene);
            writer.Property("editor"); WriteContextCharacter(writer, context?.Editor);
            writer.Property("hscene"); WriteHSceneContext(writer, context?.HScene);
            writer.EndObject();
        }

        private static void WriteHSceneContext(JsonWriter writer, HSceneContext hScene)
        {
            writer.BeginObject();
            writer.Property("available"); writer.Bool(hScene != null && hScene.Available);
            writer.Property("femaleCount"); writer.Int(hScene?.FemaleCount ?? 0);
            writer.Property("maleCount"); writer.Int(hScene?.MaleCount ?? 0);
            writer.Property("totalCount"); writer.Int(hScene?.TotalCount ?? 0);
            writer.Property("females"); WriteContextCharacters(writer, hScene?.Females);
            writer.Property("males"); WriteContextCharacters(writer, hScene?.Males);
            writer.EndObject();
        }

        private static void WriteContextCharacters(
            JsonWriter writer,
            IEnumerable<ContextCharacter> characters
        )
        {
            writer.BeginArray();
            foreach (ContextCharacter character in characters ?? Enumerable.Empty<ContextCharacter>())
            {
                WriteContextCharacter(writer, character);
            }
            writer.EndArray();
        }

        private static void WriteContextCharacter(
            JsonWriter writer,
            ContextCharacter character
        )
        {
            writer.BeginObject();
            writer.Property("available"); writer.Bool(character != null && character.Available);
            writer.Property("active"); writer.Bool(character != null && character.Active);
            writer.Property("characterIndex"); writer.Int(character?.CharacterIndex ?? -1);
            writer.Property("characterId"); writer.Int(character?.CharacterId ?? 0);
                writer.Property("sex"); writer.Int(character?.Sex ?? -1);
                writer.Property("characterName"); writer.String(character?.CharacterName);
                writer.Property("characterFileName"); writer.String(character?.CharacterFileName);
                writer.Property("current"); WriteCurrentObject(writer, character?.Current);
                writer.EndObject();
        }

        private static void WriteCurrentItems(JsonWriter writer, IEnumerable<CurrentItem> items)
        {
            writer.BeginArray();
            foreach (CurrentItem item in items ?? Enumerable.Empty<CurrentItem>())
            {
                writer.BeginObject();
                writer.Property("partType"); writer.String(item?.PartType);
                writer.Property("partIndex"); writer.Int(item?.PartIndex ?? 0);
                writer.Property("categoryNo"); writer.Int(item?.CategoryNo ?? 0);
                writer.Property("localSlot"); writer.Int(item?.LocalSlot ?? 0);
                writer.Property("resolvedId"); writer.Int(item?.LocalSlot ?? 0);
                writer.Property("listId"); writer.Int(item?.ListId ?? 0);
                writer.Property("originalId"); writer.NullableInt(item?.OriginalId);
                writer.Property("kind"); writer.Int(item?.Kind ?? 0);
                writer.Property("name"); writer.String(item?.Name);
                writer.Property("partLabel"); writer.String(item?.PartLabel);
                writer.Property("resolverRecords"); WriteResolvers(writer, item?.ResolverRecords);
                writer.EndObject();
            }
            writer.EndArray();
        }

        private static void WriteStringDictionary(
            JsonWriter writer,
            Dictionary<string, string> dictionary
        )
        {
            writer.BeginObject();
            foreach (KeyValuePair<string, string> entry in dictionary ?? new Dictionary<string, string>())
            {
                writer.Property(entry.Key);
                writer.String(entry.Value);
            }
            writer.EndObject();
        }

        private static bool TryGetInt(
            Dictionary<string, string> query,
            string name,
            out int value
        )
        {
            value = 0;
            string raw;
            return query != null
                && query.TryGetValue(name, out raw)
                && int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
        }
    }

    internal sealed class JsonWriter
    {
        private readonly StringBuilder builder = new StringBuilder();
        private readonly Stack<bool> firstValues = new Stack<bool>();
        private bool afterProperty;

        internal void BeginObject()
        {
            ValuePrefix();
            builder.Append('{');
            firstValues.Push(true);
        }

        internal void EndObject()
        {
            builder.Append('}');
            firstValues.Pop();
        }

        internal void BeginArray()
        {
            ValuePrefix();
            builder.Append('[');
            firstValues.Push(true);
        }

        internal void EndArray()
        {
            builder.Append(']');
            firstValues.Pop();
        }

        internal void Property(string name)
        {
            if (!firstValues.Peek())
            {
                builder.Append(',');
            }
            firstValues.Pop();
            firstValues.Push(false);
            WriteString(name);
            builder.Append(':');
            afterProperty = true;
        }

        internal void String(string value)
        {
            ValuePrefix();
            if (value == null)
            {
                builder.Append("null");
                return;
            }
            WriteString(value);
        }

        internal void Int(int value)
        {
            ValuePrefix();
            builder.Append(value.ToString(CultureInfo.InvariantCulture));
        }

        internal void NullableInt(int? value)
        {
            ValuePrefix();
            builder.Append(value.HasValue
                ? value.Value.ToString(CultureInfo.InvariantCulture)
                : "null");
        }

        internal void Bool(bool value)
        {
            ValuePrefix();
            builder.Append(value ? "true" : "false");
        }

        public override string ToString()
        {
            return builder.ToString();
        }

        private void ValuePrefix()
        {
            if (afterProperty)
            {
                afterProperty = false;
                return;
            }
            if (firstValues.Count == 0 || firstValues.Peek())
            {
                if (firstValues.Count > 0)
                {
                    firstValues.Pop();
                    firstValues.Push(false);
                }
                return;
            }
            builder.Append(',');
        }

        private void WriteString(string value)
        {
            builder.Append('"');
            if (value != null)
            {
                foreach (char character in value)
                {
                    switch (character)
                    {
                        case '"': builder.Append("\\\""); break;
                        case '\\': builder.Append("\\\\"); break;
                        case '\b': builder.Append("\\b"); break;
                        case '\f': builder.Append("\\f"); break;
                        case '\n': builder.Append("\\n"); break;
                        case '\r': builder.Append("\\r"); break;
                        case '\t': builder.Append("\\t"); break;
                        default:
                            if (character < 32)
                            {
                                builder.Append("\\u");
                                builder.Append(((int)character).ToString("x4", CultureInfo.InvariantCulture));
                            }
                            else
                            {
                                builder.Append(character);
                            }
                            break;
                    }
                }
            }
            builder.Append('"');
        }
    }
}
