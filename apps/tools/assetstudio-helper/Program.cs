using System.Text.Json;
using System.Text.Json.Serialization;
using AssetStudio;
using AssetObject = AssetStudio.Object;

internal static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
    };

    public static int Main(string[] args)
    {
        try
        {
            var command = CommandLine.Parse(args);
            using var session = AssetSession.Load(command.Input, command.UnityVersion);
            object result = command.Name switch
            {
                "list" => session.List(command.Type),
                "inspect" => session.Inspect(command.PathId),
                "export-raw" => session.Export(command.PathId, command.Output!, textOnly: false),
                "export-text" => session.Export(command.PathId, command.Output!, textOnly: true),
                _ => throw new CommandException($"Unsupported command: {command.Name}"),
            };
            WriteJson(new ApiResponse(true, result, null));
            return 0;
        }
        catch (CommandException ex)
        {
            WriteJson(new ApiResponse(false, null, new ApiError("invalid_arguments", ex.Message)));
            return 2;
        }
        catch (Exception ex)
        {
            WriteJson(new ApiResponse(false, null, new ApiError("assetstudio_error", ex.Message)));
            return 1;
        }
    }

    private static void WriteJson(ApiResponse response) =>
        Console.Out.WriteLine(JsonSerializer.Serialize(response, JsonOptions));
}

internal sealed class AssetSession : IDisposable
{
    private readonly AssetsManager _manager;
    private readonly Dictionary<long, AssetObject> _assets;
    private readonly Dictionary<long, string> _containers;

    private AssetSession(AssetsManager manager)
    {
        _manager = manager;
        _assets = manager.assetsFileList.SelectMany(file => file.Objects)
            .GroupBy(asset => asset.m_PathID)
            .ToDictionary(group => group.Key, group => group.First());
        _containers = BuildContainerMap(manager);
    }

    public static AssetSession Load(string input, string? unityVersion)
    {
        var fullPath = Path.GetFullPath(input);
        if (!File.Exists(fullPath))
            throw new CommandException($"Input file does not exist: {fullPath}");

        var manager = new AssetsManager { SpecifyUnityVersion = unityVersion };
        manager.LoadFiles(fullPath);
        if (manager.assetsFileList.Count == 0)
        {
            manager.Clear();
            throw new InvalidDataException("AssetStudio did not find a serialized asset file in the input.");
        }
        return new AssetSession(manager);
    }

    public object List(string? type)
    {
        var assets = _assets.Values
            .Where(asset => string.IsNullOrWhiteSpace(type) ||
                asset.type.ToString().Equals(type, StringComparison.OrdinalIgnoreCase))
            .OrderBy(asset => asset.assetsFile.fileName, StringComparer.OrdinalIgnoreCase)
            .ThenBy(asset => asset.m_PathID)
            .Select(ToSummary)
            .ToArray();
        return new { count = assets.Length, assets };
    }

    public object Inspect(long pathId)
    {
        var asset = GetAsset(pathId);
        return new
        {
            asset = ToSummary(asset),
            unityVersion = string.Join('.', asset.version),
            platform = asset.platform.ToString(),
            canExportText = asset is TextAsset,
            canExportRaw = true,
        };
    }

    public object Export(long pathId, string output, bool textOnly)
    {
        var asset = GetAsset(pathId);
        byte[] data;
        string suggestedExtension;
        if (textOnly)
        {
            if (asset is not TextAsset textAsset)
                throw new CommandException($"Asset {pathId} is {asset.type}, not TextAsset.");
            data = textAsset.m_Script;
            suggestedExtension = ".txt";
        }
        else
        {
            data = asset.GetRawData();
            suggestedExtension = ".dat";
        }

        var outputPath = Path.GetFullPath(output);
        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
        File.WriteAllBytes(outputPath, data);
        return new { path = outputPath, size = data.LongLength, suggestedExtension };
    }

    private AssetObject GetAsset(long pathId) => _assets.TryGetValue(pathId, out var asset)
        ? asset
        : throw new CommandException($"Asset Path ID was not found: {pathId}");

    private AssetSummary ToSummary(AssetObject asset) => new(
        asset.m_PathID,
        asset is NamedObject named ? named.m_Name : string.Empty,
        asset.type.ToString(),
        asset.assetsFile.fileName,
        _containers.GetValueOrDefault(asset.m_PathID, string.Empty),
        asset.byteSize);

    private static Dictionary<long, string> BuildContainerMap(AssetsManager manager)
    {
        var result = new Dictionary<long, string>();
        foreach (var bundle in manager.assetsFileList.SelectMany(file => file.Objects).OfType<AssetBundle>())
        {
            foreach (var entry in bundle.m_Container)
            {
                if (!entry.Value.asset.IsNull)
                    result.TryAdd(entry.Value.asset.m_PathID, entry.Key);
            }
        }
        return result;
    }

    public void Dispose() => _manager.Clear();
}

internal sealed record AssetSummary(long PathId, string Name, string Type, string SourceFile, string Container, uint Size);
internal sealed record ApiResponse(bool Ok, object? Result, ApiError? Error);
internal sealed record ApiError(string Code, string Message);

internal sealed class CommandLine
{
    public required string Name { get; init; }
    public required string Input { get; init; }
    public string? Output { get; init; }
    public string? Type { get; init; }
    public string? UnityVersion { get; init; }
    public long PathId { get; init; }

    public static CommandLine Parse(string[] args)
    {
        if (args.Length == 0 || args[0] is "help" or "--help" or "-h")
            throw new CommandException(Usage);
        var options = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var index = 1; index < args.Length; index += 2)
        {
            if (!args[index].StartsWith("--", StringComparison.Ordinal) || index + 1 >= args.Length)
                throw new CommandException($"Invalid option near '{args[index]}'.\n{Usage}");
            options[args[index][2..]] = args[index + 1];
        }

        var name = args[0].ToLowerInvariant();
        if (!options.TryGetValue("input", out var input))
            throw new CommandException($"--input is required.\n{Usage}");
        var needsAsset = name is "inspect" or "export-raw" or "export-text";
        if (needsAsset && (!options.TryGetValue("path-id", out var rawPathId) || !long.TryParse(rawPathId, out _)))
            throw new CommandException("--path-id must be an integer for this command.");
        var needsOutput = name is "export-raw" or "export-text";
        if (needsOutput && !options.ContainsKey("output"))
            throw new CommandException("--output is required for export commands.");

        return new CommandLine
        {
            Name = name,
            Input = input,
            Output = options.GetValueOrDefault("output"),
            Type = options.GetValueOrDefault("type"),
            UnityVersion = options.GetValueOrDefault("unity-version"),
            PathId = options.TryGetValue("path-id", out var value) ? long.Parse(value) : 0,
        };
    }

    private const string Usage = "Usage: assetstudio-helper <list|inspect|export-raw|export-text> --input <file> [--path-id <id>] [--output <file>] [--type <class>] [--unity-version <version>]";
}

internal sealed class CommandException : Exception
{
    public CommandException(string message) : base(message) { }
}
