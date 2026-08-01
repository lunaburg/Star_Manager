using System;
using System.IO;

namespace StarManager.CardMetadata
{
    internal static class SaveTargetPathIdentity
    {
        internal static string NormalizeFullPath(string path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                throw new ArgumentException("A save target path is required.", nameof(path));
            }

            return Path.GetFullPath(path.Trim()).TrimEnd(
                Path.DirectorySeparatorChar,
                Path.AltDirectorySeparatorChar
            );
        }

        internal static string NormalizeFileName(string pathOrFileName)
        {
            if (string.IsNullOrWhiteSpace(pathOrFileName))
            {
                return null;
            }

            string normalized = pathOrFileName.Trim().TrimEnd('/', '\\');
            int separatorIndex = Math.Max(
                normalized.LastIndexOf('/'),
                normalized.LastIndexOf('\\')
            );
            return normalized.Substring(separatorIndex + 1);
        }

        internal static bool Matches(string targetPath, string cardPathOrFileName)
        {
            string targetName = NormalizeFileName(targetPath);
            string cardName = NormalizeFileName(cardPathOrFileName);
            return !string.IsNullOrEmpty(targetName)
                && !string.IsNullOrEmpty(cardName)
                && string.Equals(
                    targetName,
                    cardName,
                    StringComparison.OrdinalIgnoreCase
                );
        }
    }

    internal sealed class SaveTargetConsumption<T>
    {
        internal SaveTargetConsumption(
            bool wasKnown,
            bool matches,
            string targetPath,
            T value
        )
        {
            WasKnown = wasKnown;
            Matches = matches;
            TargetPath = targetPath;
            Value = value;
        }

        internal bool WasKnown { get; }

        internal bool Matches { get; }

        internal string TargetPath { get; }

        internal T Value { get; }
    }

    internal sealed class PendingSaveTarget<T>
    {
        private bool isKnown;
        private string targetPath;
        private T value;

        internal bool IsKnown => isKnown;

        internal bool TryCapture(
            string path,
            Func<T> valueFactory,
            out string normalizedPath,
            out T capturedValue
        )
        {
            if (valueFactory == null)
            {
                throw new ArgumentNullException(nameof(valueFactory));
            }

            normalizedPath = SaveTargetPathIdentity.NormalizeFullPath(path);
            if (
                isKnown
                && string.Equals(
                    targetPath,
                    normalizedPath,
                    StringComparison.OrdinalIgnoreCase
                )
            )
            {
                capturedValue = default(T);
                return false;
            }

            Clear();
            capturedValue = valueFactory();
            targetPath = normalizedPath;
            value = capturedValue;
            isKnown = true;
            return true;
        }

        internal SaveTargetConsumption<T> Consume(string cardPathOrFileName)
        {
            bool wasKnown = isKnown;
            string consumedPath = targetPath;
            bool matches = wasKnown
                && SaveTargetPathIdentity.Matches(consumedPath, cardPathOrFileName);
            T consumedValue = matches ? value : default(T);

            Clear();
            return new SaveTargetConsumption<T>(
                wasKnown,
                matches,
                consumedPath,
                consumedValue
            );
        }

        private void Clear()
        {
            isKnown = false;
            targetPath = null;
            value = default(T);
        }
    }
}
