using System.Collections.Generic;
using System.IO;
using AIChara;
using BepInEx;
using BepInEx.Logging;
using ExtensibleSaveFormat;
using HarmonyLib;
using KKAPI;
using KKAPI.Chara;

namespace StarManager.CardMetadata
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    [BepInDependency(KoikatuAPI.GUID, BepInDependency.DependencyFlags.HardDependency)]
    [BepInDependency(ExtendedSave.GUID, BepInDependency.DependencyFlags.HardDependency)]
    public sealed class CardMetadataPlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "star.manager.cardmetadata.bridge";
        public const string PluginName = "Star Manager Card Metadata";
        public const string PluginVersion = "1.4.2";
        public const string ExtendedDataId = "star.manager.cardmetadata";

        private void Awake()
        {
            CharacterApi.RegisterExtraBehaviour<CardMetadataController>(ExtendedDataId);
            CardMetadataPersistence.Initialize(Logger);
            ExtendedSave.CardBeingLoaded += CardMetadataPersistence.OnCardBeingLoaded;
            ExtendedSave.CardBeingSaved += CardMetadataPersistence.OnCardBeingSaved;
            Harmony.CreateAndPatchAll(typeof(CardMetadataPlugin).Assembly, PluginGuid);
            Logger.LogInfo($"Registered ExtendedSave data ID: {ExtendedDataId}");
        }
    }

    /// <summary>
    /// Registers Star Manager's card metadata with HS2API. Disk metadata from
    /// the selected save target is restored by CardMetadataPersistence.
    /// </summary>
    public sealed class CardMetadataController : CharaCustomFunctionController
    {
        protected override void OnReload(GameMode currentGameMode, bool maintainState)
        {
        }

        protected override void OnCardBeingSaved(GameMode currentGameMode)
        {
        }

        internal static PluginData ClonePluginData(PluginData source)
        {
            if (source == null)
            {
                return null;
            }

            return new PluginData
            {
                version = source.version,
                data = CloneDictionary(source.data),
            };
        }

        private static Dictionary<string, object> CloneDictionary(
            Dictionary<string, object> source
        )
        {
            var output = new Dictionary<string, object>();
            if (source == null)
            {
                return output;
            }

            foreach (KeyValuePair<string, object> item in source)
            {
                output[item.Key] = CloneValue(item.Value);
            }

            return output;
        }

        private static object CloneValue(object value)
        {
            if (value is Dictionary<string, object> dictionary)
            {
                return CloneDictionary(dictionary);
            }

            if (value is byte[] bytes)
            {
                return (byte[])bytes.Clone();
            }

            if (value is object[] array)
            {
                var output = new object[array.Length];
                for (int index = 0; index < array.Length; index++)
                {
                    output[index] = CloneValue(array[index]);
                }
                return output;
            }

            if (value is IList<object> list)
            {
                var output = new List<object>(list.Count);
                foreach (object item in list)
                {
                    output.Add(CloneValue(item));
                }
                return output;
            }

            return value;
        }
    }

    internal static class CardMetadataPersistence
    {
        private static ManualLogSource logger;
        private static readonly PendingSaveTarget<PluginData> pendingTarget =
            new PendingSaveTarget<PluginData>();

        internal static void Initialize(ManualLogSource logSource)
        {
            logger = logSource;
        }

        internal static void OnCardBeingLoaded(ChaFile file)
        {
            PluginData data = ExtendedSave.GetExtendedDataById(
                file,
                CardMetadataPlugin.ExtendedDataId
            );
            logger?.LogDebug(
                $"Card load metadata: {file.charaFileName}, present={data != null}"
            );
        }

        internal static void CaptureSaveTarget(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                logger?.LogDebug("Save target metadata: no overwrite path selected");
                return;
            }

            string requestedTargetPath = Path.GetFullPath(
                Path.IsPathRooted(path) ? path : Path.Combine(Paths.GameRootPath, path)
            );
            bool targetExists = false;
            bool captured = pendingTarget.TryCapture(
                requestedTargetPath,
                () =>
                {
                    targetExists = File.Exists(requestedTargetPath);
                    return targetExists
                        ? ReadMetadataFromDisk(requestedTargetPath)
                        : null;
                },
                out string targetPath,
                out PluginData targetMetadata
            );

            // A single card save constructs multiple FileStreams for the same
            // path. The recycle-bin plugin moves the old file after the first
            // constructor, so later constructors must not replace the original
            // disk snapshot with a false "new target" result.
            if (!captured)
            {
                logger?.LogDebug(
                    $"Save target metadata: repeated path ignored: {targetPath}"
                );
                return;
            }

            if (!targetExists)
            {
                logger?.LogDebug(
                    $"Save target metadata: {targetPath}, target=new, present=false"
                );
                return;
            }

            logger?.LogDebug(
                $"Save target metadata: {targetPath}, target=existing, " +
                $"present={targetMetadata != null}"
            );
        }

        internal static void OnCardBeingSaved(ChaFile file)
        {
            SaveTargetConsumption<PluginData> consumedTarget =
                pendingTarget.Consume(file?.charaFileName);
            PluginData outputData = consumedTarget.Matches
                ? CardMetadataController.ClonePluginData(consumedTarget.Value)
                : null;
            string source = consumedTarget.Matches
                ? "disk-target"
                : "no-matching-disk-target";

            ExtendedSave.SetExtendedDataById(
                file,
                CardMetadataPlugin.ExtendedDataId,
                outputData
            );
            logger?.LogDebug(
                $"Card save metadata: {file.charaFileName}, present={outputData != null}, " +
                $"source={source}, target={consumedTarget.TargetPath ?? "<none>"}"
            );
        }

        internal static void ClearCopiedMetadata(ChaFile destination, ChaFile source)
        {
            if (destination == null || source == null)
            {
                return;
            }

            ExtendedSave.SetExtendedDataById(
                destination,
                CardMetadataPlugin.ExtendedDataId,
                null
            );
            logger?.LogDebug(
                $"Card copy metadata: {source.charaFileName} -> {destination.charaFileName}, " +
                "present=false, source=blocked-game-copy"
            );
        }

        private static PluginData ReadMetadataFromDisk(string path)
        {
            var loadFile = AccessTools.Method(
                typeof(ChaFile),
                "LoadFile",
                new[] { typeof(string), typeof(int), typeof(bool), typeof(bool) }
            );
            if (loadFile == null)
            {
                logger?.LogWarning("Could not find ChaFile.LoadFile path overload.");
                return null;
            }

            try
            {
                var existingFile = new ChaFile();
                bool loaded = (bool)loadFile.Invoke(
                    existingFile,
                    new object[] { path, 0, true, true }
                );
                if (!loaded)
                {
                    logger?.LogWarning($"Could not load save target metadata: {path}");
                    return null;
                }

                return CardMetadataController.ClonePluginData(
                    ExtendedSave.GetExtendedDataById(
                        existingFile,
                        CardMetadataPlugin.ExtendedDataId
                    )
                );
            }
            catch (System.Exception exception)
            {
                logger?.LogWarning(
                    $"Failed to read save target metadata: {path}; {exception.Message}"
                );
                return null;
            }
        }

    }

    [HarmonyPatch]
    internal static class CharacterCardFileStreamPatch
    {
        private static IEnumerable<System.Reflection.MethodBase> TargetMethods()
        {
            foreach (
                System.Reflection.ConstructorInfo constructor in
                AccessTools.GetDeclaredConstructors(typeof(FileStream))
            )
            {
                bool hasFileMode = false;
                bool hasFileAccess = false;
                foreach (
                    System.Reflection.ParameterInfo parameter in constructor.GetParameters()
                )
                {
                    hasFileMode |= parameter.ParameterType == typeof(FileMode);
                    hasFileAccess |= parameter.ParameterType == typeof(FileAccess);
                }

                if (hasFileMode && hasFileAccess)
                {
                    yield return constructor;
                }
            }
        }

        [HarmonyPrefix]
        [HarmonyPriority(Priority.First)]
        [HarmonyBefore("marco.RemoveToRecycleBin")]
        private static void Prefix(string path, FileMode mode, FileAccess access)
        {
            if (mode != FileMode.Create || (access & FileAccess.Write) == 0)
            {
                return;
            }

            string fullPath;
            try
            {
                fullPath = Path.GetFullPath(path);
            }
            catch (System.Exception)
            {
                return;
            }

            string characterRoot = Path.GetFullPath(
                Path.Combine(Paths.GameRootPath, "UserData", "chara")
            ).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)
                + Path.DirectorySeparatorChar;

            if (
                !fullPath.StartsWith(
                    characterRoot,
                    System.StringComparison.OrdinalIgnoreCase
                )
                || !fullPath.EndsWith(
                    ".png",
                    System.StringComparison.OrdinalIgnoreCase
                )
            )
            {
                return;
            }

            CardMetadataPersistence.CaptureSaveTarget(fullPath);
        }
    }

    [HarmonyPatch(
        typeof(ChaFile),
        nameof(ChaFile.CopyChaFile),
        new[]
        {
            typeof(ChaFile),
            typeof(ChaFile),
            typeof(bool),
            typeof(bool),
            typeof(bool),
            typeof(bool),
            typeof(bool),
        }
    )]
    internal static class ChaFileCopyPatch
    {
        [HarmonyPostfix]
        private static void Postfix(ChaFile dst, ChaFile src)
        {
            CardMetadataPersistence.ClearCopiedMetadata(dst, src);
        }
    }
}
