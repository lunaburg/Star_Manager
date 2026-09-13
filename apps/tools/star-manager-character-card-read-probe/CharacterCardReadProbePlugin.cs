using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using AIChara;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using UnityEngine;
using Object = UnityEngine.Object;

namespace StarManager.CharacterCardReadProbe
{
    [BepInPlugin(PluginGuid, PluginName, PluginVersion)]
    public sealed class CharacterCardReadProbePlugin : BaseUnityPlugin
    {
        public const string PluginGuid = "star.manager.charactercardreadprobe";
        public const string PluginName = "Star Manager Character Card Read Probe";
        public const string PluginVersion = "0.2.0";

        internal static CharacterCardReadProbePlugin Instance { get; private set; }

        private ConfigEntry<bool> captureSceneAfterLoad;
        private ConfigEntry<bool> captureMethodState;
        private ConfigEntry<bool> traceAssetBundleLoads;
        private ConfigEntry<KeyboardShortcut> snapshotHotkey;
        private ConfigEntry<string> outputPath;
        private ConfigEntry<int> port;
        private Harmony harmony;
        private CardReadAudit audit;
        private CharacterCardReadProbeServer server;
        private readonly List<ScheduledCapture> scheduledCaptures = new List<ScheduledCapture>();
        private int snapshotRequested;
        private int frame;

        private void Awake()
        {
            Instance = this;
            captureSceneAfterLoad = Config.Bind(
                "Capture",
                "CaptureSceneAfterLoad",
                true,
                "Capture character bones, renderers, materials and texture metadata after card/resource reloads."
            );
            captureMethodState = Config.Bind(
                "Capture",
                "CaptureMethodState",
                true,
                "Capture ChaFile section fingerprints before and after card-loading methods."
            );
            traceAssetBundleLoads = Config.Bind(
                "Capture",
                "TraceAssetBundleLoads",
                false,
                "Trace AssetBundle asset-load method calls. This can be very verbose and is disabled by default."
            );
            snapshotHotkey = Config.Bind(
                "Capture",
                "SnapshotHotkey",
                new KeyboardShortcut(KeyCode.F8),
                "Capture the current character scene state immediately."
            );
            outputPath = Config.Bind(
                "Output",
                "JsonlPath",
                Path.Combine(Paths.ConfigPath, "StarManager.CharacterCardReadProbe.jsonl"),
                "UTF-8 JSON Lines output. Relative paths are resolved from the game root."
            );
            port = Config.Bind(
                "Server",
                "Port",
                7881,
                "Loopback HTTP port for the independent character-card read probe."
            );

            audit = new CardReadAudit(Logger, ResolveOutputPath(outputPath.Value));
            Logger.LogInfo("Initializing independent character-card read probe.");

            var targets = new List<MethodBase>();
            try
            {
                targets = CardReadProbePatches.TargetMethods().ToList();
            }
            catch (Exception exception)
            {
                Logger.LogError($"Could not discover character-card methods: {exception}");
            }

            try
            {
                harmony = new Harmony(PluginGuid);
                harmony.PatchAll(typeof(CharacterCardReadProbePlugin).Assembly);
                PluginCallbackObserver.Patch(harmony);
            }
            catch (Exception exception)
            {
                Logger.LogError($"Could not patch character-card methods: {exception}");
            }

            try
            {
                audit.RecordSession(
                    targets,
                    GetLoadedPlugins(),
                    PluginCallbackObserver.DescribeTargets()
                );
            }
            catch (Exception exception)
            {
                Logger.LogError($"Could not write character-card probe session record: {exception}");
            }

            try
            {
                server = new CharacterCardReadProbeServer(
                    Logger,
                    port.Value,
                    audit,
                    RequestSceneSnapshot
                );
                server.Start();
                Logger.LogInfo(
                    $"Started independent character-card read probe; patched {targets.Count} methods. "
                        + $"Observed plugin callbacks: {PluginCallbackObserver.PatchedCount}. "
                        + $"Output: {audit.Path}; API: http://127.0.0.1:{port.Value}/api/status"
                );
            }
            catch (Exception exception)
            {
                Logger.LogError($"Could not start character-card probe HTTP API on port {port.Value}: {exception}");
            }
        }

        private void Update()
        {
            frame++;
            if (snapshotHotkey.Value.IsDown())
            {
                CaptureCurrentScene("hotkey");
            }

            if (Interlocked.Exchange(ref snapshotRequested, 0) != 0)
            {
                CaptureCurrentScene("http");
            }

            for (int index = scheduledCaptures.Count - 1; index >= 0; index--)
            {
                ScheduledCapture capture = scheduledCaptures[index];
                if (capture.DueFrame > frame)
                {
                    continue;
                }

                scheduledCaptures.RemoveAt(index);
                CaptureCurrentScene(capture.Trigger);
            }
        }

        private void RequestSceneSnapshot()
        {
            Interlocked.Exchange(ref snapshotRequested, 1);
        }

        internal void HandleMethod(
            MethodBase method,
            object instance,
            object[] args,
            MethodInvocation invocation,
            Exception exception
        )
        {
            if (method == null)
            {
                return;
            }

            try
            {
                Dictionary<string, object> record = new Dictionary<string, object>
                {
                    ["recordType"] = "method_call",
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["threadId"] = Thread.CurrentThread.ManagedThreadId,
                    ["type"] = method.DeclaringType == null ? "" : method.DeclaringType.FullName,
                    ["method"] = method.ToString(),
                    ["phase"] = exception == null ? "completed" : "threw",
                    ["durationMs"] = invocation == null ? null : ElapsedMilliseconds(invocation.StartTimestamp),
                    ["arguments"] = AuditValue.CaptureArguments(args),
                    ["instance"] = AuditValue.CaptureInstance(instance),
                    ["harmonyOwners"] = HarmonyOwnerReader.Read(method),
                };

                if (invocation != null && invocation.Before != null)
                {
                    record["before"] = invocation.Before;
                }

                if (captureMethodState.Value && instance is ChaFile)
                {
                    Dictionary<string, object> after = AuditValue.CaptureChaFile((ChaFile)instance);
                    record["after"] = after;
                    if (invocation != null && invocation.Before != null)
                    {
                        record["changedSections"] = AuditValue.FindChangedSections(invocation.Before, after);
                    }
                }

                if (exception != null)
                {
                    record["exception"] = new Dictionary<string, object>
                    {
                        ["type"] = exception.GetType().FullName,
                        ["message"] = exception.Message,
                    };
                }

                audit?.Record(record);

                string methodName = method.Name ?? "";
                if (captureSceneAfterLoad.Value
                    && (methodName.IndexOf("Load", StringComparison.OrdinalIgnoreCase) >= 0
                        || methodName.IndexOf("Reload", StringComparison.OrdinalIgnoreCase) >= 0
                        || methodName.Equals("ChangeNowCoordinate", StringComparison.Ordinal)))
                {
                    ScheduleSceneCaptures(methodName, exception == null);
                }
            }
            catch (Exception probeException)
            {
                Logger.LogDebug($"Character-card probe method capture failed: {probeException.Message}");
            }
        }

        internal bool ShouldTraceAssetBundleLoads()
        {
            return traceAssetBundleLoads != null && traceAssetBundleLoads.Value;
        }

        internal bool ConfiguredCaptureMethodState()
        {
            return captureMethodState != null && captureMethodState.Value;
        }

        internal void HandlePluginCallbackStarted(
            PluginCallbackTarget target,
            MethodBase method,
            object instance,
            object[] args,
            PluginCallbackInvocation invocation
        )
        {
            if (target == null || method == null || invocation == null)
            {
                return;
            }

            try
            {
                audit?.Record(new Dictionary<string, object>
                {
                    ["recordType"] = "plugin_callback",
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["threadId"] = Thread.CurrentThread.ManagedThreadId,
                    ["phase"] = "started",
                    ["plugin"] = target.Plugin,
                    ["pluginGuid"] = target.PluginGuid,
                    ["extensionDataId"] = target.ExtensionDataId,
                    ["callbackKind"] = target.CallbackKind,
                    ["type"] = method.DeclaringType == null ? "" : method.DeclaringType.FullName,
                    ["method"] = method.ToString(),
                    ["arguments"] = AuditValue.CaptureArguments(args),
                    ["instance"] = AuditValue.CaptureInstance(instance),
                    ["context"] = AuditValue.CapturePluginCallbackContext(target, instance),
                    ["harmonyOwners"] = HarmonyOwnerReader.Read(method),
                });
            }
            catch (Exception probeException)
            {
                Logger.LogDebug($"Character-card plugin callback start capture failed: {probeException.Message}");
            }
        }

        internal void HandlePluginCallbackCompleted(
            PluginCallbackTarget target,
            MethodBase method,
            object instance,
            object[] args,
            PluginCallbackInvocation invocation,
            Exception exception
        )
        {
            if (target == null || method == null || invocation == null)
            {
                return;
            }

            try
            {
                var record = new Dictionary<string, object>
                {
                    ["recordType"] = "plugin_callback",
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["threadId"] = Thread.CurrentThread.ManagedThreadId,
                    ["phase"] = exception == null ? "completed" : "threw",
                    ["plugin"] = target.Plugin,
                    ["pluginGuid"] = target.PluginGuid,
                    ["extensionDataId"] = target.ExtensionDataId,
                    ["callbackKind"] = target.CallbackKind,
                    ["type"] = method.DeclaringType == null ? "" : method.DeclaringType.FullName,
                    ["method"] = method.ToString(),
                    ["durationMs"] = ElapsedMilliseconds(invocation.StartTimestamp),
                    ["arguments"] = AuditValue.CaptureArguments(args),
                    ["instance"] = AuditValue.CaptureInstance(instance),
                    ["context"] = AuditValue.CapturePluginCallbackContext(target, instance),
                    ["harmonyOwners"] = HarmonyOwnerReader.Read(method),
                };
                if (exception != null)
                {
                    record["exception"] = new Dictionary<string, object>
                    {
                        ["type"] = exception.GetType().FullName,
                        ["message"] = exception.Message,
                    };
                }
                audit?.Record(record);
            }
            catch (Exception probeException)
            {
                Logger.LogDebug($"Character-card plugin callback completion capture failed: {probeException.Message}");
            }
        }

        internal void HandleAssetBundleLoad(
            MethodBase method,
            object[] args,
            object result,
            Exception exception
        )
        {
            if (!ShouldTraceAssetBundleLoads())
            {
                return;
            }

            try
            {
                audit?.Record(new Dictionary<string, object>
                {
                    ["recordType"] = "asset_bundle_load",
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["threadId"] = Thread.CurrentThread.ManagedThreadId,
                    ["method"] = method == null ? "" : method.ToString(),
                    ["arguments"] = AuditValue.CaptureArguments(args),
                    ["result"] = AuditValue.CaptureUnityObject(result),
                    ["exception"] = exception == null ? null : exception.Message,
                    ["harmonyOwners"] = method == null ? new List<object>() : HarmonyOwnerReader.Read(method),
                });
            }
            catch (Exception probeException)
            {
                Logger.LogDebug($"Character-card probe AssetBundle capture failed: {probeException.Message}");
            }
        }

        private void ScheduleSceneCaptures(string methodName, bool completed)
        {
            if (!completed)
            {
                return;
            }

            scheduledCaptures.Add(new ScheduledCapture(frame + 1, methodName + ":frame+1"));
            scheduledCaptures.Add(new ScheduledCapture(frame + 10, methodName + ":frame+10"));
            scheduledCaptures.Add(new ScheduledCapture(frame + 30, methodName + ":frame+30"));
        }

        private void CaptureCurrentScene(string trigger)
        {
            try
            {
                audit.Record(SceneCapture.Capture(trigger, frame, Logger));
            }
            catch (Exception exception)
            {
                Logger.LogWarning($"Could not capture character scene state: {exception.Message}");
                audit.Record(new Dictionary<string, object>
                {
                    ["recordType"] = "scene_snapshot_error",
                    ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                    ["trigger"] = trigger,
                    ["error"] = exception.ToString(),
                });
            }
        }

        private string ResolveOutputPath(string configuredPath)
        {
            if (string.IsNullOrWhiteSpace(configuredPath))
            {
                configuredPath = Path.Combine(Paths.ConfigPath, "StarManager.CharacterCardReadProbe.jsonl");
            }

            return Path.IsPathRooted(configuredPath)
                ? configuredPath
                : Path.Combine(Paths.GameRootPath, configuredPath);
        }

        private static List<object> GetLoadedPlugins()
        {
            var plugins = new List<object>();
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    foreach (Type type in assembly.GetTypes())
                    {
                        foreach (object attribute in type.GetCustomAttributes(false))
                        {
                            if (attribute == null || attribute.GetType().FullName != "BepInEx.BepInPlugin")
                            {
                                continue;
                            }

                            plugins.Add(new Dictionary<string, object>
                            {
                                ["guid"] = ReflectionValue.Read(attribute, "GUID"),
                                ["name"] = ReflectionValue.Read(attribute, "Name"),
                                ["version"] = ReflectionValue.Read(attribute, "Version"),
                                ["assembly"] = assembly.GetName().Name,
                                ["type"] = type.FullName,
                            });
                        }
                    }
                }
                catch
                {
                    // A partially loaded third-party assembly must not prevent
                    // the independent probe from starting.
                }
            }

            return plugins;
        }

        private static double ElapsedMilliseconds(long startTimestamp)
        {
            return Math.Round(
                (Stopwatch.GetTimestamp() - startTimestamp) * 1000d / Stopwatch.Frequency,
                3
            );
        }

        private void OnDestroy()
        {
            if (server != null)
            {
                server.Stop();
                server = null;
            }

            if (harmony != null)
            {
                harmony.UnpatchSelf();
                harmony = null;
            }

            scheduledCaptures.Clear();
            audit = null;
            Instance = null;
        }

        private sealed class ScheduledCapture
        {
            internal readonly int DueFrame;
            internal readonly string Trigger;

            internal ScheduledCapture(int dueFrame, string trigger)
            {
                DueFrame = dueFrame;
                Trigger = trigger;
            }
        }
    }

    internal sealed class MethodInvocation
    {
        internal readonly long StartTimestamp;
        internal readonly Dictionary<string, object> Before;

        internal MethodInvocation(long startTimestamp, Dictionary<string, object> before)
        {
            StartTimestamp = startTimestamp;
            Before = before;
        }

        internal bool Pushed { get; set; }
    }

    [HarmonyPatch]
    internal static class CardReadProbePatches
    {
        [ThreadStatic]
        private static Stack<MethodInvocation> invocationStack;

        internal static IEnumerable<MethodBase> TargetMethods()
        {
            var types = new[] { typeof(ChaFile), typeof(ChaFileControl), typeof(ChaControl) };
            var names = new HashSet<string>(StringComparer.Ordinal)
            {
                "LoadFile",
                "LoadFileLimited",
                "LoadCharaFile",
                "LoadFromBytes",
                "Reload",
                "ReloadAsync",
                "ChangeNowCoordinate",
                "ChangeClothes",
                "ChangeAccessory",
                "ChangeHair",
            };
            var seen = new HashSet<MethodBase>();

            foreach (Type type in types)
            {
                MethodInfo[] methods = type.GetMethods(
                    BindingFlags.Public
                        | BindingFlags.NonPublic
                        | BindingFlags.Instance
                        | BindingFlags.Static
                );
                foreach (MethodInfo method in methods)
                {
                    if (method.IsSpecialName
                        || method.ContainsGenericParameters
                        || !names.Contains(method.Name)
                        || !seen.Add(method))
                    {
                        continue;
                    }

                    yield return method;
                }
            }
        }

        [HarmonyPrefix]
        private static void Prefix(
            MethodBase __originalMethod,
            object __instance,
            object[] __args,
            ref MethodInvocation __state
        )
        {
            if (__originalMethod.DeclaringType == typeof(AssetBundle))
            {
                return;
            }

            Dictionary<string, object> before = null;
            try
            {
                CharacterCardReadProbePlugin plugin = CharacterCardReadProbePlugin.Instance;
                if (plugin != null && plugin.ConfiguredCaptureMethodState() && __instance is ChaFile)
                {
                    before = AuditValue.CaptureChaFile((ChaFile)__instance);
                }
            }
            catch
            {
                before = null;
            }

            __state = new MethodInvocation(Stopwatch.GetTimestamp(), before);
            try
            {
                invocationStack = invocationStack ?? new Stack<MethodInvocation>();
                invocationStack.Push(__state);
                __state.Pushed = true;
            }
            catch
            {
                // The call still proceeds without timing-stack bookkeeping.
            }
        }

        [HarmonyFinalizer]
        private static Exception Finalizer(
            MethodBase __originalMethod,
            object __instance,
            object[] __args,
            MethodInvocation __state,
            Exception __exception
        )
        {
            if (__originalMethod.DeclaringType == typeof(AssetBundle))
            {
                return __exception;
            }

            try
            {
                if (__state != null && __state.Pushed && invocationStack != null && invocationStack.Count > 0)
                {
                    invocationStack.Pop();
                }

                CharacterCardReadProbePlugin.Instance?.HandleMethod(
                    __originalMethod,
                    __instance,
                    __args,
                    __state,
                    __exception
                );
            }
            catch
            {
                // An audit failure must never alter the game's card-loading result.
            }
            return __exception;
        }

    }

    internal sealed class PluginCallbackTarget
    {
        internal MethodBase Method { get; set; }
        internal string Plugin { get; set; }
        internal string PluginGuid { get; set; }
        internal string ExtensionDataId { get; set; }
        internal string CallbackKind { get; set; }

        internal Dictionary<string, object> Describe()
        {
            return new Dictionary<string, object>
            {
                ["plugin"] = Plugin,
                ["pluginGuid"] = PluginGuid,
                ["extensionDataId"] = ExtensionDataId,
                ["callbackKind"] = CallbackKind,
                ["type"] = Method == null || Method.DeclaringType == null
                    ? ""
                    : Method.DeclaringType.FullName,
                ["method"] = Method == null ? "" : Method.ToString(),
            };
        }
    }

    internal sealed class PluginCallbackInvocation
    {
        internal readonly long StartTimestamp;
        internal readonly PluginCallbackTarget Target;

        internal PluginCallbackInvocation(long startTimestamp, PluginCallbackTarget target)
        {
            StartTimestamp = startTimestamp;
            Target = target;
        }
    }

    internal static class PluginCallbackObserver
    {
        private static readonly Dictionary<MethodBase, PluginCallbackTarget> patchedTargets =
            new Dictionary<MethodBase, PluginCallbackTarget>();
        private static readonly List<object> patchErrors = new List<object>();

        internal static int PatchedCount
        {
            get
            {
                lock (patchedTargets)
                {
                    return patchedTargets.Count;
                }
            }
        }

        internal static List<PluginCallbackTarget> Patch(Harmony harmony)
        {
            var discovered = DiscoverTargets().ToList();
            foreach (PluginCallbackTarget target in discovered)
            {
                if (target == null || target.Method == null)
                {
                    continue;
                }

                lock (patchedTargets)
                {
                    if (patchedTargets.ContainsKey(target.Method))
                    {
                        continue;
                    }
                }

                try
                {
                    harmony.Patch(
                        target.Method,
                        prefix: new HarmonyMethod(
                            typeof(PluginCallbackObserver),
                            nameof(CallbackPrefix)
                        ),
                        finalizer: new HarmonyMethod(
                            typeof(PluginCallbackObserver),
                            nameof(CallbackFinalizer)
                        )
                    );
                    lock (patchedTargets)
                    {
                        patchedTargets[target.Method] = target;
                    }
                }
                catch (Exception exception)
                {
                    lock (patchErrors)
                    {
                        patchErrors.Add(new Dictionary<string, object>
                        {
                            ["plugin"] = target.Plugin,
                            ["type"] = target.Method.DeclaringType == null
                                ? ""
                                : target.Method.DeclaringType.FullName,
                            ["method"] = target.Method.ToString(),
                            ["error"] = exception.GetBaseException().Message,
                        });
                    }
                }
            }

            return discovered;
        }

        internal static List<object> DescribeTargets()
        {
            var output = new List<object>();
            lock (patchedTargets)
            {
                foreach (PluginCallbackTarget target in patchedTargets.Values)
                {
                    output.Add(target.Describe());
                }
            }
            lock (patchErrors)
            {
                output.AddRange(patchErrors.Select(item => new Dictionary<string, object>
                {
                    ["status"] = "error",
                    ["value"] = item,
                }));
            }
            return output;
        }

        private static IEnumerable<PluginCallbackTarget> DiscoverTargets()
        {
            foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                string assemblyName;
                try
                {
                    assemblyName = assembly.GetName().Name;
                }
                catch
                {
                    continue;
                }

                string plugin;
                string pluginGuid;
                string extensionDataId;
                string typeName;
                HashSet<string> callbackNames;
                if (string.Equals(assemblyName, "HS2ABMX", StringComparison.OrdinalIgnoreCase))
                {
                    plugin = "ABMX";
                    pluginGuid = "KKABMX";
                    extensionDataId = "KKABMPlugin.ABMData";
                    typeName = "KKABMX.Core.BoneController";
                    callbackNames = new HashSet<string>(StringComparer.Ordinal)
                    {
                        "OnReload",
                    };
                }
                else if (string.Equals(assemblyName, "HS2_OverlayMods", StringComparison.OrdinalIgnoreCase))
                {
                    plugin = "KSOX";
                    pluginGuid = "KSOX";
                    extensionDataId = "KSOX";
                    typeName = "KoiSkinOverlayX.KoiSkinOverlayController";
                    callbackNames = new HashSet<string>(StringComparer.Ordinal)
                    {
                        "OnChaFileLoaded",
                        "OnCoordinateBeingLoaded",
                        "OnReload",
                    };
                }
                else
                {
                    continue;
                }

                Type type = null;
                try
                {
                    type = assembly.GetType(typeName, false);
                }
                catch
                {
                    // A plugin with unavailable Unity dependencies can be skipped.
                }
                if (type == null)
                {
                    continue;
                }

                MethodInfo[] methods;
                try
                {
                    methods = type.GetMethods(
                        BindingFlags.Public
                            | BindingFlags.NonPublic
                            | BindingFlags.Instance
                            | BindingFlags.Static
                            | BindingFlags.DeclaredOnly
                    );
                }
                catch
                {
                    continue;
                }

                foreach (MethodInfo method in methods)
                {
                    if (method.IsSpecialName
                        || method.ContainsGenericParameters
                        || !callbackNames.Contains(method.Name))
                    {
                        continue;
                    }

                    yield return new PluginCallbackTarget
                    {
                        Method = method,
                        Plugin = plugin,
                        PluginGuid = pluginGuid,
                        ExtensionDataId = extensionDataId,
                        CallbackKind = method.Name,
                    };
                }
            }
        }

        private static void CallbackPrefix(
            MethodBase __originalMethod,
            object __instance,
            object[] __args,
            ref PluginCallbackInvocation __state
        )
        {
            PluginCallbackTarget target;
            lock (patchedTargets)
            {
                patchedTargets.TryGetValue(__originalMethod, out target);
            }
            if (target == null)
            {
                return;
            }

            __state = new PluginCallbackInvocation(Stopwatch.GetTimestamp(), target);
            CharacterCardReadProbePlugin.Instance?.HandlePluginCallbackStarted(
                target,
                __originalMethod,
                __instance,
                __args,
                __state
            );
        }

        private static Exception CallbackFinalizer(
            MethodBase __originalMethod,
            object __instance,
            object[] __args,
            PluginCallbackInvocation __state,
            Exception __exception
        )
        {
            if (__state != null)
            {
                CharacterCardReadProbePlugin.Instance?.HandlePluginCallbackCompleted(
                    __state.Target,
                    __originalMethod,
                    __instance,
                    __args,
                    __state,
                    __exception
                );
            }
            return __exception;
        }
    }

    [HarmonyPatch]
    internal static class AssetBundleReadPatches
    {
        internal static IEnumerable<MethodBase> TargetMethods()
        {
            var names = new HashSet<string>(StringComparer.Ordinal)
            {
                "LoadAsset",
                "LoadAssetAsync",
                "LoadAllAssets",
                "LoadAllAssetsAsync",
            };
            foreach (MethodInfo method in typeof(AssetBundle).GetMethods(
                BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance
            ))
            {
                if (!method.IsSpecialName
                    && !method.ContainsGenericParameters
                    && names.Contains(method.Name))
                {
                    yield return method;
                }
            }
        }

        [HarmonyPostfix]
        private static void Postfix(
            MethodBase __originalMethod,
            object[] __args,
            object __result
        )
        {
            CharacterCardReadProbePlugin.Instance?.HandleAssetBundleLoad(
                __originalMethod,
                __args,
                __result,
                null
            );
        }

        [HarmonyFinalizer]
        private static Exception Finalizer(
            MethodBase __originalMethod,
            object[] __args,
            Exception __exception
        )
        {
            if (__exception != null)
            {
                CharacterCardReadProbePlugin.Instance?.HandleAssetBundleLoad(
                    __originalMethod,
                    __args,
                    null,
                    __exception
                );
            }

            return __exception;
        }
    }

    internal sealed class CardReadAudit
    {
        private const int MaxRecentRecords = 128;
        private readonly ManualLogSource logger;
        private readonly object sync = new object();
        private readonly LinkedList<RecentRecord> recentRecords = new LinkedList<RecentRecord>();
        private int sequence;
        private string lastRecordUtc;

        internal string Path { get; }

        internal CardReadAudit(ManualLogSource logger, string path)
        {
            this.logger = logger;
            Path = path;
        }

        internal void RecordSession(
            List<MethodBase> targets,
            List<object> plugins,
            List<object> pluginCallbackTargets
        )
        {
            Record(new Dictionary<string, object>
            {
                ["recordType"] = "session_started",
                ["schemaVersion"] = 1,
                ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                ["probe"] = new Dictionary<string, object>
                {
                    ["guid"] = CharacterCardReadProbePlugin.PluginGuid,
                    ["name"] = CharacterCardReadProbePlugin.PluginName,
                    ["version"] = CharacterCardReadProbePlugin.PluginVersion,
                },
                ["patchedMethods"] = targets.Select(item => item.ToString()).ToList(),
                ["loadedBepInExPlugins"] = plugins,
                ["pluginCallbackTargets"] = pluginCallbackTargets,
            });
        }

        internal void Record(Dictionary<string, object> record)
        {
            if (record == null)
            {
                return;
            }

            record["sequence"] = Interlocked.Increment(ref sequence);
            try
            {
                string directory = System.IO.Path.GetDirectoryName(Path);
                if (!string.IsNullOrEmpty(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                string json = JsonUtil.Serialize(record);
                lock (sync)
                {
                    File.AppendAllText(Path, json + Environment.NewLine, new UTF8Encoding(false));
                    recentRecords.AddLast(
                        new RecentRecord(
                            json,
                            record.ContainsKey("recordType")
                                ? Convert.ToString(record["recordType"], CultureInfo.InvariantCulture)
                                : string.Empty
                        )
                    );
                    while (recentRecords.Count > MaxRecentRecords)
                    {
                        recentRecords.RemoveFirst();
                    }
                    lastRecordUtc = record.ContainsKey("utc")
                        ? Convert.ToString(record["utc"], CultureInfo.InvariantCulture)
                        : lastRecordUtc;
                }
            }
            catch (Exception exception)
            {
                logger?.LogWarning($"Could not write probe output: {exception.Message}");
            }
        }

        internal string StatusJson(int port)
        {
            int recentCount;
            string latestUtc;
            lock (sync)
            {
                recentCount = recentRecords.Count;
                latestUtc = lastRecordUtc;
            }

            return JsonUtil.Serialize(new Dictionary<string, object>
            {
                ["ok"] = true,
                ["plugin"] = new Dictionary<string, object>
                {
                    ["guid"] = CharacterCardReadProbePlugin.PluginGuid,
                    ["name"] = CharacterCardReadProbePlugin.PluginName,
                    ["version"] = CharacterCardReadProbePlugin.PluginVersion,
                },
                ["outputPath"] = Path,
                ["sequence"] = Volatile.Read(ref sequence),
                ["recentRecordCount"] = recentCount,
                ["maxRecentRecords"] = MaxRecentRecords,
                ["lastRecordUtc"] = latestUtc,
                ["api"] = new Dictionary<string, object>
                {
                    ["host"] = "127.0.0.1",
                    ["port"] = port,
                    ["endpoints"] = new[]
                    {
                        "GET /api/status",
                        "GET /api/records?limit=50",
                        "GET /api/logs?recordType=method_call&limit=50",
                        "POST /api/snapshot",
                    },
                },
            });
        }

        internal string RecentRecordsJson(int limit, string recordType)
        {
            var selected = new List<string>();
            lock (sync)
            {
                LinkedListNode<RecentRecord> node = recentRecords.Last;
                while (node != null && selected.Count < limit)
                {
                    RecentRecord record = node.Value;
                    if (string.IsNullOrWhiteSpace(recordType)
                        || string.Equals(record.RecordType, recordType, StringComparison.OrdinalIgnoreCase))
                    {
                        selected.Add(record.Json);
                    }
                    node = node.Previous;
                }
            }

            var body = new StringBuilder("{\"ok\":true,\"count\":");
            body.Append(selected.Count.ToString(CultureInfo.InvariantCulture));
            body.Append(",\"records\":[");
            for (int index = 0; index < selected.Count; index++)
            {
                if (index > 0)
                {
                    body.Append(',');
                }
                body.Append(selected[index]);
            }
            body.Append("]}");
            return body.ToString();
        }

        private sealed class RecentRecord
        {
            internal readonly string Json;
            internal readonly string RecordType;

            internal RecentRecord(string json, string recordType)
            {
                Json = json;
                RecordType = recordType;
            }
        }
    }

    internal static class AuditValue
    {
        private static readonly string[] CardSections =
        {
            "custom",
            "coordinate",
            "parameter",
            "parameter2",
            "gameinfo",
            "gameinfo2",
            "status",
            "coordinateBath",
            "coordinatePajamas",
        };

        internal static Dictionary<string, object> CaptureChaFile(ChaFile file)
        {
            var result = new Dictionary<string, object>
            {
                ["type"] = file == null ? "" : file.GetType().FullName,
                ["identity"] = CaptureInstance(file),
                ["scalars"] = new Dictionary<string, object>(),
                ["sections"] = new Dictionary<string, object>(),
            };
            var scalars = (Dictionary<string, object>)result["scalars"];
            var sections = (Dictionary<string, object>)result["sections"];
            if (file == null)
            {
                return result;
            }

            foreach (string name in new[]
            {
                "charaFileName",
                "loadProductNo",
                "loadVersion",
                "language",
                "userID",
                "dataID",
                "lastLoadErrorCode",
            })
            {
                object value = ReflectionValue.Read(file, name);
                if (value != null)
                {
                    scalars[name] = Scalar(value);
                }
            }

            foreach (string sectionName in CardSections)
            {
                object section = ReflectionValue.Read(file, sectionName);
                sections[sectionName] = CaptureSection(section);
            }

            object pngData = ReflectionValue.Read(file, "pngData");
            sections["pngData"] = CaptureSection(pngData);
            result["extendedSave"] = ExtendedSaveReader.Capture(file);
            return result;
        }

        internal static List<object> FindChangedSections(
            Dictionary<string, object> before,
            Dictionary<string, object> after
        )
        {
            var changed = new List<object>();
            Dictionary<string, object> beforeSections = GetDictionary(before, "sections");
            Dictionary<string, object> afterSections = GetDictionary(after, "sections");
            foreach (string key in beforeSections.Keys.Union(afterSections.Keys).OrderBy(item => item))
            {
                string beforeHash = GetString(GetDictionary(beforeSections, key), "fingerprint");
                string afterHash = GetString(GetDictionary(afterSections, key), "fingerprint");
                if (!string.Equals(beforeHash, afterHash, StringComparison.Ordinal))
                {
                    changed.Add(key);
                }
            }

            return changed;
        }

        internal static List<object> CaptureArguments(object[] args)
        {
            var output = new List<object>();
            if (args == null)
            {
                return output;
            }

            foreach (object arg in args)
            {
                if (arg is byte[] bytes)
                {
                    output.Add(new Dictionary<string, object>
                    {
                        ["type"] = "System.Byte[]",
                        ["length"] = bytes.Length,
                        ["sha256"] = HashBytes(bytes),
                    });
                }
                else if (arg is string || arg == null || arg.GetType().IsPrimitive || arg is Enum)
                {
                    output.Add(Scalar(arg));
                }
                else
                {
                    output.Add(new Dictionary<string, object>
                    {
                        ["type"] = arg.GetType().FullName,
                        ["value"] = arg.ToString(),
                    });
                }
            }

            return output;
        }

        internal static Dictionary<string, object> CaptureInstance(object instance)
        {
            if (instance == null)
            {
                return new Dictionary<string, object> { ["type"] = "null" };
            }

            var result = new Dictionary<string, object>
            {
                ["type"] = instance.GetType().FullName,
            };
            if (instance is ChaFile file)
            {
                result["charaFileName"] = ReflectionValue.Read(file, "charaFileName");
                result["sex"] = ReflectionValue.Read(ReflectionValue.Read(file, "parameter"), "sex");
            }
            if (instance is Component component)
            {
                result["instanceId"] = component.GetInstanceID();
                result["gameObject"] = component.gameObject == null ? null : component.gameObject.name;
            }
            return result;
        }

        internal static Dictionary<string, object> CapturePluginCallbackContext(
            PluginCallbackTarget target,
            object instance
        )
        {
            var result = new Dictionary<string, object>
            {
                ["plugin"] = target == null ? "" : target.Plugin,
                ["extensionDataId"] = target == null ? "" : target.ExtensionDataId,
            };

            if (instance == null)
            {
                return result;
            }

            var state = new Dictionary<string, object>();
            string[] stateNames = target != null && string.Equals(target.Plugin, "ABMX", StringComparison.Ordinal)
                ? new[] { "ModifierDict", "Modifiers", "NeedsFullRefresh", "NeedsBaselineUpdate" }
                : new[] { "OverlayStorage", "AdditionalTextures" };
            foreach (string stateName in stateNames)
            {
                object value = ReflectionValue.Read(instance, stateName);
                if (value != null)
                {
                    state[stateName] = CaptureSection(value);
                }
            }
            result["pluginState"] = state;

            foreach (string memberName in new[]
            {
                "ChaControl",
                "chaControl",
                "_chaControl",
                "ChaCtrl",
                "chaCtrl",
                "_ctrl",
                "Character",
                "character",
                "_character",
            })
            {
                object related = ReflectionValue.Read(instance, memberName);
                if (related is ChaControl control)
                {
                    result["chaControl"] = CaptureInstance(control);
                    foreach (string fileMemberName in new[] { "chaFile", "fileParam", "FileParam" })
                    {
                        object fileValue = ReflectionValue.Read(control, fileMemberName);
                        if (fileValue is ChaFile file)
                        {
                            result["chaFile"] = CaptureInstance(file);
                            result["extendedSave"] = ExtendedSaveReader.Capture(file);
                            return result;
                        }
                    }
                }
                else if (related is ChaFile file)
                {
                    result["chaFile"] = CaptureInstance(file);
                    result["extendedSave"] = ExtendedSaveReader.Capture(file);
                    return result;
                }
            }

            return result;
        }

        internal static Dictionary<string, object> CaptureUnityObject(object value)
        {
            if (value == null)
            {
                return new Dictionary<string, object> { ["type"] = "null" };
            }

            var result = new Dictionary<string, object>
            {
                ["type"] = value.GetType().FullName,
            };
            if (value is Object unityObject)
            {
                result["instanceId"] = unityObject.GetInstanceID();
                result["name"] = unityObject.name;
            }
            if (value is Texture texture)
            {
                result["width"] = texture.width;
                result["height"] = texture.height;
            }
            return result;
        }

        private static Dictionary<string, object> CaptureSection(object value)
        {
            if (value == null)
            {
                return new Dictionary<string, object>
                {
                    ["type"] = "null",
                    ["fingerprint"] = HashText("null"),
                };
            }

            object inspected = Inspect(value, 0, new HashSet<object>(ReferenceComparer.Instance));
            string serialized = JsonUtil.Serialize(inspected);
            return new Dictionary<string, object>
            {
                ["type"] = value.GetType().FullName,
                ["fingerprint"] = HashText(serialized),
                ["value"] = inspected,
            };
        }

        private static object Inspect(object value, int depth, HashSet<object> visited)
        {
            if (value == null)
            {
                return null;
            }
            if (value is string || value.GetType().IsPrimitive || value is decimal || value is DateTime || value is Enum)
            {
                return Scalar(value);
            }
            if (value is byte[] bytes)
            {
                return new Dictionary<string, object>
                {
                    ["kind"] = "bytes",
                    ["length"] = bytes.Length,
                    ["sha256"] = HashBytes(bytes),
                };
            }
            if (value is Object unityObject)
            {
                return CaptureUnityObject(unityObject);
            }
            if (depth >= 3)
            {
                return new Dictionary<string, object>
                {
                    ["kind"] = "depth-limit",
                    ["type"] = value.GetType().FullName,
                };
            }
            if (!value.GetType().IsValueType && !visited.Add(value))
            {
                return new Dictionary<string, object>
                {
                    ["kind"] = "cycle",
                    ["type"] = value.GetType().FullName,
                };
            }

            if (value is Array array)
            {
                var output = new Dictionary<string, object>
                {
                    ["kind"] = "array",
                    ["type"] = value.GetType().FullName,
                    ["length"] = array.Length,
                    ["sha256"] = HashArray(array),
                };
                var sample = new List<object>();
                int count = Math.Min(array.Length, 12);
                for (int index = 0; index < count; index++)
                {
                    sample.Add(Inspect(array.GetValue(index), depth + 1, visited));
                }
                output["sample"] = sample;
                return output;
            }

            if (value is IDictionary dictionary)
            {
                var output = new Dictionary<string, object>
                {
                    ["kind"] = "dictionary",
                    ["type"] = value.GetType().FullName,
                    ["count"] = dictionary.Count,
                };
                var keys = new List<object>();
                foreach (object key in dictionary.Keys)
                {
                    if (keys.Count >= 64)
                    {
                        break;
                    }
                    keys.Add(Scalar(key));
                }
                output["keys"] = keys;
                return output;
            }

            var objectOutput = new Dictionary<string, object>
            {
                ["kind"] = "object",
                ["type"] = value.GetType().FullName,
                ["members"] = new Dictionary<string, object>(),
            };
            var members = (Dictionary<string, object>)objectOutput["members"];
            int memberCount = 0;
            foreach (MemberInfo member in ReflectionValue.EnumerateMembers(value.GetType()))
            {
                if (memberCount >= 80)
                {
                    break;
                }
                object memberValue = ReflectionValue.Read(value, member.Name);
                if (memberValue == null && member.MemberType != MemberTypes.Field && member.MemberType != MemberTypes.Property)
                {
                    continue;
                }
                members[member.Name] = Inspect(memberValue, depth + 1, visited);
                memberCount++;
            }
            objectOutput["memberCount"] = memberCount;
            return objectOutput;
        }

        private static object Scalar(object value)
        {
            if (value == null)
            {
                return null;
            }
            if (value is Enum)
            {
                return value.ToString();
            }
            if (value is Version)
            {
                return value.ToString();
            }
            if (value is IFormattable formattable)
            {
                return formattable.ToString(null, CultureInfo.InvariantCulture);
            }
            return value.ToString();
        }

        private static string HashArray(Array array)
        {
            var builder = new StringBuilder();
            builder.Append(array.GetType().FullName).Append('|').Append(array.Length).Append('|');
            foreach (object value in array)
            {
                builder.Append(Scalar(value)).Append(';');
            }
            return HashText(builder.ToString());
        }

        private static string HashBytes(byte[] bytes)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
            }
        }

        private static string HashText(string value)
        {
            return HashBytes(Encoding.UTF8.GetBytes(value ?? ""));
        }

        private static Dictionary<string, object> GetDictionary(Dictionary<string, object> source, string key)
        {
            if (source != null && source.TryGetValue(key, out object value) && value is Dictionary<string, object> dictionary)
            {
                return dictionary;
            }
            return new Dictionary<string, object>();
        }

        private static string GetString(Dictionary<string, object> source, string key)
        {
            return source != null && source.TryGetValue(key, out object value) ? value as string : null;
        }
    }

    internal static class SceneCapture
    {
        private static readonly string[] TexturePropertyNames =
        {
            "_MainTex",
            "_BaseMap",
            "_BaseColorMap",
            "_BumpMap",
            "_NormalMap",
            "_MatcapTex",
            "_DetailAlbedoMap",
            "_ColorMap",
            "_AlphaMap",
            "_OutlineTex",
        };

        internal static Dictionary<string, object> Capture(
            string trigger,
            int frame,
            ManualLogSource logger
        )
        {
            var record = new Dictionary<string, object>
            {
                ["recordType"] = "scene_snapshot",
                ["utc"] = DateTime.UtcNow.ToString("O", CultureInfo.InvariantCulture),
                ["frame"] = frame,
                ["trigger"] = trigger,
                ["characters"] = new List<object>(),
            };
            var characters = (List<object>)record["characters"];
            var seen = new HashSet<int>();
            foreach (ChaControl character in Resources.FindObjectsOfTypeAll<ChaControl>())
            {
                if (character == null || !seen.Add(character.GetInstanceID()))
                {
                    continue;
                }

                try
                {
                    characters.Add(CaptureCharacter(character));
                }
                catch (Exception exception)
                {
                    logger?.LogDebug($"Could not inspect character {character.name}: {exception.Message}");
                }
            }
            record["characterCount"] = characters.Count;
            return record;
        }

        private static Dictionary<string, object> CaptureCharacter(ChaControl character)
        {
            GameObject root = ReflectionValue.Read(character, "objTop") as GameObject;
            if (root == null)
            {
                root = character.gameObject;
            }
            Transform rootTransform = root == null ? character.transform : root.transform;
            SkinnedMeshRenderer[] skinnedMeshes = root == null
                ? character.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                : root.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            Renderer[] renderers = root == null
                ? character.GetComponentsInChildren<Renderer>(true)
                : root.GetComponentsInChildren<Renderer>(true);

            var bones = new List<object>();
            var seenBones = new HashSet<int>();
            var textures = new List<object>();
            var seenTextures = new HashSet<int>();
            var rendererRecords = new List<object>();
            var boneSignatures = new StringBuilder();
            var textureSignatures = new StringBuilder();

            foreach (SkinnedMeshRenderer skin in skinnedMeshes)
            {
                if (skin == null)
                {
                    continue;
                }

                Mesh mesh = skin.sharedMesh;
                var skinRecord = new Dictionary<string, object>
                {
                    ["gameObject"] = GetPath(skin.transform, rootTransform),
                    ["mesh"] = mesh == null ? null : mesh.name,
                    ["vertexCount"] = mesh == null ? 0 : mesh.vertexCount,
                    ["bindPoseCount"] = mesh == null ? 0 : mesh.bindposes.Length,
                    ["boneCount"] = skin.bones == null ? 0 : skin.bones.Length,
                    ["rootBone"] = skin.rootBone == null ? null : GetPath(skin.rootBone, rootTransform),
                };
                rendererRecords.Add(skinRecord);
                if (skin.bones != null)
                {
                    foreach (Transform bone in skin.bones)
                    {
                        if (bone == null || !seenBones.Add(bone.GetInstanceID()))
                        {
                            continue;
                        }
                        string path = GetPath(bone, rootTransform);
                        Dictionary<string, object> boneRecord = CaptureBone(bone, path, rootTransform);
                        bones.Add(boneRecord);
                        boneSignatures.Append(JsonUtil.Serialize(boneRecord)).Append('|');
                    }
                }
            }

            foreach (Renderer renderer in renderers)
            {
                if (renderer == null)
                {
                    continue;
                }
                var rendererRecord = new Dictionary<string, object>
                {
                    ["type"] = renderer.GetType().FullName,
                    ["path"] = GetPath(renderer.transform, rootTransform),
                    ["materials"] = new List<object>(),
                };
                var materialRecords = (List<object>)rendererRecord["materials"];
                Material[] materials = renderer.sharedMaterials;
                foreach (Material material in materials ?? new Material[0])
                {
                    if (material == null)
                    {
                        materialRecords.Add(null);
                        continue;
                    }
                    Dictionary<string, object> materialRecord = CaptureMaterial(material, textures, seenTextures, textureSignatures);
                    materialRecords.Add(materialRecord);
                }
                rendererRecords.Add(rendererRecord);
            }

            var result = new Dictionary<string, object>
            {
                ["instanceId"] = character.GetInstanceID(),
                ["name"] = character.name,
                ["sex"] = ReflectionValue.Read(character.chaFile == null ? null : ReflectionValue.Read(character.chaFile, "parameter"), "sex"),
                ["cardFileName"] = character.chaFile == null ? null : ReflectionValue.Read(character.chaFile, "charaFileName"),
                ["root"] = root == null ? null : root.name,
                ["transformCount"] = root == null ? 0 : root.GetComponentsInChildren<Transform>(true).Length,
                ["bones"] = bones,
                ["boneCount"] = bones.Count,
                ["boneSha256"] = HashText(boneSignatures.ToString()),
                ["renderers"] = rendererRecords,
                ["rendererCount"] = rendererRecords.Count,
                ["textures"] = textures,
                ["textureCount"] = textures.Count,
                ["textureSha256"] = HashText(textureSignatures.ToString()),
                ["interestingComponents"] = CaptureInterestingComponents(root),
            };
            return result;
        }

        private static Dictionary<string, object> CaptureBone(Transform bone, string path, Transform root)
        {
            return new Dictionary<string, object>
            {
                ["name"] = bone.name,
                ["path"] = path,
                ["parent"] = bone.parent == null ? null : GetPath(bone.parent, root),
                ["localPosition"] = Vector(bone.localPosition),
                ["localRotation"] = QuaternionValue(bone.localRotation),
                ["localScale"] = Vector(bone.localScale),
                ["active"] = bone.gameObject != null && bone.gameObject.activeInHierarchy,
            };
        }

        private static Dictionary<string, object> CaptureMaterial(
            Material material,
            List<object> textures,
            HashSet<int> seenTextures,
            StringBuilder textureSignatures
        )
        {
            var result = new Dictionary<string, object>
            {
                ["name"] = material.name,
                ["shader"] = material.shader == null ? null : material.shader.name,
                ["textures"] = new List<object>(),
            };
            var materialTextures = (List<object>)result["textures"];
            foreach (string propertyName in TexturePropertyNames)
            {
                try
                {
                    if (!material.HasProperty(propertyName))
                    {
                        continue;
                    }
                    Texture texture = material.GetTexture(propertyName);
                    Dictionary<string, object> textureInfo = AuditValue.CaptureUnityObject(texture);
                    textureInfo["property"] = propertyName;
                    materialTextures.Add(textureInfo);
                    if (texture != null && seenTextures.Add(texture.GetInstanceID()))
                    {
                        textures.Add(textureInfo);
                        textureSignatures.Append(JsonUtil.Serialize(textureInfo)).Append('|');
                    }
                }
                catch
                {
                    // A shader property can disappear while a resource bundle
                    // is being reloaded; skip only that property.
                }
            }
            return result;
        }

        private static Dictionary<string, object> CaptureInterestingComponents(GameObject root)
        {
            var counts = new Dictionary<string, object>(StringComparer.Ordinal);
            if (root == null)
            {
                return counts;
            }

            foreach (Component component in root.GetComponentsInChildren<Component>(true))
            {
                if (component == null)
                {
                    continue;
                }
                string name = component.GetType().FullName ?? component.GetType().Name;
                string lower = name.ToLowerInvariant();
                if (lower.IndexOf("bone", StringComparison.Ordinal) < 0
                    && lower.IndexOf("ik", StringComparison.Ordinal) < 0
                    && lower.IndexOf("pose", StringComparison.Ordinal) < 0
                    && lower.IndexOf("abmx", StringComparison.Ordinal) < 0
                    && lower.IndexOf("dynamic", StringComparison.Ordinal) < 0)
                {
                    continue;
                }
                counts[name] = counts.TryGetValue(name, out object value)
                    ? Convert.ToInt32(value, CultureInfo.InvariantCulture) + 1
                    : 1;
            }
            return counts;
        }

        private static Dictionary<string, object> Vector(Vector3 value)
        {
            return new Dictionary<string, object>
            {
                ["x"] = value.x,
                ["y"] = value.y,
                ["z"] = value.z,
            };
        }

        private static Dictionary<string, object> QuaternionValue(Quaternion value)
        {
            return new Dictionary<string, object>
            {
                ["x"] = value.x,
                ["y"] = value.y,
                ["z"] = value.z,
                ["w"] = value.w,
            };
        }

        private static string GetPath(Transform transform, Transform root)
        {
            if (transform == null)
            {
                return null;
            }
            var parts = new List<string>();
            Transform current = transform;
            while (current != null && current != root && parts.Count < 256)
            {
                parts.Add(current.name);
                current = current.parent;
            }
            if (root != null)
            {
                parts.Add(root.name);
            }
            parts.Reverse();
            return string.Join("/", parts);
        }

        private static string HashText(string value)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value ?? "")))
                    .Replace("-", "")
                    .ToLowerInvariant();
            }
        }
    }

    internal static class ExtendedSaveReader
    {
        internal static object Capture(ChaFile file)
        {
            if (file == null)
            {
                return new Dictionary<string, object> { ["available"] = false };
            }

            Type type = AppDomain.CurrentDomain.GetAssemblies()
                .Select(assembly => assembly.GetType("ExtensibleSaveFormat.ExtendedSave", false))
                .FirstOrDefault(item => item != null);
            if (type == null)
            {
                return new Dictionary<string, object>
                {
                    ["available"] = false,
                    ["reason"] = "ExtendedSave assembly/type not loaded",
                };
            }

            MethodInfo method = type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
                .Where(item => item.Name == "GetAllExtendedData" && !item.ContainsGenericParameters)
                .FirstOrDefault(item => item.GetParameters().Length == 1
                    && item.GetParameters()[0].ParameterType.IsAssignableFrom(file.GetType()));
            if (method == null)
            {
                return new Dictionary<string, object>
                {
                    ["available"] = false,
                    ["type"] = type.FullName,
                    ["reason"] = "GetAllExtendedData API not found",
                };
            }

            try
            {
                object value = method.Invoke(null, new object[] { file });
                return new Dictionary<string, object>
                {
                    ["available"] = true,
                    ["method"] = method.ToString(),
                    ["value"] = value == null
                        ? null
                        : JsonSafe(value),
                };
            }
            catch (Exception exception)
            {
                return new Dictionary<string, object>
                {
                    ["available"] = false,
                    ["method"] = method.ToString(),
                    ["error"] = exception.GetBaseException().Message,
                };
            }
        }

        private static object JsonSafe(object value)
        {
            if (value == null || value is string || value.GetType().IsPrimitive || value is Enum)
            {
                return value is Enum ? value.ToString() : value;
            }
            if (value is IDictionary dictionary)
            {
                var output = new Dictionary<string, object>();
                foreach (DictionaryEntry entry in dictionary)
                {
                    if (output.Count >= 128)
                    {
                        break;
                    }
                    output[Convert.ToString(entry.Key, CultureInfo.InvariantCulture)] = JsonSafe(entry.Value);
                }
                return output;
            }
            if (value is IEnumerable enumerable && !(value is byte[]))
            {
                var output = new List<object>();
                foreach (object item in enumerable)
                {
                    if (output.Count >= 128)
                    {
                        break;
                    }
                    output.Add(JsonSafe(item));
                }
                return output;
            }
            return new Dictionary<string, object>
            {
                ["type"] = value.GetType().FullName,
                ["text"] = value.ToString(),
            };
        }
    }

    internal static class HarmonyOwnerReader
    {
        internal static List<object> Read(MethodBase method)
        {
            var owners = new List<object>();
            if (method == null)
            {
                return owners;
            }

            try
            {
                MethodInfo getPatchInfo = typeof(Harmony).GetMethod(
                    "GetPatchInfo",
                    BindingFlags.Public | BindingFlags.Static,
                    null,
                    new[] { typeof(MethodBase) },
                    null
                );
                object patchInfo = getPatchInfo == null ? null : getPatchInfo.Invoke(null, new object[] { method });
                if (patchInfo == null)
                {
                    return owners;
                }

                foreach (string group in new[] { "Prefixes", "Postfixes", "Transpilers", "Finalizers" })
                {
                    IEnumerable patches = ReflectionValue.Read(patchInfo, group) as IEnumerable;
                    if (patches == null)
                    {
                        continue;
                    }
                    foreach (object patch in patches)
                    {
                        owners.Add(new Dictionary<string, object>
                        {
                            ["group"] = group,
                            ["owner"] = ReflectionValue.Read(patch, "owner"),
                            ["method"] = ReflectionValue.Read(patch, "PatchMethod")?.ToString(),
                        });
                    }
                }
            }
            catch
            {
                // Patch introspection is diagnostic-only.
            }
            return owners;
        }
    }

    internal static class ReflectionValue
    {
        internal static object Read(object instance, string name)
        {
            if (instance == null || string.IsNullOrEmpty(name))
            {
                return null;
            }
            Type type = instance.GetType();
            FieldInfo field = type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .FirstOrDefault(item => string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase));
            if (field != null)
            {
                try
                {
                    return field.GetValue(instance);
                }
                catch
                {
                    return null;
                }
            }
            PropertyInfo property = type.GetProperties(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .FirstOrDefault(item => string.Equals(item.Name, name, StringComparison.OrdinalIgnoreCase) && item.GetIndexParameters().Length == 0);
            if (property != null && property.GetMethod != null)
            {
                try
                {
                    return property.GetValue(instance, null);
                }
                catch
                {
                    return null;
                }
            }
            return null;
        }

        internal static IEnumerable<MemberInfo> EnumerateMembers(Type type)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (FieldInfo field in type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (!field.IsStatic && seen.Add(field.Name) && field.Name.IndexOf("<>", StringComparison.Ordinal) < 0)
                {
                    yield return field;
                }
            }
            foreach (PropertyInfo property in type.GetProperties(BindingFlags.Instance | BindingFlags.Public))
            {
                if (property.GetIndexParameters().Length == 0 && property.GetMethod != null && seen.Add(property.Name))
                {
                    yield return property;
                }
            }
        }
    }

    internal sealed class CharacterCardReadProbeServer
    {
        private readonly ManualLogSource logger;
        private readonly int port;
        private readonly CardReadAudit audit;
        private readonly Action requestSnapshot;
        private TcpListener listener;
        private Thread listenerThread;
        private volatile bool stopping;

        internal CharacterCardReadProbeServer(
            ManualLogSource logSource,
            int listenPort,
            CardReadAudit cardReadAudit,
            Action snapshotCallback
        )
        {
            logger = logSource;
            port = listenPort;
            audit = cardReadAudit;
            requestSnapshot = snapshotCallback;
        }

        internal void Start()
        {
            if (port < 1 || port > 65535)
            {
                throw new ArgumentOutOfRangeException(nameof(port), "HTTP port must be between 1 and 65535.");
            }

            listener = new TcpListener(IPAddress.Loopback, port);
            listener.Start();
            listenerThread = new Thread(ListenLoop)
            {
                IsBackground = true,
                Name = "StarManager.CharacterCardReadProbe.Http",
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
                        logger.LogWarning("Character-card probe HTTP listener stopped unexpectedly.");
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
                        logger.LogWarning($"Character-card probe HTTP listener error: {exception.Message}");
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
                        ProbeHttpRequest request = ProbeHttpRequest.Parse(ReadRequest(stream));
                        ProbeHttpResponse response = Route(request);
                        WriteResponse(stream, response);
                    }
                }
                catch (Exception exception)
                {
                    logger.LogDebug($"Character-card probe HTTP request failed: {exception.Message}");
                }
            }
        }

        private ProbeHttpResponse Route(ProbeHttpRequest request)
        {
            if (request == null)
            {
                return ProbeHttpResponse.Json(400, "{\"error\":\"Invalid HTTP request.\"}");
            }

            if (string.Equals(request.Method, "OPTIONS", StringComparison.OrdinalIgnoreCase))
            {
                return ProbeHttpResponse.NoContent(204);
            }

            if (string.Equals(request.Method, "POST", StringComparison.OrdinalIgnoreCase)
                && request.Path == "/api/snapshot")
            {
                requestSnapshot?.Invoke();
                return ProbeHttpResponse.Json(202, "{\"accepted\":true,\"message\":\"snapshot queued\"}");
            }

            if (!string.Equals(request.Method, "GET", StringComparison.OrdinalIgnoreCase))
            {
                return ProbeHttpResponse.Json(405, "{\"error\":\"Only GET and POST /api/snapshot are supported.\"}");
            }

            if (request.Path == "/api/status")
            {
                return ProbeHttpResponse.Json(200, audit.StatusJson(port));
            }

            if (request.Path == "/api/records" || request.Path == "/api/logs")
            {
                int limit = ParseLimit(request.Query);
                string recordType = null;
                request.Query?.TryGetValue("recordType", out recordType);
                return ProbeHttpResponse.Json(200, audit.RecentRecordsJson(limit, recordType));
            }

            return ProbeHttpResponse.Json(
                200,
                "{\"name\":\"Star Manager Character Card Read Probe\","
                    + "\"endpoints\":[\"/api/status\",\"/api/records?limit=50\","
                    + "\"/api/logs?recordType=method_call&limit=50\",\"POST /api/snapshot\"]}"
            );
        }

        private static int ParseLimit(Dictionary<string, string> query)
        {
            const int defaultLimit = 50;
            const int maxLimit = 128;
            string raw;
            int limit;
            return query != null
                && query.TryGetValue("limit", out raw)
                && int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out limit)
                ? Math.Max(1, Math.Min(maxLimit, limit))
                : defaultLimit;
        }

        private static string ReadRequest(NetworkStream stream)
        {
            using (var data = new MemoryStream())
            {
                var buffer = new byte[8192];
                while (data.Length < 65536)
                {
                    int read = stream.Read(buffer, 0, buffer.Length);
                    if (read <= 0)
                    {
                        break;
                    }
                    data.Write(buffer, 0, read);
                    byte[] bytes = data.ToArray();
                    if (FindHeaderEnd(bytes) >= 0)
                    {
                        break;
                    }
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

        private static void WriteResponse(NetworkStream stream, ProbeHttpResponse response)
        {
            response = response ?? ProbeHttpResponse.Json(500, "{\"error\":\"Empty response.\"}");
            byte[] body = Encoding.UTF8.GetBytes(response.Body ?? "{}");
            string headers = "HTTP/1.1 "
                + response.StatusCode.ToString(CultureInfo.InvariantCulture)
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

    internal sealed class ProbeHttpRequest
    {
        internal string Method;
        internal string Path;
        internal Dictionary<string, string> Query;

        internal static ProbeHttpRequest Parse(string raw)
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
            var query = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            foreach (string pair in (queryString ?? string.Empty).Split('&'))
            {
                if (string.IsNullOrEmpty(pair))
                {
                    continue;
                }
                int equals = pair.IndexOf('=');
                string key = equals < 0 ? pair : pair.Substring(0, equals);
                string value = equals < 0 ? string.Empty : pair.Substring(equals + 1);
                query[Decode(key)] = Decode(value);
            }

            return new ProbeHttpRequest
            {
                Method = parts[0],
                Path = path,
                Query = query,
            };
        }

        private static string Decode(string value)
        {
            try
            {
                return Uri.UnescapeDataString((value ?? string.Empty).Replace('+', ' '));
            }
            catch
            {
                return value ?? string.Empty;
            }
        }
    }

    internal sealed class ProbeHttpResponse
    {
        internal int StatusCode;
        internal string StatusText;
        internal string Body;

        internal static ProbeHttpResponse Json(int statusCode, string body)
        {
            return new ProbeHttpResponse
            {
                StatusCode = statusCode,
                StatusText = StatusTextFor(statusCode),
                Body = body ?? "{}",
            };
        }

        internal static ProbeHttpResponse NoContent(int statusCode)
        {
            return Json(statusCode, "{}");
        }

        private static string StatusTextFor(int statusCode)
        {
            switch (statusCode)
            {
                case 200:
                    return "OK";
                case 202:
                    return "Accepted";
                case 204:
                    return "No Content";
                case 400:
                    return "Bad Request";
                case 404:
                    return "Not Found";
                case 405:
                    return "Method Not Allowed";
                default:
                    return "Internal Server Error";
            }
        }
    }

    internal static class JsonUtil
    {
        internal static string Serialize(object value)
        {
            var writer = new JsonWriter();
            WriteValue(writer, value, new HashSet<object>(ReferenceComparer.Instance), 0);
            return writer.ToString();
        }

        private static void WriteValue(
            JsonWriter writer,
            object value,
            HashSet<object> activeObjects,
            int depth
        )
        {
            if (value == null)
            {
                writer.Null();
                return;
            }

            if (depth > 64)
            {
                writer.String("[max-depth]");
                return;
            }

            if (value is string || value is char)
            {
                writer.String(Convert.ToString(value, CultureInfo.InvariantCulture));
                return;
            }
            if (value is bool)
            {
                writer.Bool((bool)value);
                return;
            }
            if (value is Enum)
            {
                writer.String(value.ToString());
                return;
            }
            if (value is byte[])
            {
                writer.String(Convert.ToBase64String((byte[])value));
                return;
            }
            if (TryWriteNumber(writer, value))
            {
                return;
            }

            var dictionary = value as IDictionary;
            if (dictionary != null)
            {
                if (!activeObjects.Add(value))
                {
                    writer.String("[cycle]");
                    return;
                }
                writer.BeginObject();
                foreach (DictionaryEntry entry in dictionary)
                {
                    writer.Property(Convert.ToString(entry.Key, CultureInfo.InvariantCulture));
                    WriteValue(writer, entry.Value, activeObjects, depth + 1);
                }
                writer.EndObject();
                activeObjects.Remove(value);
                return;
            }

            var enumerable = value as IEnumerable;
            if (enumerable != null)
            {
                if (!activeObjects.Add(value))
                {
                    writer.String("[cycle]");
                    return;
                }
                writer.BeginArray();
                foreach (object item in enumerable)
                {
                    WriteValue(writer, item, activeObjects, depth + 1);
                }
                writer.EndArray();
                activeObjects.Remove(value);
                return;
            }

            writer.String(value.ToString());
        }

        private static bool TryWriteNumber(JsonWriter writer, object value)
        {
            if (!(value is byte)
                && !(value is sbyte)
                && !(value is short)
                && !(value is ushort)
                && !(value is int)
                && !(value is uint)
                && !(value is long)
                && !(value is ulong)
                && !(value is float)
                && !(value is double)
                && !(value is decimal))
            {
                return false;
            }

            double floating;
            if (value is float)
            {
                floating = (float)value;
            }
            else if (value is double)
            {
                floating = (double)value;
            }
            else
            {
                floating = 0d;
            }

            if ((value is float || value is double)
                && (double.IsNaN(floating) || double.IsInfinity(floating)))
            {
                writer.Null();
                return true;
            }

            writer.Number(((IFormattable)value).ToString(null, CultureInfo.InvariantCulture));
            return true;
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

        internal void Number(string value)
        {
            ValuePrefix();
            builder.Append(string.IsNullOrEmpty(value) ? "0" : value);
        }

        internal void Bool(bool value)
        {
            ValuePrefix();
            builder.Append(value ? "true" : "false");
        }

        internal void Null()
        {
            ValuePrefix();
            builder.Append("null");
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

    internal sealed class ReferenceComparer : IEqualityComparer<object>
    {
        internal static readonly ReferenceComparer Instance = new ReferenceComparer();

        public new bool Equals(object left, object right)
        {
            return ReferenceEquals(left, right);
        }

        public int GetHashCode(object value)
        {
            return System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(value);
        }
    }
}
